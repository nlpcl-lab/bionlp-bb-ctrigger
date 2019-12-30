from nltk import WordNetLemmatizer

from concepts import Doc, Entity, InputItem
from sent_dep import SentDep
from triggers import TriggerMap, get_local_context_triggers
from multibytes import replace_multibytes
from modality import check_input_for_hypo_scope, check_negation_scope, check_others_scope

def check_path_for_entity(dep_path_for_entity, entity_id='', all_entities_in_sent=None, from_root=True,
						  anno_token_idx_seq=None):
	"""
	:type dep_path_for_entity: list[(int, str, str, str)]
	:type all_entities_in_sent: list[Entity]
	:return:
	"""

	if not anno_token_idx_seq:
		anno_token_idx_seq = []

	if not all_entities_in_sent:
		all_entities_in_sent = []

	for item_idx, token_item in enumerate(dep_path_for_entity):
		token_idx, token, pos, dep_label = token_item

		print '     {token_idx} {pos:3}  "{token}"{dep_label}{anno}'.format(
			token_idx=token_idx, pos=pos, token=token, dep_label=" (%s)" % dep_label if dep_label else '',
			anno=' [ANNO]' if token_idx in anno_token_idx_seq else '')

		for ent_in_sent in all_entities_in_sent:
			if ent_in_sent.get_id() == entity_id:
				continue

			if token_idx in ent_in_sent.get_token_idx_seq_in_sent():
				print '        =>', ent_in_sent


def analyze_entity_dep_path(doc_bbevent, sent_dep_list):
	"""
	:type doc_bbevent: Doc
	:type sent_dep_list: list[sent_dep.SentDep]
	"""
	doc_id = doc_bbevent.get_id()

	print
	print '=' * 20, 'DOC %s' % doc_id, '=' * 20

	for entity in doc_bbevent.iter_entities(sort_by_offset=True):
		#if not entity.get_text()

		if not entity.is_bacteria():
			continue

		if entity.is_in_title():
			sent_offset = 'T'
			#sent_text = doc_bbevent.get_title_text(refined=True)
			sent_dep = sent_dep_list[0]  # type: SentDep
		else:
			sent_offset = entity.get_sent_offset()
			#sent_text = doc_bbevent.get_sent_by_offset(sent_offset, refined=True)
			sent_dep = sent_dep_list[sent_offset+1]  # type: SentDep

		entities_in_sent = doc_bbevent.get_entities_in_sent(sent_offset)

		print '', '-' * 3, '"%s"/s%d' % (entity.get_text(), entity.get_sent_offset()), '-' * 15

		entity_token_idx_seq = entity.get_token_idx_seq_in_sent()
		head_token_idx = entity_token_idx_seq[-1]

		supp_str = 'S%s' % (str(sent_offset))

		path_from_root = sent_dep.get_path_from_root(head_token_idx, supp_str=supp_str)
		paths_to_leaves = sent_dep.get_paths_to_leaves(head_token_idx, supp_str=supp_str)

		entity_id = entity.get_id()

		print '   root ==> (s%s)' % str(sent_offset)
		check_path_for_entity(path_from_root, entity_id, entities_in_sent, from_root=True)

		for path_to_leaf in paths_to_leaves:
			print '   ==> leaf (s%s)' % str(sent_offset)
			check_path_for_entity(path_to_leaf, entity_id, entities_in_sent, from_root=False)

		#print 'STOP1!!'; exit()


def print_intra_input_pairs(input_item, doc_id, is_for_propagation=False):
	"""

	:type input_item: InputItem
	:type doc_id: str
	:type is_for_propagation: bool
	:return:
	"""
	input_id = input_item.get_id()
	is_event = input_item.is_gold_event()
	(bac_id, bac_text, bac_token_idx_seq, loc_id, loc_text, loc_token_idx_seq) = input_item.get_bac_and_loc()
	sent_offset, _ = input_item.get_sent_offsets()
	sent_dep, _ = input_item.get_sent_dep()
	bac_head_token_idx, loc_head_token_idx = input_item.get_head_token_idx_pair()
	bac_head_token = sent_dep.get_token(bac_head_token_idx)
	loc_head_token = sent_dep.get_token(loc_head_token_idx)

	print ''
	print '====' * 14
	print '       %s%s-%s ( %s/%s ) ' % (
		'Propagation for ' if is_for_propagation else ' '*9, 'EVENT' if is_event else 'PAIR', input_id, doc_id, str(sent_offset),)
	print '====' * 14

	bac_text_replaced, _ = replace_multibytes(bac_text)
	bac_head_token_replaced, _ = replace_multibytes(bac_head_token)
	loc_text_replaced, _ = replace_multibytes(loc_text)
	loc_head_token_replaced, _ = replace_multibytes(loc_head_token)

	print '[BAC-%s] "%s",' % (bac_id, bac_text_replaced), '[%s]' % ','.join(str(i) for i in bac_token_idx_seq), 'head="%s"' % bac_head_token_replaced
	print '[LOC-%s] "%s",' % (loc_id, loc_text_replaced), '[%s]' % ','.join(str(i) for i in loc_token_idx_seq), 'head="%s"' % loc_head_token_replaced

	tokens = sent_dep.get_sent_tokens()
	tokens[bac_token_idx_seq[0]] = '<<' + tokens[bac_token_idx_seq[0]]
	tokens[loc_token_idx_seq[0]] = '<<' + tokens[loc_token_idx_seq[0]]
	tokens[bac_token_idx_seq[-1]] = tokens[bac_token_idx_seq[-1]] + '>>'
	tokens[loc_token_idx_seq[-1]] = tokens[loc_token_idx_seq[-1]] + '>>'
	tokenized_sent = ' '.join(tokens)

	unicode_sent, _ = replace_multibytes(tokenized_sent)
	print '[SENT]', unicode_sent

	#unicode_sent = tokenized_sent.decode('utf-8')
	#for unicode_c in unicode_sent:
	#	if ord(unicode_c) >= 128:
	#		unicode_sent = unicode_sent.replace(unicode_c, '@')
	#print '[SENT]', unicode_sent.encode('utf-8')


def apply_simple_patterns(bac_token_idx_seq, bac_head_token_idx_in_sent, bac_text, path_to_bac,
						  loc_token_idx_seq, loc_head_token_idx_in_sent, loc_text, path_to_loc,
						  sent_dep, is_expanded=False):
	"""


	:type input_item: InputItem
	:return:
	"""

	print
	print '---' * 3, '%sApply simple relation patterns' % ('(ex) ' if is_expanded else ''), '---' * 10
	sep = '***' * 16

	result = sent_dep.check_two_modified_in_common_np(bac_head_token_idx_in_sent, loc_head_token_idx_in_sent,
													  path_to_bac, path_to_loc)
	if result:
		print ' ', sep, '\n  ***** Simple relations: noun noun (%s) "%s"\n' % (result, ''), ' ', sep
		return result

	prep1 = sent_dep.check_t1_prep_t2(bac_head_token_idx_in_sent, loc_head_token_idx_in_sent)
	prep2 = sent_dep.check_t1_prep_t2(loc_head_token_idx_in_sent, bac_head_token_idx_in_sent) if not prep1 else prep1
	if prep1 or prep2:
		print ' ', sep, '\n  ***** Simple relations: %s\n' % ("BAC " + prep1 + " LOC" if prep1 else "LOC " + prep2 + " BAC"), ' ', sep
		return prep1 if prep1 else prep2

	vp1 = sent_dep.check_t1_ving_or_ved_prep_t2(bac_head_token_idx_in_sent, loc_head_token_idx_in_sent)
	vp2 = sent_dep.check_t1_ving_or_ved_prep_t2(loc_head_token_idx_in_sent, bac_head_token_idx_in_sent)
	if vp1 or vp2:
		print ' ', sep, '\n  ***** Simple relations: %s\n' % ("BAC " + vp1 + " LOC" if vp1 else "LOC " + vp2 + " BAC"), ' ', sep
		return vp1 if vp1 else vp2

	v1 = sent_dep.check_t1_vp_t2(bac_head_token_idx_in_sent, loc_head_token_idx_in_sent, path_to_bac, path_to_loc)
	v2 = sent_dep.check_t1_vp_t2(loc_head_token_idx_in_sent, bac_head_token_idx_in_sent, path_to_loc, path_to_bac)
	if v1 or v2:
		print ' ', sep, '\n  ***** Simple relations: %s\n' % (
			"BAC " + v1 + " LOC" if v1 else "LOC " + v2 + " BAC"), ' ', sep
		return v1 if v1 else v2

	is_bac_within_loc = all((b_idx in loc_token_idx_seq) for b_idx in bac_token_idx_seq)
	is_loc_within_bac = all((l_idx in bac_token_idx_seq) for l_idx in loc_token_idx_seq) if not is_bac_within_loc else False
	if is_bac_within_loc or is_loc_within_bac:
		print ' ', sep, '\n  ***** Simple relations: %s\n' % ('"%s" within "%s"' % ((bac_text, loc_text) if is_bac_within_loc else (loc_text, bac_text))), ' ', sep
		return is_bac_within_loc or is_loc_within_bac

	v_obj1 = sent_dep.check_t1verb_t2obj(bac_head_token_idx_in_sent, loc_head_token_idx_in_sent)
	v_obj2 = sent_dep.check_t1verb_t2obj(loc_head_token_idx_in_sent, bac_head_token_idx_in_sent)
	if v_obj1 or v_obj2:
		print ' ', sep, '\n  ***** Simple relations: %s\n' % ('"%s"(verb) "%s"(obj)' % ((bac_text, loc_text) if v_obj1 else (loc_text, bac_text))), ' ', sep
		return v_obj1 or v_obj2

	print '  No match...'

	return None


