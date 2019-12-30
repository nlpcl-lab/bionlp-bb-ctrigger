import os
import re
from sent_dep import SentDep
from multibytes import replace_multibytes

from path import g_dir_path_to_corenlp_output


def load_corenlp_dep_parser_output(target_doc_ids=None, data_type='train'):

	dir_path = os.path.join(g_dir_path_to_corenlp_output, data_type)

	print '\nLoading CoreNLP dependency parser output files from ...'
	print ' ', dir_path
	print

	doc_dep_info_by_id = {}
	cnt = 0
	suffix = "-sentsplit-corenlp.conll"

	for filename in os.listdir(dir_path):
		if not filename.endswith(suffix):
			continue

		doc_id = filename.split('-')[2]

		if target_doc_ids and (doc_id not in target_doc_ids and doc_id != target_doc_ids):
			continue

		print 'Loading "%s" ...' % filename

		filepath = os.path.join(dir_path, filename)

		with open(filepath, 'r') as f:
			doc_dep_content = f.read()
			# print doc_dep_content
			f.close()

		doc_dep_info = parse_stanford_dep_for_doc(doc_dep_content, format='conll', collapsed=False, doc_id=doc_id)

		# yield doc_dep_info

		doc_dep_info_by_id[doc_id] = doc_dep_info
		cnt += 1

	print '\nLoading complete: %d CoreNLP parser output files' % (cnt)

	return doc_dep_info_by_id





def parse_stanford_dep_for_doc(doc_content, format, collapsed, doc_id):
	"""

	:type doc_dep_content: str
	:type doc_content: str
	:type doc_id: str
	:rtype: list[sent_dep.SentDep]
	"""

	if format == 'conll' or format == 'conllx':
		parse_func = parse_conllx_content_for_sent
	else:
		parse_func = parse_stanford_dep_for_sent

	sents_content = doc_content.strip().split('\n\n')

	doc_dep_info = []

	for sent_idx, sent_content in enumerate(sents_content):

		#root_token_idx, root_token_word, \
		#token_dep_list, sent_tokens \
		#	= parse_stanford_dep_for_sent(sent_content, doc_id, collapsed=collapsed)
		root_token_idx, root_token_form, token_dep_list \
			= parse_func(sent_content)

		sent_dep_info = SentDep(root_token_idx, root_token_form, token_dep_list, doc_id)
		doc_dep_info.append(sent_dep_info)

	return doc_dep_info


g_escape_table = {'-LRB-': '(', '-RRB-': ')', '-LSB-': '[', '-RSB-': ']', '-LCB-': '{', '-RCB-': '}',
				  "``": '"', "''": '"'}
g_dep_re_pat = r'^([^(]+?)\((\S*)-([0-9]+\'*), (\S*)-([0-9]+\'*)\)$'


