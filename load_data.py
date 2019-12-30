from concepts import Doc, Para, Entity, Event, Events, get_entity_by_id
from multibytes import refine_multibytes
from path import g_dir_path_to_official_data, g_dir_path_to_corenlp_output

import os


def load_bb_event_doc_data(doc_id, file_path_a1, file_path_a2, file_path_txt, tokenized_sents, data_type, base_tokenization_type):
	"""

	:type doc_id: str
	:type file_path_a1: str
	:type file_path_a2: str
	:type file_path_txt: str
	:type tokenized_sents: list[str]
	:rtype: Doc
	"""

	title_text, title_text_refined, title_offset, \
	doc_text_refined, sents_refined, sent_char_offsets, \
	para_list, bacteria_list, habitat_list, geo_list, \
	multibyte_info \
		= parse_file_a1(file_path_a1, file_path_txt, tokenized_sents, doc_id, base_tokenization_type)

	#if False:
	if True:
		validate_a1(doc_id, doc_text_refined, title_text, title_text_refined, title_offset, para_list,
					bacteria_list + habitat_list + geo_list)

	if data_type == 'test':
		events = Events(event_list=[])
	else:
		events = parse_file_a2(file_path_a2, bacteria_list, habitat_list, geo_list)

	#validate_a2()

	doc = Doc(doc_id, doc_text_refined=doc_text_refined, multibyte_info=multibyte_info,
			  title_text=title_text, title_text_refined=title_text_refined, title_offset=title_offset,
			  para_list=para_list, bacteria_list=bacteria_list, habitat_list=habitat_list, geo_list=geo_list,
			  events=events, sents_refined=sents_refined, sent_char_offsets=sent_char_offsets)

	return doc