def propagate_relations_among_input_items(input_item, expanded_input_items, predicted_items):
	"""
	:type input_item: InputItem
	:type predicted_items: list[InputItem]
	:return:
	"""
	debug_print = False
	#debug_print = True

	if debug_print:
		print '$$$$$$$$$ Propagation Check! $$$$$$$$$'
		for ex_input_item in expanded_input_items:
			print '-- Extended:', 'BAC="%s"(%d), LOC="%s"(%d)' % (
				ex_input_item.get_bac_text(), ex_input_item.get_bac_head_token_idx_in_sent(),
				ex_input_item.get_loc_text(), ex_input_item.get_loc_head_token_idx_in_sent())
		for pd_input_item in predicted_items:
			print '- Predicted:', 'BAC="%s"(%d), LOC="%s"(%d)' % (
				pd_input_item.get_bac_text(), pd_input_item.get_bac_head_token_idx_in_sent(),
				pd_input_item.get_loc_text(), pd_input_item.get_loc_head_token_idx_in_sent())

	result, matched_item = propagate_relations_with_local_patterns(input_item, predicted_items, special_conj=True)

	if result:
		if debug_print:
			print '@@! Result: Match by input with pred-input', 'BAC="%s", LOC="%s"' % (matched_item.get_bac_text(), matched_item.get_loc_text())
		return True

	for expanded_input_item in expanded_input_items:
		result, matched_item = propagate_relations_with_local_patterns(expanded_input_item, predicted_items, special_conj=False)
		if result:
			if debug_print:
				print '@@! Result: Match by ex-input with pred-input'
				print 'Ex-input: BAC="%s"(%d), LOC="%s"(%d)' % (
					expanded_input_item.get_bac_text(), expanded_input_item.get_bac_head_token_idx_in_sent(),
					expanded_input_item.get_loc_text(), expanded_input_item.get_loc_head_token_idx_in_sent())
				print 'Pd-input: BAC="%s"(%d), LOC="%s"(%d)' % (
					matched_item.get_bac_text(), matched_item.get_bac_head_token_idx_in_sent(),
					matched_item.get_loc_text(), matched_item.get_loc_head_token_idx_in_sent())
			return True

	return False


def propagate_relations_with_local_patterns(input_item, predicted_items, special_conj=False):
	"""
	:type input_item: InputItem
	:type predicted_items: list[InputItem]
	:rtype: (bool, InputItem)
	"""

	sent_offset, _ = input_item.get_sent_offsets()
	sent_dep, _ = input_item.get_sent_dep()
	(bac_id, bac_text, bac_token_idx_seq, loc_id, loc_text, loc_token_idx_seq) = input_item.get_bac_and_loc()
	bac_head_token_idx_in_sent, loc_head_token_idx_in_sent = input_item.get_head_token_idx_pair()
	bac_token_idx_seq = input_item.get_bac_token_idx_seq()
	loc_token_idx_seq = input_item.get_loc_token_idx_seq()


	matched = False
	matched_item = None
	sep = '****' * 16

	debug_print = False
	#debug_print = True

	for predicted_item in predicted_items:
		if debug_print:
			print '\nCandidate: "%s" (%s) & "%s" (%s)\nPredicted: "%s" (%s) & "%s" (%s)' % (
				input_item.get_bac_text(), input_item.get_bac_id(), input_item.get_loc_text(), input_item.get_loc_id(),
				predicted_item.get_bac_text(), predicted_item.get_bac_id(), predicted_item.get_loc_text(), predicted_item.get_loc_id())

		predicted_sent_offset, _ = predicted_item.get_sent_offsets()

		if predicted_sent_offset != sent_offset:
			continue

		pred_bac_head_token_idx_in_sent = predicted_item.get_bac_head_token_idx_in_sent()
		pred_loc_head_token_idx_in_sent = predicted_item.get_loc_head_token_idx_in_sent()

		pred_bac_head_idx = predicted_item.get_bac_head_token_idx_in_sent()
		input_bac_head = sent_dep.get_token(bac_head_token_idx_in_sent)
		pred_bac_head = sent_dep.get_token(pred_bac_head_idx)
		if loc_head_token_idx_in_sent == pred_loc_head_token_idx_in_sent \
				and bac_head_token_idx_in_sent != pred_bac_head_token_idx_in_sent \
				and input_bac_head == pred_bac_head:
			continue
			pass

		pred_bac_text, pred_bac_token_idx_seq = predicted_item.get_bac()
		pred_loc_text, pred_loc_token_idx_seq = predicted_item.get_loc()
		is_bac_nested = all((idx in pred_bac_token_idx_seq) for idx in bac_token_idx_seq)
		is_loc_nested = all((idx in pred_loc_token_idx_seq) for idx in loc_token_idx_seq)

		if is_bac_nested and is_loc_nested:
			print ' ', sep
			if is_bac_nested:
				print '  ***** Propagation (nested BAC): "%s" %s "%s"' % (
					bac_text, '==' if bac_text == pred_bac_text else '<=', pred_bac_text)
			if is_loc_nested:
				print '  ***** Propagation (nested LOC): "%s" %s "%s"' % (
					loc_text, '==' if loc_text == pred_loc_text else '<=', pred_loc_text)

			# print_sent_tokens_with_anno(sent_dep, bac_token_idx_seq, loc_token_idx_seq)
			print ' ', sep

			matched = True
			matched_item = predicted_item
			break

		is_bac_conj = (loc_head_token_idx_in_sent == pred_loc_head_token_idx_in_sent
					   and sent_dep.check_t1_conj_t2(bac_head_token_idx_in_sent, pred_bac_head_token_idx_in_sent))
		is_loc_conj = (bac_head_token_idx_in_sent == pred_bac_head_token_idx_in_sent
					   and sent_dep.check_t1_conj_t2(loc_head_token_idx_in_sent, pred_loc_head_token_idx_in_sent))
		if not is_bac_conj and loc_head_token_idx_in_sent == pred_loc_head_token_idx_in_sent:
			token_in_bac_middle = ''
			if pred_bac_token_idx_seq[0] - bac_token_idx_seq[-1] == 2:
				token_in_bac_middle = sent_dep.get_token(bac_token_idx_seq[-1] + 1)
			elif bac_token_idx_seq[0] - pred_bac_token_idx_seq[-1] == 2:
				token_in_bac_middle = sent_dep.get_token(pred_bac_token_idx_seq[-1] + 1)
			is_bac_conj = (token_in_bac_middle == 'and' or token_in_bac_middle == 'or')
		if not is_loc_conj and bac_head_token_idx_in_sent == pred_bac_head_token_idx_in_sent:
			token_in_loc_middle = ''
			if pred_loc_token_idx_seq[0] - loc_token_idx_seq[-1] == 2:
				token_in_loc_middle = sent_dep.get_token(loc_token_idx_seq[-1] + 1)
			elif loc_token_idx_seq[0] - pred_loc_token_idx_seq[-1] == 2:
				token_in_loc_middle = sent_dep.get_token(pred_loc_token_idx_seq[-1] + 1)
			is_loc_conj = (token_in_loc_middle == 'and' or token_in_loc_middle == 'or')


		matched = is_bac_conj or is_loc_conj

		if is_bac_conj:
			print ' ', sep, '\n  ***** Propagation (BAC conj BAC): "%s" and "%s"' % (bac_text, pred_bac_text), '\n ', sep
		if is_loc_conj:
			print ' ', sep, '\n  ***** Propagation (LOC conj LOC): "%s" and "%s"' % (loc_text, pred_loc_text), '\n ', sep

		if matched:
			matched_item = predicted_item
			break

		is_bac_of_bac = False
		is_loc_of_loc = False
		phrase = ''
		if loc_head_token_idx_in_sent == pred_loc_head_token_idx_in_sent:
			if pred_bac_head_token_idx_in_sent < bac_head_token_idx_in_sent:
				phrase = sent_dep.check_t1_prep_t2(pred_bac_head_token_idx_in_sent, bac_head_token_idx_in_sent)
			else:
				phrase = sent_dep.check_t1_prep_t2(bac_head_token_idx_in_sent, pred_bac_head_token_idx_in_sent) #if not phrase else phrase

			if phrase:
				is_bac_of_bac = True
			elif pred_bac_head_token_idx_in_sent < bac_head_token_idx_in_sent:
				phrase = sent_dep.check_t1_ving_or_ved_prep_t2(pred_bac_head_token_idx_in_sent, bac_head_token_idx_in_sent)
			else:
				phrase = sent_dep.check_t1_ving_or_ved_prep_t2(bac_head_token_idx_in_sent, pred_bac_head_token_idx_in_sent) #if not phrase else phrase

			if phrase:
				is_bac_of_bac = True

		if not is_bac_of_bac and bac_head_token_idx_in_sent == pred_bac_head_token_idx_in_sent:

			if pred_loc_head_token_idx_in_sent < loc_head_token_idx_in_sent:
				phrase = sent_dep.check_t1_prep_t2(pred_loc_head_token_idx_in_sent, loc_head_token_idx_in_sent)
			else:
				phrase = sent_dep.check_t1_prep_t2(loc_head_token_idx_in_sent, pred_loc_head_token_idx_in_sent) #if not phrase else phrase

			if phrase:
				is_loc_of_loc = True
			elif pred_loc_head_token_idx_in_sent < loc_head_token_idx_in_sent:
				phrase = sent_dep.check_t1_ving_or_ved_prep_t2(pred_loc_head_token_idx_in_sent, loc_head_token_idx_in_sent)
			else:
				phrase = sent_dep.check_t1_ving_or_ved_prep_t2(loc_head_token_idx_in_sent, pred_loc_head_token_idx_in_sent) #if not phrase else phrase

			if phrase:
				is_loc_of_loc = True

		matched = is_bac_of_bac or is_loc_of_loc

		if is_bac_of_bac:
			print ' ', sep, '\n  ***** Propagation (BAC %s BAC): "%s" %s "%s"' % (phrase, pred_bac_text, phrase, bac_text), '\n ', sep
		if is_loc_of_loc:
			print ' ', sep, '\n  ***** Propagation (LOC %s LOC): "%s" %s "%s"' % (phrase, pred_loc_text, phrase, loc_text), '\n ', sep

		if matched:
			matched_item = predicted_item
			break

		is_bac_appos = (loc_head_token_idx_in_sent == pred_loc_head_token_idx_in_sent
					   and sent_dep.check_t1_appos_t2(bac_head_token_idx_in_sent, pred_bac_head_token_idx_in_sent))
		is_loc_appos = (bac_head_token_idx_in_sent == pred_bac_head_token_idx_in_sent
					   and sent_dep.check_t1_appos_t2(loc_head_token_idx_in_sent, pred_loc_head_token_idx_in_sent))

		if not is_loc_appos and bac_head_token_idx_in_sent == pred_bac_head_token_idx_in_sent:
			is_loc_appos = (sent_dep.check_t1_comma_t2(loc_head_token_idx_in_sent, loc_token_idx_seq,
													  pred_loc_head_token_idx_in_sent, pred_loc_token_idx_seq)
							or sent_dep.check_t1_comma_t2(pred_loc_head_token_idx_in_sent, pred_loc_token_idx_seq,
													  loc_head_token_idx_in_sent, loc_token_idx_seq))

		matched = is_bac_appos or is_loc_appos

		if is_bac_appos:
			print ' ', sep, '\n  ***** Propagation (BAC appos BAC): "%s" <- "%s"' % (bac_text, pred_bac_text), '\n ', sep
		if is_loc_appos:
			print ' ', sep, '\n  ***** Propagation (LOC appos LOC): "%s" <- "%s"' % (loc_text, pred_loc_text), '\n ', sep

		if matched:
			matched_item = predicted_item
			break

		is_bac_equi = (loc_head_token_idx_in_sent == pred_loc_head_token_idx_in_sent
						and (sent_dep.check_t1_is_t2(bac_head_token_idx_in_sent, pred_bac_head_token_idx_in_sent)
							 or sent_dep.check_t1_is_t2(pred_bac_head_token_idx_in_sent, bac_head_token_idx_in_sent)))
		is_loc_equi = (bac_head_token_idx_in_sent == pred_bac_head_token_idx_in_sent
						and (sent_dep.check_t1_is_t2(loc_head_token_idx_in_sent, pred_loc_head_token_idx_in_sent)
							 or sent_dep.check_t1_is_t2(pred_loc_head_token_idx_in_sent, loc_head_token_idx_in_sent)))

		matched = is_bac_equi or is_loc_equi

		if is_bac_equi:
			print ' ', sep, '\n  ***** Propagation (BAC is BAC): "%s" and "%s"' % (
				bac_text, pred_bac_text), '\n ', sep
		if is_loc_equi:
			print ' ', sep, '\n  ***** Propagation (LOC is LOC): "%s" and "%s"' % (
				loc_text, pred_loc_text), '\n ', sep

		if matched:
			matched_item = predicted_item
			break

		path_from_subroot_to_bac = path_from_subroot_to_pred_bac = None
		path_from_subroot_to_loc = path_from_subroot_to_pred_loc = None
		is_bac_nn = is_loc_nn = False
		if loc_head_token_idx_in_sent == pred_loc_head_token_idx_in_sent \
				and bac_head_token_idx_in_sent != pred_bac_head_token_idx_in_sent:
			path_from_subroot_to_bac, path_from_subroot_to_pred_bac \
				= sent_dep.get_lowest_subtree(bac_head_token_idx_in_sent, pred_bac_head_token_idx_in_sent)
			is_bac_nn = sent_dep.check_two_modified_in_common_np(
								bac_head_token_idx_in_sent, pred_bac_head_token_idx_in_sent,
								path_from_subroot_to_bac, path_from_subroot_to_pred_bac)
		if bac_head_token_idx_in_sent == pred_bac_head_token_idx_in_sent \
				and loc_head_token_idx_in_sent != pred_loc_head_token_idx_in_sent:
			path_from_subroot_to_loc, path_from_subroot_to_pred_loc \
				= sent_dep.get_lowest_subtree(loc_head_token_idx_in_sent, pred_loc_head_token_idx_in_sent)
			is_loc_nn = sent_dep.check_two_modified_in_common_np(
								loc_head_token_idx_in_sent, pred_loc_head_token_idx_in_sent,
								path_from_subroot_to_loc, path_from_subroot_to_pred_loc)

		matched = is_bac_nn or is_loc_nn

		if is_bac_nn:
			print ' ', sep, '\n  ***** Propagation (BAC[noun]-BAC[noun]): "%s" and "%s"' % (
				bac_text, pred_bac_text), '\n ', sep
		if is_loc_nn:
			print ' ', sep, '\n  ***** Propagation (LOC[noun]-LOC[noun]): "%s" and "%s"' % (
				loc_text, pred_loc_text), '\n ', sep

		if matched:
			matched_item = predicted_item
			break

		if not special_conj:
			continue

		if False and bac_head_token_idx_in_sent == 15 and loc_head_token_idx_in_sent == 5:
			print loc_head_token_idx_in_sent == pred_loc_head_token_idx_in_sent \
				and bac_head_token_idx_in_sent != pred_bac_head_token_idx_in_sent
			print path_from_subroot_to_bac
			print path_from_subroot_to_pred_bac
			is_vp_bac_ving_bac = sent_dep.check_vp_t1_ving_or_ved_prep_t2(
				pred_bac_head_token_idx_in_sent, bac_head_token_idx_in_sent,
				path_from_subroot_to_pred_bac, path_from_subroot_to_bac)
			print is_vp_bac_ving_bac
			exit()

		is_vp_bac_ving_bac = is_vp_loc_ving_loc = False
		if loc_head_token_idx_in_sent == pred_loc_head_token_idx_in_sent \
				and bac_head_token_idx_in_sent != pred_bac_head_token_idx_in_sent:
			if not (path_from_subroot_to_bac and path_from_subroot_to_pred_bac):
				path_from_subroot_to_bac, path_from_subroot_to_pred_bac \
					= sent_dep.get_lowest_subtree(bac_head_token_idx_in_sent, pred_bac_head_token_idx_in_sent)

			is_vp_bac_ving_bac = sent_dep.check_vp_t1_ving_or_ved_prep_t2(
				pred_bac_head_token_idx_in_sent, bac_head_token_idx_in_sent,
				path_from_subroot_to_pred_bac, path_from_subroot_to_bac)

		if bac_head_token_idx_in_sent == pred_bac_head_token_idx_in_sent \
				and loc_head_token_idx_in_sent != pred_loc_head_token_idx_in_sent:
			if not (path_from_subroot_to_loc and path_from_subroot_to_pred_loc):
				path_from_subroot_to_loc, path_from_subroot_to_pred_loc \
					= sent_dep.get_lowest_subtree(loc_head_token_idx_in_sent, pred_loc_head_token_idx_in_sent)

			is_vp_loc_ving_loc = sent_dep.check_vp_t1_ving_or_ved_prep_t2(
				pred_loc_head_token_idx_in_sent, loc_head_token_idx_in_sent,
				path_from_subroot_to_pred_loc, path_from_subroot_to_loc)

		matched = is_vp_bac_ving_bac or is_vp_loc_ving_loc

		if is_vp_bac_ving_bac:
			print ' ', sep, '\n  ***** Propagation (vp BAC ving/ved BAC): pred="%s"(%s) and cand="%s"(%s)' % (
				pred_bac_text, predicted_item.get_bac_id(), bac_text, bac_id), '\n ', sep
		if is_vp_loc_ving_loc:
			print ' ', sep, '\n  ***** Propagation (vp LOC ving/ved LOC): pred="%s"(%s) and cand="%s"(%s)' % (
				pred_loc_text, predicted_item.get_loc_id(), loc_text, loc_id), '\n ', sep

		if matched:
			matched_item = predicted_item
			break

	return matched, matched_item


