from concepts import Doc, Entity, InputItem
from triggers import TriggerMap, get_local_context_triggers
from extract_intrasent_events import apply_simple_patterns, expand_input_item_by_syntax, g_expansion_cues, \
	check_valid_modality_between_bac_and_loc_in_sent
from modality import check_token_for_hypo_scope_in_sent, check_negation_scope
from multibytes import replace_multibytes

from nltk.stem.lancaster import LancasterStemmer
lancaster_stemmer = LancasterStemmer()
stemmer = lancaster_stemmer


def create_entity_map_from_predictions(input_items):
	intra_map_for_bac = {}
	intra_map_for_loc = {}

	for input_item in input_items:
		bac_id = input_item.get_bac_id()
		loc_id = input_item.get_loc_id()

		if input_item.is_cross_sent():
			continue

		if bac_id not in intra_map_for_bac:
			intra_map_for_bac[bac_id] = []
		if loc_id not in intra_map_for_loc:
			intra_map_for_loc[loc_id] = []

		if input_item.is_predicted():
			assert bac_id not in intra_map_for_loc[loc_id]
			assert loc_id not in intra_map_for_bac[bac_id]
			intra_map_for_bac[bac_id].append(loc_id)
			intra_map_for_loc[loc_id].append(bac_id)

	intra_map_for_bac = dict((bac_id, sorted(intra_map_for_bac[bac_id], key=lambda i: int(i[1:]))) for bac_id in intra_map_for_bac)
	intra_map_for_loc = dict((loc_id, sorted(intra_map_for_loc[loc_id], key=lambda i: int(i[1:]))) for loc_id in intra_map_for_loc)

	return intra_map_for_bac, intra_map_for_loc


def detect_intrasent_rel_between_trigger_and_loc(trigger_item, loc_item, sent_dep, debug_print=True):

	trigger_id, trigger_text, trigger_token_idx_seq, trigger_token_idx = trigger_item
	loc_id, loc_text, loc_token_idx_seq, loc_head_token_idx = loc_item

	path_to_trigger, path_to_loc = sent_dep.get_lowest_subtree(trigger_token_idx, loc_head_token_idx)

	result1 = get_local_context_triggers([trigger_token_idx], path_to_trigger, loc_token_idx_seq, path_to_loc,
										 sent_dep, debug_print=debug_print)

	if result1:
		asso_trigger, loc_prep_matched = result1
		_, asso_trigger_span = asso_trigger
		rel_type = 'asso_trigger-"%s"-"%s"' % (asso_trigger_span, loc_prep_matched[1])
		return rel_type, asso_trigger

	result2 = apply_simple_patterns([trigger_token_idx], trigger_token_idx, trigger_text, path_to_trigger,
									loc_token_idx_seq, loc_head_token_idx, loc_text, path_to_loc, sent_dep)

	if result2:
		rel_type = 'simple'
		return rel_type, None

	return None


def check_two_bac_ents_compatible(bac1_text, bac1_head_token, bac2_text, bac2_head_token):

	if bac1_text == bac2_text:
		return True

	bac1_words = bac1_text.split()
	bac2_words = bac2_text.split()

	if len(bac1_words) == len(bac2_words):

		for bac1_word, bac2_word in zip(bac1_words, bac2_words):
			if bac1_word == bac2_word:
				continue
			elif bac1_word[0] == bac2_word[0] \
					and ((len(bac1_word) == 2 and bac1_word.endswith('.')) or (len(bac2_word) == 2 and bac2_word.endswith('.'))):
				continue
			elif (bac1_word.endswith("bacteria") or bac1_word.endswith("bacterium") or bac1_word.endswith("bacterial")) \
					and (bac2_word.endswith("bacteria") or bac2_word.endswith("bacterium") or bac2_word.endswith("bacterial")):
				if bac1_word[:bac1_word.find("bacteri")] == bac2_word[:bac2_word.find("bacteri")]:
					continue
				else:
					return False
			else:
				return False
		return True
	elif bac1_head_token == bac2_head_token and (len(bac1_words) == 1 or len(bac2_words) == 1):
		return True

	return False


def select_relevant_locs_by_strict_rules(bac, loc_ents, loc_id_to_triggers_map,
										 loc_expansion_map, triggers_in_bac_sent):
	selected_locs = []
	direct_generic_bac_terms = TriggerMap.direct_generic_terms

	for loc in loc_ents:
		loc_id = loc.get_id()

		if loc_id in loc_expansion_map:
			loc = loc_expansion_map[loc_id]
			loc_id = loc.get_id()

		print '       | "%s" <= ' % (loc.get_text()),

		is_relevant_trigger_found = False

		for token_idx, trigger_lemma_in_loc_sent in loc_id_to_triggers_map[loc_id]:

			print '"%s"(ti=%d)' % (trigger_lemma_in_loc_sent, token_idx),

			if trigger_lemma_in_loc_sent in direct_generic_bac_terms:
				print "\n          ---> DIRECT TRIGGER! \"%s\"" % trigger_lemma_in_loc_sent,
				is_relevant_trigger_found = True
				break

			for trigger_item in triggers_in_bac_sent:
				trigger_token_idx_in_bac_sent, trigger_lemma_in_bac_sent, trigger_freq = trigger_item

				if trigger_lemma_in_bac_sent == trigger_lemma_in_loc_sent:
					is_relevant_trigger_found = True
					break
				else:
					trigger_stem_in_bac_sent = stemmer.stem(trigger_lemma_in_bac_sent)
					trigger_stem_in_loc_sent = stemmer.stem(trigger_lemma_in_loc_sent)
					if trigger_stem_in_bac_sent == trigger_stem_in_loc_sent:
						is_relevant_trigger_found = True
						break
			#
			if is_relevant_trigger_found:
				print "\n          ---> TRIGGER is found in BAC sent : \"%s\"" % trigger_lemma_in_loc_sent,
				break

		print

		if is_relevant_trigger_found:
			selected_locs.append(loc)

	return selected_locs


