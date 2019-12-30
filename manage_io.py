import os
import zipfile

from concepts import Doc, InputItem, Event, Entity
from sent_dep import SentDep

from path import g_dir_path_to_prediction_official_format, g_dir_path_to_verse_output


def get_input_items(doc_bbevent, sent_dep_list, target_sents=None, is_gold_target=False):
	"""

	:type doc_bbevent: Doc
	:type sent_dep_list: list[sent_dep.SentDep]
	:type target_sents: list[int] | list[str]
	:type is_gold_target: bool
	:return:
	"""

	input_items = []

	debug_analysis = False
	#debug_analysis = True

	if is_gold_target:
		input_iterator = doc_bbevent.iter_events()
		#if sent_type == 'intra':
		#	input_iterator = doc_bbevent.iter_intrasent_events()
		#elif sent_type == 'cross' or sent_type == 'inter':
		#	input_iterator = doc_bbevent.iter_crosssent_events()
		#else:
		#	input_iterator = doc_bbevent.iter_events()
	else:
		input_iterator = doc_bbevent.iter_all_cand_pairs()
		#if sent_type == 'intra':
		#	input_iterator = doc_bbevent.iter_all_intrasent_cand_pairs()
		#elif sent_type == 'cross' or sent_type == 'inter':
		#	input_iterator = doc_bbevent.iter_all_crosssent_cand_pairs()
		#else:
		#	input_iterator = doc_bbevent.iter_all_cand_pairs()

	for input_idx, input in enumerate(input_iterator):
		if isinstance(input, Event):
			input_id = input.get_id()
			bac = input.get_bacteria()  # type: Entity
			loc = input.get_location()  # type: Entity
		else:
			input_id = 'PAIR-%d' % input_idx
			bac, loc = input  # type: (Entity, Entity)

		bac_sent_offset, loc_sent_offset = bac.get_sent_offset(), loc.get_sent_offset()

		#if bac_sent_offset != loc.get_sent_offset():
		#	continue

		if debug_analysis:
			bac_sent_dep = sent_dep_list[bac_sent_offset + 1] if bac_sent_offset != 'T' else sent_dep_list[0]
			loc_sent_dep = sent_dep_list[loc_sent_offset + 1] if loc_sent_offset != 'T' else sent_dep_list[0]

			if bac_sent_offset == loc_sent_offset:

				if bac.get_head_token_idx_in_sent() == loc.get_head_token_idx_in_sent():
					print '\n[NOTE] SAME HEAD of BAC & LOC! (%s)' % ('GOLD' if doc_bbevent.has_event(bac, loc) else 'NOT GOLD')
					print '=> s%s: "%s" & "%s"\n' % (bac_sent_offset, bac.get_text(), loc.get_text())
					#print raw_input()
				#loc_sent_dep = sent_dep_list[bac_sent_offset + 1] if loc_sent_offset != 'T' else sent_dep_list[0]

				if loc_sent_dep.get_token(loc.get_head_token_idx_in_sent()).startswith('cell'):
					print '\n[NOTE] Location is "cell" (%s)' % ('GOLD' if doc_bbevent.has_event(bac, loc) else 'NOT GOLD')
					print '=> s%s: "%s" & "%s"\n' % (bac_sent_offset, bac.get_text(), loc.get_text())
					print raw_input()

		if target_sents and (bac_sent_offset != loc_sent_offset
							 or (bac_sent_offset if not bac.is_in_title() else 'T') not in target_sents):
			continue

		input_item = create_input_item(input_id, bac, loc, sent_dep_list)
		input_items.append(input_item)

	return input_items