g_expansion_cues = {
	'qty_nouns': ['one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
				  'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'nineteen', 'twenty',
				  'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety', 'hundred',
				  'tens', 'hundreds', 'thousands', 'millions', 'group', 'groups',
				  'rate', 'rates', 'ratio', 'proportion', 'proportions', 'percentage',
				  'some', 'any', 'part', 'parts', 'number', 'numbers', 'amount', 'amounts', 'count', 'counts',
		          'variety', 'diverse', 'diversity', 'variant',
				  'case', 'cases', 'type', 'types', 'family', 'families',
				  'quantity', 'quantities', 'range', 'ranges', 'class', 'classes', 'sample', 'samples',
				  'level', 'levels',
				  'pattern', 'patterns', 'frequency', 'frequencies', 'density',
				  'form', 'forms', 'value', 'values', 'property', 'properties',
				  'role', 'roles',
				  'species',
	],
	'loc_nouns': ['region', 'location', 'area', 'site', 'scene', 'position', 'space', 'position',
				  'scope', 'spot', 'country', 'state', 'city', 'town', 'section', 'distinct', 'zone', 'domain', 'sector'],
	'qty_symbols': range(0, 10) + ['%'],
}


def expand_input_item_by_syntax(bac_item, loc_item, input_id, sent_offset, sent_dep, id_suffix=''):
	"""
	:type input_item: InputItem
	:rtype: list[InputItem]
	"""
	qty_nouns = g_expansion_cues['qty_nouns']
	qty_symbols = g_expansion_cues['qty_symbols']
	loc_nouns = g_expansion_cues['loc_nouns']