def check_propagation_by_syntax_between_two_locs(loc1, loc2, sent_dep):

	loc1_head_token_idx_in_sent = loc1.get_head_token_idx_in_sent()
	loc1_token_idx_seq = loc1.get_token_idx_seq_in_sent()
	loc1_text = loc1.get_text()

	loc2_head_token_idx_in_sent = loc2.get_head_token_idx_in_sent()
	loc2_token_idx_seq = loc2.get_token_idx_seq_in_sent()
	loc2_text = loc2.get_text()

	sep = '****' * 16

	is_loc_nested = all((idx in loc1_token_idx_seq) for idx in loc2_token_idx_seq)

	if is_loc_nested:
		print ' ', sep
		if is_loc_nested:
			print '  ***** Propagation (nested LOC): "%s" %s "%s"' % (
				loc2_text, '==' if loc1_text == loc2_text else '<=', loc1_text)

		print ' ', sep
		return True

	is_loc_conj = sent_dep.check_t1_conj_t2(loc1_head_token_idx_in_sent, loc2_head_token_idx_in_sent)


	if not is_loc_conj:
		token_in_loc_middle = ''
		if loc2_token_idx_seq[0] - loc1_token_idx_seq[-1] == 2:
			token_in_loc_middle = sent_dep.get_token(loc1_token_idx_seq[-1] + 1)
		elif loc1_token_idx_seq[0] - loc2_token_idx_seq[-1] == 2:
			token_in_loc_middle = sent_dep.get_token(loc2_token_idx_seq[-1] + 1)
		is_loc_conj = (token_in_loc_middle == 'and' or token_in_loc_middle == 'or')

	if is_loc_conj:
		print ' ', sep, '\n  ***** Propagation (LOC conj LOC): "%s" and "%s"' % (loc1_text, loc2_text), '\n ', sep
		return True

	is_loc_of_loc = False

	if loc2_head_token_idx_in_sent < loc1_head_token_idx_in_sent:
		phrase = sent_dep.check_t1_prep_t2(loc2_head_token_idx_in_sent, loc1_head_token_idx_in_sent)
	else:
		phrase = sent_dep.check_t1_prep_t2(loc1_head_token_idx_in_sent, loc2_head_token_idx_in_sent)

	if phrase:
		is_loc_of_loc = True
	elif loc2_head_token_idx_in_sent < loc1_head_token_idx_in_sent:
		phrase = sent_dep.check_t1_ving_or_ved_prep_t2(loc2_head_token_idx_in_sent, loc1_head_token_idx_in_sent)
	else:
		phrase = sent_dep.check_t1_ving_or_ved_prep_t2(loc1_head_token_idx_in_sent, loc2_head_token_idx_in_sent)

	if phrase:
		is_loc_of_loc = True

	if is_loc_of_loc:
		print ' ', sep, '\n  ***** Propagation (LOC %s LOC): "%s" %s "%s"' % (phrase, loc1_text, phrase, loc2_text), '\n ', sep
		return True

	is_loc_appos = sent_dep.check_t1_appos_t2(loc1_head_token_idx_in_sent, loc2_head_token_idx_in_sent)

	if not is_loc_appos:
		is_loc_appos = (sent_dep.check_t1_comma_t2(loc1_head_token_idx_in_sent, loc1_token_idx_seq,
												  loc2_head_token_idx_in_sent, loc2_token_idx_seq)
						or sent_dep.check_t1_comma_t2(loc2_head_token_idx_in_sent, loc2_token_idx_seq,
												  loc1_head_token_idx_in_sent, loc1_token_idx_seq))

	if is_loc_appos:
		print ' ', sep, '\n  ***** Propagation (LOC appos LOC): "%s" <- "%s"' % (loc1_text, loc2_text), '\n ', sep
		return True

	is_loc_equi = (sent_dep.check_t1_is_t2(loc1_head_token_idx_in_sent, loc2_head_token_idx_in_sent)
				   or sent_dep.check_t1_is_t2(loc2_head_token_idx_in_sent, loc1_head_token_idx_in_sent))

	if is_loc_equi:
		print ' ', sep, '\n  ***** Propagation (LOC is LOC): "%s" and "%s"' % (loc1_text, loc2_text), '\n ', sep
		return True

	path_from_subroot_to_loc1, path_from_subroot_to_loc2 \
		= sent_dep.get_lowest_subtree(loc1_head_token_idx_in_sent, loc2_head_token_idx_in_sent)
	is_loc_nn = sent_dep.check_two_modified_in_common_np(
						loc1_head_token_idx_in_sent, loc2_head_token_idx_in_sent,
						path_from_subroot_to_loc1, path_from_subroot_to_loc2)

	if is_loc_nn:
		print ' ', sep, '\n  ***** Propagation (LOC[noun]-LOC[noun): "%s" and "%s"' % (loc1_text, loc2_text), '\n ', sep
		return True