def parse_stanford_dep_for_sent(sent_dep_content, doc_id, collapsed=False):
	parsed_items = []

	token_offset = 0

	lines = sent_dep_content.split('\n')
	last_token_idx = -9999
	head_tail_idx_pairs = []
	token_dep_list = [{'form': '', 'lemma': '', 'pos': '', 'incoming': [], 'outgoing': []} for _ in
					  range(len(lines))]

	for line in lines:
		m = re.match(g_dep_re_pat, line.strip())

		if not m: print doc_id; print line; continue

		dep_label, head_token, head_idx, tail_token, tail_idx = m.group(1, 2, 3, 4, 5)

		head_idx = head_idx.replace("'", "")
		tail_idx = tail_idx.replace("'", "")

		if head_idx == tail_idx:
			continue

		if (head_idx, tail_idx) in head_tail_idx_pairs:
			continue

		head_idx = int(head_idx) - 1
		tail_idx = int(tail_idx) - 1

		if head_token in g_escape_table:
			head_token = g_escape_table[head_token]
		if tail_token in g_escape_table:
			tail_token = g_escape_table[tail_token]

		parsed_items.append((dep_label, head_token, head_idx, tail_token, tail_idx))

		assert collapsed or int(tail_idx) == token_offset

		# token_dep_list.append([tail_token, incoming_dep])
		#token_dep_list.append({'token': tail_token, 'token_idx': tail_idx,
		#					   'incoming': [], 'outgoing': []})

		last_token_idx = tail_idx
		head_tail_idx_pairs.append((head_idx, tail_idx))
		token_offset += 1

	assert len(lines) == last_token_idx + 1

	root_token_idx = -999
	root_token_word = ''

	for token_idx, dep_item in enumerate(parsed_items):
		dep_label, head_token, head_idx, tail_token, tail_idx = dep_item

		if head_idx == -1:
			root_token_idx = token_idx
			root_token_word = tail_token
			#continue

		curr_token_dep_item = token_dep_list[tail_idx]
		head_token_dep_item = token_dep_list[head_idx]

		curr_token_dep_item['form'] = tail_token
		curr_token_dep_item['lemma'] = ''  #
		curr_token_dep_item['pos'] = ''  #

		curr_token_dep_item['incoming'].append((head_idx, dep_label))

		head_token_dep_item['outgoing'].append((tail_idx, dep_label))

	#	for token_idx, token_dep_info in enumerate(token_dep_list):
	#		if len(token_dep_info) == 3:
	#			token_dep_list[token_idx] = (token_dep_info[0], token_dep_info[1], token_dep_info[2])
	#		else:
	#			token_dep_list[token_idx] = (token_dep_info[0], token_dep_info[1])

	# token_dep_list = {'root': (root_token_idx, root_token_word), 'dep_info': token_dep_list}

	return root_token_idx, root_token_word, token_dep_list


def parse_conllx_content_for_sent(sent_conllx_content):

	# for line in sent_conllx_content.split('\n'):
	#	items = line.split('\t')
	#	token_id = items[0]
	#	token_form = items[1]
	#	token_pos = items[2]

	#return [line.split('\t')[4] for line in sent_conllx_content.split('\n')]

	lines = sent_conllx_content.split('\n')

	root_token_idx = ''
	root_token_form = ''
	token_dep_list = [{'form': '', 'lemma': '', 'pos': '', 'incoming': [], 'outgoing': []} for _ in range(len(lines))]

	for line_no, line in enumerate(lines):
		token_id, token_form, token_lemma, c_postag, postag, feats, head_id, dep_rel, p_head_idx, p_dep_rel \
			= line.split('\t')

		#print token_id, token_form, token_lemma, c_postag, postag, feats, head_id, dep_rel, p_head_idx, p_dep_rel

		#is_root = (dep_rel == 'root' or head_id == token_id or head_id == "0")
		is_root = (dep_rel == 'root' or head_id == "0")

		curr_token_idx = int(token_id) - 1
		head_token_idx = int(head_id) - 1

		if token_form in g_escape_table:
			token_form = g_escape_table[token_form]

		if is_root:
			root_token_idx = curr_token_idx
			root_token_form = token_form

		curr_token_dep_item = token_dep_list[curr_token_idx]
		head_token_dep_item = token_dep_list[head_token_idx]

		#if head_token_idx == 19:
		#	print '!!!!head', token_form
		#	#exit()

		curr_token_dep_item['form'] = token_form
		curr_token_dep_item['lemma'] = token_lemma if token_lemma != '_' else ''
		curr_token_dep_item['pos'] = postag if postag != '_' else ''

		if curr_token_idx == head_token_idx:
			continue

		if not is_root:
			curr_token_dep_item['incoming'].append((head_token_idx, dep_rel))
			head_token_dep_item['outgoing'].append((curr_token_idx, dep_rel))
		#print 'Head item (%d):' % head_token_idx, head_token_dep_item

	#print '\n@@@@token dep list@@@@'
	#print '\n'.join(str(i) for i in token_dep_list)
	#if token_dep_list[0]['lemma'] == 'francisella':
	#	exit()

	#print '=>', root_token_idx, root_token_form
	assert root_token_idx >= 0 and root_token_form

	return root_token_idx, root_token_form, token_dep_list


