from nltk import WordNetLemmatizer
lemmatizer = WordNetLemmatizer()
test_lemma = lemmatizer.lemmatize('apple')  # Loading WordNet lemmatizer by executing it for the first time...

class SentDep(object):

	all_preps = ['in', 'on', 'upon', 'of', 'to', 'with', 'by', 'from', 'at', 'for',
				 'as',  'into', 'onto', 'about', 'under', 'concerning', 'including',
				 'against', 'among', 'over', 'between', 'within', 'without',
				 'along', 'across', 'behind', 'beyond', 'except', 'around',
				 'above', 'through', 'before', 'after', ]
	loc_preps = ['in', 'on', 'to', 'with', 'by', 'from', 'at', 'for',
				 'as',  # BAC used as LOC
				 'into', 'onto', 'under',
				 'among', 'over', 'between', 'within',
				 'along', 'across', 'behind', 'beyond', 'around',
				 'above', 'through', ]

	loc_strong_preps = ['in', 'on', 'from', 'at', 'into', 'onto', 'within']
	nn_neighbor_labels = ['amod', 'appos', 'advmod', 'nn', 'poss']

	def __init__(self, root_token_idx, root_token_word, token_dep_list, doc_id):
		"""

		:type root_token_idx: int
		:type root_token_word: str
		:type token_dep_list: list[dict[str]]
		:type doc_id: str
		"""
		self._doc_id = doc_id
		self._root_token_idx = root_token_idx
		self._root_token_word = root_token_word
		self._token_dep_list = token_dep_list
		self._lemma_list = []

	def __len__(self):
		"""

		:rtype: int
		"""

		return self.get_num_tokens()

	def __iter__(self):
		return (t['form'] for t in self._token_dep_list)

	def get_root(self):
		"""
		Return root token index (int) & root token word (str)

		:rtype: (int, str)
		"""
		return self._root_token_idx, self._root_token_word

	def get_num_tokens(self):
		return len(self._token_dep_list)

	def get_sent_tokens(self):
		"""

		:rtype: list[str]
		"""
		return [t['form'] for t in self._token_dep_list]

	def get_token(self, token_idx):
		"""

		:rtype token_idx: int
		:rtype: str
		"""
		return self._token_dep_list[token_idx]['form']

	def get_token_pos(self, token_idx):
		"""

		:rtype token_idx: int
		:return:
		"""
		return self._token_dep_list[token_idx]['pos']

	def get_token_pos_seq(self, token_idx_seq):
		"""

		:rtype token_idx: list[int]
		:rtype: list[str]
		"""
		return [self._token_dep_list[idx]['pos'] for idx in token_idx_seq]

	def get_token_lemma_seq(self):

		if self._lemma_list:
			return self._lemma_list

		lemma_list = []

		for token_idx, token in enumerate(self):

			pos = self.get_token_pos(token_idx)
			#is_noun = sent_dep.check_dep_pos_noun(pos)
			is_verb = self.check_dep_pos_verb(pos)

			lemma = lemmatizer.lemmatize(token.lower().decode('utf-8'), pos=('v' if is_verb else 'n'))
			lemma_list.append(lemma)

		self._lemma_list = lemma_list
		return lemma_list


	def get_path_from_root(self, start_token_idx, supp_str=''):
		"""
		Return a list (paths) of lists (path) of pairs (token_idx, dep_label)

		:type start_token_idx: int
		:type supp_str: str
		:rtype: list[(int, str, str, str)]
		"""

		#print '@@@'; print self._token_dep_list

		start_token_item = self._token_dep_list[start_token_idx]  # type: dict[str, list]
		start_token = start_token_item['form']
		start_pos = self.get_token_pos(start_token_idx)

		working_path_queue = []
		result_paths = []

		init_path = [(start_token_idx, start_token, start_pos, '')]
		working_path_queue.append(init_path)

		while working_path_queue:

			#print 'Queue:', working_path_queue

			path = working_path_queue.pop(0)

			#print ' - Path:', path

			leading_token_idx, leading_token, leading_pos, dep_label = path[0]
			incoming_tokens = self._token_dep_list[leading_token_idx]['incoming']

			#print ' - incoming:', incoming_tokens
			#print ' - dep:', self._token_dep_list[leading_token_idx]

			if not incoming_tokens:
				result_paths.append(path)
				continue

			for in_token_idx, dep_label in incoming_tokens:
				in_token = self._token_dep_list[in_token_idx]['form']
				in_token_pos = self._token_dep_list[in_token_idx]['pos']
				longer_path = [(in_token_idx, in_token, in_token_pos, dep_label)] + path[:]
				#print ' - longer:', longer_path
				working_path_queue.append(longer_path)

	#	print '\n%s Path (%d) ROOT => "%s" (%d)' % (
	#		supp_str, len(result_paths), start_token, start_token_idx)
	#	for path in result_paths:
	#		print ' -> '.join('"%s"(%d/%s/%s)' % (t[1],t[0],t[2],t[3]) for t in path)

		assert len(result_paths) == 1
		result_path = result_paths[0]

		for item_idx in reversed(range(len(result_path))):
			token_idx, token, token_pos, dep_label_to_next = result_path[item_idx]

			if item_idx == 0:
				prev_label = 'root'
			else:
				_, _, _, prev_label = result_path[item_idx-1]
			result_path[item_idx] = token_idx, token, token_pos, prev_label

		return result_path


	def get_paths_to_leaves(self, start_token_idx, supp_str=''):
		"""

		:type start_token_idx: int
		:type supp_str: str
		:rtype: list[list[(int, str, str, str)]]
		"""

		start_token_item = self._token_dep_list[start_token_idx]  # type: dict[str, list]
		start_token = start_token_item['form']
		start_pos = self.get_token_pos(start_token_idx)

		working_path_queue = []
		result_paths = []

		init_path = [(start_token_idx, start_token, start_pos, '')]
		working_path_queue.append(init_path)

		while working_path_queue:

			#print '------------ Queue ------------'
			#print '\n'.join(str(q) for q in working_path_queue)
			#print '----------- Complete ----------'
			#print '\n'.join(str(p) for p in result_paths)
			#print '~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~'

			path = working_path_queue.pop(0)

			#print ' - Path:', path

			tail_token_idx, tail_token, tail_pos, dep_label = path[-1]
			outgoing_tokens = self._token_dep_list[tail_token_idx]['outgoing']

			#print ' - incoming:', outgoing_tokens
			#print ' - dep:', self._token_dep_list[tail_token_idx]

			if not outgoing_tokens:
				result_paths.append(path)
				continue

			for out_token_idx, dep_label in outgoing_tokens:
				out_token = self._token_dep_list[out_token_idx]['form']
				out_token_pos = self._token_dep_list[out_token_idx]['pos']
				longer_path = path[:] + [(out_token_idx, out_token, out_token_pos, dep_label)]
				# print ' - longer:', longer_path
				working_path_queue.append(longer_path)

			#print raw_input()

	#	print '\n%s Path (%d) "%s" => LEAF (%d)' % (
	#		supp_str, len(result_paths), start_token, start_token_idx)
	#	for path in result_paths:
	#		print ' -> '.join('"%s"(%d/%s/%s)' % (t[1], t[0], t[2], t[3]) for t in path)

		for result_path in result_paths:
			for item_idx, (token_idx, token, token_pos, dep_label_to_next) in enumerate(result_path):
				if item_idx == 0:
					continue
				_, _, _, prev_label = result_path[item_idx - 1]
				result_path[item_idx] = token_idx, token, token_pos, prev_label

		return result_paths

	def get_parent_tokens(self, token_idx):
		"""

		:type token_idx: int
		:rtype: list[(int, str)]
		"""
		incoming_tokens = self._token_dep_list[token_idx]['incoming']
		return incoming_tokens  # list of (in_token_idx, dep_label)

	def get_children_tokens(self, token_idx):
		"""

		:param token_idx:
		:rtype: list[(int, str)]
		"""
		outgoing_tokens = self._token_dep_list[token_idx]['outgoing']
		return outgoing_tokens  # list of (in_token_idx, dep_label)

	def get_nsubj_token_of_verb(self, verb_token_idx):
		"""

		:param verb_token_idx:
		:rtype: int
		"""

		children = self.get_children_tokens(verb_token_idx)

		for child_token_idx, dep_label in children:
			if self.check_dep_label_nsubjx(dep_label):
				return child_token_idx
		return -99999


	def get_head_token_for_span(self, span_token_idx_seq_in_sent):
		"""
		return (head_token_idx_in_sent, head_token_offset_in_ent)

		:param span_token_idx_seq_in_sent:
		:param entity_text:
		:param sent_offset:
		:rtype: (int, int)
		"""

		if len(span_token_idx_seq_in_sent) == 1:
			return span_token_idx_seq_in_sent[0], 0

		preps = SentDep.all_preps

		token_idx_before_prep_in_sent = 99999
		token_offset_before_prep_in_ent = 99999

		sent_tokens = self.get_sent_tokens()
		#print '~~!!', span_token_idx_seq, entity_text

		for token_offset_in_ent, token_idx_in_sent in enumerate(span_token_idx_seq_in_sent):
			token = sent_tokens[token_idx_in_sent]

			if token_idx_in_sent > 0 and token in preps:
				token_idx_before_prep_in_sent = span_token_idx_seq_in_sent[token_offset_in_ent - 1]
				token_offset_before_prep_in_ent = token_offset_in_ent - 1
				is_prep_found = True
				#print '@prep$', token, token_idx_in_sent, token_idx_before_prep_in_sent, token_offset_before_prep_in_ent
				break

		#print '@prep@', token_idx_before_prep_in_sent, token_offset_before_prep_in_ent

		collected_results = []

		outer_left_token = sent_tokens[span_token_idx_seq_in_sent[0] - 1] if span_token_idx_seq_in_sent[0] != 0 else ''
		inner_off_tokens = sent_tokens[span_token_idx_seq_in_sent[0]:span_token_idx_seq_in_sent[-1]]

		if 'and' in inner_off_tokens:
			conj_idx = inner_off_tokens.index('and') + span_token_idx_seq_in_sent[0]
			is_conj_found = True
		elif 'or' in inner_off_tokens:
			conj_idx = inner_off_tokens.index('or') + span_token_idx_seq_in_sent[0]
			is_conj_found = True
		elif outer_left_token == 'and' or outer_left_token == 'or':
			conj_idx = None
			is_conj_found = True
		else:
			conj_idx = None
			is_conj_found = False

		cnt_dep_head_from_right = 0

		for token_offset_in_entity, token_idx_in_sent in enumerate(span_token_idx_seq_in_sent):
			token_item = self._token_dep_list[token_idx_in_sent]
			incoming_items = token_item['incoming']

			try:
				incoming_token_idx, dep_label = incoming_items[0]
			except IndexError:
				return token_idx_in_sent, token_offset_in_entity

			if incoming_token_idx not in span_token_idx_seq_in_sent:
				if token_idx_in_sent < incoming_token_idx:
					cnt_dep_head_from_right += 1

				collected_results.append((token_idx_in_sent, token_offset_in_entity))

		#print '$$collected_results:', collected_results

		if cnt_dep_head_from_right == len(span_token_idx_seq_in_sent):
			is_nested_noun_seq = True
		else:
			is_nested_noun_seq = False

		#assert collected_results

		last_token_idx_in_sent = span_token_idx_seq_in_sent[-1]
		last_token_offset_in_ent = len(span_token_idx_seq_in_sent) - 1

		#print '#token_idx_before_prep_in_sent:', token_idx_before_prep_in_sent
		#print '#last_token_idx_in_sent:', last_token_idx_in_sent

		if token_idx_before_prep_in_sent < last_token_idx_in_sent:
			default_result = token_idx_before_prep_in_sent, token_offset_before_prep_in_ent
		else:
			default_result = last_token_idx_in_sent, last_token_offset_in_ent

		is_hyphen_found = False

		#print '$default_result:', default_result
		#print '#is_nested_noun_seq:', is_nested_noun_seq
		#print '#is_hyphen_found:', is_hyphen_found

		if is_nested_noun_seq:
			collected_result = collected_results[-1]
		else:
			collected_result = collected_results[0]

		token_idx_in_sent, _ = collected_result

		prev_token = sent_tokens[token_idx_in_sent - 1] if token_idx_in_sent - 1 in span_token_idx_seq_in_sent else ''
		next_token = sent_tokens[token_idx_in_sent + 1] if token_idx_in_sent + 1 in span_token_idx_seq_in_sent else ''

		if prev_token == '-':
			hyphen_idx = token_idx_in_sent - 1
			is_hyphen_found = True
		elif next_token == '-':
			hyphen_idx = token_idx_in_sent + 1
			is_hyphen_found = True
		else:
			hyphen_idx = None

		#print '@!@', collected_result, default_result, token_idx_before_prep_in_sent, is_conj_found, conj_idx, is_hyphen_found

		if (not is_conj_found or default_result[0] < conj_idx) \
				and (not is_hyphen_found or default_result[0] < hyphen_idx)\
				and collected_result < default_result:
			result = collected_result
		else:
			result = default_result

	#	print 'HEAD "%s"' % entity_text, span_token_idx_seq
	#	print '  ->', result, sent_tokens[result[0]]

	#	if is_hyphen_found or is_prep_found or result[0] != span_token_idx_seq[-1]:
	#		print 'HEAD "%s" (%s)' % (entity_text, str(sent_offset)), span_token_idx_seq
	#		print '  ->', result, sent_tokens[result[0]]

		return result

	def get_lowest_subtree(self, token1_idx, token2_idx):
		"""

		:param token1_idx:
		:param token2_idx:
		:rtype: (list[(int, str, str, str)], list[(int, str, str, str)])
		"""

		if token1_idx > token2_idx:
			#	token1_idx, token2_idx = token2_idx, token1_idx
			pass
		elif token1_idx == token2_idx:
			return []

		path_from_root_to_token1 = self.get_path_from_root(token1_idx)
		path_from_root_to_token2 = self.get_path_from_root(token2_idx)

		#print '$$!!@@'
		#print path_from_root_to_token1
		#print path_from_root_to_token2


		lowest_common_ancestor_offset = 0
		assert path_from_root_to_token1[0] == path_from_root_to_token2[0]

		for path_inner_offset in range(min(len(path_from_root_to_token1), len(path_from_root_to_token2))):
			token_offset1, token1, pos1, dep_label1 = path_from_root_to_token1[path_inner_offset]
			token_offset2, token2, pos2, dep_label2 = path_from_root_to_token2[path_inner_offset]

			#print '!Compare:', '[%d]' % path_inner_offset, token_offset1, token_offset2, token_offset1 != token_offset2

			if token_offset1 != token_offset2:
				#lowest_common_ancestor_offset = path_inner_offset - 1
				break

			lowest_common_ancestor_offset = path_inner_offset

		#print '@@lowest_common_ancestor_offset:', lowest_common_ancestor_offset

		lower_path1 = path_from_root_to_token1[lowest_common_ancestor_offset:]
		lower_path2 = path_from_root_to_token2[lowest_common_ancestor_offset:]

		return lower_path1, lower_path2


	def get_shortest_path(self, token1_idx, token2_idx):
		"""

		:param token1_idx:
		:param token2_idx:
		:rtype: list[(int, str, str, str)]
		"""

		if token1_idx > token2_idx:
		#	token1_idx, token2_idx = token2_idx, token1_idx
			pass
		elif token1_idx == token2_idx:
			return []

		path_from_root_to_token1 = self.get_path_from_root(token1_idx)
		path_from_root_to_token2 = self.get_path_from_root(token2_idx)


		lowest_common_ancestor_offset = -9999

		for path_inner_offset in range(len(path_from_root_to_token1)):
			token_offset1, token1, pos1, dep_label1 = path_from_root_to_token1[path_inner_offset]
			token_offset2, token2, pos2, dep_label2 = path_from_root_to_token2[path_inner_offset]

			if token_offset1 != token_offset2:
				break

			lowest_common_ancestor_offset = path_inner_offset

		assert lowest_common_ancestor_offset >= 0

		lower_path1 = path_from_root_to_token1[lowest_common_ancestor_offset + 1:]
		lower_path2 = path_from_root_to_token2[lowest_common_ancestor_offset:]
		_, _, _, dep_label_to_lca = path_from_root_to_token1[lowest_common_ancestor_offset]


		reversed_lower_path1 = list(reversed(lower_path1))

		for i in range(len(reversed_lower_path1)):
			curr_token_offset, curr_token, curr_pos, curr_dep_label = reversed_lower_path1[i]

			if i < len(reversed_lower_path1) - 1:
				next_token_offset, next_token, next_pos, next_dep_label = reversed_lower_path1[i + 1]
				dep_label = next_dep_label
			else:
				dep_label = dep_label_to_lca

			reversed_lower_path1[i] = curr_token_offset, curr_token, curr_pos, dep_label

		shortest_path = reversed_lower_path1 + lower_path2

		return shortest_path

	def check_t1_conj_t2(self, token1_idx, token2_idx):
		# "token1 and token2"
		token1_parents = self.get_parent_tokens(token1_idx)
		if token1_parents and token1_parents[0] == (token2_idx, 'conj'):
			return True
		# "token2 and token1"
		token2_parents = self.get_parent_tokens(token2_idx)
		if token2_parents and token2_parents[0] == (token1_idx, 'conj'):
			return True

		return False
		#return self.get_parent_tokens(token1_idx)[0] == (token2_idx, 'conj') or \
		#	   self.get_parent_tokens(token2_idx)[0] == (token1_idx, 'conj')

	def check_t1_appos_t2(self, token1_idx, token2_idx):
		# "Token1 = Token2"
		token1_parents = self.get_parent_tokens(token1_idx)
		if token1_parents and token1_parents[0] == (token2_idx, 'appos'):
			return True
		# "Token2 = Token1"
		token2_parents = self.get_parent_tokens(token2_idx)
		if token2_parents and token2_parents[0] == (token1_idx, 'appos'):
			return True

		return False

	def check_t1_comma_t2(self, span1_head_idx, span1_idx_seq, span2_head_idx, span2_idx_seq):
		return (span2_idx_seq[0] - span1_idx_seq[-1] == 2 and self.get_token(span1_idx_seq[-1] + 1) == ',') \
			   or (span1_head_idx != span2_head_idx and self.get_parent_tokens(span1_head_idx) == self.get_parent_tokens(span2_head_idx))

	def check_t1_comp_t2(self, token1_idx, token2_idx):
		token1_parents = self.get_parent_tokens(token1_idx)
		if token1_parents:
			parent_idx, dep_label = token1_parents[0]
			if parent_idx == token2_idx and self.check_dep_label_comp(dep_label):
				return True
			#if token1_parents[0] == (token2_idx, 'appos'):
			#	return True
		token2_parents = self.get_parent_tokens(token2_idx)
		if token2_parents:
			parent_idx, dep_label = token2_parents[0]
			if parent_idx == token1_idx and self.check_dep_label_comp(dep_label):
				return True
			#if token2_parents[0] == (token1_idx, 'appos'):
			#	return True

		return False

	def check_t1_is_t2(self, token1_idx, token2_idx):
		parents = self.get_parent_tokens(token1_idx)
		if parents:
			parent_idx, dep_label = parents[0]
			return parent_idx == token2_idx \
				   and self.check_dep_label_nsubjx(dep_label) \
				   and self.check_dep_pos_noun(self.get_token_pos(parent_idx))
		return False

	def check_t1_prep_t2(self, token1_idx, token2_idx, prep=''):
		parents = self.get_parent_tokens(token2_idx)
		if not parents:
			return ''
		parent_idx, parent_dep_label = parents[0]
		if prep and self.get_token(parent_idx) != prep:
			return ''
		gr_parents = self.get_parent_tokens(parent_idx)
		if not gr_parents:
			return ''
		gr_parent_idx, gr_parent_dep_label = gr_parents[0]
		if self.check_dep_label_pobj(parent_dep_label) \
				and self.check_dep_label_prep(gr_parent_dep_label) \
				and gr_parent_idx == token1_idx:
			return self.get_token(parent_idx)
		else:
			return ''

	def check_t1_ving_or_ved_prep_t2(self, token1_idx, token2_idx):

		parents = self.get_parent_tokens(token2_idx)
		if not parents:
			return ''
		parent_idx, parent_dep_label = parents[0]

		gr1_parents = self.get_parent_tokens(parent_idx)
		if not gr1_parents:
			return ''
		gr1_parent_idx, gr1_parent_dep_label = gr1_parents[0]

		if self.check_dep_label_dobj(parent_dep_label):
			if self.check_dep_label_vmod(gr1_parent_dep_label) and gr1_parent_idx == token1_idx:
				return self.get_token(parent_idx)
			else:
				return ''

		gr2_parents = self.get_parent_tokens(gr1_parent_idx)
		if not gr2_parents:
			return ''
		gr2_parent_idx, gr2_parent_dep_label = gr2_parents[0]

		if self.check_dep_label_pobj(parent_dep_label) \
				and self.check_dep_label_prep(gr1_parent_dep_label)\
				and self.check_dep_label_vmod(gr2_parent_dep_label)\
				and gr2_parent_idx == token1_idx:
			return self.get_token(gr1_parent_idx) + " " + self.get_token(parent_idx)


		return ''

	def check_t1_vp_t2(self, token1_idx, token2_idx, path_from_subroot_to_t1, path_from_subroot_to_t2):

		if len(path_from_subroot_to_t1) == 1 or len(path_from_subroot_to_t2) == 1:
			return ''

		subroot_token_idx, subroot_token, _, _ = path_from_subroot_to_t1[0]

		path_token_idx1, _, _, dep_label1 = path_from_subroot_to_t1[1]
		_, _, _, dep_label2_1 = path_from_subroot_to_t2[1]

		if len(path_from_subroot_to_t2) > 2:
			path_token_idx2_2, _, _, dep_label2_2 = path_from_subroot_to_t2[2]
		else:
			path_token_idx2_2 = dep_label2_2 = ''

		strict_check = True

		if strict_check:

			if not self.check_dep_label_nsubjx(dep_label1) or path_token_idx1 != token1_idx:
				return ''

			if self.check_dep_label_dobj(dep_label2_1) \
					or (self.check_dep_label_prep(dep_label2_1) and self.check_dep_label_pobj(dep_label2_2)
						and path_token_idx2_2 == token2_idx):
				return '"%s"(%d)' % (subroot_token, subroot_token_idx)

		else:

			if not self.check_dep_label_nsubjx(dep_label1):
				return ''

			if self.check_dep_label_dobj(dep_label2_1) \
					or (self.check_dep_label_prep(dep_label2_1) and self.check_dep_label_pobj(dep_label2_2)):
				return '"%s"(%d)' % (subroot_token, subroot_token_idx)

	def check_t1verb_t2obj(self, token1_idx, token2_idx):
		parents = self.get_parent_tokens(token2_idx)
		if not parents:
			return ''
		parent_idx, parent_dep_label = parents[0]

		if parent_idx == token1_idx \
				and (self.check_dep_label_dobj(parent_dep_label) or self.check_dep_label_pobj(parent_dep_label)):
			return self.get_token(token1_idx) + " " + self.get_token(token2_idx)

		return ''


	def check_vp_t1_ving_or_ved_prep_t2(self, token1_idx, token2_idx, subroot_to_token1_path, subroot_to_token2_path):

		debug_print = False
		#debug_print = True

		if token1_idx >= token2_idx:
			return False

		subroot_token_idx, _, _, _ = subroot_to_token1_path[0]

		if not self.check_dep_pos_verb(self.get_token_pos(subroot_token_idx)):
			return False

		strict_syntax = True
		strict_syntax = False

		#if debug_print:
		#	print '     --> subroot (v): %s' % self.get_token(subroot_token_idx)

		is_token1_dobj = check_path_for_dobj_with_ent(subroot_to_token1_path[1:], [token1_idx],
													  strict_syntax=strict_syntax, debug_print=debug_print)

		if not is_token1_dobj:
			is_token1_pobj = check_path_for_prep_pobj_with_ent(subroot_to_token1_path[1:], [token1_idx],
															   strict_syntax=strict_syntax, debug_print=debug_print)
			if not is_token1_pobj:
				return False

		second_token_idx_in_path2, _, _, _ = subroot_to_token2_path[1]
		if not self.check_dep_pos_verb(self.get_token_pos(second_token_idx_in_path2)):
			return False

		is_token2_dobj = check_path_for_dobj_with_ent(subroot_to_token2_path[2:], [token2_idx],
													  strict_syntax=strict_syntax, debug_print=debug_print)

		if not is_token2_dobj:
			is_token2_pobj = check_path_for_prep_pobj_with_ent(subroot_to_token2_path[2:], [token2_idx],
															   strict_syntax=strict_syntax, debug_print=debug_print)
			if not is_token2_pobj:
				return False

		return True


	def check_two_modified_in_common_np(self, token1_idx, token2_idx, subroot_to_token1_path, subroot_to_token2_path):
		#    amod (adjectival modifier); appos (appositional modifier);
		#    advmod (adverb modifier); nn (noun compound modifier);
		#    poss: possession modifier;

		dep_labels = self.nn_neighbor_labels

		#if len(subroot_to_token1_path) > 2 or len(subroot_to_token2_path) > 2:
		#	return False

		is_path1_ok = False
		is_path2_ok = False
		token1_dep_labels = []
		token2_dep_labels = []
		subroot_token_idx, _, _, _ = subroot_to_token1_path[0]

		if subroot_token_idx == token1_idx:
			is_path1_ok = True
			token1_dep_labels.append('subroot')
		elif len(subroot_to_token1_path) > 1:
			for _, _, _, token1_dep_label in subroot_to_token1_path[1:]:
				if token1_dep_label not in dep_labels:
					is_path1_ok = False
					break
				token1_dep_labels.append(token1_dep_label)
			else:
				is_path1_ok = True

		if subroot_token_idx == token2_idx:
			is_path2_ok = True
			token2_dep_labels.append('subroot')
		elif len(subroot_to_token2_path) > 1:
			# _, _, _, token2_dep_label = subroot_to_token2_path[1]
			for _, _, _, token2_dep_label in subroot_to_token2_path[1:]:
				if token2_dep_label not in dep_labels:
					is_path2_ok = False
					break
				token2_dep_labels.append(token2_dep_label)
			else:
				is_path2_ok = True

		if is_path1_ok and is_path2_ok:
			return "dep label: '%s' '%s'" % ('->'.join(token1_dep_labels), '->'.join(token2_dep_labels))

	def check_t1_is_ancestor_of_t2(self, t1_idx, t2_idx):
		"""

		:type t1_idx: int
		:type t2_idx: int
		:rtype: bool
		"""

		curr_idx = t2_idx
		while curr_idx >= 0:
			parents = self.get_parent_tokens(curr_idx)
			if not parents:
				return False
			parent_idx, _ = parents[0]
			if parent_idx == t1_idx:
				return True
			curr_idx = parent_idx

		return False

	@staticmethod
	def check_dep_pos_verb(dep_pos):
		return dep_pos.startswith('V') or dep_pos.startswith('v')

	@staticmethod
	def check_dep_pos_adj(dep_pos):
		return dep_pos.startswith('J') or dep_pos.startswith('j')

	@staticmethod
	def check_dep_pos_noun(dep_pos):
		return dep_pos.startswith('N') or dep_pos.startswith('n')

	@staticmethod
	def check_dep_pos_proper_noun(dep_pos):
		return dep_pos == 'NNP' or dep_pos == 'nnp'

	@staticmethod
	def check_dep_pos_adverb(dep_pos):
		return dep_pos.startswith('RB') or dep_pos.startswith('rb')

	@staticmethod
	def check_dep_pos_prep(dep_pos):
		return dep_pos == 'IN' or dep_pos == 'in'

	@staticmethod
	def check_dep_label_prep(dep_label):
		return dep_label.startswith('prep')

	@staticmethod
	def check_dep_label_dobj(dep_label):
		return dep_label.startswith('dobj')

	@staticmethod
	def check_dep_label_pobj(dep_label):
		return dep_label.startswith('pobj')

	@staticmethod
	def check_dep_label_nsubjx(dep_label):
		return dep_label.startswith('nsubj')

	@staticmethod
	def check_dep_label_conj(dep_label):
		return dep_label.startswith('conj')

	@staticmethod
	def check_dep_label_appos(dep_label):
		return dep_label.endswith('appos')

	@staticmethod
	def check_dep_label_comp(dep_label):
		# acomp: adjectival complement / "She looks very beautiful." => acomp(looks, beautiful)
		# ccomp: clausal complement / "He says that you like to swim." => ccomp(says, like)
		# pcomp: prepositional complement / "They heard about you missing classes." => pcomp(about, missing)
		# xcomp: open clausal complement / "He says that you like to swim." => xcomp(like, swim)
		return dep_label.endswith('comp')

	@staticmethod
	def check_dep_label_vmod(dep_label):
		return dep_label.startswith('vmod')

	@staticmethod
	def check_dep_label_unknown(dep_label):
		return dep_label.startswith('dep')