def propagate_cand_loc_per_sent(cand_loc_ents_per_sent, sent_dep_list, doc):

	print '\n$$$$$$$$$ Propagation Check (between locations)! $$$$$$$$$'


	sent_offsets = ['T'] + range(doc.get_num_sents())

	debug_print = False
	#debug_print = True

	cand_loc_expansion_map = {}

	for sent_offset in sent_offsets:

		loc_ents_to_be_added = []

		cand_loc_ents_in_sent = cand_loc_ents_per_sent[sent_offset]
		cand_loc_ids_in_sent = [l.get_id() for l in cand_loc_ents_in_sent]

		if sent_offset == 'T':
			sent_dep = sent_dep_list[0]
		else:
			sent_dep = sent_dep_list[sent_offset + 1]

		another_loc_ents_in_sent = doc.get_loc_entities_in_sent(sent_offset)

		for loc in cand_loc_ents_in_sent:
			print '[S%s] Trying to propagate "%s"(%s) ...' % (str(sent_offset), loc.get_text(), loc.get_id())

			for another_loc in another_loc_ents_in_sent:
				if another_loc.get_id() in cand_loc_ids_in_sent:
					continue

				if debug_print:
					print '   - another_loc: "%s"/%s' % (another_loc.get_text(), another_loc.get_id())
					print '   - loc_ents_to_be_added:', [e.get_text() for e in loc_ents_to_be_added]

				if another_loc not in loc_ents_to_be_added \
						and check_propagation_by_syntax_between_two_locs(loc, another_loc, sent_dep):
					loc_ents_to_be_added.append(another_loc)
					cand_loc_expansion_map[another_loc.get_id()] = loc

		cand_loc_ents_in_sent.extend(loc_ents_to_be_added)

		cand_loc_ents_per_sent[sent_offset] = sorted(cand_loc_ents_in_sent, key=lambda e: int(e.get_id()[1:]))


	return cand_loc_ents_per_sent, cand_loc_expansion_map


def print_cand_loc_ents_per_sent(cand_loc_ents_per_sent, loc_to_triggers_map,
								 cand_loc_exp_map, doc_id):
	"""
	:type cand_loc_ents_per_sent: dict[int, list[Entity]]
	:type loc_to_triggers_map: dict[str, list[(int, str)]]
	:type cand_loc_exp_map: dict[str, Entity]
	:type doc_id:
	"""

	print '\n=========================================================================='
	print '   Final candidate set of location entities for cross-sentence inference'
	print '==========================================================================\n'

	sent_offsets = ['T'] + sorted(o for o in cand_loc_ents_per_sent if isinstance(o, int))
	print 'DOC:', doc_id

	for sent_offset in sent_offsets:
		cand_loc_ents = cand_loc_ents_per_sent[sent_offset]
		if not cand_loc_ents:
			continue

		print '[S{so}]'.format(so=sent_offset)
		for loc in cand_loc_ents:
			loc_id = loc.get_id()
			print '     {loc_id} "{loc_text}"'.format(loc_text=loc.get_text(), loc_id=loc_id,),
			if loc_id in cand_loc_exp_map:
				original_loc = cand_loc_exp_map[loc_id]
				print ' <~~(by_expansion)~  "%s"(%s)' % (original_loc.get_text(), original_loc.get_id())
			elif loc_id in loc_to_triggers_map:
				print ' <<=(from_trigger)=  ',
				for trigger_token_idx, trigger_span in loc_to_triggers_map[loc_id]:
					print '"%s"(%d)' % (trigger_span, trigger_token_idx),
				print



def select_cand_bac_entities_per_sent(intra_map_for_bac, cross_map_for_bac, hypo_words_per_sent, sent_dep_list, doc,
									  only_bac_with_no_intra_predicted_loc=False,
									  debug_print=False):
	"""

	:param intrasent_input_items:
	:param intra_map_for_bac:
	:param hypo_words_per_sent:
	:param sent_dep_list:
	:param doc:
	:param debug_print:
	:rtype: dict[int, list[Entity]]
	"""

	want_check_hypo_scope = bool(hypo_words_per_sent)
	sent_offsets = ['T'] + range(doc.get_num_sents())


	#entities_by_title_and_sents = dict((so, doc.get_entities_in_title() if so == 'T' else doc.get_entities_in_sent(so))
	#							   for so in sent_offsets)

	print '\n----- Selecting candidate BACTERIA entities for each sentence -----'
	#print 'Candidate BACs must satisfy one of the following two conditions:'
	#print '  (1) They must be found without any LOC within a sentence, or'
	#print '  (2) They must %sbe connected to at least one LOC within a sentence\n' % \
	#	  ('not ' if only_bac_with_no_intra_predicted_loc else '')
	cand_bac_entities_per_sent = {}

	for sent_offset in sent_offsets:

		#if debug_print:
		#	print '[S%s]' % str(sent_offset)

		sent_dep = sent_dep_list[(0 if sent_offset == 'T' else sent_offset + 1)]

		bac_entities_in_sent = doc.get_bac_entities_in_sent(sent_offset)
		loc_entities_in_sent = doc.get_loc_entities_in_sent(sent_offset)

		cand_bac_entities_per_sent[sent_offset] = []

		for bac in sorted(bac_entities_in_sent, key=lambda e: int(e.get_id()[1:])):
			bac_id = bac.get_id()
			bac_token_idx = bac.get_head_token_idx_in_sent()

			intra_mapped_locs = intra_map_for_bac[bac_id] if bac_id in intra_map_for_bac else []
			cross_mapped_locs = cross_map_for_bac[bac_id] if bac_id in cross_map_for_bac else []

			if loc_entities_in_sent:

				if only_bac_with_no_intra_predicted_loc:
					is_valid_cand_bac = not intra_mapped_locs and not cross_mapped_locs

				else:
					is_valid_cand_bac = intra_mapped_locs or cross_mapped_locs

			else:
				is_valid_cand_bac = True

			if not is_valid_cand_bac:
				continue

			bac_text_replaced = replace_multibytes(bac.get_text())[0]

			if want_check_hypo_scope \
					and check_token_for_hypo_scope_in_sent(bac_token_idx, sent_dep, hypo_words_per_sent[sent_offset]):
				#print '     - (hypothesis filtered out!) %s "%s"' % (bac_id, bac_text_replaced)
				print '     ===###==> hypothesis filtered out! BACTERIA %s "%s"' % (bac_id, bac_text_replaced)
				continue

			detected_phrase = check_negation_scope(bac_token_idx, sent_dep)
			if detected_phrase:
				#print '     - (Negation filtered out!) %s %s' % (bac_id, detected_phrase)
				print '     ===###==> Negation filtered out! BACTERIA %s %s' % (bac_id, detected_phrase)
				continue

			if debug_print:
				print '[S%s] %s "%s"' % (str(sent_offset), bac_id, bac_text_replaced)

			cand_bac_entities_per_sent[sent_offset].append(bac)

	return cand_bac_entities_per_sent