def get_sent_range_for_para(doc_id, para_id, para_offset, para_text_refined, tokenized_sents_refined,
							scan_start_sent_offset, para_text_multibytes):
	"""
	:type para_text_refined: str
	:type tokenized_sents_refined: list[str]
	:type para_text_multibytes: list[(int, str)]
	:rtype: ((int, int), list[str], list[(int, int)], dict[int, list[(int, str)]])
	"""
	begin_sent_offset = 99999
	end_sent_offset = -1
	#para_slice = para_text
	#para_slice_being_offset = 0

	#print '#para#', para_slice
	inner_sent_begin_char_offset = 0
	inner_sents = []
	inner_sent_char_offsets = []

	#print 'scan_start_sent_offset: %d' % scan_start_sent_offset

	for sent_offset, tokenized_sent in enumerate(tokenized_sents_refined):

		if sent_offset < scan_start_sent_offset:
			continue

		#token_segments = tokenized_sent.rsplit(None, 3)
		#sent_final_token = token_segments[-3] + ' ' + ''.join(token_segments[-2:])

		if not tokenized_sent.split()[-1][0].isalnum():
			sent_final_token = ''.join(tokenized_sent.rsplit(None, 2)[-2:])
		else:
			sent_final_token = ' '.join(tokenized_sent.rsplit(None, 2)[-2:])
			#raise Exception('[Warning] (doc %s) The last token of tokenized sentence is not an independent punctuation mark!' % doc_id)

		if sent_offset < len(tokenized_sents_refined) - 1:
			#print len(tokenized_sents[sent_offset + 1])
			#print tokenized_sents[sent_offset + 1].split(None, 1)
			sent_final_token_exp = sent_final_token + ' ' + tokenized_sents_refined[sent_offset + 1].split(None, 1)[0]
		else:
			sent_final_token_exp = sent_final_token

		para_slice = para_text_refined[inner_sent_begin_char_offset:]

	#	print '@@@ Tokenized sent (given) @@@'
	#	print tokenized_sent
	##	print '@@@ Sent_delimit (s%d): "%s"' % (sent_offset, sent_final_token_exp)
	#	print '@@@ Remaining para @@@\n', para_slice
	#	print sent_final_token_exp in para_slice, para_slice.endswith(sent_final_token), '\n'

		if para_slice.strip() and not (sent_final_token_exp in para_slice or para_slice.endswith(sent_final_token)):
			print '\n[ERROR] Sentence sync failed. Sentence boundary was not found! (doc %s)' % doc_id
			print 'Sent-final expression: "%s"' % sent_final_token_exp
			print '----- Remaining Paragraph (below) -----'
			print para_slice
			print
			raise Exception('[ERROR] Sentence sync failed.')

		if sent_final_token_exp in para_slice or para_slice.endswith(sent_final_token):
			#print sent_final_token
			#assert para_slice.count(sent_final_token) == 1
			if not para_slice.endswith(sent_final_token) and para_slice.count(sent_final_token_exp) != 1:
				#print '     - [$$ Warning $$] more than 1 tokenized_sent-final token: "%s"' % sent_final_token_exp
				pass

			if sent_offset < begin_sent_offset:
				begin_sent_offset = sent_offset
			end_sent_offset = sent_offset + 1

			if para_slice.endswith(sent_final_token):
				sent_final_token_offset = para_slice.index(sent_final_token)
			else:
				sent_final_token_offset = para_slice.index(sent_final_token_exp)
				#inner_sent_begin_char_offset = sent_final_token_offset + len(sent_final_token_exp)

			end_char_offset_in_slice = sent_final_token_offset+len(sent_final_token)

			sent_sliced = para_slice[:end_char_offset_in_slice]

			inner_sent_end_char_offset = inner_sent_begin_char_offset + end_char_offset_in_slice

			inner_sents.append(sent_sliced)
			inner_sent_char_offsets.append((inner_sent_begin_char_offset, inner_sent_end_char_offset))

			#print '### Detected Sent ###', sent_sliced

			inner_sent_begin_char_offset += end_char_offset_in_slice + 1

			#para_slice = para_slice[inner_sent_begin_char_offset:]

	if begin_sent_offset >= 99999:
		print 'Doc & para:', doc_id, para_id

	assert begin_sent_offset < 99999

	num_sents_scanned = end_sent_offset - begin_sent_offset

	debug = False
	#debug = True
	if debug: print '#### Sync Para-%s char range=(%d, %d) [len=%d], tokenized_sent range=(%d, %d) [%d sents] ' % (
		para_id, para_offset[0], para_offset[1], para_offset[1]-para_offset[0],
		begin_sent_offset, end_sent_offset, num_sents_scanned)
	#assert len(tokenized_sents) == num_sents_scanned
	#print '<<< Para text >>>', para_text
	#print '\n<<< Detected tokenized_sent >>>', sents

	#assert len(inner_sents) == len(inner_sent_char_offsets)

	multibytes_by_sent = {}

	if para_text_multibytes:
		for sent_idx, (begin_char_offset, end_char_offset) in enumerate(inner_sent_char_offsets):
			sent_offset_in_doc = sent_idx + begin_sent_offset
			inner_sent_multibytes = []

			for letter_offset, multibyte_letter in sorted(para_text_multibytes):
				if begin_char_offset <= letter_offset < end_char_offset:
					letter_offset_in_sent = letter_offset - begin_char_offset
					inner_sent_multibytes.append((letter_offset_in_sent, multibyte_letter))

			if inner_sent_multibytes:
				multibytes_by_sent[sent_offset_in_doc] = inner_sent_multibytes

	#print '$$$', doc_id, multibytes_by_sent

	return (begin_sent_offset, end_sent_offset), inner_sents, inner_sent_char_offsets, multibytes_by_sent


