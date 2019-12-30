G_ENTITY_BACTERIA = 0
G_ENTITY_HABITAT = 1
G_ENTITY_GEOGRAPHICAL = 2
G_ENTITY_ANY = 3

def get_entity_by_id(entity_id, entity_list):
	for entity in entity_list:
		if entity.match_by_id(entity_id):
			return entity
	return None


class Doc(object):

	def __init__(self, doc_id, doc_text_refined, title_text, title_text_refined, title_offset, para_list,
				 bacteria_list, habitat_list, geo_list, events, sents_refined, sent_char_offsets,
				 multibyte_info):
		"""

		:type doc_id: str
		:type doc_text_refined: str
		:type title_text: str
		:type title_text_refined: str
		:type title_offset: (int, int)
		:type para_list: list[Para]
		:type bacteria_list: list[Entity]
		:type habitat_list: list[Entity]
		:type geo_list: list[Entity]
		:type events: Events
		:type sents_refined: list[str]
		:param sent_char_offsets:
		:type sent_char_offsets: list[(int, int)]
		:type multibyte_info: dict[str, list]
		"""
		self._id = doc_id
		self._doc_text_refined = doc_text_refined
		self._title_text = title_text
		self._title_text_refined = title_text_refined
		self._title_offsets = title_offset
		self._para_list = para_list
		self._bacteria_list = bacteria_list
		self._habitat_list = habitat_list
		self._geo_list = geo_list
		self._events = events

		self._sents = None
		self._sents_refined = sents_refined
		self._sent_char_offsets = sent_char_offsets

		self._multibyte_info = multibyte_info

	def get_id(self):
		return self._id

	def get_doc_stat(self):
		num_entities = self.get_num_entities()
		num_bacteira = self.get_num_bacteria()
		num_locations = self.get_num_locations()
		num_habitat = self.get_num_habitat()
		num_geo = self.get_num_geographical()
		num_events = self.get_num_events()
		num_crst_events = self.get_num_crst_events()

		doc_stat_str = \
			'entity={n_ent} (bac={n_bac}/loc={n_loc}/hab={n_hab}/geo={n_geo}), ' \
			'event={n_evt} (cross-sent={n_evt_crst})'.format(
			n_ent=num_entities, n_bac=num_bacteira, n_loc=num_locations, n_hab=num_habitat,
			n_geo=num_geo, n_evt=num_events, n_evt_crst=num_crst_events)

		return doc_stat_str

	def iter_para(self):
		for para in self._para_list:
			yield para

	def get_multibyte_map(self, info_type):
		"""
		:rtype: list[(int, str)] | list[list[(int, str)]]
		"""
		if info_type == 'doc':
			return self._multibyte_info['doc']
		elif info_type == 'sents':
			return self._multibyte_info['sents']
		elif info_type == 'title':
			return self._multibyte_info['title']
		else:
			return None

	# ==================== Entities =====================
	def iter_entities(self, sort_by_offset=False):
		if sort_by_offset:
			for entity in sorted(self._bacteria_list+self._habitat_list+self._geo_list,
								 key=lambda e: e.get_offsets()):
				yield entity
		else:
			for entity in self._bacteria_list+self._habitat_list+self._geo_list:
				yield entity

	def iter_bacteria_entities(self):
		for entity in self._bacteria_list:
			yield entity

	def iter_location_entities(self):
		for entity in self._habitat_list+self._geo_list:
			yield entity

	def iter_habitat_entities(self):
		for entity in self._habitat_list:
			yield entity

	def iter_geo_entities(self):
		for entity in self._geo_list:
			yield entity

	#def get_entities_in_title(self):
	#	return [entity for entity in self.iter_entities() if entity.is_in_title()]

	def get_entities_in_sent(self, sent_offset):
		""":rtype: list[Entity]"""
		if sent_offset == 'T':
			return [entity for entity in self.iter_entities() if entity.is_in_title()]
		else:
			return [entity for entity in self.iter_entities() if entity.get_sent_offset() == sent_offset]

	def get_bac_entities_in_sent(self, sent_offset):
		""":rtype: list[Entity]"""
		return [e for e in self.get_entities_in_sent(sent_offset) if e.is_bacteria()]

	def get_loc_entities_in_sent(self, sent_offset):
		""":rtype: list[Entity]"""
		return [e for e in self.get_entities_in_sent(sent_offset) if e.is_location()]

	def get_num_entities(self, entity_type=G_ENTITY_ANY):
		if entity_type == G_ENTITY_BACTERIA:
			return len(self._bacteria_list)
		elif entity_type == G_ENTITY_HABITAT:
			return len(self._habitat_list)
		elif entity_type == G_ENTITY_GEOGRAPHICAL:
			return len(self._geo_list)
		else:
			return len(self._bacteria_list) + len(self._habitat_list) + len(self._geo_list)

	def get_num_bacteria(self):
		return self.get_num_entities(G_ENTITY_BACTERIA)

	def get_num_locations(self):
		return self.get_num_entities(G_ENTITY_HABITAT) + self.get_num_entities(G_ENTITY_GEOGRAPHICAL)

	def get_num_habitat(self):
		return self.get_num_entities(G_ENTITY_HABITAT)

	def get_num_geographical(self):
		return self.get_num_entities(G_ENTITY_GEOGRAPHICAL)

	def get_bacteria_by_id(self, entity_id):
		return get_entity_by_id(entity_id, self._bacteria_list)

	def get_habitat_by_id(self, entity_id):
		return get_entity_by_id(entity_id, self._habitat_list)

	def get_geographical_by_id(self, entity_id):
		return get_entity_by_id(entity_id, self._geo_list)

	def get_location_by_id(self, entity_id):
		return self.get_habitat_by_id(entity_id) or self.get_geographical_by_id(entity_id)

	#def get_entities_in_title(self):
	#	for e in self._bacteria_list + self._habitat_list + self._geo_list:

	def get_matched_entity(self, span_text, token_idx_seq_in_sent):
		for ent in self.iter_entities():
			if span_text == ent.get_text() and token_idx_seq_in_sent == ent.get_token_idx_seq_in_sent():
				return ent

		return None

	# ==================== Events =====================
	def iter_all_cand_pairs(self):
		""":rtype: collections.Iterable[(Entity, Entity)]"""
		sort_key = lambda e: e.get_offsets()

		for bac in sorted(self._bacteria_list, key=sort_key):
			for loc in sorted(self._habitat_list + self._geo_list, key=sort_key):
				yield bac, loc

	def iter_all_intrasent_cand_pairs(self):
		""":rtype: collections.Iterable[(Entity, Entity)]"""
		return ((bac, loc) for (bac, loc) in self.iter_all_cand_pairs()
				if bac.get_sent_offset() == loc.get_sent_offset())

	def iter_all_crosssent_cand_pairs(self):
		""":rtype: collections.Iterable[(Entity, Entity)]"""
		return ((bac, loc) for (bac, loc) in self.iter_all_cand_pairs()
				if bac.get_sent_offset() != loc.get_sent_offset())

	def iter_events(self, sent_offset=None):
		""":rtype: collections.Iterable[Event]"""
		if isinstance(sent_offset, int):
			for event in self._events:
				if event.get_bacteria().get_sent_offset() \
						== event.get_location().get_sent_offset() == sent_offset:
					yield event
		elif sent_offset == 'T':
			for event in self._events:
				if event.get_bacteria().is_in_title() and event.get_location().is_in_title():
					yield event
		else:
			for event in self._events:
				yield event

	def iter_intrasent_events(self, sent_offset=None):
		""":rtype: collections.Iterable[Event]"""
		return filter(lambda e: not e.is_cross_sent(), self.iter_events(sent_offset))

	def iter_crosssent_events(self, sent_offset=None):
		""":rtype: collections.Iterable[Event]"""
		return filter(lambda e: e.is_cross_sent(), self.iter_events(sent_offset))

	def get_num_events(self):
		return len(self._events)

	def get_num_crst_events(self, backward=False):
		if backward:
			cnt = 0
			for e in self._events:
				if not e.is_cross_sent():
					continue
				bac = e.get_bacteria()
				loc = e.get_location()
				if loc.get_sent_offset() < bac.get_sent_offset():
					cnt += 1
			return cnt

		else:
			return len([e for e in self._events if e.is_cross_sent()])

	def has_event(self, bac, loc):
		"""

		:type bac: str | Entity
		:type loc: str | Entity
		:rtype: str
		"""
		return bool(self.get_event_id(bac, loc))

	def get_event_id(self, bac, loc):
		"""

		:type bac: str | Entity
		:type loc: str | Entity
		:rtype: str
		"""
		return self._events.get_event_id(bac, loc)

	def get_location_list_for_bacteria(self, bacteria):
		"""

		:type bacteria: str | Entity
		:rtype: list[Entity]
		"""
		loc_ids = self._events.get_loc_ids_for_bac_id(bacteria)
		return [self.get_location_by_id(lid) for lid in loc_ids]
		#return self.get_location_by_id(loc_id)

	def get_bacteria_list_for_location(self, location):
		"""

		:type location: str | Entity
		:rtype: list[Entity]
		"""
		bac_ids = self._events.get_bac_ids_for_loc_id(location)
		return [self.get_bacteria_by_id(bid) for bid in bac_ids]

	def check_entity_belong_to_event(self, entity_id):
		return self._events.get_bac_ids_for_loc_id(entity_id) \
			   or self._events.get_loc_ids_for_bac_id(entity_id)

	# ================== Coreference =====================
	def iter_coref_chains(self):
		"""

		:rtype: collections.Iterable[list[str]]
		"""
		return self._events.iter_coref_chains()

	# ==================== Sentences =====================

	def get_doc_text_refined(self):
		return self._doc_text_refined

	def get_title_text(self, refined=False):
		if refined:
			return self._title_text_refined
		else:
			return self._title_text

	def get_title_offsets(self):
		return self._title_offsets

	def get_original_title(self):
		"""

		:rtype: (str, bool, list)
		"""
		debug = False
		#debug = True

		is_changed = False
		multibyte_map_for_title = self.get_multibyte_map(info_type='title')

		if not multibyte_map_for_title:
			return self.get_title_text(refined=True), is_changed, []

		title_letters = list(self.get_title_text(refined=True))

		for letter_idx, original_m_letter in multibyte_map_for_title:
			if debug:
				print '[Multibytes]', letter_idx, original_m_letter, title_letters[letter_idx]

			assert title_letters[letter_idx] == '@'
			title_letters[letter_idx] = original_m_letter
			is_changed = True

		original_title = ''.join(title_letters)
		return original_title, is_changed, multibyte_map_for_title


	def iter_sents(self, refined=False):
		if refined:
			for sent_refined in self._sents_refined:
				yield sent_refined
		else:
			for sent in self._sents:
				yield sent

	def iter_original_sents(self):
		"""

		:rtype: collections.Iterable[(str, bool, list)]
		"""
		debug = False
		#debug = True

		multibyte_map_for_sents = self.get_multibyte_map(info_type='sents')
		for sent_offset, refined_sent in enumerate(self.iter_sents(refined=True)):
			is_changed = False
			if sent_offset not in multibyte_map_for_sents:
				sent = self.get_sent_by_offset(sent_offset, refined=True)
				yield sent, is_changed, []
			else:
				multibyte_map_for_sent = multibyte_map_for_sents[sent_offset]

				sent_letters = list(refined_sent)

				for letter_idx, original_m_letter in multibyte_map_for_sent:
					if debug:
						print '[Multibytes]', letter_idx, original_m_letter, sent_letters[letter_idx]

					assert sent_letters[letter_idx] == '@'
					sent_letters[letter_idx] = original_m_letter
					is_changed = True

				original_sent = ''.join(sent_letters)
				yield original_sent, is_changed, multibyte_map_for_sent


	def get_num_sents(self):
		return len(self._sents_refined)

	def get_sent_by_offset(self, sent_offset, refined=False):
		if refined:
			return self._sents_refined[sent_offset]
		else:
			return self._sents[sent_offset]

	def get_char_offsets_for_sent(self, sent_offset):
		"""

		:type sent_offset: int
		:rtype: (int, int)
		"""
		return self._sent_char_offsets[sent_offset]