#	input_id = input_item.get_id()
#	sent_dep, _ = input_item.get_sent_dep()
#	(bac_id, bac_text, bac_token_idx_seq, loc_id, loc_text, loc_token_idx_seq) = input_item.get_bac_and_loc()
#	bac_head_token_idx_in_sent, loc_head_token_idx_in_sent = input_item.get_head_token_idx_pair()
	bac_id, bac_text, bac_token_idx_seq, bac_head_token_idx_in_sent = bac_item
	loc_id, loc_text, loc_token_idx_seq, loc_head_token_idx_in_sent = loc_item
	bac_source = bac_text
	loc_source = loc_text

	checked_token_indices_in_sent = [bac_head_token_idx_in_sent, loc_head_token_idx_in_sent]
	token_queue = [(True, bac_head_token_idx_in_sent, bac_source),
				   (False, loc_head_token_idx_in_sent, loc_source)]

	expanded_bac_tokens = []
	expanded_loc_tokens = []

	sep = '* * ' * 16
	debug = False
	#debug = True

	print 'Expanding by local syntactic info...'

	while token_queue:
		is_from_bac, curr_token_idx, source_token_form = token_queue.pop()  # type: bool, int, str
		parent_token_indices = sent_dep.get_parent_tokens(curr_token_idx)  # type: list[tuple[int, str]]
		children_token_indices = sent_dep.get_children_tokens(curr_token_idx)
		neighbor_token_indices = [(i, d, sent_dep.get_token(i), True, source_token_form) for i, d in parent_token_indices] \
								 + [(i, d, sent_dep.get_token(i), False, source_token_form) for i, d in children_token_indices]

		if debug: print '@@[%s]:' % ('BAC' if is_from_bac else 'LOC'), sent_dep.get_token(curr_token_idx)

		for neighbor_idx, dep_label, neighbor_token_form, is_parent, source_token_form in neighbor_token_indices:  # type: int, str, str, bool, str

			neighbor_token_form, _ = replace_multibytes(neighbor_token_form)

			if debug: print ' -->%s: "%s" (%d/%s)' % ('P' if is_parent else 'C', neighbor_token_form, neighbor_idx, dep_label)

			if neighbor_idx in checked_token_indices_in_sent:
				continue

			if sent_dep.check_dep_label_conj(dep_label):
				#exp_type = id_suffix + '-conj'
				if sent_dep.check_dep_pos_verb(sent_dep.get_token_pos(curr_token_idx)) \
						and sent_dep.check_dep_pos_verb(sent_dep.get_token_pos(neighbor_idx)):
					nsubj_of_curr_token_idx = sent_dep.get_nsubj_token_of_verb(curr_token_idx)
					nsubj_of_neigh_token_idx = sent_dep.get_nsubj_token_of_verb(neighbor_idx)
					if nsubj_of_curr_token_idx >= 0 and nsubj_of_neigh_token_idx >= 0 \
							and nsubj_of_curr_token_idx != nsubj_of_neigh_token_idx:
						exp_type = ''
						print ' ~~~~~> "conj" found, but filtered out: "%s" & "%s" (VERB conj VERB with different subjects!)' % (
							sent_dep.get_token(curr_token_idx), sent_dep.get_token(neighbor_idx))
					else:
						exp_type = id_suffix + '-conj'
				else:
					exp_type = id_suffix + '-conj'
			elif sent_dep.check_dep_label_appos(dep_label):
				exp_type = id_suffix + '-appos'
			elif sent_dep.check_dep_label_comp(dep_label):
				exp_type = id_suffix + '-xcomp'
			elif sent_dep.check_dep_label_unknown(dep_label):
				exp_type = id_suffix + '-dep'
			else:
				exp_type = ''

			#exp_type = id_suffix + '-conj' if sent_dep.check_dep_label_conj(dep_label) else ''
			#exp_type = id_suffix + '-appos' if not exp_type and sent_dep.check_dep_label_appos(dep_label) else exp_type
			#exp_type = id_suffix + '-xcomp' if not exp_type and sent_dep.check_dep_label_comp(dep_label) else exp_type
			#exp_type = id_suffix + '-dep' if not exp_type and sent_dep.check_dep_label_unknown(dep_label) else exp_type

			#print '  @@!', exp_type

			#neighbor_token_form = sent_dep.get_token(neighbor_idx)

			if exp_type:
				#exp_type = '(conj/apps/xcomp/dep)'
				checked_token_indices_in_sent.append(neighbor_idx)
				print '   ~~~~ "%s" (%d) [%s] (%s: "%s")' % (neighbor_token_form, neighbor_idx, exp_type, 'BAC' if is_from_bac else 'LOC', source_token_form)
			elif sent_dep.check_t1_is_t2(curr_token_idx, neighbor_idx):
				exp_type = id_suffix + '-A_is_B'
				checked_token_indices_in_sent.append(neighbor_idx)
				print '   ~~~~ "%s" (%d) [A_is_B] (%s: "%s")' % (neighbor_token_form, neighbor_idx, 'BAC' if is_from_bac else 'LOC', source_token_form)
			elif is_parent and sent_dep.check_dep_label_pobj(dep_label):
				gr_parents = sent_dep.get_parent_tokens(neighbor_idx)
				if gr_parents:
					gr_parent_idx, parent_dep_label = gr_parents[0]
					gr_parent_token = sent_dep.get_token(gr_parent_idx)
					if neighbor_token_form == 'of' or neighbor_token_form == 'from' or neighbor_token_form == 'in':
						if '-' in gr_parent_token:
							gr_parent_tail_token = gr_parent_token.split('-')[-1]
						else:
							gr_parent_tail_token = ''

						# neighbor_token_form = gr_parent_token
						if (gr_parent_token in qty_nouns or gr_parent_tail_token in qty_nouns
								or gr_parent_token[-1] in qty_symbols):
							print '   ~~~~ "%s" (%d) [qty_%s] (%s: "%s")' % (
								gr_parent_token, neighbor_idx, neighbor_token_form, 'BAC' if is_from_bac else 'LOC', source_token_form)
							exp_type = id_suffix + '-qty_%s' % neighbor_token_form

						elif lemmatizer.lemmatize(gr_parent_token, pos='n') in loc_nouns:
							print '   ~~~~ "%s" (%d) [loc_%s] (%s: "%s")' % (
								gr_parent_token, neighbor_idx, neighbor_token_form, 'BAC' if is_from_bac else 'LOC', source_token_form)
							exp_type = id_suffix + '-loc_%s' % neighbor_token_form

					if exp_type:
						checked_token_indices_in_sent.append(neighbor_idx)
						checked_token_indices_in_sent.append(gr_parent_idx)
						neighbor_idx = gr_parent_idx
			elif not is_from_bac and is_parent and dep_label in sent_dep.nn_neighbor_labels \
					and lemmatizer.lemmatize(neighbor_token_form, pos='n') in loc_nouns:
				print '   ~~~~ "%s" (%d) [loc_loc] (%s: "%s")' % (
					neighbor_token_form, neighbor_idx, 'BAC' if is_from_bac else 'LOC', source_token_form)
				exp_type = id_suffix + '-loc_%s' % neighbor_token_form
				checked_token_indices_in_sent.append(neighbor_idx)

			first_char_of_exp_token =  sent_dep.get_token(neighbor_idx)[0]
			if not first_char_of_exp_token.isalnum() and first_char_of_exp_token not in qty_symbols:
				continue

			if exp_type:
				if is_from_bac:
					expanded_bac_tokens.append((neighbor_idx, source_token_form, exp_type))
				else:
					expanded_loc_tokens.append((neighbor_idx, source_token_form, exp_type))

				token_queue.append((is_from_bac, neighbor_idx, source_token_form))

	if not expanded_bac_tokens and not expanded_loc_tokens:
		print '   (Nothing to expand...)'
		return []

	if debug:
		print '  Expansion result:'
		print '  ===> ex-BAC:', ' | '.join('"%s"_%d(%s) <= "%s"' % (sent_dep.get_token(i), i, m, s) for i, s, m in expanded_bac_tokens)
		print '  ===> ex-LOC:', ' | '.join('"%s"_%d(%s) <= "%s"' % (sent_dep.get_token(i), i, m, s) for i, s, m in expanded_loc_tokens)
		print '   ex-items: %d' % ((len(expanded_bac_tokens) + 1) * (len(expanded_loc_tokens) + 1))
	#sent_offset, _ = input_item.get_sent_offsets()
	ex_cnt = 0
	expanded_input_items = []

	for ex_bac_token_idx, source_bac, exp_type_bac in [(bac_head_token_idx_in_sent, bac_text, '')] + expanded_bac_tokens:
		for ex_loc_token_idx, source_loc, exp_type_loc in [(loc_head_token_idx_in_sent, loc_text, '')] + expanded_loc_tokens:
			if ex_bac_token_idx == bac_head_token_idx_in_sent and ex_loc_token_idx == loc_head_token_idx_in_sent:
				continue

			if ex_bac_token_idx == ex_loc_token_idx:
				continue

			is_from_bac = bool(source_bac)
			is_from_loc = bool(source_loc)
			assert is_from_bac or is_from_loc

			if exp_type_bac:
				ex_bac_id = 'exB-s%s-h%d' % (str(sent_offset), ex_bac_token_idx)
			else:
				ex_bac_id = bac_id
			if exp_type_loc:
				ex_loc_id = 'exL-s%s-h%d' % (str(sent_offset), ex_loc_token_idx)
			else:
				ex_loc_id = loc_id

			ex_bac_text = sent_dep.get_token(ex_bac_token_idx)
			ex_loc_text = sent_dep.get_token(ex_loc_token_idx)
			ex_input_id = str(input_id) + '-ex%s%d' % ('-'+id_suffix if id_suffix else '', ex_cnt)
			ex_lowest_subtree = sent_dep.get_lowest_subtree(ex_bac_token_idx, ex_loc_token_idx)
			ex_input_item = InputItem(ex_input_id, ex_bac_id, ex_loc_id,
									  ex_bac_text, [ex_bac_token_idx], ex_bac_token_idx, sent_offset, sent_dep,
									  ex_loc_text, [ex_loc_token_idx], ex_loc_token_idx, sent_offset, sent_dep,
									  ex_lowest_subtree, is_gold_event=False,
									  is_expanded_from_bac=is_from_bac, is_expanded_from_loc=is_from_loc,
									  exp_source=(source_bac, source_loc), exp_type=(exp_type_bac, exp_type_loc))
			expanded_input_items.append(ex_input_item)
			ex_cnt += 1

	return expanded_input_items




lemmatizer = WordNetLemmatizer()
g_nums = ['one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',]
g_ratio_nouns = ['rate', 'ratio', 'proportion', 'percentage']