def assign_sent_offset_to_entities(entity_list, title_text_refined, title_offset, para_list, doc_id):
	"""
	:type entity_list: list[Entity]
	:type para_list: list[Para]
	:rtype: int
	"""

	debug_print = False
	#debug_print = True

	for entity in entity_list:

		entity_begin_offset = entity.get_offsets()[0][0]
		entity_end_offset = entity.get_offsets()[-1][-1]

		if debug_print:
			print '\n* Entity anno (%s in %s): "%s" offset=(%d, %d)' % (
				entity.get_id(), doc_id, entity.get_text(), entity_begin_offset, entity_end_offset)

		if (title_offset[0] <= entity_begin_offset and entity_end_offset <= title_offset[1]):
			if debug_print:
				print 'Title anno: offset=(%d, %d)' % (title_offset[0], title_offset[1])
			entity.mark_in_title()
			entity.assign_sent_offset('T')
			#exit(1)
			continue

		num_prev_paras_sents = 0

		for para_idx, para in enumerate(para_list):
			para_begin_offset, para_end_offset = para.get_offset()

			#para_text = para.get_text()
			if debug_print: print 'Para anno (%s): offset=(%d, %d)' % (para.get_id(), para_begin_offset, para_end_offset)
			#print para.get_text_refined()

			if not (para_begin_offset <= entity_begin_offset and entity_end_offset <= para_end_offset):
				#print '-> Not in this para!', para_begin_offset <= entity_begin_offset, entity_end_offset <= para_end_offset
				num_prev_paras_sents += para.get_num_sents()
				continue

			entity_begin_offset_in_para = entity_begin_offset - para_begin_offset
			entity_end_offset_in_para = entity_end_offset - para_begin_offset

			if debug_print:
				entity_sliced = para.get_text(refined=True)[entity_begin_offset_in_para:entity_end_offset_in_para]
				print '-> Offset-in-para=(%d, %d) "%s"' % (entity_begin_offset_in_para, entity_end_offset_in_para, entity_sliced)
				if entity_sliced != entity.get_text():
					print '[***Warning***] sliced="%s" anno="%s"' % (entity_sliced, entity.get_text())

			is_found = False

			for sent_idx_in_para, (sent_begin_char_offset, sent_end_char_offset) in enumerate(para.get_inner_sent_char_offsets()):
				sent_idx_in_doc = sent_idx_in_para + num_prev_paras_sents
			#	num_sents_in_para += 1
				if debug_print:
					print '-- Sent (in_para=%d, in_doc=%d): offset=(%d, %d)' % (
						sent_idx_in_para, sent_idx_in_doc, sent_begin_char_offset, sent_end_char_offset)
					#print '  "%s"' % para.get_text_refined()[sent_begin_char_offset:sent_end_char_offset]

				#sent_text = para_text[sent_begin_char_offset:sent_end_char_offset]
				if (sent_begin_char_offset <= entity_begin_offset_in_para
						and entity_end_offset_in_para <= sent_end_char_offset):
					entity.assign_sent_offset(sent_idx_in_doc)
					entity.assign_para_offset(para_idx)
					if debug_print: print '   [Found!] sent_idx_in_doc=%d sent_idx_in_para=%d char_offset_in_para=(%d, %d)' % (
						sent_idx_in_doc, sent_idx_in_para, entity_begin_offset_in_para, entity_end_offset_in_para)
					is_found = True
					break

			num_prev_paras_sents += para.get_num_sents()

			if is_found:
				break

		assert entity.get_sent_offset() >= 0 or entity.mark_in_title()