class Para(object):

	def __init__(self, tid, offset, text, text_refined, sent_range, inner_sent_char_offsets):
		self._tid = tid
		self._text = text
		self._text_refined = text_refined  #
		self._offset = offset
		self._sent_range = sent_range
		self._inner_sent_char_offsets = inner_sent_char_offsets

	def get_id(self):
		return self._tid

	def get_offset(self):
		return self._offset

	def get_text(self, refined=False):
		"""

		:param refined:
		:rtype: str
		"""
		if refined:
			return self._text_refined
		else:
			return self._text

	#def get_text_refined(self):
	#	return self._text_refined

	def get_sent_range(self):
		return self._sent_range

	def get_num_sents(self):
		return self._sent_range[1] - self._sent_range[0]

	def get_inner_sent_char_offsets(self):
		return self._inner_sent_char_offsets

	#def put_text_refined(self, text_refined):
	#	self._text_refined = text_refined


class Entity(object):

	def __init__(self, tid, entity_type, offsets, text,
				 sent_offset=-9999, para_offset=-9999, nesting_level=-9999,
				 is_in_title=False):
		"""

		:type tid: str
		:type offsets: list[(int, int)]
		:type text: str
		"""
		self._tid = tid
		self._offsets = offsets
		self._text = text
		self._para_offset = para_offset
		self._is_in_title = is_in_title

		#assert sent_offset != -1

		if is_in_title:
			self._sent_offset = 'T'
		else:
			self._sent_offset = sent_offset

		self._type_name = entity_type

		if entity_type == 'Bacteria':
			self._type_value = G_ENTITY_BACTERIA
		elif entity_type == 'Habitat':
			self._type_value = G_ENTITY_HABITAT
		else:
			self._type_value = G_ENTITY_GEOGRAPHICAL

		self._num_words = len(text.split())
		self._graphical_nesting_level = nesting_level

		self._pos_seq = []

		self._head_token_offset_in_ent = -999999999
		self._head_pos = ''

		self._token_idx_seq_in_sent = []
		self._token_form_seq = []


	def __eq__(self, other):
		"""

		:type other: Entity
		:return:
		"""
		return self._tid == other.get_id()

	def __cmp__(self, other):
		"""

		:type other: Entity
		:return:
		"""
		return self.get_offsets() < other.get_offsets()

	def __str__(self):
		return '<{type} ID="{id}" TEXT="{text}" OFFSET="{offset}" DISCONT="{discont}">'.format(
			type=self._type_name.upper(), id=self._tid, offset=self.get_offset_str(), text=self._text,
			discont='Y' if self.is_discontinuous() else 'N',
		)

	def get_inline_tag_str(self):
		"""
		:rtype: (str, str)
		"""

		tag_id = self._tid
		label = self._type_name

		begin_tag = '<tag-{tid} id="{tid}" label="{label}" text="{text}" offsets="{offsets}" discont="{discont}">'.format(
			tid=tag_id, label=label, text=self.get_text(), offsets=self.get_offset_str(),
			discont='Y' if self.is_discontinuous() else 'N')
		end_tag = '</tag-{tid}>'.format(tid=tag_id)
		return begin_tag, end_tag

	def get_id(self):
		return self._tid

	def get_type(self):
		return self._type_value

	def get_text(self):
		"""

		:rtype: str
		"""
		return self._text

	def is_bacteria(self):
		return self._type_value == G_ENTITY_BACTERIA

	def is_habitat(self):
		return self._type_value == G_ENTITY_HABITAT

	def is_geographical(self):
		return self._type_value == G_ENTITY_GEOGRAPHICAL

	def is_location(self):
		return self.is_habitat() or self.is_geographical()

	def get_cat_letter(self):
		if self.is_bacteria():
			cat = 'B'
		elif self.is_habitat():
			cat = 'H'
		else:
			cat = 'G'
		return cat

	def get_num_words(self):
		"""

		:rtype: int
		"""
		return self._num_words

	def get_para_offset(self):
		"""
		:rtype: int
		"""
		return self._para_offset

	def get_offsets(self):
		"""
		return list of (begin char-offset & end char-offset) of each token
		:rtype: list[(int, int)]
		"""
		return self._offsets

	def get_outermost_offset(self):
		"""
		return (begin-char-offset of the first token & end-char-offset of the last token)
		:rtype: (int, int)
		"""
		return self._offsets[0][0], self._offsets[-1][-1]

	def get_num_outermost_letters(self):
		"""

		:rtype: int
		"""
		begin, end = self.get_outermost_offset()
		return end - begin

	def get_offset_str(self):
		if self.is_in_title():
			s_off = 'sT'
			p_off = 'pT'
		else:
			s_off = 's%d' % self._sent_offset
			p_off = 'p%d' % self._para_offset

		if self.is_discontinuous():
			w_off = '+'.join('w%d-%d' % (offset[0], offset[1])
							   for offset in self.get_offsets())
		else:
			w_off = 'w%d-%d' % (self._offsets[0][0], self._offsets[0][1])


		return s_off + ';' + p_off + ';' + w_off

	@staticmethod
	def get_offsets_from_offset_str(offset_str):
		"""
		:param offset_str:
		:rtype: (bool, int, int, list[(int, int)])
		"""
		is_in_title = False

		s_off_str, p_off_str, c_offs_str = offset_str.split(';')
		sent_offset = s_off_str[1:]

		#assert sent_offset != -1

		if sent_offset == 'T':
			is_in_title = True
		else:
			sent_offset = int(sent_offset)

		para_offset = int(p_off_str[1:])

		char_offsets = [tuple(map(int, c_off_str[1:].split('-')))
						for c_off_str in c_offs_str.split('+')]

		return is_in_title, sent_offset, para_offset, char_offsets

	def is_discontinuous(self):
		return len(self._offsets) > 1

	def match_by_id(self, entity_id):
		"""
		:type entity_id: str
		"""
		return self._tid == entity_id

	def match_by_offsets(self, entity):
		"""
		:type entity: Entity
		"""
		return self._offsets == entity.get_offsets()

	def match_by_head_offset(self, head_offset):
		pass

	def assign_sent_offset(self, sent_offset):
		#assert sent_offset != -1
		#assert sent_offset != '-1'
		self._sent_offset = sent_offset

	def assign_para_offset(self, para_offset):
		self._para_offset = para_offset

	def assign_graphical_nesting_level(self, level):
		self._graphical_nesting_level = level

	def get_graphical_nesting_level(self):
		return self._graphical_nesting_level

	def get_sent_offset(self):
		#assert self._sent_offset != -1
		return self._sent_offset

	def mark_in_title(self):
		self._is_in_title = True

	def is_in_title(self):
		return self._is_in_title

	def assign_pos_seq(self, pos_seq):
		"""

		:type pos_seq: list[str]
		"""
		self._pos_seq = pos_seq

	def get_pos_seq(self):
		"""

		:rtype: list[str]
		"""
		return self._pos_seq

	def assign_head_token(self, token_offset):
		self._head_token_offset_in_ent = token_offset
		self._head_pos = self._pos_seq[token_offset]

	def get_head_token_offset_in_ent(self):
		return self._head_token_offset_in_ent

	def get_head_token_idx_in_sent(self):
		return self._token_idx_seq_in_sent[self._head_token_offset_in_ent]

	def is_head_verb(self):
		head_pos = self._head_pos
		return head_pos.startswith('V') or head_pos.startswith('v')

	def assign_token_idx_seq_in_sent(self, token_idx_seq):
		"""

		:type token_idx_seq: list[int]
		:return:
		"""
		self._token_idx_seq_in_sent = token_idx_seq

	def get_token_idx_seq_in_sent(self):
		"""
		:rtype: list[int]
		"""
		return self._token_idx_seq_in_sent

	def assign_token_form_seq(self, token_form_seq):
		""":type token_form_seq: list[str]"""
		self._token_form_seq = token_form_seq

	def get_token_form_seq(self):
		""":rtype: list[str]"""
		return self._token_form_seq

	def mark_hypothesized(self, hypo_type):
		self._hypothesized_type = hypo_type

	def is_hypothesized(self):
		return bool(self._hypothesized_type)

	def get_hypothesis_type(self):
		return self._hypothesized_type


