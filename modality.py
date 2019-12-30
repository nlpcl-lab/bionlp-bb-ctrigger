from concepts import InputItem
from sent_dep import SentDep

g_mod_test_verbs = [
	'test', 'determine',
	'investigate', 'examine', 'explore', 'analyze', 'check', 'identify',
	'assess', 'estimate', 'verify', 'recognize',
	'judge', 'calculate', 'rate', 'monitor',
	'demonstrate',
	'confirm',
	'find',
	'understand', 'prove', 'verify', 'justify',
	'demonstrate',
]

g_mod_aim_verbs = [
	'aim', 'plan',
	'suppose', 'assume', 'suspect', 'presume', 'conjecture', 'hypothesize', 'guess',
]

#from nltk import WordNetLemmatizer
#lemmatizer = WordNetLemmatizer()


def collect_hypo_words_per_sent(sent_dep_list, doc_id):
	"""

	:type sent_dep_list: list[sent_dep.SentDep]
	:type doc_id: str
	:rtype: dict[int, list[(int, str)]]
	"""

	print '\n=========================================================================='
	print '       Extracting hypothesis-bound words from a document : %s' % (doc_id)
	print '==========================================================================\n'

	hypo_words_per_sent = {}
	mod_test_verbs = g_mod_test_verbs
	mod_aim_verbs = g_mod_aim_verbs
	is_any_found = False

	for sent_idx, sent_dep in enumerate(sent_dep_list):
		sent_offset = 'T' if sent_idx == 0 else sent_idx - 1
		sent_tokens = sent_dep.get_sent_tokens()
		hypo_words_per_sent[sent_offset] = []

		token_lemma_seq = sent_dep.get_token_lemma_seq()

		for token_idx, token in enumerate(sent_tokens):
			is_found = False

			if token in mod_test_verbs:

				if sent_dep.get_token(token_idx - 1).lower() == 'to' \
						or (token_idx >= 2
							and sent_dep.get_token(token_idx - 2).lower() == 'to'
							and sent_dep.check_dep_pos_adverb(sent_dep.get_token_pos(token_idx - 1))):
					print '[S%s] Candidate TEST verbs: "%s"' % (str(sent_offset), token),

					if token_idx > 1 or sent_dep.get_parent_tokens(token_idx):
						is_found = True
						print '=> FOUND! %s' % (('(adverb: "%s")' % sent_dep.get_token(token_idx - 1))
												if sent_dep.get_token(token_idx - 2).lower() == 'to' else '')
					else:
						'=> REJECT: ROOT of this sentence (noun phrase)!'

			if not is_found:
				if sent_dep.check_dep_pos_verb(sent_dep.get_token_pos(token_idx)):
					#token_lemma = lemmatizer.lemmatize(token, 'v')
					token_lemma = token_lemma_seq[token_idx]

					if token_lemma in mod_aim_verbs:
						print '[S%s] AIM verb found: "%s"' % (str(sent_offset), token)
						is_found = True
						pass

			if is_found:
				is_any_found = True
				hypo_words_per_sent[sent_offset].append((token_idx, token))

	if not is_any_found:
		print 'No hypothesis scope found...\n'
	else:
		print

	return hypo_words_per_sent


def check_input_for_hypo_scope(input_item, hypo_words_per_sent):
	"""

	:type input_item: InputItem
	:type hypo_words_per_sent: dict[int, list[(int, str)]]
	:rtype: bool
	"""
	bac_sent_offset, loc_sent_offset = input_item.get_sent_offsets()
	bac_sent_dep, loc_sent_dep = input_item.get_sent_dep()

	hypo_words_in_bac_sent = hypo_words_per_sent[bac_sent_offset]
	bac_token_idx = input_item.get_bac_head_token_idx_in_sent()

	result = check_token_for_hypo_scope_in_sent(bac_token_idx, bac_sent_dep, hypo_words_in_bac_sent)
	if result:
		print '  ~~~~> [hypo-scope] BAC token "%s"(%d): %s' % (
			bac_sent_dep.get_token(bac_token_idx), bac_token_idx, result)
		return True

	hypo_words_in_loc_sent = hypo_words_per_sent[loc_sent_offset]
	loc_token_idx = input_item.get_loc_head_token_idx_in_sent()

	result = check_token_for_hypo_scope_in_sent(loc_token_idx, loc_sent_dep, hypo_words_in_loc_sent)
	if result:
		print '  ~~~~> [hypo-scope] LOC token "%s"(%d) found in hypo-scope: %s' % (
			loc_sent_dep.get_token(loc_token_idx), loc_token_idx, result)
		return True

	return False