def select_cand_loc_entities_per_sent(intra_map_for_loc, hypo_words_per_sent, policy1_for_target_loc, policy2_for_target_loc,
									  trigger_map, min_freq_triggers, sent_dep_list, doc, debug_print=False):
	"""

	:type intra_map_for_loc: dict
	:type hypo_words_per_sent: dict
	:type policy1_for_target_loc: str
	:type policy2_for_target_loc: str
	:type trigger_map: TriggerMap
	:type min_freq_triggers: int
	:type sent_dep_list: list[sent_dep.SentDep]
	:type doc: Doc
	:param debug_print:
	:rtype: (dict[int, list[Entity]], dict[str, list[(int, str)]])
	"""
	doc_id = doc.get_id()
	want_check_hypo_scope = bool(hypo_words_per_sent)
	sent_offsets = ['T'] + range(doc.get_num_sents())

	is_nested_trigger_always_predicted = False
	#is_nested_trigger_always_predicted = True

	qty_nouns = g_expansion_cues['qty_nouns']
	#loc_nouns = g_expansion_cues['loc_nouns']

	print '\n----- Selecting candidate LOCATION entities for each sentence -----'
	cand_loc_entities_per_sent = {}
	loc_to_triggers_syntactic_map = {}

	for sent_offset in sent_offsets:
		triggers_in_loc_sent = trigger_map.get_triggers_in_sent_for_crosssent_detection(sent_offset)
		triggers_in_loc_sent = [(tk_idx, tk_form, freq) for (tk_idx, tk_form, freq) in triggers_in_loc_sent
								if freq >= min_freq_triggers]

		sent_dep = sent_dep_list[(0 if sent_offset == 'T' else sent_offset + 1)]

		#entities_in_sent = doc.get_entities_in_sent(sent_offset)  # type: list[Entity]
		#bac_entities_in_sent = [e for e in entities_in_sent if e.is_bacteria()]
		#loc_entities_in_sent = [e for e in entities_in_sent if e.is_location()]
		bac_entities_in_sent = doc.get_bac_entities_in_sent(sent_offset)
		loc_entities_in_sent = doc.get_loc_entities_in_sent(sent_offset)

		if debug_print:
			#trigger_summary = ' / '.join('"%s"(token_idx=%d,freq=%d)' % (tk_form, tk_idx, freq) for (tk_idx, tk_form, freq) in triggers_in_loc_sent)
			trigger_summary = ' / '.join('"%s"(offset=%d)' % (tk_form, tk_idx) for (tk_idx, tk_form, freq) in triggers_in_loc_sent)

			print '[S%s] # BACTERIA : %d\n' \
				  '     # LOCATIONS: %d\n' \
				  '     # Candidate triggers: %d  %s' % (
				str(sent_offset), len(bac_entities_in_sent), len(loc_entities_in_sent),
				len(triggers_in_loc_sent), ('=> ' + trigger_summary) if triggers_in_loc_sent else '')

		cand_loc_entities_per_sent[sent_offset] = []

		for target_loc in sorted(loc_entities_in_sent, key=lambda e: int(e.get_id()[1:])):
			loc_id = target_loc.get_id()
			if policy1_for_target_loc == 'no_bac_in_sent':
				if bac_entities_in_sent:
					#print '     ===###==> SOME BAC in sent: %s' % '/'.join(replace_multibytes(b.get_text())[0] for b in bac_entities_in_sent)
					continue

			elif policy1_for_target_loc == 'no_associated_bac_in_sent':
				if intra_map_for_loc[loc_id]:
					#print '     ===###==> SOME connected BAC in sent: %s' % '/'.join(b_id for b_id in intra_map_for_loc[loc_id])
					continue
			else:
				raise ValueError("Unknown policy1: %s" % policy1_for_target_loc)

			loc_text = target_loc.get_text()
			loc_text_lowered = loc_text.lower()
			if loc_text_lowered.endswith('cell') or loc_text_lowered.endswith('cells'):
				print '     ===###==> Cand LOC filtered out by "cell": %s' % loc_text
				continue

			loc_token_idx = target_loc.get_head_token_idx_in_sent()

			if want_check_hypo_scope and check_token_for_hypo_scope_in_sent(loc_token_idx, sent_dep, hypo_words_per_sent[sent_offset]):
				print '     ===###==> Cand LOC Filtered out by hypothesis! "%s"' % loc_text
				continue

			if debug_print:
				#print '<<<<<<<<<<<  Candidate LOC: %s "%s" (s%s %s)  >>>>>>>>>>>' % (loc_id, loc.get_text(), str(sent_offset), doc_id)
				pass

			loc_token_idx_seq = target_loc.get_token_idx_seq_in_sent()


			if policy2_for_target_loc == 'syntactic_rel_with_trigger':

				connected_triggers_for_this_loc = []
				trigger_idx_closest_to_this_loc = None
				min_dist_between_loc_and_trigger = 1000000000

				for trigger_item in triggers_in_loc_sent:  # type: tuple[int, str, int]
					trigger_token_idx, trigger_lemma, trigger_freq = trigger_item
					trigger_lemma, _ = replace_multibytes(trigger_lemma)

					if debug_print:
						print '\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n' \
							  '  {doc_id}/s{sent_offset} Syntactic checking: trigger and LOCATION\n' \
							  '      Trigger: "{trigger}" ({trigger_idx})\n' \
							  '      LOC    : "{loc}" ({loc_id})\n' \
							  '~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~'.format(
							sent_offset=sent_offset, doc_id=doc_id, loc=target_loc.get_text(), loc_id=loc_id,
							trigger=trigger_lemma, trigger_idx=trigger_token_idx, )

					detected_result = False

					if trigger_lemma in qty_nouns:
						if debug_print:
							print '====###===> Trigger Filtered out: General quantity/quality nouns! "%s"(%d)\n' % (trigger_lemma, trigger_token_idx)
						continue

					#if sent_dep.check_dep_pos_verb(sent_dep.get_token_pos(trigger_token_idx)):
					#	print '====###===> Not included ("%s" is a VERB token)! "%s"(%d)\n' % (
					#		sent_dep.get_token(trigger_token_idx), trigger_lemma, trigger_token_idx)
					#	continue

					if trigger_token_idx in loc_token_idx_seq:
						if is_nested_trigger_always_predicted:
							if debug_print:
								print '==========> LOC includes trigger! "%s"(%d)\n' % (
								trigger_lemma, trigger_token_idx)
							#try:
							#	loc_to_triggers_syntactic_map[loc_id].append((trigger_token_idx, trigger_lemma))
							#except KeyError:
							#	loc_to_triggers_syntactic_map[loc_id] = [(trigger_token_idx, trigger_lemma)]
							#
							detected_result = ('nested', '')
						else:
							if debug_print:
								print '====###===> Trigger Filtered out: trigger nested in this LOC span! "%s"(%d)\n' % (
								trigger_lemma, trigger_token_idx)
							continue


					if not detected_result:
						is_trigger_nested_in_loc_span = False
						for other_loc in loc_entities_in_sent:
							if other_loc == target_loc:
								continue

							if trigger_token_idx in other_loc.get_token_idx_seq_in_sent():
								if debug_print:
									# print '==========> LOC includes trigger! "%s"(%d)\n' % (trigger_lemma, trigger_token_idx)
									print '====###===> Trigger Filtered out: trigger nested in other LOC span "%s"! "%s"(%d)\n' % (
										other_loc.get_text(), trigger_lemma, trigger_token_idx)
								is_trigger_nested_in_loc_span = True
								break
						if is_trigger_nested_in_loc_span:
							continue

					trigger_id = 'tr-s%s-%d' % (str(sent_offset), trigger_token_idx)
					trigger_item = trigger_id, trigger_lemma, [trigger_token_idx], trigger_token_idx
					loc_item = loc_id, loc_text, loc_token_idx_seq, loc_token_idx

					pair_id = 'pair-%s-%s' % (trigger_id, loc_id)

					if not detected_result:
						detected_result = detect_intrasent_rel_between_trigger_and_loc(trigger_item, loc_item, sent_dep)

					if not detected_result:
						for ex_input_item in expand_input_item_by_syntax(trigger_item, loc_item, pair_id, sent_offset, sent_dep, id_suffix='syn'):

							(ex_trg_id, ex_trg_text, ex_trg_token_idx_seq, ex_loc_id, ex_loc_text, ex_loc_token_idx_seq) = ex_input_item.get_bac_and_loc()
							ex_trg_token_idx, ex_loc_token_idx = ex_input_item.get_head_token_idx_pair()
							ex_trigger_item = ex_trg_id, ex_trg_text, ex_trg_token_idx_seq, ex_trg_token_idx
							ex_loc_item = ex_loc_id, ex_loc_text, ex_loc_token_idx_seq, ex_loc_token_idx
							exp_type = ex_input_item.get_exp_type()
							exp_id = ex_input_item.get_id()

							print '\nEX-INPUT: "{ex_trg_text}" ({ex_trg_idx}) & "{ex_loc_text}" ({ex_loc_id}) / exp_type={exp_type} [{exp_id}]'.format(
								ex_trg_idx=ex_trg_token_idx, ex_trg_text=ex_trg_text, ex_loc_text=ex_loc_text, ex_loc_id=ex_loc_id,
								exp_type=exp_type, exp_id=exp_id
							)

							detected_result = detect_intrasent_rel_between_trigger_and_loc(ex_trigger_item, ex_loc_item, sent_dep)
							if detected_result:
								break

					if detected_result:
						rel_type, asso_trigger = detected_result

						is_valid = check_valid_modality_between_bac_and_loc_in_sent([trigger_token_idx], loc_token_idx_seq, asso_trigger, sent_dep, rel_type='cross')
						#is_negated = False
						if is_valid:
							if debug_print:
								print '==========> Valid trigger: "%s"(%d) (%s)\n' % (trigger_lemma, trigger_token_idx, rel_type)

							#try:
							#	loc_to_triggers_syntactic_map[loc_id].append((trigger_token_idx, trigger_lemma))
							#except KeyError:
							#	loc_to_triggers_syntactic_map[loc_id] = [(trigger_token_idx, trigger_lemma)]
							#break
						connected_triggers_for_this_loc.append((trigger_token_idx, trigger_lemma, is_valid))

						dist = abs(loc_token_idx - trigger_token_idx)
						if dist < min_dist_between_loc_and_trigger:
							min_dist_between_loc_and_trigger = dist
							trigger_idx_closest_to_this_loc = trigger_token_idx

				is_closest_trigger_valid = False

				loc_to_triggers_syntactic_map[loc_id] = []
				for trigger_token_idx, trigger_lemma, is_valid in connected_triggers_for_this_loc:
					if is_valid:
						loc_to_triggers_syntactic_map[loc_id].append((trigger_token_idx, trigger_lemma))

						if trigger_token_idx == trigger_idx_closest_to_this_loc:
							is_closest_trigger_valid = True

				if loc_id in loc_to_triggers_syntactic_map and loc_to_triggers_syntactic_map[loc_id]\
						and is_closest_trigger_valid:
					cand_loc_entities_per_sent[sent_offset].append(target_loc)

			elif policy2_for_target_loc == 'existence_of_trigger':
				#triggers = trigger_map.get_triggers_in_sent(sent_offset, trigger_type='all')
				if triggers_in_loc_sent:
					if debug_print:
						print '==========> Existence of triggers in sent: %s\n' % (' / '.join('"%s"(%d)' % (ti, tt) for ti, tt in triggers_in_loc_sent))
					cand_loc_entities_per_sent[sent_offset].append(target_loc)
			else:
				raise ValueError("Unknown policy2: %s" % policy1_for_target_loc)

	return cand_loc_entities_per_sent, loc_to_triggers_syntactic_map