def sync_words_in_discont_entity_with_tokens(words_in_ent, begin_token_idx, sent_dep_info, debug_print):

	token_idx_seq = []
	curr_token_idx = begin_token_idx

	for curr_word_in_ent in words_in_ent:
		matched_token_idx = -99999999

		for next_token_idx_in_sent in range(curr_token_idx, len(sent_dep_info)):
			next_token_in_sent = sent_dep_info.get_token(next_token_idx_in_sent)

			if debug_print:
				print '- [F] Word-token: "%s" | "%s"' % (next_token_in_sent, curr_word_in_ent)
			if next_token_in_sent == curr_word_in_ent:
				token_idx_seq.append(next_token_idx_in_sent)
				matched_token_idx = next_token_idx_in_sent
				if debug_print:
					print '   ===> fully matched!'
				break

		if matched_token_idx >= 0:
			curr_token_idx = matched_token_idx + 1
			continue

		for next_token_idx_in_sent in range(curr_token_idx, len(sent_dep_info)):
			next_token_in_sent = sent_dep_info.get_token(next_token_idx_in_sent)

			if debug_print:
				print '- [P] Word-token: "%s" | "%s"' % (next_token_in_sent, curr_word_in_ent)

			if curr_word_in_ent.startswith(next_token_in_sent):
				curr_word_in_ent = curr_word_in_ent[len(next_token_in_sent):]
				token_idx_seq.append(next_token_idx_in_sent)
				matched_token_idx = next_token_idx_in_sent

				if debug_print:
					print '   ===> Partially matched! (token is substring)'
				if not curr_word_in_ent:
					break

			elif next_token_in_sent.startswith(curr_word_in_ent) or curr_word_in_ent in next_token_in_sent:
				token_idx_seq.append(next_token_idx_in_sent)
				matched_token_idx = next_token_idx_in_sent
				if debug_print:
					print '   ===> Partially matched! (anno word is substring)!'
				break

		if matched_token_idx >= 0:
			curr_token_idx = matched_token_idx + 1
		else:
			raise Exception('A word in the annotated span cannot match any of tokens!')

	return token_idx_seq