def check_token_for_hypo_scope_in_sent(token_idx, sent_dep, hypo_words_in_sent):
	"""

	:type token_idx: int
	:type sent_dep: sent_dep.SentDep
	:type hypo_words_in_sent: list[(int, str)]
	:rtype: bool
	"""

	#print ' @@@!!@ checking hypo-scope for token: %s' % sent_dep.get_token(token_idx)

	match_type = ''

	for hypo_word_idx, hypo_word in hypo_words_in_sent:
		if (hypo_word_idx == 1 or hypo_word_idx == 2 ) \
				and sent_dep.get_token(0).lower() == 'to' \
				and sent_dep.get_parent_tokens(hypo_word_idx):
			match_type = 'TO-"%s" (Sentence-leading to-adverbial phrase)' % hypo_word
			return match_type

		if sent_dep.check_t1_is_ancestor_of_t2(hypo_word_idx, token_idx):
			match_type = 'TO-"%s"' % hypo_word
			return match_type

	sent_tokens = sent_dep.get_sent_tokens()
	if_token_indices = [i for i, t in enumerate(sent_tokens) if (t.lower() == 'if' or t.lower() == 'whether')]

	for if_token_idx in if_token_indices:
		parents = sent_dep.get_parent_tokens(if_token_idx)
		(main_verb_in_if_cls, dep_label) = parents[0] if parents else (None, None)
		if sent_dep.check_t1_is_ancestor_of_t2(main_verb_in_if_cls, token_idx):
			match_type = 'if/whether-clause!'
			return match_type

	return match_type


def check_negation_scope(token_idx, sent_dep, is_entity=False):
	"""

	:type token_idx: int
	:type sent_dep: SentDep
	:type is_entity: bool
	:return:
	"""

	detected_phrase = ''

	token = sent_dep.get_token(token_idx)

	for prev_token_idx in range(token_idx - 1, -1, -1):
		prev_token = sent_dep.get_token(prev_token_idx).lower()
		if (prev_token == 'no' or prev_token == 'neither' or prev_token == 'not' or prev_token == 'never'):
			if prev_token_idx + 1 == token_idx:
				#print '====###===> [%s] Filtered out by negation!: "%s"->"%s"' % (rel_type, prev_token, token)
				detected_phrase = '"%s"->"%s"' % (prev_token, token)
				break
			parents = sent_dep.get_parent_tokens(prev_token_idx)
			parent_idx, dep_label = parents[0] if parents else (None, None)
			if parent_idx == token_idx:
				#print '====###===> [%s] Filtered out by negation!: "%s"->"%s"' % (rel_type, prev_token, token)
				detected_phrase = '"%s"->"%s"' % (prev_token, token)
				break

		if prev_token == 'none' and sent_dep.get_token(prev_token_idx + 1).lower() == 'of':
			if prev_token_idx + 2 == token_idx:
				#print '====###===> [%s] Filtered out by negation!: "none of"->"%s"' % (rel_type, token)
				detected_phrase = '"none of"->"%s"' % token
				break
			parents = sent_dep.get_parent_tokens(token_idx)
			parent_idx, dep_label = parents[0] if parents else (None, None)
			if parent_idx == prev_token_idx + 1:
				#print '====###===> [%s] Filtered out by negation!: "none of"->"%s"' % (rel_type, token)
				detected_phrase = '"none of"->"%s"' % token
				break

	if detected_phrase:
		return detected_phrase

	is_token_verb = sent_dep.check_dep_pos_verb(sent_dep.get_token_pos(token_idx))

	if not is_token_verb and 'not' in sent_dep.get_sent_tokens():

		curr_token_idx = token_idx
		closest_verb_idx = -99999

		while curr_token_idx >= 0:
			parents = sent_dep.get_parent_tokens(curr_token_idx)
			if parents:
				parent_idx, dep_label = parents[0]
				if sent_dep.check_dep_pos_verb(sent_dep.get_token_pos(parent_idx)):
					closest_verb_idx = parent_idx
					break
				curr_token_idx = parent_idx
			else:
				curr_token_idx = -99999

		#if token == 'isolates' and token_idx == 11:
		#	print curr_token_idx
		#	exit()

		if closest_verb_idx >= 0:
			children = sent_dep.get_children_tokens(closest_verb_idx)
			for child_token_idx, dep_label in children:
				if sent_dep.get_token(child_token_idx) == 'not':
					closest_verb_token = sent_dep.get_token(closest_verb_idx)
					detected_phrase = '"not"-->"%s"-->"%s"' % (closest_verb_token, token)
					break

	return detected_phrase



def check_others_scope(token_idx, sent_dep):

	detected_phrase = ''

	token = sent_dep.get_token(token_idx)
	for prev_token_idx in range(token_idx - 1, -1, -1):
		prev_token = sent_dep.get_token(prev_token_idx).lower()

		if (prev_token == 'other' or prev_token == 'another' or prev_token == 'various' or prev_token == 'diverse'):
				#and token_idx == bac_first_token_idx:
			# print '$$##OTHER$$', sent_dep.get_parent_tokens(prev_token_idx)
			if prev_token_idx + 1 == token_idx:
				#print '====###===> [%s] Filtered out by other/another/various/diverse!: "%s"->"%s"' % (rel_type, prev_token, token)
				detected_phrase = '"%s"->"%s"' % (prev_token, token)
				break
			parents = sent_dep.get_parent_tokens(prev_token_idx)
			parent_idx, dep_label = parents[0] if parents else (None, None)
			if parent_idx == token_idx:
				#print '====###===> [%s] Filtered out by other/another/various/diverse!: "%s"->"%s"' % (rel_type, prev_token, token)
				detected_phrase = '"%s"->"%s"' % (prev_token, token)
				break

	return detected_phrase