def filter_out_cross_sent_loc(cand_loc_ents_per_sent, cross_map_for_loc):
	"""

	:type cand_loc_ents_per_sent: dict[int, list[Entity]]
	:type cross_map_for_loc: dict[str, list[str]]
	:rtype: dict[int, list[Entity]]
	"""

	print '\n----- Filtering out candidate LOCs predicted cross-sententially -------'

	filtered_cands_per_sent = {}

	#print '!!@@!@cross_map_for_loc', cross_map_for_loc

	sorted_sent_offsets = sorted(cand_loc_ents_per_sent)
	if 'T' in cand_loc_ents_per_sent:
		sorted_sent_offsets.pop(sorted_sent_offsets.index('T'))
		sorted_sent_offsets = ['T'] + sorted_sent_offsets

	for sent_offset in sorted_sent_offsets:
		filtered_cands_per_sent[sent_offset] = []
		cand_loc_ents = cand_loc_ents_per_sent[sent_offset]

		for loc in cand_loc_ents:
			loc_id = loc.get_id()
			if cross_map_for_loc[loc_id]:
				print '[S%s] %s "%s"' % ( str(sent_offset), loc_id, loc.get_text())
				continue
			filtered_cands_per_sent[sent_offset].append(loc)

	return filtered_cands_per_sent