def sync_tokens_between_bbevent_anno_and_stanford_dep(doc_bbevent, sent_dep_info_list, parse_type):


	assert parse_type == 'corenlp' or parse_type == 'biomedical_sota'

	special_chars_in_token = ["'", ":", ";", '"', '-',]
	r = re.compile(r"\s+", flags=re.UNICODE)

	doc_id = doc_bbevent.get_id()

	debug_print = False
	#debug_print = True


	if debug_print:
		print 'Sync tokens between annotation and dependency parse for %s' % doc_id

	# $$$$$$$$$ START for distribution $$$$$$$$$$
	#doc_ids_with_diff_sents = ['3074181', '16432479', '24198224', '24361838']
	#if doc_id in doc_ids_with_diff_sents:
	#	#raise Exception('Doc with sentence mismatch between BB-event and StanfordDependency')
	#	pass
	# $$$$$$$$$ END for distribution $$$$$$$$$$

	#if doc_bbevent.get_id() in doc_ids_with_diff_sents:
	#	return None

	if doc_bbevent.get_num_sents() + 1 != len(sent_dep_info_list):
		print doc_id
		#print '\n'.join('@ '+s for s in doc_bbevent.iter_sents(refined=True))
		print '# sents in anno:', doc_bbevent.get_num_sents() + 1
		print '# sents in dep :', len(sent_dep_info_list)
		raise Exception('Mismatch in # sents between BB-event and StanfordDependency')

	for entity in doc_bbevent.iter_entities(sort_by_offset=True):
		entity_text = entity.get_text()
		char_offsets_in_doc = entity.get_outermost_offset()

		if entity.is_in_title():
			sent = doc_bbevent.get_title_text(refined=True)
			sent_original, _, _ = doc_bbevent.get_original_title()
			sent_offset = 'T'
			char_offsets_for_sent = doc_bbevent.get_title_offsets()
			#sent_dep_info = sent_dep_info_list[0]['dep_info']
			#root_token_idx, root_token = sent_dep_info_list[0]['root']
			sent_dep_info = sent_dep_info_list[0]  # type: SentDep
			root_token_idx, root_token = sent_dep_info.get_root()
		else:
			sent_offset = entity.get_sent_offset()
			sent = doc_bbevent.get_sent_by_offset(sent_offset, refined=True)
			sent_original, _, _ = list(doc_bbevent.iter_original_sents())[sent_offset]
			char_offsets_for_sent = doc_bbevent.get_char_offsets_for_sent(sent_offset)
			#sent_dep_info = sent_dep_info_list[sent_offset + 1]['dep_info']
			#root_token_idx, root_token = sent_dep_info_list[sent_offset + 1]['root']
			sent_dep_info = sent_dep_info_list[sent_offset+1]  # type: SentDep
			root_token_idx, root_token = sent_dep_info_list[sent_offset + 1].get_root()

		begin_char_offset_in_sent = char_offsets_in_doc[0] - char_offsets_for_sent[0]
		end_char_offset_in_sent = char_offsets_in_doc[1] - char_offsets_for_sent[0]

		if debug_print:
			print char_offsets_in_doc[0], char_offsets_for_sent[0], begin_char_offset_in_sent, entity

		#num_prec_chars_for_entity_in_anno = len(sent_original.decode('utf8')[:begin_char_offset_in_sent].replace(' ', ''))
		if parse_type == 'corenlp':
			prec_span = r.sub('', sent_original.decode('utf8')[:begin_char_offset_in_sent])
		elif parse_type == 'biomedical_sota':
			prec_span = r.sub('', sent[:begin_char_offset_in_sent])
		else:
			raise ValueError('Unknown parse type: %s' % parse_type)

		num_prec_chars_for_entity_in_anno = len(prec_span)
		#print prec_span.encode('utf8')

		sliced_span = sent[begin_char_offset_in_sent:end_char_offset_in_sent]

		if debug_print:
			print 'Anno  : %s' % entity_text
			print 'Sliced: %s (num_prec_chars: %d)' % (sliced_span, num_prec_chars_for_entity_in_anno)
			print '- Preceding slice:', sent[:begin_char_offset_in_sent].replace(' ', ' ')
			print 'ROOT: %s (token_idx=%d)' % (root_token, root_token_idx)
		# print sent, '\n'

		begin_token_idx = -9999
		is_token_substr = False

		sent_tokens = sent_dep_info.get_sent_tokens()

		#if doc_id == '24198224' and root_token == 'days':
		#if doc_id == '4387161' and root_token == 'days':
		#	print sent
		#	print len(sent_tokens[16])

		for token_offset in range(len(sent_dep_info)):
			num_prec_chars_in_dep = sum(len(token.decode('utf-8')) for token in sent_tokens[:token_offset])
			if debug_print:
				#print '- token:', sent_tokens[token_offset], num_prec_chars_in_dep
				token_refined, _ = replace_multibytes(sent_tokens[token_offset])
				print '- token:', token_refined, num_prec_chars_in_dep , '   ====> *** Multibyte replaced ***' if '@' in token_refined else ''

			if num_prec_chars_in_dep == num_prec_chars_for_entity_in_anno:
				begin_token_idx = token_offset
				if debug_print:
					print '   ===> First word matched with this token! ("%s")' % token_refined
				break

			len_token = len(sent_tokens[token_offset].decode('utf-8'))
			idx_diff = num_prec_chars_for_entity_in_anno - num_prec_chars_in_dep

			if 0 < idx_diff < len_token:
				token_substr = sent_tokens[token_offset][idx_diff:idx_diff+len(entity_text)]
				#print '^%^%%', token_substr, entity_text
				if entity_text.startswith(token_substr):
					begin_token_idx = token_offset
					is_token_substr = True
					if debug_print:
						print '   ===> First word Partially matched with this token! ("%s")' % token_refined

		assert begin_token_idx >= 0

		if debug_print:
			print '\nTrying to detect the whole token sequence ...'

		if entity.is_discontinuous():
			words_in_discont_ent = entity_text.split()

			token_idx_seq = []
			token_idx_seq = sync_words_in_discont_entity_with_tokens(words_in_discont_ent, begin_token_idx, sent_dep_info, debug_print)

			if not token_idx_seq:
				comp_token_idx = begin_token_idx
				for next_word_in_ent in words_in_discont_ent:
					is_matched_with_token = False
					for next_token_idx_in_sent in range(comp_token_idx, len(sent_dep_info)):
						next_token_in_sent = sent_dep_info.get_token(next_token_idx_in_sent)

						if debug_print:
							print '- Word-token: "%s" | "%s"' % (next_token_in_sent, next_word_in_ent)
						if next_token_in_sent == next_word_in_ent:
							token_idx_seq.append(next_token_idx_in_sent)
							is_matched_with_token = True
							if debug_print:
								print '   ===> fully matched!'
							break
						elif next_word_in_ent.startswith(next_token_in_sent):
							next_word_in_ent = next_word_in_ent[len(next_token_in_sent):]
							token_idx_seq.append(next_token_idx_in_sent)
							is_matched_with_token = True
							if debug_print:
								print '   ===> Partially matched! (token is substring)'
						elif next_token_in_sent.startswith(next_word_in_ent) or next_word_in_ent in next_token_in_sent:
							token_idx_seq.append(next_token_idx_in_sent)
							if debug_print:
								print '   ===> Partially matched! (anno word is substring)!'
							is_matched_with_token = True
							break

					if is_matched_with_token:
						comp_token_idx += 1
					else:
						raise Exception('A word in the annotated span cannot match any of tokens!')

		else:
			num_words_in_entity = entity.get_num_words()
			end_token_idx = begin_token_idx + num_words_in_entity
			token_span = ' '.join(sent_dep_info.get_token(i) for i in range(begin_token_idx, end_token_idx))

			if token_span == entity_text \
					or entity_text in token_span:
				token_idx_seq = range(begin_token_idx, end_token_idx)
			else:

				if parse_type == 'corenlp':
					entity_char_seq = r.sub('', entity_text.decode('utf8')).encode('utf8')
				else:
					entity_char_seq = entity_text.replace(' ', '')

				token_idx_seq = []
				for token_idx_in_sent in range(begin_token_idx, len(sent_dep_info)):
					accumulated_char_seq = ''.join(sent_tokens[begin_token_idx:token_idx_in_sent + 1])
					#print '@^ %d-%d ACCU: %s' % (begin_token_idx, token_idx_in_sent, accumulated_char_seq)
					#print '         SPAN: %s' % entity_char_seq

					if entity_char_seq in accumulated_char_seq:
						for ti in range(begin_token_idx, token_idx_in_sent + 1):
							token_idx_seq.append(ti)
						#print '[token_span(false)]', token_span
						#print '[entity_char_seq]', entity_text
						#print '[token_idx_seq]', str(token_idx_seq)
						break

		if not token_idx_seq:
			raise Exception("[ERROR] Sync failed: Entity text span <=> tokenized text")

		if debug_print:
			print '\nEntity tokens sync (in sent): "%s" <=> %s [doc: %s]:' % (entity.get_text(), token_idx_seq, doc_id)
			print sent
			print sent_tokens, '\n'

		token_form_seq = [sent_dep_info.get_token(token_idx) for token_idx in token_idx_seq]

		ent_char_seq = ''.join(entity_text.split())
		token_char_seq = ''.join(token_form_seq)

		if token_char_seq != ent_char_seq and ent_char_seq not in token_char_seq:
			#print "@ent_char_seq:" ent_char_seq
			#print "@token_char_seq:", token_char_seq
			#assert ent_char_seq in token_char_seq
			for c in special_chars_in_token:
				if c in token_char_seq:
					segment_spans = token_char_seq.split(c)
					if ent_char_seq not in segment_spans:
						print '[Error] Token sync failed! [%s/%s]' % (doc_id, str(sent_offset))
						print '@entity_anno_text:', entity_text
						print '@token_form_seq  : %s (idx_seq: %s)' % (str(token_form_seq), str(token_idx_seq))
						print
						assert False

		entity.assign_token_idx_seq_in_sent(token_idx_seq)
		entity.assign_token_form_seq(token_form_seq)

		entity_pos_seq = sent_dep_info.get_token_pos_seq(token_idx_seq)
		entity.assign_pos_seq(entity_pos_seq)

		head_token_idx_in_sent, head_token_offset_in_entity \
			= sent_dep_info.get_head_token_for_span(token_idx_seq)

		entity.assign_head_token(head_token_offset_in_entity)

		if debug_print:
			print


if __name__ == '__main__':
	pass
