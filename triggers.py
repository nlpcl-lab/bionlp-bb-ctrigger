import os

from concepts import Entity, Doc
from multibytes import replace_multibytes

#from nltk.stem.porter import PorterStemmer
#porter_stemmer = PorterStemmer()
from nltk.stem.lancaster import LancasterStemmer

import sent_dep
from sent_dep import check_pat_noun_of_bac_in_loc1, check_pat_noun_of_bac_in_loc2, check_pat_verb_bac_in_loc, \
	check_pat_bac_v_or_be_pp_in_loc, check_pat_bac_pp_or_n_in_loc, SentDep

lancaster_stemmer = LancasterStemmer()
stemmer = lancaster_stemmer

from path import g_file_path_to_triggers


class TriggerMap(object):

	def __init__(self, bac_list, sent_dep_list, doc_id,
				 auto_triggers_for_intra, auto_triggers_for_cross,
				 policy_for_direct, policy_for_indirect):
		"""

		:type bac_list: list[Entity]
		:type sent_dep_list: list[SentDep]
		"""
		self._bac_list = bac_list
		self._sent_dep_list = sent_dep_list
		self._doc_id = doc_id

	#	trigger_sets = [
	#		('direct', direct_target_triggers), ('indirect', indirect_target_triggers),
	#		('auto-intra', auto_triggers_for_intra), ('auto-cross', auto_triggers_for_cross)]
	#	self._categorized_triggers_per_sent = self._collect_all_triggers_per_sent_for_each_trigger_type(trigger_sets)
	#	self._direct_triggers_per_sent = self._categorized_triggers_per_sent['direct']
	#	self._indirect_triggers_per_sent = self._categorized_triggers_per_sent['indirect']
	#	self._auto_triggers_per_sent_for_intra = self._categorized_triggers_per_sent['auto-intra']
	#	self._auto_triggers_per_sent_for_cross = self._categorized_triggers_per_sent['auto-cross']

	#	self._direct_triggers_per_sent = self._collect_all_triggers_per_sent(direct_target_triggers, 'direct')
		self._direct_triggers_per_sent = []
	#	self._indirect_triggers_per_sent = self._collect_all_triggers_per_sent(indirect_target_triggers, 'indirect')
		self._indirect_triggers_per_sent = []
	#	self._auto_triggers_per_sent_for_intra = self._collect_all_triggers_per_sent(auto_triggers_for_intra, 'auto-intra')
		self._auto_triggers_per_sent_for_intra = []
		self._auto_triggers_per_sent_for_cross = self._collect_all_triggers_per_sent(auto_triggers_for_cross, 'auto-cross')

		#self._bac_id_to_direct_triggers_in_sents = self._create_intrasent_map(policy, trigger_type='direct')
		self._bac_id_to_direct_triggers_in_sents \
			= self._create_bac_to_trigger_map_in_sents(policy_for_direct, trigger_type='direct')
		#self._bac_id_to_direct_triggers_in_sents = self._create_intrasent_map('only_one_bac_for_trigger', trigger_type='direct')
		#self._bac_id_to_direct_triggers_in_sents = self._create_intrasent_map('only_one_trigger_for_bac', trigger_type='direct')

		self._bac_id_to_indirect_triggers_in_sents \
			= self._create_bac_to_trigger_map_in_sents(policy_for_indirect, trigger_type='indirect')
		#self._bac_id_to_indirect_triggers_in_sents = self._create_intrasent_map('all_pairs', trigger_type='indirect')
		#self._bac_id_to_indirect_triggers_in_sents = self._create_intrasent_map('only_one_bac_for_trigger', trigger_type='indirect')
		#self._bac_id_to_indirect_triggers_in_sents = self._create_intrasent_map('only_one_trigger_for_bac', trigger_type='indirect')

		self._bac_id_to_auto_triggers_in_sents \
			= self._create_bac_to_trigger_map_in_sents(policy_for_indirect, trigger_type='auto-intra')

	def get_triggers_in_sent_for_crosssent_detection(self, sent_offset):
		"""
		:param sent_offset:
		:param trigger_type:
		:rtype: list[(int, str, int)]
		"""
		#return self._direct_triggers_per_sent[sent_offset] \
		#	   + self._indirect_triggers_per_sent[sent_offset]\
		#	   + self._auto_triggers_per_sent_for_cross[sent_offset]
		return self._auto_triggers_per_sent_for_cross[sent_offset]

	def _create_bac_to_trigger_map_in_sents(self, policy, trigger_type):
		"""
		:type policy: str
		:type trigger_type: str
		:rtype: dict[str, list[(int, str, int)]]
		"""
		bac_id_to_triggers_in_sents = {}

		if trigger_type == 'direct':
			triggers_per_sent = self._direct_triggers_per_sent
		elif trigger_type == 'indirect':
			triggers_per_sent = self._indirect_triggers_per_sent
		elif trigger_type == 'auto-intra':
			triggers_per_sent = self._auto_triggers_per_sent_for_intra
		else:
			raise Exception('Unknown trigger type: "%s"' % trigger_type)

		if policy == 'all_pairs':
			trigger_map_func = self._map_all_pairs_in_sent
		elif policy == 'only_one_bac_for_trigger':
			trigger_map_func = self._map_trigger_to_only_one_bac_in_sent
		elif policy == 'only_one_trigger_for_bac':
			trigger_map_func = self._map_bac_to_only_one_trigger_in_sent
		else:
			raise Exception('Unknown policy for trigger mapping: "%s"' % policy)

		assert trigger_map_func

		#print '!!!@! ', self._matched_triggers_by_sent

		for sent_offset in triggers_per_sent:
			triggers_in_sent = [(tk_idx, tk_form, freq)
								for (tk_idx, tk_form, freq)
								in triggers_per_sent[sent_offset]]
								#in triggers_per_sent[sent_offset] if freq >= min_freq]

			bac_list_in_sent = [b for b in self._bac_list
								if ('T' if b.is_in_title() else b.get_sent_offset()) == sent_offset]

			#print '!@!@', bac_list_in_sent, [b.get_sent_offset() for b in self._bac_list]

			if not bac_list_in_sent:
				continue

			bac_trigger_pairs = trigger_map_func(bac_list_in_sent, triggers_in_sent)

			for bac_id, trigger_item in bac_trigger_pairs:
				try:
					bac_id_to_triggers_in_sents[bac_id].append(trigger_item)
				except KeyError:
					bac_id_to_triggers_in_sents[bac_id] = [trigger_item]

		return bac_id_to_triggers_in_sents

	@staticmethod
	def _map_all_pairs_in_sent(bac_list_in_sent, triggers_in_sent):
		"""
		:type bac_list_in_sent: list[Entity]
		:type triggers_in_sent: list[str]
		:rtype: list[(str, (int, str))]
		"""
		bac_trigger_pairs = [(bac.get_id(), trigger)
							 for bac in bac_list_in_sent for trigger in triggers_in_sent]

		return bac_trigger_pairs

	@staticmethod
	def _map_trigger_to_only_one_bac_in_sent(bac_list_in_sent, triggers_in_sent):
		"""
		:type bac_list_in_sent: list[Entity]
		:type triggers_in_sent: list[(int, str, int)]
		:rtype: list[(str, (int, str))]
		"""

		#bac_id_to_triggers_in_sent = {}

		if len(bac_list_in_sent) == 1:
			bac = bac_list_in_sent[0]
			#bac_id_to_triggers_in_sent[bac.get_id()] = triggers_in_sent
			return [(bac.get_id(), trigger_item) for trigger_item in triggers_in_sent]

		bac_trigger_pairs = []

		for trigger_item in triggers_in_sent:
			trigger_token_idx, trigger_token, trigger_freq = trigger_item
			min_dist = 100000000
			bac_with_min_dist = None
			for bac in bac_list_in_sent:
				dist = abs(trigger_token_idx - bac.get_head_token_idx_in_sent())
				if dist < min_dist:
					min_dist = dist
					bac_with_min_dist = bac

			target_bac_id = bac_with_min_dist.get_id()
			bac_trigger_pairs.append((target_bac_id, trigger_item))
			assert bac_with_min_dist
			#try:
			#	bac_id_to_triggers_in_sent[target_bac_id].append(trigger_item)
			#except KeyError:
			#	bac_id_to_triggers_in_sent[target_bac_id] = [trigger_item]

		return bac_trigger_pairs
		#return bac_id_to_triggers_in_sent

	@staticmethod
	def _map_bac_to_only_one_trigger_in_sent(bac_list_in_sent, triggers_in_sent):
		"""
		:type bac_list_in_sent: list[Entity]
		:type triggers_in_sent: list[(int, str)]
		:return:
		"""
		bac_trigger_pairs = []

		for bac in bac_list_in_sent:
			bac_idx = bac.get_head_token_idx_in_sent()
			min_dist = 100000000
			trigger_with_min_dist = ''

			for trigger_item in triggers_in_sent:
				trigger_token_idx, trigger_token = trigger_item
				dist = abs(bac_idx - trigger_token_idx)
				if dist < min_dist:
					min_dist = dist
					trigger_with_min_dist = trigger_item

			bac_trigger_pairs.append((bac.get_id(), trigger_with_min_dist))
			assert trigger_with_min_dist

		return bac_trigger_pairs


	def _collect_all_triggers_per_sent_for_each_trigger_type(self, target_trigger_sets):
		"""

		:type target_trigger_sets: list[(str, list[(int, str)])]
		:rtype: dict[str, dict[int, list[(int, str, int)]]]
		"""

		print '------------' * 5
		print 'Collecting all matched triggers for each sentence'
		print '(' + ' / '.join('"%s": %d' % (tr_type, len(trs)) for tr_type, trs in target_trigger_sets) + ')'

		triggers_by_sent_for_each_type = {}

		for trigger_type, typed_triggers in target_trigger_sets:
			triggers_by_sent_for_each_type[trigger_type] = {}

		#typed_triggers_by_sent = {}

		for sent_idx, sent_dep in enumerate(self._sent_dep_list):
			if sent_idx == 0:
				sent_offset = 'T'
			else:
				sent_offset = sent_idx - 1

			#typed_triggers_by_sent[sent_offset] = {}
			for trigger_type, typed_triggers in target_trigger_sets:
			#	typed_triggers_by_sent[sent_offset][trigger_type] = []
				triggers_by_sent_for_each_type[trigger_type][sent_offset] = []

			token_lemma_seq = sent_dep.get_token_lemma_seq()

			cand_tokens = sent_dep.get_sent_tokens()
			for token_idx, token in enumerate(cand_tokens):
				pos = sent_dep.get_token_pos(token_idx)
				# is_token_noun = sent_dep.check_dep_pos_noun(pos)
				is_token_verb = sent_dep.check_dep_pos_verb(pos)

				#if is_token_verb:
				#	continue

				token_lemma = token_lemma_seq[token_idx]
				token_verb_stem = stemmer.stem(token_lemma) if is_token_verb else ''

				for trigger_type, typed_triggers in target_trigger_sets:

					is_matched_with_trigger, trigger_freq, stem_match_info \
						= self.check_token_matched_with_triggers(token_lemma, token_verb_stem, typed_triggers, is_token_verb)

					if is_matched_with_trigger:

						#print '  MATCH SUCCESS by %s trigger (token: "%s")' % (trigger_type, token)

						freq_str = ("(freq=%d) " % trigger_freq) if trigger_type == 'auto' else ''

						if stem_match_info:
							(trigger_matched_by_stem, trigger_stem, token_verb_stem) = stem_match_info
							print '  | STEM MATCH by %s trigger | (S%s) token: "%s" %s(stem: "%s") | trigger: "%s" (stem: "%s")' % (
								trigger_type, str(sent_offset), token, freq_str, token_verb_stem, trigger_matched_by_stem, trigger_stem)
						else:

							print '  | LEMMA MATCH by %s trigger | (S%s) token: "%s" %s(lemma: "%s")' % (
								trigger_type, str(sent_offset), token, freq_str, token_lemma)

						if sent_dep.get_token(token_idx + 1) == 'of':
							idx_range = range(token_idx, min(token_idx + 6, len(sent_dep)))
							print '       =============> of_found: <<<%s>>>"' % ' '.join(
								sent_dep.get_token(i) for i in idx_range)

						triggers_by_sent_for_each_type[trigger_type][sent_offset].append((token_idx, token_lemma, trigger_freq))
						#typed_triggers_by_sent[sent_offset][trigger_type].append((token_idx, token_lemma, trigger_freq))

		return triggers_by_sent_for_each_type
		#return typed_triggers_by_sent


	def _collect_all_triggers_per_sent(self, target_triggers, trigger_type):
		"""

		:type target_triggers: list[(int, str)]
		:type trigger_type: str
		:rtype: dict[int, list[(int, str, int)]]
		"""
		print '------------' * 6
		#print 'Collecting all matched triggers for each sentence (%s)' % (trigger_type.upper())
		print 'Collecting all matched triggers for each sentence'

		triggers_by_sent = {}

		for sent_idx, sent_dep in enumerate(self._sent_dep_list):
			if sent_idx == 0:
				sent_offset = 'T'
			else:
				sent_offset = sent_idx - 1

			triggers_by_sent[sent_offset] = []

			token_lemma_seq = sent_dep.get_token_lemma_seq()

			cand_tokens = sent_dep.get_sent_tokens()
			for token_idx, token in enumerate(cand_tokens):

				pos = sent_dep.get_token_pos(token_idx)
				# is_noun = sent_dep.check_dep_pos_noun(pos)
				is_token_verb = sent_dep.check_dep_pos_verb(pos)

				#if is_token_verb:
				#	continue

				token_lemma = token_lemma_seq[token_idx]
				token_verb_stem = stemmer.stem(token_lemma) if is_token_verb else ''

				is_matched_with_trigger, trigger_freq, stem_match_info \
					= self.check_token_matched_with_triggers(token_lemma, token_verb_stem, target_triggers, is_token_verb)

				if is_matched_with_trigger:
					freq_str = ("(freq=%d) " % trigger_freq) if trigger_type.startswith('auto') else ''

					if stem_match_info:
						(trigger_matched_by_stem, trigger_stem, token_stem) = stem_match_info
						print '  | MATCH BY STEM  | S%s t%-2d "%s" %s(stem: "%s") | trigger: "%s" (stem: "%s")' % (
							str(sent_offset), token_idx, token, freq_str, token_stem, trigger_matched_by_stem, trigger_stem)
					else:

						print '  | MATCH BY LEMMA | S%s t%-2d "%s" %s(lemma: "%s")' % (
							str(sent_offset), token_idx, token, freq_str, token_lemma)

					#if sent_dep.get_token(token_idx + 1) == 'of':
					#	idx_range = range(token_idx, min(token_idx+6, len(sent_dep)))
					#	print '       =============> of_found: <<<%s>>>"' % ' '.join(sent_dep.get_token(i) for i in idx_range)

					triggers_by_sent[sent_offset].append((token_idx, token_lemma, trigger_freq))

		return triggers_by_sent


	@staticmethod
	def check_token_matched_with_triggers(token_lemma, token_verb_stem, trigger_lemmas, is_token_verb):

		is_matched_with_trigger = False
		trigger_freq = -1
		stem_match_info = None

		for freq, trigger in trigger_lemmas:
			if token_lemma == trigger:
				is_matched_with_trigger = True
				trigger_freq = freq
				break
		if not is_matched_with_trigger and is_token_verb:
			for freq, trigger in trigger_lemmas:
				trigger_stem = stemmer.stem(trigger)
				if token_verb_stem == trigger_stem:
					is_matched_with_trigger = True
					trigger_matched_by_stem = trigger
					trigger_freq = freq
					stem_match_info = (trigger_matched_by_stem, trigger_stem, token_verb_stem)
					break

		return is_matched_with_trigger, trigger_freq, stem_match_info

	def get_matched_triggers_for_bac_in_sent(self, bac, trigger_type):
		"""
		list of (token_idx, trigger_form, trigger_freq)

		:type bac: Entity | str
		:rtype: list[(int, str, int)]
		"""
		if isinstance(bac, Entity):
			bac_id = bac.get_id()
		else:
			bac_id = bac

		if trigger_type == 'direct':
			bac_id_to_triggers_in_sent = self._bac_id_to_direct_triggers_in_sents
		elif trigger_type == 'indirect':
			bac_id_to_triggers_in_sent = self._bac_id_to_indirect_triggers_in_sents
		elif trigger_type == 'auto-intra':
			bac_id_to_triggers_in_sent = self._bac_id_to_auto_triggers_in_sents
		else:
			raise Exception('Unknown trigger type: %s' % trigger_type)

		if bac_id in bac_id_to_triggers_in_sent:
			return bac_id_to_triggers_in_sent[bac_id]
		else:
			return []

	def show_mapping_in_sent(self, trigger_type):

		if trigger_type == 'direct':
			bac_id_to_triggers_in_sent = self._bac_id_to_direct_triggers_in_sents
		elif trigger_type == 'indirect':
			bac_id_to_triggers_in_sent = self._bac_id_to_indirect_triggers_in_sents
		elif trigger_type == 'auto-intra':
			bac_id_to_triggers_in_sent = self._bac_id_to_auto_triggers_in_sents
		else:
			raise Exception('Unknown trigger type: %s' % trigger_type)

		for bac_id in sorted(bac_id_to_triggers_in_sent):
			for bac in self._bac_list:
				if bac.get_id() == bac_id:
					bac_text = bac.get_text()
					try:
						print '  BAC(%s/s%s) "%s" | Trigger:' % (bac_id, str(bac.get_sent_offset()), bac_text),
					except IOError:
						bac_text_refined, _ = replace_multibytes(bac_text)
						print '"%s" | Trigger:' % (bac_text_refined),
					break
			for trigger_token_idx, trigger_token, trigger_freq in bac_id_to_triggers_in_sent[bac_id]:
				try:
					print '"%s"(%d/f=%d)' % (trigger_token, trigger_token_idx, trigger_freq),
				except IOError:
					trigger_token_refined, _ = replace_multibytes(trigger_token)
					print '"%s"(%d/f=%d)' % (trigger_token, trigger_token_idx, trigger_freq),
			print