def search_for_cross_sent_loc_ents(target_bac_text, target_bac_head, sent_offsets_to_be_searched,
								   cand_loc_ents_per_sent, search_policies, doc, sent_dep_list):
	"""

	:param target_bac_text:
	:param target_bac_head:
	:param sent_offsets_to_be_searched:
	:param cand_loc_ents_per_sent:
	:param search_policies:
	:param already_detected_cross_sent_locs:
	:param doc:
	:param sent_dep_list:
	:rtype: list[Entity]
	"""

	stop_if_any_bac_in_sent = search_policies['stop_if_any_bac_in_sent']
	stop_if_all_locs_nonselected_in_sent = search_policies['stop_if_all_locs_nonselected_in_sent']

	detected_locs = []

	#print '!!!!@sent_offsets_to_be_searched:', sent_offsets_to_be_searched

	for next_sent_offset in sent_offsets_to_be_searched:

		bac_ents_in_next_sent = doc.get_bac_entities_in_sent(next_sent_offset)
		loc_ents_in_next_sent = doc.get_loc_entities_in_sent(next_sent_offset)

		#print '@@@Curr BACs in s%s: %s' % (str(next_sent_offset), '/'.join(b.get_text() for b in bac_ents_in_next_sent))

		if stop_if_any_bac_in_sent:
			if bac_ents_in_next_sent:
				first_other_bac_ent = bac_ents_in_next_sent[0]
				print '    | S%s  -> STOP due to other %d BACTERIA entities found: %s' % (
					str(next_sent_offset), len(bac_ents_in_next_sent),
					'"%s"' % replace_multibytes(first_other_bac_ent.get_text())[0] + (
						' / ...' if len(bac_ents_in_next_sent) > 1 else '')
					# ' / '.join('"%s"' % replace_multibytes(b.get_text())[0] for b in bac_ents_in_next_sent)
				)
				break
		else:
			next_sent_dep = sent_dep_list[0 if next_sent_offset == 'T' else (next_sent_offset + 1)]
			is_same_bac_found = False

			for other_bac in bac_ents_in_next_sent:
				other_bac_head = next_sent_dep.get_token(other_bac.get_head_token_idx_in_sent())
				other_bac_text = other_bac.get_text()
				if other_bac_head not in other_bac_text:
					other_bac_head = other_bac_text.split()[-1]

				if check_two_bac_ents_compatible(target_bac_text, target_bac_head, other_bac_text, other_bac_head):
					print '    | S%s  -> STOP due to the same BACTERIA entity: "%s"' % (str(next_sent_offset),
																	replace_multibytes(other_bac_text)[0])
					is_same_bac_found = True
					break
			if is_same_bac_found:
				break

		if not loc_ents_in_next_sent:
			continue

		cand_loc_ents_in_sent = cand_loc_ents_per_sent[next_sent_offset]

		if not cand_loc_ents_in_sent:
			if stop_if_all_locs_nonselected_in_sent:
				print '    | S%s  -> STOP due to no candidate LOCATION from %d LOCATION entities' % (str(next_sent_offset), len(loc_ents_in_next_sent))
				break
			else:
				print '    | S%s  -> PASS due to no candidate LOCATION from %d LOCATION entities' % (str(next_sent_offset), len(loc_ents_in_next_sent))
				continue

		print '    | S%s  %d cand LOC' % (str(next_sent_offset), len(cand_loc_ents_in_sent))

		best_fit_locs = cand_loc_ents_in_sent

		# if not best_fit_locs:
		#	best_fit_locs = select_relevant_locs_by_strict_rules(
		#		target_bac, cand_loc_ents_in_sent,
		#		loc_id_to_triggers_map, loc_expansion_map, triggers_in_bac_sent)

		for best_fit_loc in best_fit_locs:
			print '          ******** SELECTED:  (%s) "%s"' % (best_fit_loc.get_id(), best_fit_loc.get_text())
			#detected_pairs.append((start_bac, best_fit_loc))
			detected_locs.append(best_fit_loc)

		if not best_fit_locs and stop_if_all_locs_nonselected_in_sent \
				and not bac_ents_in_next_sent:
			print '    | S%s  STOP by %d non-selected LOC (and no BAC): %s' % (
				str(next_sent_offset), len(loc_ents_in_next_sent),
				replace_multibytes(loc_ents_in_next_sent[0].get_text())[0] + (
					' / ...' if len(loc_ents_in_next_sent) > 1 else '')
				# ' / '.join('"%s"' % replace_multibytes(b.get_text())[0] for b in bac_ents_in_next_sent)
			)
			break


	return detected_locs