def is_numerical_token(token):

	if token.lower() in g_nums:
		return True

	if not token[0].isdigit():
		return False

	for c in token:
		if not (c.isdigit() or c == '.' or c == ',' or c == '%'):
			return False

	return True


def has_plural_meaning(token, token_idx, sent_dep):
	return ((token.endswith('s') or token in g_ratio_nouns)
				and sent_dep.check_dep_pos_noun(sent_dep.get_token_pos(token_idx)))


def check_numerical_ref_for_ent(cand_super_noun_idx, cand_sub_noun_idx, sent_dep):
	"""
	:type cand_super_noun_idx: int
	:type cand_sub_noun_idx: int
	:type sent_dep: sent_dep.SentDep
	:return:
	"""
	false_idx_pair = (-99999, -99999)

	if cand_sub_noun_idx <= cand_super_noun_idx:
		return false_idx_pair

	if cand_sub_noun_idx == len(sent_dep) - 1:
		return false_idx_pair

	if is_numerical_token(sent_dep.get_token(cand_sub_noun_idx - 1)):
		cand_sub_noun_idx = cand_sub_noun_idx - 1
	elif not is_numerical_token(sent_dep.get_token(cand_sub_noun_idx)):
		return false_idx_pair

	cand_super_noun = sent_dep.get_token(cand_super_noun_idx)
	cand_sub_token = sent_dep.get_token(cand_sub_noun_idx)
	cand_prev_sub_token = sent_dep.get_token(cand_sub_noun_idx - 1)

	if cand_sub_token.isdigit() and (cand_prev_sub_token == '(' or cand_prev_sub_token == '['):
		cand_next_sub_token = sent_dep.get_token(cand_sub_noun_idx + 1)
		if cand_next_sub_token == ')' or cand_next_sub_token == ']':
			return false_idx_pair

	is_bac_with_num = False
	ref_noun = ''
	ref_noun_idx = -999999
	preps = ['of', 'in', 'from', 'on', 'to']
	#plural_pronouns = ['them', 'these', 'those']
	bac_parents = None
	super_num_match_type = ''

	debug = False
	#debug = True


	if debug:
		print '======= [Test] check_numerical_ref_for_bac ======'
		print 'Super-num: "%s" (%d)' % (cand_super_noun, cand_super_noun_idx)
		print '  sub-num: "%s" (%d)' % (cand_sub_token, cand_sub_noun_idx)

	if cand_super_noun_idx > 0 and is_numerical_token(sent_dep.get_token(cand_super_noun_idx - 1)):
		is_bac_with_num = True
		ref_noun = cand_super_noun
		ref_noun_idx = cand_super_noun_idx
	else:
		for prev_token_idx in range(cand_super_noun_idx - 1, -1, -1):
			parents_prev = sent_dep.get_parent_tokens(prev_token_idx)
			if not parents_prev:
				continue
			parent_prev_idx, _ = parents_prev[0]
			parents_this = sent_dep.get_parent_tokens(cand_super_noun_idx)
			parent_this_idx, _ = parents_this[0] if parents_this else ('', '')
			#if cand_super_noun == 'isolates' and cand_sub_token == 'five':
			#	print '   ->', sent_dep.get_token(prev_token_idx), is_numerical_token(sent_dep.get_token(prev_token_idx)), \
			#		parent_prev_idx, cand_super_token_idx, parent_this_idx
			if is_numerical_token(sent_dep.get_token(prev_token_idx)) \
					and (parent_prev_idx == cand_super_noun_idx or parent_prev_idx == parent_this_idx):
				is_bac_with_num = True
				ref_noun = cand_super_noun
				ref_noun_idx = cand_super_noun_idx
				super_num_match_type = 'num("%s") {bac(ref)}' % sent_dep.get_token(prev_token_idx)
				break
	if not is_bac_with_num:
		bac_parents = sent_dep.get_parent_tokens(cand_super_noun_idx)
		if bac_parents:
			parent_idx, parent_dep_label = bac_parents[0]
			parent_token = sent_dep.get_token(parent_idx)
			if parent_token in preps:
				gr_parents = sent_dep.get_parent_tokens(parent_idx)
				if gr_parents:
					gr_parent_idx, gr_parent_dep_label = gr_parents[0]
					gr_parent_token = sent_dep.get_token(gr_parent_idx)
					if is_numerical_token(gr_parent_token):
						is_bac_with_num = True
						ref_noun_idx = cand_super_noun_idx
						ref_noun = cand_super_noun
						super_num_match_type = 'num("%s") %s {bac(ref)}' % (gr_parent_token, parent_token)
					else:
						ref_noun_idx = gr_parent_idx
						ref_noun = gr_parent_token
						super_num_match_type = 'ref("%s") %s {bac}' % (gr_parent_token, parent_token)

	if not ref_noun and not is_bac_with_num:
		if cand_super_noun_idx < len(sent_dep) - 1 and sent_dep.get_parent_tokens(cand_super_noun_idx + 1) == bac_parents:
			ref_noun_idx = cand_super_noun_idx + 1
			ref_noun = sent_dep.get_token(ref_noun_idx)
			super_num_match_type = '{bac} + ref'
		else:
			return false_idx_pair

	if ref_noun:
		if not has_plural_meaning(ref_noun, ref_noun_idx, sent_dep):
			return false_idx_pair
	elif not is_bac_with_num:
		return false_idx_pair

	if debug:
		print '    ~~~> Super-num matched! (ref_noun: "%s") match type: %s' % (ref_noun, super_num_match_type)

	next1_token_idx = cand_sub_noun_idx + 1
	next1_token_pos = sent_dep.get_token_pos(next1_token_idx)
	#next2_token_idx = cand_sub_noun_idx + 2
	#next2_token = sent_dep.get_token(next2_token_idx) if cand_sub_noun_idx < len(sent_dep) - 2 else ''
	if sent_dep.get_token(next1_token_idx) == ref_noun:
		sub_noun_idx = next1_token_idx
	elif not sent_dep.check_dep_pos_noun(next1_token_pos):
		sub_noun_idx = cand_sub_noun_idx
	else:
		sub_noun_idx = -99999

	super_noun_idx = cand_super_noun_idx

	if debug and super_noun_idx >= 0 and sub_noun_idx >= 0:
		print '  ==> <Success> check_numerical_ref_for_bac ~~~~~~'
		print 'Super-num: "%s" (%d)' % (sent_dep.get_token(cand_super_noun_idx), cand_super_noun_idx)
		print '  Sub-num: "%s" (%d)' % (sent_dep.get_token(cand_sub_noun_idx), cand_sub_noun_idx)

	return super_noun_idx, sub_noun_idx


def semantic_expansion_filtering(bac_text, bac_token_idx_seq, bac_head_token_idx_in_sent, sent_dep, is_bac_generic):
	"""

	:type bac_text: str
	:type bac_token_idx_seq: list[int]
	:type bac_head_token_idx_in_sent: int
	:type sent_dep: sent_dep.SentDep
	:return:
	"""

	if is_bac_generic:
		bac_text_lowered = bac_text.lower()
		if 'gram-positive' in bac_text_lowered or 'gram positive' in bac_text_lowered\
				or 'gram-negative' in bac_text_lowered or 'gram negative' in bac_text_lowered:
			#raise Exception('Debugging!')
			return False

	return True


def expand_input_item_by_semantics(input_item, trigger_map, id_suffix=''):
	"""

	:type input_item: InputItem
	:type trigger_map: TriggerMap
	:rtype: list[InputItem]
	"""

	input_id = input_item.get_id()
	sent_dep, _ = input_item.get_sent_dep()
	sent_offset, _ = input_item.get_sent_offsets()
	(bac_id, bac_text, bac_token_idx_seq, loc_id, loc_text, loc_token_idx_seq) = input_item.get_bac_and_loc()
	bac_head_token_idx_in_sent, loc_head_token_idx_in_sent = input_item.get_head_token_idx_pair()

	bac_id = input_item.get_bac_id()

	direct_trigger_items_for_bac = trigger_map.get_matched_triggers_for_bac_in_sent(bac_id, trigger_type='direct')
	#indirect_trigger_items_for_bac = trigger_map.get_matched_triggers_for_bac_in_sent(bac_id, trigger_type='indirect')
	auto_trigger_items_for_bac = trigger_map.get_matched_triggers_for_bac_in_sent(bac_id, trigger_type='auto-intra')

	#nondirect_trigger_items_for_bac = indirect_trigger_items_for_bac
	nondirect_trigger_items_for_bac = auto_trigger_items_for_bac

	expanded_input_items = []
	ex_cnt = 0

	#bac_last_token = sent_dep.get_token(bac_token_idx_seq[-1])
	#bac_head_token = sent_dep.get_token(bac_head_token_idx_in_sent)

	#print '@@@@@@'
	#print nondirect_trigger_items_for_bac

	debug_print = False
	#debug_print = True

	print 'Expanding by semantic info (only for bacteria)...'

	cand_tokens = sent_dep.get_sent_tokens()

	for token_idx, token in enumerate(cand_tokens):

		if token_idx in bac_token_idx_seq or token_idx in loc_token_idx_seq:
			continue

		pos = sent_dep.get_token_pos(token_idx)
		is_noun = sent_dep.check_dep_pos_noun(pos)

		if not is_noun:
			continue

		is_verb = sent_dep.check_dep_pos_verb(pos)

		#print '!!!@@^^^', is_verb, token, lemmatizer.lemmatize(token.lower().decode('utf-8'), pos='n')

		exp_type = ''

		if not is_verb:
			for trigger_token_idx, trigger, trigger_freq in direct_trigger_items_for_bac:
				if token_idx == trigger_token_idx:
					exp_type = id_suffix + '-context-direct-trigger'
					break

		if not exp_type:
			for trigger_token_idx, trigger, trigger_freq in nondirect_trigger_items_for_bac:
				if token_idx == trigger_token_idx:
					exp_type = id_suffix + '-context-indirect-trigger'
					break

		if exp_type:
			bac_text_replaced, _ = replace_multibytes(bac_text)
			print '   ~~~~ "%s" (%d) %s (BAC: "%s")' % (token, token_idx, exp_type, bac_text_replaced)

			ex_input_id = str(input_id) + '-ex%s%d' % ('-'+id_suffix if id_suffix else '', ex_cnt)
			ex_bac_id = 'exB-s%s-h%s' % (str(sent_offset), token_idx)
			assert token_idx != loc_head_token_idx_in_sent

			ex_lowest_subtree = sent_dep.get_lowest_subtree(token_idx, loc_head_token_idx_in_sent)
			assert ex_lowest_subtree

			ex_input_item = InputItem(ex_input_id, ex_bac_id, loc_id,
									  token, [token_idx], token_idx, sent_offset, sent_dep,
									  loc_text, loc_token_idx_seq, loc_head_token_idx_in_sent, sent_offset, sent_dep,
									  ex_lowest_subtree, is_gold_event=False,
									  is_expanded_from_bac=True, exp_source=(bac_text, loc_text), exp_type=(exp_type, ''))
			expanded_input_items.append(ex_input_item)
			ex_cnt += 1

	if not expanded_input_items:
		print '   (Nothing to expand...)'
		return []

	return expanded_input_items