def check_pat_noun_of_bac_in_loc1(path_to_bac, bac_token_idx_seq, path_to_loc, loc_token_idx_seq,
								  bac_loc_reversed=False, strict_syntax=False, debug_print=False):
	"""

	:type path_to_bac: list[(int, str, str, str)]
	:type bac_token_idx_seq: list[int]
	:type path_to_loc: list[(int, str, str, str)]
	:type loc_token_idx_seq: list[int]
	:rtype: ((int, str), (int, str))
	"""
	false_result = None

	if bac_token_idx_seq[0] > loc_token_idx_seq[0]:
		return false_result

	#debug_print = False
	#debug_print = True

	if debug_print: print '  -- Checking pattern [noun_of_%s]...' % ("LOC_in_BAC" if bac_loc_reversed else "BAC_in_LOC")

	subroot_token_idx, subroot_token, subroot_pos, _ = path_to_bac[0]

	if not SentDep.check_dep_pos_noun(subroot_pos):
		return false_result

	if subroot_token_idx > bac_token_idx_seq[0]:
		return false_result

	if debug_print: print '     --> subroot is a noun!: "%s"' % subroot_token

	target_span = subroot_token
	target_span_idx = subroot_token_idx

	if bac_loc_reversed:
		preps_for_bac = SentDep.loc_preps
		#constraint_on_prep_for_bac = False
		constraint_on_prep_for_bac = True
		preps_for_loc = SentDep.all_preps
		constraint_on_prep_for_loc = False
	else:
		preps_for_bac = SentDep.all_preps
		constraint_on_prep_for_bac = False
		preps_for_loc = SentDep.loc_preps
		constraint_on_prep_for_loc = True

	result = check_path_for_prep_pobj_with_ent(path_to_bac[1:], bac_token_idx_seq, preps=preps_for_bac,
											   only_one_prep_in_path=constraint_on_prep_for_bac,
											   strict_syntax=strict_syntax, debug_print=debug_print)
	if not result:
		if debug_print:
			print '     --> [FAIL] No "prep->pobj" found in %s path! (subroot: "%s")' % ('LOC' if bac_loc_reversed else 'BAC', subroot_token)
		return false_result

	if debug_print: print '     --> "prep->pobj" found in %s path! (subroot: "%s")' % ('LOC' if bac_loc_reversed else 'BAC', subroot_token)

	result = check_path_for_prep_pobj_with_ent(path_to_loc[1:], loc_token_idx_seq, preps=preps_for_loc,
											   only_one_prep_in_path=constraint_on_prep_for_loc,
											   strict_syntax=strict_syntax, debug_print=debug_print)
	if not result:
		if debug_print:
			print '     --> [FAIL] No "prep->pobj" found in %s path! (subroot: "%s")' % ('BAC' if bac_loc_reversed else 'LOC', subroot_token)
		return false_result

	if debug_print: print '     --> "prep->pobj" found in %s path! (subroot: "%s")' % ('BAC' if bac_loc_reversed else 'LOC', subroot_token)

	prep_matched = result['prep']
	return (target_span_idx, target_span), prep_matched