def assign_nesting_level_to_entities(entity_list, doc_text_refined, max_num_words=30):
	"""
	:type entity_list: list[Entity]
	:type doc_text_refined: str
	:type max_num_words: int
	:return:
	"""
	is_debug = False
	#is_debug = True

	dict_len_to_ent = {}
	for n in xrange(1, max_num_words+1):
		dict_len_to_ent[n] = []

	for ent in entity_list:
		outer_begin, outer_end = ent.get_outermost_offset()
		outermost_text_span = doc_text_refined[outer_begin:outer_end]
		#
		num_max_span_words = len(outermost_text_span.replace('/', ' /').split())
		if num_max_span_words == 1:
			ent.assign_graphical_nesting_level(0)
		#print ent.get_text()
		try:
			dict_len_to_ent[num_max_span_words].append(ent)
		except KeyError:
			dict_len_to_ent[num_max_span_words] = [ent]

	#for ent in entity_list:
	#	print ent.get_num_words(), ent.get_nesting_level(), ent

	for target_num in xrange(2, max_num_words+1):

		if is_debug:
			print 'target_num_max_span_words:', target_num

		for ent in dict_len_to_ent[target_num]:  # type: Entity
			if is_debug:
				print ent
			max_inner_level = -9999

			is_nested_found = False

			for short_num in xrange(1, target_num):
				for shorter_ent in dict_len_to_ent[short_num]:  # type: Entity
					begin, end = ent.get_outermost_offset()

					shorter_begin, shorter_end = shorter_ent.get_outermost_offset()
					if begin <= shorter_begin and shorter_end <= end:
						level = shorter_ent.get_graphical_nesting_level()
						if level > max_inner_level:
							max_inner_level = level
							is_nested_found = True

					if is_debug:
						print '*' if begin <= shorter_begin and shorter_end <= end else '-',
						print shorter_ent.get_graphical_nesting_level(), shorter_ent

			if is_nested_found:
				nesting_level = max_inner_level + 1
			else:
				nesting_level = 0

			if is_debug:
				print ' =>', nesting_level

			ent.assign_graphical_nesting_level(nesting_level)

	for ent in entity_list:
		assert ent.get_graphical_nesting_level() >= 0

	if is_debug:
		raise Exception('\nTemp stop ~~!')