def create_trigger_map(doc, sent_dep_list, doc_id,
					   auto_triggers_for_intra, auto_triggers_for_cross, trigger_policies):
	"""

	:type doc: Doc
	:type sent_dep_list: list[SentDep]
	:type doc_id: str
	:type trigger_policies: (str, str)
	:rtype: TriggerMap
	"""

	bac_list = list(doc.iter_bacteria_entities())

	direct_trigger_policy, indirect_trigger_policy = trigger_policies

	trigger_map = TriggerMap(bac_list, sent_dep_list, doc_id, auto_triggers_for_intra, auto_triggers_for_cross,
							 direct_trigger_policy, indirect_trigger_policy)

	#print '\n----- Bacteria-direct trigger mapping (policy: "%s") -----' % direct_trigger_policy
	#trigger_map.show_mapping_in_sent(trigger_type='direct')
	#print '----- Bacteria-indirect trigger mapping (policy: "%s") -----' % indirect_trigger_policy
	#trigger_map.show_mapping_in_sent(trigger_type='indirect')
	#print '----- Bacteria-trigger mapping (policy: "%s") -----' % indirect_trigger_policy
	#trigger_map.show_mapping_in_sent(trigger_type='auto-intra')

	return trigger_map


def load_precollected_triggers():
	file_path = g_file_path_to_triggers

	# print '\nLoading pre-collected triggers from "%s"' % filename
	filename = os.path.basename(g_file_path_to_triggers)
	print '\nLoading pre-collected triggers from ...\n   %s' % g_file_path_to_triggers
	trigger_items = []

	with open(file_path, 'r') as f:
		for line in f:
			if not line.strip():
				continue
			trigger, freq = line.split()
			trigger_items.append((int(freq), trigger))
	return trigger_items