def get_meronym_ref_indices_in_sent(input_token_idx, sent_dep):
	"""

	:type input_token_idx: int
	:type sent_dep: sent_dep.SentDep
	:rtype: list[int]
	"""
	debug = False
	#debug = True

	ref_indices = []

	for token_idx, token in enumerate(sent_dep.get_sent_tokens()):

		#if token_idx in bac_token_idx_seq or token_idx in loc_token_idx_seq:
		#	continue

		if input_token_idx < token_idx:
			if debug:
				ref_head_token = sent_dep.get_token(input_token_idx)
				print '!!@@!! super="%s" / sub="%s"(%d)' % (ref_head_token, token, token_idx)
			_, ex_token_idx = check_numerical_ref_for_ent(input_token_idx, token_idx, sent_dep)
		else:
			if debug:
				ref_head_token = sent_dep.get_token(input_token_idx)
				print '!!@@!! super="%s"(%d) / sub="%s"' % (token, token_idx, ref_head_token)
			ex_token_idx, _ = check_numerical_ref_for_ent(token_idx, input_token_idx, sent_dep)

		if ex_token_idx >= 0:
			ref_indices.append(ex_token_idx)

	return ref_indices


def expand_input_item_by_meronyms(input_item, id_suffix='', is_for_ex=False):
	"""

	:type input_item: InputItem
	:type id_suffix: str
	:return:
	"""
	input_id = input_item.get_id()
	sent_dep, _ = input_item.get_sent_dep()
	sent_offset, _ = input_item.get_sent_offsets()
	(bac_id, bac_text, bac_token_idx_seq, loc_id, loc_text, loc_token_idx_seq) = input_item.get_bac_and_loc()
	bac_head_token_idx_in_sent, loc_head_token_idx_in_sent = input_item.get_head_token_idx_pair()

	bac_text_replaced, _ = replace_multibytes(bac_text)
	loc_text_replaced, _ = replace_multibytes(loc_text)

	expanded_input_items = []
	ex_cnt = 0

	#bac_head_token = sent_dep.get_token(bac_head_token_idx_in_sent)

	debug = False
	# debug = True

	print 'Expanding by meronyms (%sinput: BAC "%s"(%s) & LOC "%s"(%s))...' % (
		'ex-' if is_for_ex else '', bac_text_replaced, bac_id, loc_text_replaced, loc_id)

	expanded_idx_pairs = []

	for cand_bac_ref_idx in get_meronym_ref_indices_in_sent(bac_head_token_idx_in_sent, sent_dep):
		if cand_bac_ref_idx in bac_token_idx_seq or cand_bac_ref_idx in loc_token_idx_seq \
				or cand_bac_ref_idx == loc_head_token_idx_in_sent:
			continue

		expanded_idx_pairs.append((cand_bac_ref_idx, loc_head_token_idx_in_sent, True))

	for cand_loc_ref_idx in get_meronym_ref_indices_in_sent(loc_head_token_idx_in_sent, sent_dep):
		if cand_loc_ref_idx in bac_token_idx_seq or cand_loc_ref_idx in loc_token_idx_seq \
				or cand_loc_ref_idx == bac_head_token_idx_in_sent:
			continue

		expanded_idx_pairs.append((bac_head_token_idx_in_sent, cand_loc_ref_idx, False))

	for ex_bac_head_idx, ex_loc_head_idx, is_expanded_from_bac in expanded_idx_pairs:
		exp_type = id_suffix

		if is_expanded_from_bac:
			exp_source = (bac_text, '')
			exp_type = (exp_type, '')
			ex_bac_token = sent_dep.get_token(ex_bac_head_idx)
			ex_bac_token_idx_seq = [ex_bac_head_idx]
			ex_loc_token = loc_text
			ex_loc_token_idx_seq = loc_token_idx_seq
			print '   ~~~~ "%s"(%d) [%s] (BAC: "%s"(%s))' % (ex_bac_token, ex_bac_head_idx, exp_type, bac_text_replaced, bac_id)
		else:
			exp_source = ('', loc_text)
			exp_type = ('', exp_type)
			ex_bac_token = bac_text
			ex_bac_token_idx_seq = bac_token_idx_seq
			ex_loc_token = sent_dep.get_token(ex_loc_head_idx)
			ex_loc_token_idx_seq = [ex_loc_head_idx]
			print '   ~~~~ "%s"(%d) [%s] (LOC: "%s"(%s))' % (ex_loc_token, ex_loc_head_idx, exp_type, loc_text_replaced, loc_id)

		ex_input_id = str(input_id) + '-ex%s%d' % ('-' + id_suffix if id_suffix else '', ex_cnt)
		ex_bac_id = 'exB-s%s-h%s' % (str(sent_offset), ex_bac_head_idx)
		ex_loc_id = 'exL-s%s-h%s' % (str(sent_offset), ex_loc_head_idx)
		ex_lowest_subtree = sent_dep.get_lowest_subtree(ex_bac_head_idx, loc_head_token_idx_in_sent)


		assert ex_lowest_subtree

		ex_input_item = InputItem(ex_input_id, ex_bac_id, ex_loc_id,
								  ex_bac_token, ex_bac_token_idx_seq, ex_bac_head_idx, sent_offset, sent_dep,
								  ex_loc_token, ex_loc_token_idx_seq, ex_loc_head_idx, sent_offset, sent_dep,
								  ex_lowest_subtree, is_gold_event=False,
								  is_expanded_from_bac=is_expanded_from_bac, exp_source=exp_source, exp_type=exp_type)
		expanded_input_items.append(ex_input_item)
		ex_cnt += 1

	if not expanded_input_items:
		print '   (Nothing to expand...)'
		return []

	return expanded_input_items


def expand_input_items(input_item, all_input_items_in_doc, trigger_map, all_gold_entities):
	"""

	:type input_item: InputItem
	:type all_input_items_in_doc: list[InputItem]
	:type trigger_map: TriggerMap
	:type all_gold_entities: list[Entity]
	:rtype: list[InputItem]
	"""

	input_id = input_item.get_id()
	sent_dep, _ = input_item.get_sent_dep()
	sent_offset, _ = input_item.get_sent_offsets()
	(bac_id, bac_text, bac_token_idx_seq, loc_id, loc_text, loc_token_idx_seq) = input_item.get_bac_and_loc()
	bac_head_token_idx_in_sent, loc_head_token_idx_in_sent = input_item.get_head_token_idx_pair()

	bac_item = bac_id, bac_text, bac_token_idx_seq, bac_head_token_idx_in_sent
	loc_item = loc_id, loc_text, loc_token_idx_seq, loc_head_token_idx_in_sent

	expanded_input_items_by_syn = expand_input_item_by_syntax(bac_item, loc_item, input_id, sent_offset, sent_dep, id_suffix='syn')
	expanded_input_items_by_sem = expand_input_item_by_semantics(input_item, trigger_map, id_suffix='sem')

	expanded_input_items_by_semsyn = []
	for ex_i, ex_input_item in enumerate(expanded_input_items_by_sem):
		(ex_bac_id, ex_bac_text, ex_bac_token_idx_seq, ex_loc_id, ex_loc_text, ex_loc_token_idx_seq) = ex_input_item.get_bac_and_loc()
		ex_bac_head_token_idx_in_sent, ex_loc_head_token_idx_in_sent = ex_input_item.get_head_token_idx_pair()
		ex_bac_item = ex_bac_id, ex_bac_text, ex_bac_token_idx_seq, ex_bac_head_token_idx_in_sent
		ex_loc_item = ex_loc_id, ex_loc_text, ex_loc_token_idx_seq, ex_loc_head_token_idx_in_sent

		expanded_input_items_by_semsyn.extend(expand_input_item_by_syntax(ex_bac_item, ex_loc_item, input_id, sent_offset, sent_dep, id_suffix='semsyn'))

	expanded_input_items = expanded_input_items_by_syn + expanded_input_items_by_sem + expanded_input_items_by_semsyn

	expanded_input_items_by_meronyms = expand_input_item_by_meronyms(input_item, id_suffix='meronym')

	for ex_i, ex_input_item in enumerate(expanded_input_items):
		expanded_input_items_by_meronyms.extend(expand_input_item_by_meronyms(ex_input_item, id_suffix='meronym', is_for_ex=True))

	expanded_input_items.extend(expanded_input_items_by_meronyms)

	filtered_items = remove_duplicate_expansion(expanded_input_items, input_item, all_input_items_in_doc, all_gold_entities)
	return filtered_items