def get_next_sent_offsets(start_sent_offset, all_sent_offsets, direction, context_window_size):

	if direction == 'forward':
		if start_sent_offset == 'T':
			next_sent_offsets = all_sent_offsets[1:]
		else:
			next_sent_offsets = all_sent_offsets[start_sent_offset + 2:]
	else:
		if start_sent_offset == 'T':
			next_sent_offsets = []
		else:
			next_sent_offsets = list(reversed(all_sent_offsets[0:start_sent_offset+1]))

	if isinstance(context_window_size, int) and context_window_size >= 0:
		next_sent_offsets = next_sent_offsets[:context_window_size]

	return next_sent_offsets



def detect_cross_sent_relations_from_candidates(
		input_items, cand_bac_ents_per_sent, cand_loc_ents_per_sent,
		search_direction, search_policies, context_window_size,
		sent_dep_list, doc):
	"""

	:type input_items: list[InputItem]
	:type cand_bac_ents_per_sent: dict[int, list[Entity]]
	:type cand_loc_ents_per_sent: dict[int, list[Entity]]
	:type search_policies: dict[str]
	:type sent_dep_list: list[sent_dep.SentDep]
	:type doc: Doc
	:rtype: (dict[str, list[str]], dict[str, list[str]])
	"""

	assert search_direction == 'forward' or search_direction == 'backward'
	assert isinstance(context_window_size, int)

	sent_offsets = ['T'] + range(doc.get_num_sents())
	newly_detected_pairs = []

	#search_direction = search_policies['direction']

	print '\n=========================================================================='
	print '       Detecting cross-sentence events from candidate entities : %s' % (doc.get_id())
	print '                        ' + '<<< %s Search >>>' % search_direction.title()
	print '==========================================================================\n'


	for offset_idx, sent_offset in enumerate(sent_offsets):
		sent_dep = sent_dep_list[0 if sent_offset=='T' else sent_offset+1]
		cand_bac_ents_in_sent = cand_bac_ents_per_sent[sent_offset]

		next_sent_offsets = get_next_sent_offsets(sent_offset, sent_offsets, search_direction, context_window_size)

		for target_bac in cand_bac_ents_in_sent:
			target_bac_text = target_bac.get_text()
			target_bac_head = sent_dep.get_token(target_bac.get_head_token_idx_in_sent())
			if target_bac_head not in target_bac_text:
				target_bac_head = target_bac_text.split()[-1]
			print '[S{sent}] BACTERIA {bid} "{text}" (head="{head}")'.format(
				sent=sent_offset, text=replace_multibytes(target_bac_text)[0], bid=target_bac.get_id(),
				head=replace_multibytes(target_bac_head)[0])

			detected_locs \
				= search_for_cross_sent_loc_ents(target_bac_text, target_bac_head, next_sent_offsets,
												 cand_loc_ents_per_sent, search_policies, doc, sent_dep_list)
			for loc in detected_locs:
				newly_detected_pairs.append((target_bac, loc))

	# bac id => list of loc ids
	cross_map_for_bac = {}
	cross_map_for_loc = {}

	for input_item in input_items:
		input_bac_id = input_item.get_bac_id()
		input_loc_id = input_item.get_loc_id()

		if input_bac_id not in cross_map_for_bac:
			cross_map_for_bac[input_bac_id] = []
		if input_loc_id not in cross_map_for_loc:
			cross_map_for_loc[input_loc_id] = []

		for bac, loc in newly_detected_pairs:
			assert bac.get_sent_offset() != loc.get_sent_offset()
			if input_bac_id == bac.get_id() and input_loc_id == loc.get_id():
				input_item.mark_predicted('cross')
				break

	for bac, loc in newly_detected_pairs:
		bac_id = bac.get_id()
		loc_id = loc.get_id()
		if loc_id not in cross_map_for_bac[bac_id]:
			cross_map_for_bac[bac_id].append(loc_id)
		if bac_id not in cross_map_for_loc[loc_id]:
			cross_map_for_loc[loc_id].append(bac_id)

	#print '!!@@!@cross_map_for_loc', cross_map_for_loc

	return cross_map_for_bac, cross_map_for_loc