def parse_file_a1(file_path_a1, file_path_txt, tokenized_sents, doc_id, base_tokenization):
	"""
	:type file_path_a1: str
	:type tokenized_sents: list[str]
	:type doc_id: str
	:return:
	"""

	title_text = ''
	title_text_refined = ''
	title_offset = None
	para_list = []
	entity_list = []
	bacteria_list = []
	habitat_list = []
	geo_list = []

	scan_start_sent_offset = 0
	num_sents_parsed = 0
	sents_all_refined = []
	sent_char_offsets = []

	multibytes_by_sent_in_doc = {}

	debug_print = False
	#debug_print = True

	multibyte_info = {'doc': None, 'title': None, 'sents': []}

	with open(file_path_txt) as f:
		doc_text = f.read()
		doc_text_refined, doc_text_multibytes = refine_multibytes(doc_text, doc_id)
		multibyte_info['doc'] = doc_text_multibytes

	tokenized_sents_refined = []
	for sent_idx, tokenized_sent in enumerate(tokenized_sents):
		tokenized_sent_refined, sent_multibytes = refine_multibytes(tokenized_sent, doc_id)
		tokenized_sents_refined.append(tokenized_sent_refined)

		#if sent_idx > 0:
		#	multibyte_info['sents'].append(sent_multibytes)

	f = open(file_path_a1, 'r')

	#if base_tokenization == 'all':
	#	para_start_sent_offset = (1 if doc_id != '3074181' else 2)
	#else:
	#	para_start_sent_offset = 1

	para_start_sent_offset = 1

	for line in f:
		#print line
	#	items = line.split(None, 4)
	#	concept_id = items[0]
	#	concept_type = items[1]
	#	offsets = int(items[2]), int(items[3])
	#	text_span = items[4]

		items = line.strip().split('\t')
		concept_id = items[0]
		concept_info = items[1]
		text_span = items[2]

		#print text_span[-10:]

		concept_type, offset_str = concept_info.split(' ', 1)

		# For titles or paragraphs
		if concept_type == 'Title' or concept_type == 'Paragraph':
			offset_items = offset_str.split()
			offset = (int(offset_items[0]), int(offset_items[1]))

			if concept_type == 'Title':
				title_text = text_span
				title_text_refined, title_text_multibytes = refine_multibytes(title_text, doc_id)
				multibyte_info['title'] = title_text_multibytes
				title_offset = offset

			elif concept_type == 'Paragraph':
				para_text = text_span
				para_text_refined, para_text_multibytes = refine_multibytes(para_text, doc_id)
				para_offset = offset
				sent_range, sents_refined, inner_sent_char_offsets, multibytes_by_sent_in_para \
					= get_sent_range_for_para(doc_id, concept_id, para_offset, para_text_refined,
											  #tokenized_sents[para_start_sent_offset:],
											  tokenized_sents_refined[para_start_sent_offset:],
											  scan_start_sent_offset, para_text_multibytes)

				scan_start_sent_offset = sent_range[1]
				para_list.append(Para(concept_id, para_offset, para_text, para_text_refined,
									  sent_range, inner_sent_char_offsets))
				num_sents_parsed += len(sents_refined)
				sents_all_refined.extend(sents_refined)
				sent_char_offsets.extend(
					(para_offset[0]+begin, para_offset[0]+end) for (begin, end) in inner_sent_char_offsets)

				for sent_offset in multibytes_by_sent_in_para:
					assert sent_offset not in multibytes_by_sent_in_doc
					multibytes_by_sent_in_doc[sent_offset] = multibytes_by_sent_in_para[sent_offset]
		# For entities
		else:
			# For discontinuous entities (divided by ;)
			if ';' in offset_str:
				offsets = [(int(x), int(y)) for x, y in
						   (offset_str.split() for offset_str in offset_str.split(';'))]
				#print '1@@@', offset_str
			# For continuous entities
			else:
				offsets = [tuple(int(x) for x in offset_str.split())]

			entity = Entity(concept_id, concept_type, offsets, text_span)
			entity_list.append(entity)

			if concept_type == 'Bacteria':
				bacteria_list.append(entity)
			elif concept_type == 'Habitat':
				habitat_list.append(entity)
			elif concept_type == 'Geographical':
				geo_list.append(entity)
			else:
				raise Exception('\n[Error] Unknown concept type: %s' % concept_type)

	f.close()

	if debug_print:
		print '------ Debug (%s) ------ ' % doc_id
		print num_sents_parsed, len(tokenized_sents[para_start_sent_offset:])
		print '<<< Parsed sents >>>'
		print '\n'.join('[#%d] %s' % (i, sent) for i, sent in enumerate(sents_all_refined)) + '\n'
		print '<<< Tokenized sents (provided by task organizers) >>>'
		print ''.join('[#%d] %s' % (i, sent) for i, sent in enumerate(tokenized_sents[para_start_sent_offset:])) + '\n'

	assert title_offset and title_text

	if num_sents_parsed != len(tokenized_sents[para_start_sent_offset:]):
		print '\n[ERROR] Incorrect sentence sync in %s' % doc_id
		print '  - # sentences from original a1 file  :', num_sents_parsed
		print '  - # sentences from given tokenization:', len(tokenized_sents[para_start_sent_offset:])
		raise Exception('[ERROR] Incorrect sentence sync')


	#title_text_refined, doc_text_refined, para_list_refined \
	#	= refine_text_for_multibytes(doc_id, title_text, doc_text, para_list)

	#for para in para_list:
	#	print len(para.get_text_refined())
	#	print para.get_text_refined()

	#print 'Stop!'; exit(1)

	multibyte_info['sents'] = multibytes_by_sent_in_doc

	assign_sent_offset_to_entities(entity_list, title_text_refined, title_offset, para_list, doc_id)
	assign_nesting_level_to_entities(entity_list, doc_text_refined)

	a = False
	#a = True
	if a:
		assert len(sents_all_refined) == len(sent_char_offsets)
		for sent_idx, sent in enumerate(sents_all_refined):
			begin_char_offset, end_char_offset = sent_char_offsets[sent_idx]
			sent_sliced = doc_text_refined[begin_char_offset:end_char_offset]
			if sent != sent_sliced:
				msg = "\nError: sentence offsets are not correct.\n" \
					  "offset %d %d\nSliced: %s\nParsed: %s" % (
					begin_char_offset, end_char_offset, sent_sliced, sent
				)
				raise Exception(msg)

	return (title_text, title_text_refined, title_offset,
			doc_text_refined, sents_all_refined, sent_char_offsets,
			para_list, bacteria_list, habitat_list, geo_list,
			multibyte_info)