def remove_duplicate_expansion(expanded_input_items, original_input_item, all_input_items, all_gold_entities):
	"""

	:type expanded_input_items: list[InputItem]
	:type original_input_item: InputItem
	:type all_input_items: list[InputItem]
	:type all_gold_entities: list[Entity]
	:rtype: list[InputItem]
	"""
	filtered_items = []
	origin_bac_token_idx, origin_loc_token_idx = original_input_item.get_head_token_idx_pair()

	dup_span = ''

	print '\nFiltering out expanded input items'


	for ex_i, expanded_item in enumerate(expanded_input_items):
		reason_for_out = ''
		is_duplicated = False
		ex_bac_token_idx, ex_loc_token_idx = expanded_item.get_head_token_idx_pair()

		assert expanded_item.is_intra_sent()
		sent_offset, _ = expanded_item.get_sent_offsets()

		if ex_bac_token_idx == ex_loc_token_idx:
			reason_for_out = 'same bac and loc token indices: idx=%d' % ex_bac_token_idx
			is_duplicated = True

		is_expanded_from_bac = (ex_bac_token_idx != origin_bac_token_idx)
		is_expanded_from_loc = (ex_loc_token_idx != origin_loc_token_idx)

		ex_bac_id = ex_bac_token_idx if is_expanded_from_bac else expanded_item.get_bac_id()
		ex_loc_id = ex_loc_token_idx if is_expanded_from_loc else expanded_item.get_loc_id()

		print '   BAC%s="%s"(%s), LOC%s="%s"(%s)' % (
			'(ex)' if is_expanded_from_bac else '', expanded_item.get_bac_text(), ex_bac_id,
			'(ex)' if is_expanded_from_loc else '', expanded_item.get_loc_text(), ex_loc_id)

		ex_sent_offset, _ = expanded_item.get_sent_offsets()

		if not is_duplicated:
			for another_expanded_item in expanded_input_items[ex_i + 1:]:
				if another_expanded_item.is_cross_sent() \
						or another_expanded_item.get_sent_offsets()[0] != sent_offset:
					continue

				if (ex_bac_token_idx, ex_loc_token_idx) == another_expanded_item.get_head_token_idx_pair():
					reason_for_out = 'Duplicated with another expanded item: B="%s", L="%s"' % (
						another_expanded_item.get_bac_text(), another_expanded_item.get_loc_text())
					is_duplicated = True
					break

		if not is_duplicated:

			for another_input_item in all_input_items:
				if another_input_item.is_cross_sent():
					continue
				another_sent_offset, _ = another_input_item.get_sent_offsets()
				if ex_sent_offset != another_sent_offset:
					continue

				if (ex_bac_token_idx, ex_loc_token_idx) == another_input_item.get_head_token_idx_pair():
					#print '!!!@@', (ex_bac_token_idx, ex_loc_token_idx), another_input_item.get_head_token_idx_pair()
					reason_for_out = 'Duplicated with another input item: B="%s", L="%s"' % (
						another_input_item.get_bac_text(), another_input_item.get_loc_text())
					is_duplicated = True
					break

		if not is_duplicated:

			for gold_entity in all_gold_entities:
				if gold_entity.get_sent_offset() == ex_sent_offset:
					#print '   !!!~~Comparing to', gold_entity.get_text(), gold_entity.get_sent_offset(), ex_sent_offset

					gold_ent_token_idx = gold_entity.get_head_token_idx_in_sent()
					if (is_expanded_from_bac and ex_bac_token_idx == gold_ent_token_idx) \
							or (is_expanded_from_loc and ex_loc_token_idx == gold_ent_token_idx):
						reason_for_out = 'Duplicated with a gold entity'
						is_duplicated = True
						break
						pass

		if not is_duplicated:
			print '    ==> IN'
			filtered_items.append(expanded_item)
		else:
			print '    ==> OUT (%s)' % (reason_for_out)


	return filtered_items


g_cell_terms = ['host', 'human', 'plant', 'animal']


def is_non_target_cell(text_span, token_idx_seq, loc_sent_dep, loc_prep_matched=None, want_check_prep=True):

	if text_span.endswith('cells') or text_span.endswith('cell'):
		cell_token_idx = token_idx_seq[-1]

		for prev_token_idx in range(cell_token_idx - 1, -1, -1):
			prev_token = loc_sent_dep.get_token(prev_token_idx)
			#print '%%$', prev_token_idx, prev_token
			if not prev_token.isalpha():
				continue

			prev_lemma = lemmatizer.lemmatize(prev_token, pos='n')
			if prev_lemma in g_cell_terms:
				parents = loc_sent_dep.get_parent_tokens(prev_token_idx)
				if parents:
					parent_token_idx, _ = parents[0]
					if parent_token_idx == cell_token_idx:
						return False

		if want_check_prep and not loc_prep_matched:
			return True

		prep_idx, prep_token = loc_prep_matched

		if prep_token == 'in' or prep_token == 'inside' or prep_token == 'into':
			return False
		else:
			return True

	return False


def syntactic_decision_filtering(input_item, trigger, loc_prep_matched, verb_matched, sent_dep):
	"""

	:type input_item: InputItem
	:type trigger: (int, str)
	:type loc_prep_matched: (int, str)
	:type verb_matched: str
	:type sent_dep: sent_dep.SentDep
	:rtype: bool
	"""
	is_filtered_in = True


	loc_text = input_item.get_loc_text()
	_, loc_sent_dep = input_item.get_sent_dep()
	loc_token_idx_seq = input_item.get_loc_token_idx_seq()
	#msg = "filtering out for 'cells'"

	if is_non_target_cell(loc_text, loc_token_idx_seq, loc_sent_dep, loc_prep_matched):
		print '====###===> [intra] Filtered out (LOC is "cell")!: "%s"' % (loc_text)
		is_filtered_in = False

	if not is_filtered_in:
		return is_filtered_in

	bac_token_idx_seq = input_item.get_bac_token_idx_seq()

	is_filtered_in = check_valid_modality_between_bac_and_loc_in_sent(bac_token_idx_seq, loc_token_idx_seq, trigger, sent_dep, rel_type='intra')
	return is_filtered_in



def check_valid_modality_between_bac_and_loc_in_sent(bac_token_idx_seq, loc_token_idx_seq, trigger_item, sent_dep, rel_type):
	"""

	:type bac_token_idx: int
	:type loc_token_idx_seq: list[int]
	:type trigger_item: (int, str)
	:type sent_dep: sent_dep.SentDep
	:return:
	"""

	bac_first_token_idx = bac_token_idx_seq[0]
	loc_first_token_idx = loc_token_idx_seq[0]

	if trigger_item:
		trigger_token_idx, trigger_span = trigger_item
		if trigger_token_idx >= 0:
			token_indices_interested = [bac_first_token_idx, loc_first_token_idx, trigger_token_idx]
		else:
			token_indices_interested = [bac_first_token_idx, loc_first_token_idx]
	else:
		token_indices_interested = [bac_first_token_idx, loc_first_token_idx]

	for token_idx in token_indices_interested:
		#if token_idx == bac_first_token_idx or token_idx == loc_first_token_idx:
		#	pass

		detected_phrase = check_negation_scope(token_idx, sent_dep)
		if detected_phrase:
			print '====###===> [%s] Filtered out by negation!: %s' % (rel_type, detected_phrase)
			return False

		if token_idx == bac_first_token_idx:
			detected_phrase = check_others_scope(token_idx, sent_dep)
			if detected_phrase:
				print '====###===> [%s] Filtered out by other/another/various/diverse!: %s' % (rel_type, detected_phrase)
				return False

	#qty_nouns = g_expansion_cues['qty_nouns']
	#loc_nouns = g_expansion_cues['loc_nouns']
	#if not trigger_lemma in qty_nouns + loc_nouns:
	#	pass

	# "Gram-negative bacterium Vibrio parahaemolyticus" [19049879/5]
	# "The ratios of gram positive bacteria and" [19099664/6]
	# "Pseudomonas aeruginosa is a Gram-negative bacterium that causes ..." [23908036/0]

	return True


def check_entity_span_nested_by_any_other(ent_id, ent_token_idx_seq, ents_in_sent):
	"""

	:type ent_id: str
	:type ent_token_idx_seq: list[int]
	:type ents_in_sent: list[Entity]
	:return:
	"""
	for other_ent in ents_in_sent:
		if ent_id == other_ent.get_id() or ent_token_idx_seq == other_ent.get_token_idx_seq_in_sent():
			continue

		if all((i in other_ent.get_token_idx_seq_in_sent()) for i in ent_token_idx_seq):
			return True

	return False


def check_pairs_for_validity_by_inbetween_entites(input_item, entities_in_sent):
	"""
	:type input_item: InputItem
	:type all_input_items: list[InputItem]
	:type entities_in_sent: list[Entity]
	:return:
	"""

	bac_ents_in_sent = [e for e in entities_in_sent if e.is_bacteria()]
	loc_ents_in_sent = [e for e in entities_in_sent if e.is_location()]

	if len(bac_ents_in_sent) < 2 or len(loc_ents_in_sent) < 2:
		return True

	bac_id = input_item.get_bac_id()
	loc_id = input_item.get_loc_id()
	ent_ids_in_sent = [e.get_id() for e in entities_in_sent]
	if bac_id not in ent_ids_in_sent or loc_id not in ent_ids_in_sent:
		return True

	bac_token_idx_seq = input_item.get_bac_token_idx_seq()
	loc_token_idx_seq = input_item.get_loc_token_idx_seq()
	if check_entity_span_nested_by_any_other(bac_id, bac_token_idx_seq, entities_in_sent) \
			or check_entity_span_nested_by_any_other(loc_id, loc_token_idx_seq, entities_in_sent):
		return True

	non_nested_ents = []

	for ent in entities_in_sent:
		ent_token_idx_seq = ent.get_token_idx_seq_in_sent()
		ent_id = ent.get_id()
		if not check_entity_span_nested_by_any_other(ent_id, ent_token_idx_seq, entities_in_sent):
			non_nested_ents.append(ent)

	non_nested_bac_ents = [e for e in non_nested_ents if e.is_bacteria()]
	non_nested_loc_ents = [e for e in non_nested_ents if e.is_location()]

	if len(non_nested_bac_ents) < 2 or len(non_nested_loc_ents) < 2:
		return True

	bac_head_token_idx, loc_head_token_idx = input_item.get_head_token_idx_pair()

	for other_bac in non_nested_bac_ents:
		if other_bac.get_id() == bac_id:
			continue
		other_bac_idx = other_bac.get_head_token_idx_in_sent()

		for other_loc in non_nested_loc_ents:
			if other_loc.get_id() == loc_id:
				continue
			other_loc_idx = other_loc.get_head_token_idx_in_sent()
			if bac_head_token_idx < other_loc_idx < other_bac_idx < loc_head_token_idx \
					or loc_head_token_idx < other_bac_idx < other_loc_idx < bac_head_token_idx:
				return False

	return True