def check_pat_noun_of_bac_in_loc2(path_to_bac, bac_token_idx_seq, path_to_loc, loc_token_idx_seq,
								  sent_dep=None, bac_loc_reversed=False,
								  strict_syntax=False, debug_print=False):
	"""

	:type path_to_bac: list[(int, str, str, str)]
	:type bac_token_idx_seq: list[int]
	:type path_to_loc: list[(int, str, str, str)]
	:type loc_token_idx_seq: list[int]
	:rtype: ((int, str), (int, str))
	"""
	false_result = None

	if bac_token_idx_seq[0] > loc_token_idx_seq[0]:
		return false_result

	#debug_print = False
	#debug_print = True

	if debug_print: print '  -- Checking pattern [noun_of] + [%s]...' % ("LOC_in_BAC" if bac_loc_reversed else "BAC_in_LOC")

	target_span = ''
	target_span_idx = -9999999
	subroot_token_idx, subroot_token, subroot_pos, _ = path_to_bac[0]

	if subroot_token_idx > bac_token_idx_seq[0]:
		return false_result

	is_subroot_in_bac = False
	if subroot_token_idx in bac_token_idx_seq:
		is_subroot_in_bac = True
		if debug_print: print '     --> subroot is in %s!: "%s"' % ('LOC' if bac_loc_reversed else 'BAC', subroot_token)

	if not is_subroot_in_bac:
		return false_result

	#if bac_loc_reversed:
	#	preps_for_loc = SentDep.all_preps
	#	constraint_on_prep = False
	#else:
	#	preps_for_loc = SentDep.loc_preps
	#	constraint_on_prep = True

	preps_for_loc = SentDep.all_preps
	constraint_on_prep = True
	#preps_for_loc = SentDep.loc_preps
	#constraint_on_prep = True

	result_for_loc = check_path_for_prep_pobj_with_ent(path_to_loc[1:], loc_token_idx_seq, preps=preps_for_loc,
													   only_one_prep_in_path=constraint_on_prep,
													   strict_syntax=strict_syntax, debug_print=debug_print)
	if not result_for_loc:
		return false_result

	if debug_print: print '     --> "prep->pobj" found in %s path!: "%s"' % ('BAC' if bac_loc_reversed else 'LOC', result_for_loc['form'])

	parent_tokens = sent_dep.get_parent_tokens(subroot_token_idx)
	if parent_tokens:
		parent_token_idx, dep_label = parent_tokens[0]
		gr_parent_tokens = sent_dep.get_parent_tokens(parent_token_idx)

		if gr_parent_tokens:
			gr_parent_token_idx, parent_dep_label = gr_parent_tokens[0]
			gr_parent_token_pos = sent_dep.get_token_pos(gr_parent_token_idx)

			#print '@@11', dep_label, parent_dep_label, gr_parent_token_pos

			if (SentDep.check_dep_label_pobj(dep_label)
					and SentDep.check_dep_label_prep(parent_dep_label)
					and SentDep.check_dep_pos_noun(gr_parent_token_pos)):
				gr_parent_token = sent_dep.get_token(gr_parent_token_idx)
				parent_token = sent_dep.get_token(parent_token_idx)
				target_span = gr_parent_token
				target_span_idx = gr_parent_token_idx

				phrase = '%s %s' % (gr_parent_token, parent_token)
				if debug_print: print '     --> "noun->prep->%s" found!: "%s"' % ('LOC' if bac_loc_reversed else 'BAC', phrase)

	loc_prep_matched = result_for_loc['prep']

	return (target_span_idx, target_span), loc_prep_matched