def get_selected_input_items(doc_bbevent, sent_dep_list, selected_input_pairs=None):
	"""

	:param doc_bbevent:
	:param sent_dep_list:
	:param target_sents:
	:param selected_input_pairs:
	:rtype: list[InputItem]
	"""
	bac_id_gen = {}
	loc_id_gen = {}


	input_items = []
	if selected_input_pairs:
		doc_id = doc_bbevent.get_id()
		if doc_id not in selected_input_pairs:
			return

		sents = selected_input_pairs[doc_id]

		sent_offsets = sorted(sents) if 'T' not in sents else ['T'] + sorted(sents)[:-1]

		pair_idx = 0

		for sent_offset in sent_offsets:
			pairs_in_sent = sents[sent_offset]
			if not pairs_in_sent:
				input_items_in_sent = get_input_items(doc_bbevent, sent_dep_list, target_sents=[sent_offset])
				input_items.extend(input_items_in_sent)
				continue

			if sent_offset == 'T':
				sent_dep = sent_dep_list[0]
				#sent_text = doc_bbevent.get_title_text(refined=True)
			else:
				sent_dep = sent_dep_list[sent_offset + 1]
				#sent_text = doc_bbevent.get_sent_by_offset(sent_offset, refined=True)

			for pair in pairs_in_sent:

				((bac_text, bac_token_idx_seq), (loc_text, loc_token_idx_seq)) = pair
				bac_id = 'B-%s-%s' % (str(sent_offset), ','.join(bac_token_idx_seq))
				loc_id = 'L-%s-%s' % (str(sent_offset), ','.join(bac_token_idx_seq))

				bac_head_token_idx_in_sent, _ = sent_dep.get_head_token_for_span(bac_token_idx_seq)
				loc_head_token_idx_in_sent, _ = sent_dep.get_head_token_for_span(loc_token_idx_seq)

				lowest_subtree = sent_dep.get_lowest_subtree(bac_head_token_idx_in_sent, loc_head_token_idx_in_sent)

				input_item = InputItem(pair_idx, bac_id, loc_id,
									   bac_text, bac_token_idx_seq, bac_head_token_idx_in_sent, sent_offset, sent_dep,
									   loc_text, loc_token_idx_seq, loc_head_token_idx_in_sent, sent_offset, sent_dep,
									   lowest_subtree, is_gold_event=False)

				input_items.append(input_item)

			#	input_items.append((pair_idx, (bac_text, bac_token_idx_seq), (loc_text, loc_token_idx_seq), sent_offset,
			#						sent_dep, sent_text))
				pair_idx += 1

	return input_items


def mark_input_items_with_gold_intrasents(input_items, gold_doc):
	"""

	:type input_items: list[InputItem]
	:type gold_doc: Doc
	:return:
	"""
	for input_item in input_items:
		bac_id = input_item.get_bac_id()
		loc_id = input_item.get_loc_id()
		if input_item.is_intra_sent() and gold_doc.has_event(bac_id, loc_id):
		#if gold_doc.has_event(bac_id, loc_id):
			input_item.mark_predicted(pred_type='gold')



def load_verse_output():

	#base_dir_path = os.path.join(g_root_path, "data", "predicted_output_in_official_format")
	#target_dir_path = os.path.join(base_dir_path, 'prediction-test-20190122_164348-VERSE-F=55.33')

	target_dir_path = g_dir_path_to_verse_output

	print '\nLoading intra-sentence events in the VERSE output from ... \n  %s' % target_dir_path

	pairs_per_doc = {}

	for filename in os.listdir(target_dir_path):
		doc_id = filename.rsplit('.')[0].split('-')[2]
		file_path = os.path.join(target_dir_path, filename)

		pairs_per_doc[doc_id] = []

		with open(file_path, 'r') as f:
			for line in f:
				if not line.strip():
					continue

				items = line.split()
				assert items[1] == 'Lives_In'
				assert items[2].startswith('Bacteria:T')
				assert items[3].startswith('Location:T')

				bac_id = items[2].split(':')[1]
				loc_id = items[3].split(':')[1]
				pairs_per_doc[doc_id].append((bac_id, loc_id))

	#print pairs_per_doc
	#exit()

	return pairs_per_doc


def mark_input_items_with_verse_output(input_items, verse_pairs_in_doc):
	"""

	:type input_items: list[InputItem]
	:type verse_pairs_in_doc: list[(str, str)]
	:return:
	"""

	for input_item in input_items:
		bac_id = input_item.get_bac_id()
		loc_id = input_item.get_loc_id()
		pair = (bac_id, loc_id)
		if input_item.is_intra_sent() and pair in verse_pairs_in_doc:
			input_item.mark_predicted(pred_type='verse')


def create_input_item(pair_id, bac, loc, sent_dep_list):
	"""

	:type pair_id: str
	:type bac: Entity
	:type loc: Entity
	:type sent_dep_list: list[sent_dep.SentDep]
	:rtype: InputItem
	"""


	bac_token_idx_seq = bac.get_token_idx_seq_in_sent()
	loc_token_idx_seq = loc.get_token_idx_seq_in_sent()
	bac_head_token_idx_in_sent = bac.get_head_token_idx_in_sent()
	loc_head_token_idx_in_sent = loc.get_head_token_idx_in_sent()
	bac_text = bac.get_text()
	loc_text = loc.get_text()
	bac_id = bac.get_id()
	loc_id = loc.get_id()

	if bac.is_in_title():
		bac_sent_offset = 'T'
		bac_sent_dep = sent_dep_list[0]  # type: SentDep
	else:
		bac_sent_offset = bac.get_sent_offset()
		bac_sent_dep = sent_dep_list[bac_sent_offset + 1]  # type: SentDep

	if loc.is_in_title():
		loc_sent_offset = 'T'
		loc_sent_dep = sent_dep_list[0]  # type: SentDep
	else:
		loc_sent_offset = loc.get_sent_offset()
		loc_sent_dep = sent_dep_list[loc_sent_offset + 1]  # type: SentDep

	#print '!@#!@#', pair_id, bac_sent_offset, bac_text, bac_token_idx_seq, loc_text, loc_token_idx_seq

	if bac_sent_offset == loc_sent_offset:
		lowest_subtree = bac_sent_dep.get_lowest_subtree(bac_head_token_idx_in_sent, loc_head_token_idx_in_sent)
	else:
		lowest_subtree = None

	input_item = InputItem(pair_id, bac_id, loc_id,
						   bac_text, bac_token_idx_seq, bac_head_token_idx_in_sent, bac_sent_offset, bac_sent_dep,
						   loc_text, loc_token_idx_seq, loc_head_token_idx_in_sent, loc_sent_offset, loc_sent_dep,
						   lowest_subtree, is_gold_event=True)

	return input_item