class Event(object):

	def __init__(self, rid, bacteria, location):
		"""

		:type rid: str
		:type bacteria: Entity
		:type location: Entity
		"""
		#assert bacteria.is_bacteria()
		#assert location.is_habitat() or location.is_geographical()

		self._rid = rid
		self._bacteria = bacteria
		self._location = location
		#self._bacteria_id = bacteria_id
		#self._location_id = location_id

		assert self._bacteria.get_sent_offset() >= 0 or self._bacteria.get_sent_offset() == 'T' or self._bacteria.get_sent_offset() == -9999
		assert self._location.get_sent_offset() >= 0 or self._location.get_sent_offset() == 'T' or self._location.get_sent_offset() == -9999

	def __str__(self):

		return '<EVENT ID="{id}" BAC="{bac}" LOC="{loc}"{others}>'.format(
			id=self._rid, bac=self._bacteria.get_text(), loc=self._location.get_text(),
			others=' cross-sent' if self.is_cross_sent() else '',
		)

	def get_inline_tag_str(self):
		return '<rel id="{id}" type="directed" arg1TagId="{bac_id}" arg2TagId="{loc_id}" label="Lives_In" />'.format(
			id=self._rid, bac_id=self._bacteria.get_id(), loc_id=self._location.get_id()
		)

	def get_id(self):
		return self._rid

	def get_bacteria(self):
		""":rtype: Entity"""
		return self._bacteria

	def get_location(self):
		""":rtype: Entity"""
		return self._location

	def is_intra_sent(self):
		return self._bacteria.get_sent_offset() == self._location.get_sent_offset()

	def is_cross_sent(self):
		return not self.is_intra_sent()


	def match_by_id(self, bac, loc):
		"""

		:type bac: str | Entity
		:type loc: str | Entity
		:rtype: bool
		"""
		if isinstance(bac, str):
			return self._bacteria.get_id() == bac and self._location.get_id() == loc
		else:
			return self._bacteria.get_id() == bac.get_id() and self._location.get_id() == loc.get_id()