def parse_file_a2(file_path, bacteria_list, habitat_list, geo_list):
	"""
	:type file_path: str
	:type geo_list: list[Entity]
	:type habitat_list: list[Entity]
	:type bacteria_list: list[Entity]
	:rtype: Events
	"""
	event_list = []
	coref_chains = []

	f = open(file_path, 'r')

	for line in f:
		items = line.strip().split()
		event_id = items[0]
		event_type = items[1]
		arg1 = items[2]
		arg2 = items[3]

		if ':' in arg1:
			arg1_type, arg1_id = arg1.split(':')
			arg2_type, arg2_id = arg2.split(':')
			assert arg1_type == 'Bacteria' or arg2_type == 'Location'
			#assert arg1_type == 'Bacteria' or arg1_type == 'Location'
			#assert arg2_type == 'Bacteria' or arg2_type == 'Location'
			assert event_type == 'Lives_In'

			arg1_entity = get_entity_by_id(arg1_id, bacteria_list)
			arg2_entity = get_entity_by_id(arg2_id, habitat_list) \
						  or get_entity_by_id(arg2_id, geo_list)

			event = Event(event_id, arg1_entity, arg2_entity)
			event_list.append(event)
		else:
			assert event_type == 'Equiv'

			for chain in coref_chains:
				if arg1 in chain:
					chain.append(arg2)
					break
				if arg2 in chain:
					chain.append(arg1)
					break
			else:
				coref_chains.append([arg1, arg2])

	f.close()

	return Events(event_list, coref_chains)


def validate_a1(doc_id, doc_text_refined, title_text, title_text_refined, title_offset, para_list, entity_list):
	"""
	:type doc_id: str
	:type file_path_txt: str
	:type title_text: str
	:type title_offset: (int, int)
	:type para_list: list[Para]
	:type entity_list: list[Entity]
	:rtype: bool
	"""

	#print title_text
	#print num_multibyte_chars

	title_sliced = doc_text_refined[title_offset[0]:title_offset[1]]
	if title_text_refined != title_sliced:
		#print len(content_txt)
		try:
			print '==> Title mismatch\nSliced: "%s"\nAnno: "%s"' % (title_sliced, title_text)
		except IOError:
			print '  ********* IOERROR *********'

		#msg = 'Validation error\nSliced: "%s"\nAnno: "%s"' % (title_sliced, title_text)
		#raise Exception('Validation error')

	for para in para_list:
		para_anno_offset = para.get_offset()
		#para_anno_text = para.get_text()
		para_anno_text = para.get_text(refined=True)
		para_anno_tokens = para_anno_text.split()

		para_sliced_text = doc_text_refined[para_anno_offset[0]:para_anno_offset[1]]
		para_sliced_token = para_sliced_text.split()

		is_len_same = (len(para_anno_tokens) == len(para_sliced_token)
					   or len(para_sliced_text) == para_anno_offset[1]-para_anno_offset[0])
		is_first_token_same = para_anno_tokens[0] == para_sliced_token[0]
		is_last_token_same = para_anno_tokens[-1] == para_sliced_token[-1]

		#if para_anno_text != para_sliced_text:
		if not is_len_same or not is_first_token_same or not is_last_token_same:
			print '\n==> Para error [%s] %s (diff=%d) doc=%s ' % (
				para.get_id(), str(para_anno_offset), para_anno_offset[1] - para_anno_offset[0], doc_id)
			print '    # token: sliced=%d anno=%d' % (len(para_sliced_token), len(para_anno_tokens))
			try:
				print '<sliced> %d\n%s' % (len(para_sliced_text), para_sliced_text)
				print '<anno> %d\n%s' % (len(para_anno_text), para_anno_text)
			except IOError:
				#print '<sliced>\n%s\n<anno>\n%s' % (para_sliced_text, "<ERROR>")
				print '  ********* IOERROR *********'
			raise Exception('Validation error (para sync)')

	for entity in entity_list:
		entity_offsets = entity.get_offsets()
		entity_text = entity.get_text()

		# For discontinuous entities, merge partial segment strings
		if len(entity_offsets) > 1:
			entity_partials = []
			for entity_offset in entity_offsets:
				entity_partials.append(doc_text_refined[entity_offset[0]:entity_offset[1]])
			entity_sliced = ' '.join(entity_partials)
		else:
			entity_offset = entity_offsets[0]
			entity_sliced = doc_text_refined[entity_offset[0]:entity_offset[1]]

		if '@' in entity_sliced:
			repl_idxs = [i for i in range(len(entity_sliced)) if entity_sliced.startswith('@', i)]
			entity_text_uni = entity_text.decode('utf8')
			for repl_idx in repl_idxs:
				entity_text_uni = entity_text_uni.replace(entity_text_uni[repl_idx], '@')
			entity_text_escaped = entity_text_uni.encode('utf8')
		else:
			entity_text_escaped = entity_text

		while '  ' in entity_text_escaped:
			entity_text_escaped = entity_text_escaped.replace('  ', ' ')

		#if entity_text != entity_sliced:
		if entity_text_escaped != entity_sliced:
			try:
				#print '  ==> Entity error (%s)' % entity.get_id()
				print '  => Entity error in %s (%s): %s sliced="%s", anno="%s":' % (
					doc_id, entity.get_id(), str(entity_offsets), entity_sliced, entity_text)

			except IOError:
				#print '  ==> Entity error (%s): %s sliced="%s", anno="%s":' % (
				#	entity.get_id(), str(entity_offsets), "<ERROR>", entity_text)
				print '  ********* IOERROR *********'
			raise Exception('Validation error (token sync)')