def detect_crosssent_events(input_items, trigger_map, min_freq_triggers, hypo_words_per_sent,
							policies_forward_search, policies_backward_search, context_window_sizes,
							sent_dep_list, doc):
	"""

	:type input_items: list[InputItem]
	:type trigger_map: TriggerMap
	:type hypo_words_per_sent: dict[int, list[(int, str)]]
	:type min_freq_triggers: int
	:type doc: Doc
	"""


	sep = '*******' * 10
	print '\n'
	print sep; print sep; print sep
	print '                 CROSS-SENTENCE INFERENCE ( DOC: %s )' % doc.get_id()
	print sep; print sep; print sep
	print

	num_intra_predicted = len([i for i in input_items if i.is_predicted()])

	debug_print = True
	#debug_print = False

	intra_map_for_bac, intra_map_for_loc \
		= create_entity_map_from_predictions(input_items)
	cross_map_for_bac = {}

	if debug_print:
		#print 'intra_map_for_bac:\n', '\n'.join("   %s: %s" % (bac_id, str(intra_map_for_bac[bac_id]))
		#									  for bac_id in sorted(intra_map_for_bac, key=lambda i: int(i[1:])))
		#print 'intra_map_for_loc:\n', '\n'.join("   %s: %s" % (loc_id, str(intra_map_for_loc[loc_id]))
		#									  for loc_id in sorted(intra_map_for_loc, key=lambda i: int(i[1:])))
		pass

	cand_bac_ents_per_sent \
		= select_cand_bac_entities_per_sent(intra_map_for_bac, cross_map_for_bac, hypo_words_per_sent,
											sent_dep_list, doc, debug_print=debug_print)

	policy1_for_target_loc = 'no_bac_in_sent'
	#policy1_for_target_loc = 'no_associated_bac_in_sent'

	policy2_for_target_loc = 'syntactic_rel_with_trigger'
	#policy2_for_target_loc = 'existence_of_trigger'

	cand_loc_ents_per_sent, loc_to_triggers_map = select_cand_loc_entities_per_sent(
		intra_map_for_loc, hypo_words_per_sent, policy1_for_target_loc, policy2_for_target_loc,
		trigger_map, min_freq_triggers, sent_dep_list, doc, debug_print)

	cand_loc_ents_per_sent, cand_loc_expansion_map = propagate_cand_loc_per_sent(cand_loc_ents_per_sent, sent_dep_list, doc)

	print_cand_loc_ents_per_sent(cand_loc_ents_per_sent, loc_to_triggers_map, cand_loc_expansion_map, doc.get_id())

	#policies_forward_search = {'direction': 'forward',
	#						   'stop_if_any_bac_in_sent': True,  #
	#						   'stop_if_all_locs_nonselected_in_sent': True}  #
	forward_context_window_size, backward_context_window_size = context_window_sizes

	cross_map_for_bac, cross_map_for_loc = \
		detect_cross_sent_relations_from_candidates(input_items, cand_bac_ents_per_sent, cand_loc_ents_per_sent,
													'forward', policies_forward_search, forward_context_window_size,
													sent_dep_list, doc)

	cand_bac_ents_per_sent = select_cand_bac_entities_per_sent(intra_map_for_bac, cross_map_for_bac,
															   hypo_words_per_sent, sent_dep_list, doc,
															   only_bac_with_no_intra_predicted_loc=True,
															   debug_print=debug_print)
	filtred_cand_loc_ents_per_sent = filter_out_cross_sent_loc(cand_loc_ents_per_sent, cross_map_for_loc)

	#policies_backward_search = {'direction': 'backward',
	#				   'stop_if_any_bac_in_sent': True,  #
	#				   'stop_if_all_locs_nonselected_in_sent': True}  #
	detect_cross_sent_relations_from_candidates(input_items, cand_bac_ents_per_sent, filtred_cand_loc_ents_per_sent,
												'backward', policies_backward_search, backward_context_window_size,
												sent_dep_list, doc)


	num_total_predicted = len([i for i in input_items if i.is_predicted()])
	num_cross_predicted = num_total_predicted - num_intra_predicted
	print '\n\nCross-sentence inference complete!'
	print '# predictions:'
	print '  Intra: %2d ' % num_intra_predicted
	print '  Cross: %2d ' % num_cross_predicted
	print '  Total: %2d \n' % num_total_predicted


if __name__ == '__main__':
	pass