class Events(object):

	def __init__(self, event_list, coref_list=None):
		"""
		:type event_list: list[Event]
		:type coref_list: list[list[str]]
		"""
		self._event_list = event_list
		self._coref_list = coref_list if coref_list else []

		self._bac_to_loc_map = {}
		self._loc_to_bac_map = {}

		self._create_event_map()

	def __len__(self):
		return len(self._event_list)

	def __iter__(self):
		return (event for event in self._event_list)

	def iter_coref_chains(self):
		"""

		:rtype: collections.Iterable[list[str]]
		"""
		return (chain for chain in self._coref_list)

	def _create_event_map(self):
		for event in self._event_list:
			bac = event.get_bacteria()
			bac_id = bac.get_id()
			loc = event.get_location()
			loc_id = loc.get_id()
			#event_id = event.get_id()

			try:
				if loc_id not in self._bac_to_loc_map[bac_id]:
					self._bac_to_loc_map[bac_id].append(loc_id)
			except KeyError:
				self._bac_to_loc_map[bac_id] = [loc_id]

			try:
				if bac_id not in self._loc_to_bac_map[loc_id]:
					self._loc_to_bac_map[loc_id].append(bac_id)
			except KeyError:
				self._loc_to_bac_map[loc_id] = [bac_id]

	def check_event_hold(self, bac, loc):
		"""

		:type bac: str | Entity
		:type loc: str | Entity
		:rtype: bool
		"""
		return bool(self.get_event_id(bac, loc))

	def get_event_id(self, bac, loc):
		"""

		:type bac: str | Entity
		:type loc: str | Entity
		:rtype: str
		"""
		for event in self._event_list:
			if event.match_by_id(bac, loc):
				return event.get_id()
		return ''

	def get_loc_ids_for_bac_id(self, bacteria):
		"""

		:type bacteria: str | Entity
		:rtype: list[str]
		"""
		if isinstance(bacteria, Entity):
			bac_id = bacteria.get_id()
		else:
			bac_id = bacteria

		try:
			return self._bac_to_loc_map[bac_id]
		except KeyError:
			return []

	def get_bac_ids_for_loc_id(self, location):
		"""

		:type location: str | Entity
		:rtype: list[str]
		"""
		if isinstance(location, Entity):
			loc_id = location.get_id()
		else:
			loc_id = location

		try:
			return self._loc_to_bac_map[loc_id]
		except KeyError:
			return []