def check_pat_verb_bac_in_loc(bac_path, bac_token_idx_seq, loc_path, loc_token_idx_seq,
							  bac_loc_reversed=False, strict_syntax=False, debug_print=False):
	"""
	:type bac_path: list[(int, str, str, str)]
	:type bac_token_idx_seq: list[int]
	:type loc_path: list[(int, str, str, str)]
	:type loc_token_idx_seq: list[int]
	:rtype: ((int, str), (int, str))
	"""
	false_result = None

	if bac_token_idx_seq[0] > loc_token_idx_seq[0]:
		return false_result

	#debug_print = False
	#debug_print = True

	if debug_print: print '  -- Checking pattern [verb_%s]...' % ("LOC_in_BAC" if bac_loc_reversed else "BAC_in_LOC")

	subroot_token_idx, subroot_token, subroot_pos, _ = bac_path[0]

	if not SentDep.check_dep_pos_verb(subroot_pos):
		return false_result

	if subroot_token_idx > bac_token_idx_seq[0]:
		return false_result

	if debug_print: print '     --> subroot is a verb!: "%s"(%d)' % (subroot_token, subroot_token_idx)

	target_span = subroot_token
	target_span_idx = subroot_token_idx

	if not check_path_for_dobj_with_ent(bac_path[1:], bac_token_idx_seq, strict_syntax=strict_syntax, debug_print=debug_print):
		return false_result

	if debug_print: print '     --> "dobj" found in %s path! (verb: "%s")' % ('LOC' if bac_loc_reversed else 'BAC', subroot_token)

	if bac_loc_reversed:
		preps_for_loc = SentDep.all_preps
	else:
		preps_for_loc = SentDep.loc_preps

	result_for_loc = check_path_for_prep_pobj_with_ent(loc_path[1:], loc_token_idx_seq, preps=preps_for_loc,
													   strict_syntax=strict_syntax, debug_print=debug_print)
	if not result_for_loc:
		return false_result

	if debug_print: print '     --> "prep->pobj" found in %s path! (verb: "%s")' % ('BAC' if bac_loc_reversed else 'LOC', subroot_token)

	loc_prep_matched = result_for_loc['prep']
	return (target_span_idx, target_span), loc_prep_matched