def merge_pilot_test_cases(test_pairs1, test_pairs2):

	doc_ids = list(set(test_pairs1.keys() + test_pairs2.keys()))

	merged_pairs = {}

	for doc_id in doc_ids:
		merged_pairs[doc_id] = {}
		for test_pairs in (test_pairs1, test_pairs2):
			if doc_id in test_pairs:
				for sent_offset in test_pairs[doc_id]:

					if not test_pairs[doc_id][sent_offset]:
						merged_pairs[doc_id][sent_offset] = []

					for pair in test_pairs[doc_id][sent_offset]:
						try:
							merged_pairs[doc_id][sent_offset].append(pair)
						except:
							merged_pairs[doc_id][sent_offset] = [pair]

	return merged_pairs




def get_pairs_per_doc(input_items_per_doc):
	"""

	:type input_items_per_doc: dict[str, (list[InputItem], Doc)]
	:return:
	"""

	pred_pairs_per_doc = {}

	for doc_id in input_items_per_doc:
		input_items, doc = input_items_per_doc[doc_id]
		pred_pairs_per_doc[doc_id] = []

		for input_item in sorted(input_items, key=lambda i: i.get_head_token_idx_pair()):
			if not input_item.is_predicted():
				continue

			bac_id = input_item.get_bac_id()
			bac_text = input_item.get_bac_text()
			loc_id = input_item.get_loc_id()
			loc_text = input_item.get_loc_text()

			pair = ((bac_id, bac_text), (loc_id, loc_text))
			pred_pairs_per_doc[doc_id].append(pair)

	return pred_pairs_per_doc


def export_as_official_output_a2_file(predicted_pairs_per_doc, data_type, start_time, system_name):
	"""

	:type predicted_pairs_per_doc: dict[str, list[((str, str), (str, str))]]
	:type data_type: str
	:type start_time: str
	:type system_name: str
	:return:
	"""

	#output_base_path = os.path.join(g_root_path, 'data', 'predicted_output_in_official_format')
	output_base_path = g_dir_path_to_prediction_official_format

	assert data_type == 'train' or data_type == 'dev' or data_type == 'test'

	output_by_doc = {}

	for doc_id in predicted_pairs_per_doc:
		lines = []
		pred_idx = 1

		for pair in predicted_pairs_per_doc[doc_id]:
			((bac_id, bac_text), (loc_id, loc_text)) = pair

			line = "R{pred_idx}\tLives_In Bacteria:{bac_id} Location:{loc_id}".format(
				pred_idx=pred_idx, bac_id=bac_id, loc_id=loc_id
			)
			lines.append(line)
			pred_idx += 1

		lines.append('')
		content = '\n'.join(lines)

		output_by_doc[doc_id] = content

	new_dir_name = "prediction-%s-%s%s" % (data_type, start_time, ('-' + system_name) if system_name else '')
	output_dir_path = os.path.join(output_base_path, new_dir_name)

	if not os.path.exists(output_dir_path):
		os.makedirs(output_dir_path)

	zip_file_name = '%s.zip' % new_dir_name
	zip_file_path = os.path.join(output_base_path, zip_file_name)
	zipf = zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED)

	for doc_id in output_by_doc:
		output = output_by_doc[doc_id]

		if doc_id.startswith('BB-event-'):
			filename = '%s.a2' % doc_id
		else:
			filename = 'BB-event-%s.a2' % doc_id

		output_file_path = os.path.join(output_dir_path, filename)

		with open(output_file_path, 'w') as f:
			print 'Saving output in official format: "%s"' % filename
			f.write(output)
			f.close()
			zipf.write(output_file_path, os.path.relpath(output_file_path, os.path.join(output_dir_path, '.')))

	print '\nCreating a zip archive for output files: %s' % zip_file_path
	print 'You can submit this zip file to the BioNLP-ST 2016 Evaluation Service for automatic evaluation.'
	zipf.close()



if __name__ == '__main__':
	#from datetime import datetime
	#time = datetime.now().strftime('%Y%m%d_%H%M%S')
	#backup_sourcecode_as_zip_archive(time)
	pass