class InputItem(object):

	pred_type_trigger = 1
	pred_type_simple = 2
	pred_type_exp_trigger = 3
	pred_type_exp_simple = 4
	pred_type_propagation = 5
	pred_type_exp_propagation = 5

	def __init__(self, input_id, bac_id, loc_id,
				 bac_text, bac_token_idx_seq, bac_head_token_idx_in_sent, bac_sent_offset, bac_sent_dep,
				 loc_text, loc_token_idx_seq, loc_head_token_idx_in_sent, loc_sent_offset, loc_sent_dep,
				 lowest_subtree=None, is_gold_event=False,
				 is_expanded_from_bac=False, is_expanded_from_loc=False,
				 exp_source=None, exp_type=''):
		self._input_id = input_id
		self._bac_id = bac_id
		self._bac_text = bac_text
		self._bac_token_idx_seq = bac_token_idx_seq
		self._bac_head_token_idx_in_sent = bac_head_token_idx_in_sent
		self._loc_id = loc_id
		self._loc_text = loc_text
		self._loc_token_idx_seq = loc_token_idx_seq
		self._loc_head_token_idx_in_sent = loc_head_token_idx_in_sent

		#assert bac_sent_offset != -1
		#assert loc_sent_offset != -1

		self._bac_sent_offset = bac_sent_offset
		self._bac_sent_dep = bac_sent_dep
		self._loc_sent_offset = loc_sent_offset
		self._loc_sent_dep = loc_sent_dep
		self._lowest_subtree = lowest_subtree

		self._is_gold_event = is_gold_event
		self._prediction_type = None
		self._is_expanded_from_bac = is_expanded_from_bac
		self._is_expanded_from_loc = is_expanded_from_loc
		self._exp_source = exp_source
		self._exp_type = exp_type
		self._hypothesized_type = ''

	def __eq__(self, other):
		return self.get_bac_token_idx_seq() == other.get_bac_token_idx_seq \
			and self.get_loc_token_idx_seq() == other.get_loc_token_idx_seq

	def get_id(self):
		""":rtype: str"""
		return self._input_id

	def get_bac_id(self):
		""":rtype: str"""
		return self._bac_id

	def get_loc_id(self):
		""":rtype: str"""
		return self._loc_id

	def get_bac_and_loc(self):
		""":rtype: (str, str, list[int], str, str, list[int])"""
		return self._bac_id, self._bac_text, self._bac_token_idx_seq, self._loc_id, self._loc_text, self._loc_token_idx_seq

	def get_head_token_idx_pair(self):
		""":rtype: (int, int)"""
		return self._bac_head_token_idx_in_sent, self._loc_head_token_idx_in_sent

	def get_bac(self):
		"""
		return (bac_text, bac_token_idx_seq)
		:rtype: (str, list[int])
		"""
		return self._bac_text, self._bac_token_idx_seq

	def get_bac_token_idx_seq(self):
		""":rtype: list[int]"""
		return self._bac_token_idx_seq

	def get_bac_head_token_idx_in_sent(self):
		""":rtype: int"""
		return self._bac_head_token_idx_in_sent

	def get_bac_text(self):
		""":rtype: str"""
		return self._bac_text

	def get_loc(self):
		"""
		return (loc_text, loc_token_idx_seq)
		:rtype: (str, list[int])
		"""
		return self._loc_text, self._loc_token_idx_seq

	def get_loc_token_idx_seq(self):
		""":rtype: list[int]"""
		return self._loc_token_idx_seq

	def get_loc_head_token_idx_in_sent(self):
		""":rtype: int"""
		return self._loc_head_token_idx_in_sent

	def get_loc_text(self):
		""":rtype: str"""
		return self._loc_text

	def is_in_title(self):
		""":rtype: bool"""
		return (self._bac_sent_offset == 'T', self._loc_sent_offset == 'T')

	def get_sent_offsets(self):
		""":rtype: (int, int)"""
		return self._bac_sent_offset, self._loc_sent_offset

	def get_sent_dep(self):
		""":rtype: (sent_dep.SentDep, sent_dep.SentDep)"""
		return self._bac_sent_dep, self._loc_sent_dep

	def get_lowest_subtree(self):
		return self._lowest_subtree

	def is_intra_sent(self):
		""":rtype: bool"""
		bac_sent_offset, loc_sent_offset = self.get_sent_offsets()
		return bac_sent_offset == loc_sent_offset

	def is_cross_sent(self):
		""":rtype: bool"""
		return not self.is_intra_sent()

	def is_gold_event(self):
		""":rtype: bool"""
		return self._is_gold_event

	def is_predicted(self):
		""":rtype: bool"""
		return self._prediction_type

	def mark_predicted(self, pred_type, pred_info=None):
		assert pred_type
		self._prediction_type = pred_type

	def is_expanded(self):
		""":rtype: bool"""
		return self._is_expanded_from_bac or self._is_expanded_from_loc

	def is_expanded_from_bac(self):
		""":rtype: bool"""
		return self._is_expanded_from_bac

	def is_expanded_from_loc(self):
		""":rtype: bool"""
		return self._is_expanded_from_loc

	def get_exp_type(self):
		return self._exp_type

	def get_exp_source(self):
		return self._exp_source




class TokenDep(object):

	def __init__(self, token_idx, token,
				 incoming_token, incoming_idx, incoming_label,
				 outgoing_token, outgoing_idx, outgoing_label):

		self._token_idx = token_idx
		self._token = token
		self._incoming_token = incoming_token
		self._incoming_idx = incoming_idx
		self._incoming_label = incoming_label
		self._outgoing_token = outgoing_token
		self._outgoing_idx = outgoing_idx
		self._outgoing_label = outgoing_label

	def get_incoming_token(self):
		"""

		:rtype: int, str, str
		"""
		return self._incoming_idx, self._incoming_token, self._incoming_label

	def get_outgoing_token(self):
		"""

		:return:
		"""
		return self._outgoing_idx, self._outgoing_token, self._outgoing_label