def load_bb_event_files(dir_path, target_doc_id, debug_print=True):
	"""

	:param dir_path:
	:return:
	"""

	if debug_print:
		print '\n============= Loading BB-event file paths ============='

	file_cnt = 0

	for filename in sorted(os.listdir(dir_path)):
		if not filename.startswith('BB-event-') or not filename.endswith('.txt'):
			continue

		doc_info = filename.split('-')[2]
		doc_id, doc_type = doc_info.split('.')

		if target_doc_id and doc_id != target_doc_id:
			continue

		if debug_print:
			print '-------------------------------' * 2
			print '[#%d] Loading "%s"...' % (file_cnt, filename)
		file_cnt += 1

		if doc_type == 'a1':
			pass
		elif doc_type == 'a2':
			pass
		elif doc_type == 'txt':
			pass

		file_path_a1 = os.path.join(dir_path, "BB-event-%s.a1" % doc_id)
		file_path_a2 = os.path.join(dir_path, "BB-event-%s.a2" % doc_id)
		file_path_txt = os.path.join(dir_path, "BB-event-%s.txt" % doc_id)

		#files[doc_id] = (file_a1, file_a2, file_txt)
		yield doc_id, file_path_a1, file_path_a2, file_path_txt

	#return files



def extract_tokenization_from_corenlp_parsed_text(conll_input_dir_path, target_doc_id, debug_print):
	"""
	:param data_type:
	:rtype: dict[str, list[str]]
	"""

	from dep_parser import g_escape_table

	tokenized_texts_by_doc = {}

	for filename in os.listdir(conll_input_dir_path):
		if not filename.endswith('-sentsplit-corenlp.conll'):
			continue
		doc_id = filename.split('-')[2].split('.')[0]

		if target_doc_id and doc_id != target_doc_id:
			continue

		conll_file_path = os.path.join(conll_input_dir_path, filename)
		with open(conll_file_path, 'r') as f:
			conll_text = f.read()
			f.close()
		conll_sents = conll_text.strip().split('\n\n')
		tokenized_sents = []

		for conll_sent in conll_sents:
			tokenized_sent = ' '.join(line.split('\t')[1] for line in conll_sent.split('\n'))

			for escaped in g_escape_table:
				original = g_escape_table[escaped]
				tokenized_sent = tokenized_sent.replace(escaped, original)

			tokenized_sents.append(tokenized_sent + '\n')

		tokenized_texts_by_doc[doc_id] = tokenized_sents

	#if '19552770' in tokenized_texts_by_doc:
	#	tokenized_texts_joined = ''.join(tokenized_texts_by_doc['19552770'])
	#	tokenized_texts_joined = tokenized_texts_joined.replace('spp. .\nThe', 'spp.\nThe')
	#	tokenized_texts_by_doc['19552770'] = tokenized_texts_joined.strip().split('\n')

	return tokenized_texts_by_doc