def check_pat_bac_v_or_be_pp_in_loc(bac_path, bac_token_idx_seq, loc_path, loc_token_idx_seq,
									bac_loc_reversed=False, strict_syntax=False, debug_print=False):
	"""

	:type bac_path: list[(int, str, str, str)]
	:type bac_token_idx_seq: list[int]
	:type loc_path: list[(int, str, str, str)]
	:type loc_token_idx_seq: list[int]
	:rtype: ((int, str), (int, str))
	"""
	false_result = None

	if bac_token_idx_seq[0] > loc_token_idx_seq[0]:
		return false_result

	subroot_token_idx, subroot_token, subroot_pos, _ = bac_path[0]
	target_span = subroot_token
	target_span_idx = subroot_token_idx

	if subroot_token_idx < bac_token_idx_seq[0]:
		return false_result

	#print subroot_pos, bac_path

	#debug_print = False
	#debug_print = True

	if debug_print: print '  -- Checking pattern [%s_v(be_pp)_in_%s]...' % (("LOC", "BAC") if bac_loc_reversed else ("BAC", "LOC"))

	if subroot_token_idx in bac_token_idx_seq \
			or subroot_token_idx in loc_token_idx_seq \
			or not (SentDep.check_dep_pos_verb(subroot_pos) or SentDep.check_dep_pos_adj(subroot_pos)):
		return false_result

	if debug_print: print '     --> subroot is a predicate!: "%s"' % subroot_token

	is_bac_nsubj = False
	nsubj = ''
	for token_idx, token, pos, dep_label in bac_path[1:]:
		if token_idx in bac_path:
			continue
		if SentDep.check_dep_pos_verb(pos):
			if SentDep.check_dep_label_comp(dep_label):
				target_span = subroot_token
			else:
				return false_result
		if SentDep.check_dep_label_nsubjx(dep_label) and token_idx in bac_token_idx_seq:
			is_bac_nsubj = True
			nsubj = token
			break

	if not is_bac_nsubj:
		return false_result

	if debug_print: print '     --> nsubj found in the path to %s: "%s"' % ('LOC' if bac_loc_reversed else 'BAC', nsubj)

	if bac_loc_reversed:
		preps_for_loc = SentDep.all_preps
	else:
		preps_for_loc = SentDep.loc_preps

	result_for_loc = check_path_for_prep_pobj_with_ent(loc_path, loc_token_idx_seq, preps_for_loc,
													   strict_syntax=strict_syntax, debug_print=debug_print)
	if not result_for_loc:
		return false_result

	loc_prep_matched = result_for_loc['prep']
	return (target_span_idx, target_span), loc_prep_matched