def get_local_context_triggers(bac_token_idx_seq, path_from_subroot_to_bac, loc_token_idx_seq, path_from_subroot_to_loc,
							   sent_dep, is_expanded=False, strict_syntax=False, only_for_bac_trigger=False,
							   debug_print=False):
	"""

	:type input_item: InputItem
	:rtype: ((int, str), (int, str))
	"""

	#print 'Path-to-BAC'; check_path_for_entity(path_to_bac, anno_token_idx_seq=bac_token_idx_seq)
	#print 'Path-to-LOC'; check_path_for_entity(path_to_loc, anno_token_idx_seq=loc_token_idx_seq)


	if debug_print:
		print
		print '---' * 3, '%sChecking local syntactic context' % ('(ex) ' if is_expanded else ''), '---' * 10
	sep = '***' * 16

	result = check_pat_noun_of_bac_in_loc1(path_from_subroot_to_bac, bac_token_idx_seq,
										   path_from_subroot_to_loc, loc_token_idx_seq,
										   strict_syntax=strict_syntax, debug_print=debug_print)
	if result:
		trigger, loc_prep_matched = result
		trigger_token_idx, trigger_span = trigger
		if debug_print:
			print ' ', sep, '\n  ******* Pattern matched: [{noun} of BAC prep LOC] (trigger: "%s")' % trigger_span
			#print_sent_tokens_with_anno(sent_dep, bac_token_idx_seq, loc_token_idx_seq)
			print ' ', sep
		return trigger, loc_prep_matched

	result = check_pat_noun_of_bac_in_loc2(path_from_subroot_to_bac, bac_token_idx_seq,
										   path_from_subroot_to_loc, loc_token_idx_seq,
										   sent_dep, strict_syntax=strict_syntax, debug_print=debug_print)
	if result:
		trigger, loc_prep_matched = result
		trigger_token_idx, trigger_span = trigger
		if debug_print:
			print ' ', sep, '\n  ******* Pattern matched: [{noun} of] + [BAC prep LOC] (trigger: "%s")' % trigger_span
			#print_sent_tokens_with_anno(sent_dep, bac_token_idx_seq, loc_token_idx_seq)
			print ' ', sep
		return trigger, loc_prep_matched

	result = check_pat_verb_bac_in_loc(path_from_subroot_to_bac, bac_token_idx_seq,
									   path_from_subroot_to_loc, loc_token_idx_seq,
									   strict_syntax=strict_syntax, debug_print=debug_print)
	if result:
		trigger, loc_prep_matched = result
		trigger_token_idx, trigger_span = trigger
		if debug_print:
			print ' ', sep, '\n  ******* Pattern matched: [{verb} BAC prep LOC] (trigger: "%s")' % trigger_span
			#print_sent_tokens_with_anno(sent_dep, bac_token_idx_seq, loc_token_idx_seq)
			print ' ', sep
		return trigger, loc_prep_matched

	result = check_pat_bac_v_or_be_pp_in_loc(path_from_subroot_to_bac, bac_token_idx_seq,
											 path_from_subroot_to_loc, loc_token_idx_seq,
											 strict_syntax=strict_syntax, debug_print=debug_print)
	if result:
		trigger, loc_prep_matched = result
		trigger_token_idx, trigger_span = trigger
		if debug_print:
			print ' ', sep, '\n  ******* Pattern matched: [BAC {V/be-pp} prep LOC] (trigger: "%s")' % trigger_span
			#print_sent_tokens_with_anno(sent_dep, bac_token_idx_seq, loc_token_idx_seq)
			print ' ', sep
		return trigger, loc_prep_matched

	result = check_pat_bac_pp_or_n_in_loc(path_from_subroot_to_bac, bac_token_idx_seq,
										  path_from_subroot_to_loc, loc_token_idx_seq,
										  strict_syntax=strict_syntax, debug_print=debug_print)
	if result:
		trigger, loc_prep_matched = result
		trigger_token_idx, trigger_span = trigger
		if debug_print:
			print ' ', sep, '\n  ******* Pattern matched: [BAC {pp/n} prep LOC] (trigger: "%s")' % trigger_span
			#print_sent_tokens_with_anno(sent_dep, bac_token_idx_seq, loc_token_idx_seq)
			print ' ', sep
		return trigger, loc_prep_matched


	if only_for_bac_trigger:
		return None

	result = check_pat_noun_of_bac_in_loc1(path_from_subroot_to_loc, loc_token_idx_seq,
										   path_from_subroot_to_bac, bac_token_idx_seq,
										   bac_loc_reversed=True, strict_syntax=strict_syntax,
										   debug_print=debug_print)
	if result:
		trigger, loc_prep_matched = result
		trigger_token_idx, trigger_span = trigger
		if debug_print:
			print ' ', sep, '\n  ******* Pattern matched: {noun} of LOC prep BAC (trigger: "%s")' % trigger_span
			# print_sent_tokens_with_anno(sent_dep, bac_token_idx_seq, loc_token_idx_seq)
			print ' ', sep
		return trigger, loc_prep_matched

	result = check_pat_verb_bac_in_loc(path_from_subroot_to_loc, loc_token_idx_seq,
									   path_from_subroot_to_bac, bac_token_idx_seq,
									   bac_loc_reversed=True, strict_syntax=strict_syntax,
									   debug_print=debug_print)
	if result:
		trigger, loc_prep_matched = result
		trigger_token_idx, trigger_span = trigger
		if debug_print:
			print ' ', sep, '\n  ******* Pattern matched: {verb} LOC prep BAC (trigger: "%s")' % trigger_span
			# print_sent_tokens_with_anno(sent_dep, bac_token_idx_seq, loc_token_idx_seq)
			print ' ', sep
		return trigger, loc_prep_matched

	result = check_pat_bac_v_or_be_pp_in_loc(path_from_subroot_to_loc, loc_token_idx_seq,
											 path_from_subroot_to_bac, bac_token_idx_seq,
											 bac_loc_reversed=True, strict_syntax=strict_syntax,
											 debug_print=debug_print)
	if result:
		trigger, loc_prep_matched = result
		trigger_token_idx, trigger_span = trigger
		if debug_print:
			print ' ', sep, '\n  ******* Pattern matched: LOC {V/be-pp} prep BAC (trigger: "%s")' % trigger_span
			# print_sent_tokens_with_anno(sent_dep, bac_token_idx_seq, loc_token_idx_seq)
			print ' ', sep
		return trigger, loc_prep_matched

	result = check_pat_bac_pp_or_n_in_loc(path_from_subroot_to_loc, loc_token_idx_seq,
										  path_from_subroot_to_bac, bac_token_idx_seq,
										  bac_loc_reversed=True, strict_syntax=strict_syntax,
										  debug_print=debug_print)
	if result:
		trigger, loc_prep_matched = result
		trigger_token_idx, trigger_span = trigger
		if debug_print:
			print ' ', sep, '\n  ******* Pattern matched: LOC {pp/n} prep BAC (trigger: "%s")' % trigger_span
			# print_sent_tokens_with_anno(sent_dep, bac_token_idx_seq, loc_token_idx_seq)
			print ' ', sep
		return trigger, loc_prep_matched

	return None


if __name__ == '__main__':
	pass