def detect_event_by_local_syntax(input_item, is_expanded=False):
	"""

	:type input_item: InputItem
	:rtype: None | (str, (int, str), str, str)
	"""
	trigger = ''
	loc_prep_matched = ''
	verb_matched = ''
	false_result = None

	(bac_id, bac_text, bac_token_idx_seq, loc_id, loc_text, loc_token_idx_seq) = input_item.get_bac_and_loc()
	bac_head_token_idx_in_sent, loc_head_token_idx_in_sent = input_item.get_head_token_idx_pair()
	sent_offset, _ = input_item.get_sent_offsets()
	sent_dep, _ = input_item.get_sent_dep()
	path_to_bac, path_to_loc = input_item.get_lowest_subtree()

	result = get_local_context_triggers(bac_token_idx_seq, path_to_bac,
										loc_token_idx_seq, path_to_loc, sent_dep,
										is_expanded=is_expanded, debug_print=True)
	if result:
		trigger, loc_prep_matched = result
		if syntactic_decision_filtering(input_item, trigger, loc_prep_matched, verb_matched, sent_dep):
			#triggers.append(trigger)
			match_type = 'trigger'
			#input_item.mark_predicted('trigger')
			return match_type, trigger, loc_prep_matched, verb_matched

	if apply_simple_patterns(bac_token_idx_seq, bac_head_token_idx_in_sent, bac_text, path_to_bac,
							 loc_token_idx_seq, loc_head_token_idx_in_sent, loc_text, path_to_loc,
							 sent_dep, is_expanded=is_expanded):
		#print '=====>(1/2) MATCHED BY SIMPLE PATTERNS'

		if syntactic_decision_filtering(input_item, trigger, loc_prep_matched, verb_matched, sent_dep):
			match_type = 'simple'
			#input_item.mark_predicted('simple')

			#print '=====>(2/2) MATCHED BY SIMPLE PATTERNS - filtered in!'
			return match_type, trigger, loc_prep_matched, verb_matched


	return false_result




def detect_intrasent_events(input_items, trigger_map, hypo_words_per_sent, doc_bbevent):
	"""

	:type input_items: list[InputItem]
	:type trigger_map: TriggerMap
	:type hypo_words_per_sent: dict[int, list[(int, str)]]
	:type doc_bbevent: Doc
	:return:
	"""

	bac_list = list(doc_bbevent.iter_bacteria_entities())
	loc_list = list(doc_bbevent.iter_location_entities())
	ent_list = bac_list + loc_list
	doc_id = doc_bbevent.get_id()

#	print 'Bacteria-direct trigger mapping: %s' % trigger_policy
#	trigger_map.show_mapping_in_sent(trigger_type='direct')
#	print 'Bacteria-indirect trigger mapping: %s' % trigger_policy
#	trigger_map.show_mapping_in_sent(trigger_type='indirect')

	initial_num_predicted_events = len([i for i in input_items if i.is_predicted()])
	num_gold_events = len([i for i in input_items if i.is_gold_event()])
	entities_per_sent = {}

	for input_item in input_items:
		if input_item.is_cross_sent() or input_item.is_predicted():
			continue
		sent_offset = input_item.get_sent_offsets()[0]
		if sent_offset not in entities_per_sent:
			entities_per_sent[sent_offset] = [e for e in ent_list if e.get_sent_offset() == sent_offset]

	triggers = []

	if not input_items:
		print 'No intra-sentential events in this doc. Nothing to collect.'
		return triggers

	#print '@@!!$$ all input items', '\n'.join('  "%s"(%d), "%s"(%d)' % (i.get_bac_text(), i.get_bac_head_token_idx_in_sent(), i.get_loc_text(), i.get_loc_head_token_idx_in_sent()) for i in input_items)

	expanded_input_dict = {}

	for input_item in input_items:
		if input_item.is_cross_sent() or input_item.is_predicted():
			continue

		print_intra_input_pairs(input_item, doc_id)

		if input_item.is_intra_sent():
			bac_head, loc_head = input_item.get_head_token_idx_pair()
			if bac_head == loc_head:
				print '** Bacteria and location have the same head token... Not a candidate for prediction!'
				continue

		sent_offset = input_item.get_sent_offsets()[0]
		entities_in_sent = entities_per_sent[sent_offset]

		if not check_pairs_for_validity_by_inbetween_entites(input_item, entities_in_sent):
			print '** Filtered out by invalid sequence of BAC and LOC in sent!'
			continue

		detection_result = detect_event_by_local_syntax(input_item)
		if detection_result:
			match_type, trigger, loc_prep_matched, verb_matched = detection_result
			if trigger:
				triggers.append(trigger)

			is_hypo_scoped = hypo_words_per_sent and check_input_for_hypo_scope(input_item, hypo_words_per_sent)

			if is_hypo_scoped:
				print ' ** ===###==> hypothesis filtered out!'
			else:
			#	if check_pairs_for_validity_by_inbetween_entites(input_item, entities_in_sent):
			#		input_item.mark_predicted(match_type)  # 'trigger' or 'simple'
			#	else:
			#		print '  ******* ===> Filtered out by invalid sequence of BAC and LOC in sent!'
				print ' ** ====> Predicted as a positive event! (original pair)'
				input_item.mark_predicted(match_type)  # 'trigger' or 'simple'

		print '\n', '^^^^' * 5, "Expanding input pair", '^^^^' * 5
		expanded_input_items = expand_input_items(input_item, input_items, trigger_map, ent_list)

		is_predicted_by_exp = False

		for ex_i, ex_input_item in enumerate(expanded_input_items):
			print '\nEX-INPUT(%d): "%s" (%d) & "%s" (%d) / exp_type=%s [%s]' % (
				ex_i, ex_input_item.get_bac_text(), ex_input_item.get_bac_head_token_idx_in_sent(),
				ex_input_item.get_loc_text(), ex_input_item.get_loc_head_token_idx_in_sent(),
				str(ex_input_item.get_exp_type()), ex_input_item.get_id())
			#if get_local_context_triggers(ex_input_item, is_expanded=True)\
			#		or apply_simple_patterns(ex_input_item, is_expanded=True):
			if detect_event_by_local_syntax(ex_input_item, is_expanded=True):
				if not hypo_words_per_sent or not check_input_for_hypo_scope(input_item, hypo_words_per_sent):
				#	if check_pairs_for_validity_by_inbetween_entites(input_item, entities_in_sent):
				#		input_item.mark_predicted('expansion')
				#		is_predicted_by_exp = True
				#	else:
				#		print '  ******* ===> Filtered out by invalid sequence of BAC and LOC in sent!'

					if not detection_result:
						print ' ** ====> Predicted as a positive event! (expanded pair)'
						input_item.mark_predicted('expansion')
					else:
						print ' ** (The original pair has already been predicted as positive. No need to duplicate prediction!)'
					is_predicted_by_exp = True
					break

		if not is_predicted_by_exp:
			expanded_input_dict[input_item.get_id()] = expanded_input_items

	predicted_items = [i for i in input_items if i.is_predicted()]
	num_predicted_items = len(predicted_items)
	num_input_items = len(input_items)
	print '\n', '####' * 14

	if num_predicted_items > initial_num_predicted_events:
		print 'Propagation through patterns (doc: %s)' % doc_id
		print 'All: %d / Gold: %d / Predicted: %d / Remaining: %d' % (
			num_input_items, num_gold_events, num_predicted_items, num_input_items - num_predicted_items)

		is_new_candidate = True
		propa_round = 0

		while is_new_candidate:
			print '\n', '<<<<<<' * 4 + '>>>>>>' * 4
			print '<<<<<<' * 2, ' Propagation Round %d' % (propa_round), '>>>>>>>' * 2
			print '<<<<<<' * 4 + '>>>>>>' * 4

			is_new_candidate = False

			for input_item in input_items:
				if input_item.is_cross_sent() or input_item.is_predicted():
					continue

				print_intra_input_pairs(input_item, doc_id, is_for_propagation=True)

				sent_offset = input_item.get_sent_offsets()[0]
				entities_in_sent = entities_per_sent[sent_offset]
				if not check_pairs_for_validity_by_inbetween_entites(input_item, entities_in_sent):
					print '** Filtered out by invalid sequence of BAC and LOC in sent!'
					continue

				if input_item.is_intra_sent():
					bac_head, loc_head = input_item.get_head_token_idx_pair()
					if bac_head == loc_head:
						continue

				expanded_input_items = expanded_input_dict[input_item.get_id()]
				result = propagate_relations_among_input_items(input_item, expanded_input_items, predicted_items)

				if result:
					if not hypo_words_per_sent or not check_input_for_hypo_scope(input_item, hypo_words_per_sent):
						print ' ** ====> Predicted as a positive event! (propagated pair)'
						input_item.mark_predicted('expansion')
						predicted_items.append(input_item)
						is_new_candidate = True
				else:
					print '\n   ===> Nothing to propagate... fail!'

			propa_round += 1

	elif num_predicted_items == initial_num_predicted_events:
		print 'All pairs have been predicted. Nothing to propagate.'
	else:
		print 'No predicted pairs. Nothing to propagate.'


	#final_num_predicted_events = len([i for i in input_items if i.is_predicted()])

	# ====================================================================
	return triggers


if __name__ == '__main__':
	pass