def check_pat_bac_pp_or_n_in_loc(bac_path, bac_token_idx_seq, loc_path, loc_token_idx_seq,
								 bac_loc_reversed=False, strict_syntax=False, debug_print=False):
	"""

	:type bac_path: list[(int, str, str, str)]
	:type bac_token_idx_seq: list[int]
	:type loc_path: list[(int, str, str, str)]
	:type loc_token_idx_seq: list[int]
	:rtype: ((int, str), (int, str))
	"""
	false_result = None

	if bac_token_idx_seq[0] > loc_token_idx_seq[0]:
		return false_result

	subroot_token_idx, subroot_token, subroot_pos, _ = bac_path[0]

	if debug_print: print '  -- Checking pattern [%s_pp(or_n)_in_%s]...' % (("LOC", "BAC") if bac_loc_reversed else ("BAC", "LOC"))

	is_subroot_in_bac = False
	if subroot_token_idx in bac_token_idx_seq:
		is_subroot_in_bac = True
		if debug_print: print '     --> subroot is in %s!: "%s"' % ('LOC' if bac_loc_reversed else 'BAC', subroot_token)

	is_bac_below_subroot = False
	if SentDep.check_dep_pos_noun(subroot_pos) \
			and subroot_token_idx not in bac_token_idx_seq \
			and len(bac_path) > 1:
		next_token_idx, next_token, _, next_dep_label = bac_path[1]
		if next_token_idx in bac_token_idx_seq and not SentDep.check_dep_label_conj(next_dep_label):
			is_bac_below_subroot = True
			if debug_print: print '     --> %s is right below noun subroot: "%s"' % ('LOC' if bac_loc_reversed else 'BAC', subroot_token)

	if not is_subroot_in_bac and not is_bac_below_subroot:
		return false_result

	if bac_loc_reversed:
		preps_for_loc = SentDep.all_preps
		constraint_on_prep_freq = False
		#constraint_on_prep_freq = True
	else:
		preps_for_loc = SentDep.loc_preps
		constraint_on_prep_freq = True

	result = check_path_for_prep_pobj_with_ent(loc_path[1:], loc_token_idx_seq, preps_for_loc,
											   only_one_prep_in_path=constraint_on_prep_freq,
											   strict_syntax=strict_syntax, debug_print=debug_print)

	if not result:
		return false_result

	prep_token_idx, prep_token = result['prep']
	#pobj_token_idx, pobj_token = result['pobj']
	target_span = ''
	target_span_idx = -99999999

	if is_subroot_in_bac:
		for idx_on_path, (token_idx, token, _, _) in enumerate(loc_path):
			if token_idx == prep_token_idx:
				pp_token_idx, pp_token, _, _ = loc_path[idx_on_path - 1]
				if pp_token_idx not in bac_token_idx_seq and pp_token_idx not in loc_token_idx_seq:
					target_span = pp_token
					target_span_idx = pp_token_idx
	elif is_bac_below_subroot:
		target_span = subroot_token
		target_span_idx = subroot_token_idx

	return (target_span_idx, target_span), (prep_token_idx, prep_token)