def load_official_bb_event_docs(data_type, base_tokenization, target_doc_id=''):

	bb_event_dir_path = os.path.join(g_dir_path_to_official_data, "BioNLP-ST-2016_BB-event_%s" % data_type)

	debug_print = False
	#debug_print = True

	files = load_bb_event_files(bb_event_dir_path, target_doc_id, debug_print=debug_print)

	#if base_tokenization == 'all':
	#	#bb_event_all_token_dir_path = base_dir_path + "\\supporting_resources\\BB3_tokenization_resources\\%s\\BioNLP-ST-2016_BB-event_%s" % (data_type, data_type)
	#	bb_event_all_token_dir_path = os.path.join(g_dir_path_to_bb_tokenization, "%s\\BioNLP-ST-2016_BB-event_%s" % (data_type, data_type))
	#	tokenized_texts = load_bb_event_all_tokenized_texts(bb_event_all_token_dir_path, target_doc_id, debug_print=debug_print)
	if base_tokenization == 'sents':
		#conll_input_dir_path = base_dir_path + "\\corenlp_output_with_modified_sent_split\\%s" % data_type
		conll_input_dir_path = os.path.join(g_dir_path_to_corenlp_output, "%s" % data_type)

		tokenized_texts = extract_tokenization_from_corenlp_parsed_text(conll_input_dir_path, target_doc_id, debug_print=debug_print)
	else:
		raise ValueError('Unknown type of tokenized input: %s' % base_tokenization)

	for doc_id, file_path_a1, file_path_a2, file_path_txt in files:
		if target_doc_id and doc_id != target_doc_id:
			continue

		tokenized_sents = tokenized_texts[doc_id]


		doc = load_bb_event_doc_data(doc_id, file_path_a1, file_path_a2, file_path_txt, tokenized_sents, data_type, base_tokenization)

		#print
		#print '\n'.join('@ ' + s for s in doc.iter_sents(refined=True))
		#print doc.get_bacteria_by_id('T23')
		#exit()



		yield doc


def get_original_plain_sents(doc):
	"""

	:type doc: Doc
	:rtype: (str, list[str])
	"""
	refined_sents = list(doc.iter_sents(refined=True))

	original_title, was_refined, multibyte_map_for_title = doc.get_original_title()
	print '------' * 3, 'Title', '------' * 3
	if was_refined:
		print doc.get_title_text(refined=True)

	num_original_sents = 0
	original_sents = []

	for sent_offset, (original_sent, was_refined, multibyte_map_for_sent) in enumerate(doc.iter_original_sents()):
		print '------' * 3,'Sent #%d' % sent_offset, '------' * 3

		if was_refined:
			refined_sent = doc.get_sent_by_offset(sent_offset, refined=True)

			# print '   - # of "@":', refined_sent.count('@')
			# print '   - # of multibyte chars:', len(multibyte_map_for_sent)
			assert refined_sent.count('@') == len(multibyte_map_for_sent)

			print refined_sent

		original_sents.append(original_sent)
		num_original_sents += 1

	assert num_original_sents == len(refined_sents)

	return original_title, original_sents
	#original_text = original_title + '\n' + '\n'.join(original_sents)
	#return original_text



if __name__ == '__main__':


	pass