def check_path_for_prep_pobj_with_ent(path, target_idx_seq, preps=None, only_target_as_pobj=True,
									  only_one_prep_in_path=True, strict_syntax=False, debug_print=False):
	"""

	:type path: list
	:type target_idx_seq: list[int]
	:type preps: list[str]
	:type only_target_as_pobj: bool
	:return:
	"""
	#debug_print = True


	if not preps:
		preps = SentDep.loc_preps

	is_first_prep_found = False
	prep = None

	for node_idx, (token_idx, token, pos, dep_label) in enumerate(path):

		if SentDep.check_dep_label_prep(dep_label) \
				and token in preps \
				and token_idx not in target_idx_seq:

			if debug_print: print '     --> prep found: "%s"' % token

			if is_first_prep_found and only_one_prep_in_path:
				if debug_print: print '         Already prep found before: %s => Fail!' % str(prep)
				return None
				#if token != 'of':
				#	return None
				#pass
			else:
				#	head_token_idx, head_token_of_prep, head_pos_of_prep, _ = loc_path[idx_on_path - 1]
				#	if head_token_idx not in bac_token_idx_seq and head_token_idx not in loc_token_idx_seq:
				#		target_span = head_token_of_prep
				is_first_prep_found = True
				prep = (token_idx, token)
		elif node_idx == 0 and strict_syntax:
			return None

		if SentDep.check_dep_label_pobj(dep_label) \
				and (not only_target_as_pobj or token_idx in target_idx_seq):
			if is_first_prep_found:
				if debug_print: print '     --> pobj found: "%s"' % token
				pobj = (token_idx, token)
				return {'prep': prep, 'pobj': pobj, 'form': '%s_%s' % (prep[1], pobj[1])}


	return None


def check_path_for_dobj_with_ent(path, target_idx_seq, only_target_as_dobj=True, strict_syntax=False, debug_print=False):
	"""

	:param path:
	:param target_idx_seq:
	:param preps:
	:param only_target_as_dobj:
	:return:
	"""

	#debug_print = True

	for node_idx, (token_idx, token, pos, dep_label) in enumerate(path):
		if SentDep.check_dep_label_dobj(dep_label) \
				and (not only_target_as_dobj or token_idx in target_idx_seq):
			if debug_print:
				print '  ~~ dobj found: "%s"' % token
			return (token_idx, token)
		elif node_idx == 0 and strict_syntax:
			return None

	return None

