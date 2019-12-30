import sys
from datetime import datetime

from concepts import Doc
from load_data import load_official_bb_event_docs
from dep_parser import load_corenlp_dep_parser_output, \
    sync_tokens_between_bbevent_anno_and_stanford_dep
from modality import collect_hypo_words_per_sent

from manage_io import get_input_items, get_selected_input_items, \
    mark_input_items_with_verse_output, load_verse_output, \
    export_as_official_output_a2_file, get_pairs_per_doc
from extract_crosssent_events import detect_crosssent_events
from triggers import create_trigger_map, load_precollected_triggers


from nltk.stem.porter import PorterStemmer
stemmer = PorterStemmer()


def print_doc_sep(doc_id):
    print
    print '===' * 19
    print '====' * 5, '               ', '====' * 5
    print '====' * 5, ' DOC: %8s ' % doc_id, '====' * 5
    print '====' * 5, '               ', '====' * 5
    print '===' * 19
    print


def print_context_triggers_by_stem(triggers):
    """
    :type triggers: list[str]
    :return:
    """
    trigger_by_stem = {}
    for trigger in triggers:
        try:
            stem = stemmer.stem(trigger)
        except UnicodeDecodeError:
            continue

        try:
            trigger_by_stem[stem].append(trigger)
        except KeyError:
            trigger_by_stem[stem] = [trigger]

    #print
    #print '====' * 20
    #print '====' * 20
    #print 'Collected trigger words (sorted by stem frequency):'

    for stem, triggers in sorted((trigger_by_stem.items()), reverse=True, key=lambda x: len(x[1])):
        print '"%s" (%d):' % (stem, len(triggers)), ' / '.join(triggers)


def print_context_triggers_by_freq(triggers):
    """

    :type triggers: list[(int, str)]
    :return:
    """

    trigger_freq_dist = {}
    trigger_freq_dist_reversed = {}
    for trigger_token_idx, trigger_span in triggers:
        try:
            trigger_freq_dist[trigger_span] += 1
        except KeyError:
            trigger_freq_dist[trigger_span] = 1

    for trigger_span, freq in trigger_freq_dist.items():
        try:
            trigger_freq_dist_reversed[freq].append(trigger_span)
        except KeyError:
            trigger_freq_dist_reversed[freq] = [trigger_span]

    print
    print '====' * 20
    print '====' * 20
    print 'Collected trigger words (sorted by frequency):'

    for freq, trigger_span in sorted((trigger_freq_dist_reversed.items()), reverse=True):
        print '[%s]' % freq, ' / '.join(trigger_span)


def load_doc_with_ent_anno_and_dep_parse(data_type, base_tokenization, target_doc_id):
    """
    :param data_type:
    :param base_tokenization:
    :param target_doc_id:
    :rtype: list[(str, Doc, list[sent_dep.SentDep])]
    """

    docs = load_official_bb_event_docs(data_type=data_type, base_tokenization=base_tokenization, target_doc_id=target_doc_id)

    # $$$$$$$$$ START for distribution $$$$$$$$$$
    #if base_tokenization == 'all':
    #    dep_info_by_doc = load_sota_biomedical_dep_parser_output(target_doc_id, data_type)
    #    parser_type = 'biomedical_sota'
    #if base_tokenization == 'sents':
    #    dep_info_by_doc = load_corenlp_dep_parser_output(target_doc_id, data_type)
    #    parser_type = 'corenlp'
    #else:
    #    raise ValueError("[ERROR] Unknown tokenization option: %s" % base_tokenization)
    dep_info_by_doc = load_corenlp_dep_parser_output(target_doc_id, data_type)
    parser_type = 'corenlp'
    # $$$$$$$$$ END for distribution $$$$$$$$$$

    sorted_docs = [doc for (int_doc_id, doc) in sorted(((int(doc.get_id()), doc) for doc in docs), key=lambda x: x[0])]

    doc_items = []

    print '\nSync between gold-standard annotation and dependency parse...'
    for doc in sorted_docs:
        doc_id = doc.get_id()
        sent_dep_list = dep_info_by_doc[doc_id]
        sync_tokens_between_bbevent_anno_and_stanford_dep(doc, sent_dep_list, parser_type)
        doc_items.append((doc_id, doc, sent_dep_list))
    print '... Done'

    return doc_items


def main():

    data_type = 'test'
    is_gold_target = False
    target_doc_id = ''
    pilot_pairs = []
    target_sents = []
    apply_hypo_intra_scope = True
    apply_hypo_cross_scope = True
    output_as_file = True
    min_trigger_freq_for_crosssent = 300
    mapping_policy_for_direct_triggers = 'all_pairs'
    mapping_policy_for_auto_triggers = 'only_one_bac_for_trigger'
    forward_context_window_size = 3
    backward_context_window_size = 3

    #config_note = '<Config> data: {data_type} / only gold target: {is_gold_target} / gold intra given: {intra_source} ' \
    #			  '/ target sents: {target_sents} / Hypo-scope: intra={apply_hypo_intra_scope} cross={apply_hypo_cross_scope}' \
    #			  '/ Min frequeny of used triggers: {min_freq_triggers}'.format(
    #	data_type=data_type, is_gold_target='Y' if is_gold_target else 'N',
    #	intra_source='Y' if intra_source else 'N', target_sents=str(target_sents) if target_sents else 'none',
    #	apply_hypo_intra_scope=apply_hypo_intra_scope, apply_hypo_cross_scope=apply_hypo_cross_scope,
    #	min_freq_triggers=min_freq_triggers)

    start_time = datetime.now()
    start_time_formatted = datetime.now().strftime('%Y%m%d_%H%M%S')
    print '\nStart time: %s' % str(start_time)

    #base_tokenization = 'all'
    base_tokenization = 'sents'

#	docs = load_official_bb_event_docs(data_type=data_type, base_tokenization=base_tokenization, target_doc_id=target_doc_id)

#	if base_tokenization == 'all':
#		dep_info_by_doc = load_sota_biomedical_dep_parser_output(target_doc_id, data_type)
#		parser_type = 'biomedical_sota'
#	elif base_tokenization == 'sents':
#		dep_info_by_doc = load_corenlp_dep_parser_output(target_doc_id, data_type)
#		parser_type = 'corenlp'
#	else:
#		raise ValueError("[ERROR] Unknown tokenization option: %s" % base_tokenization)

#	sorted_docs = [doc for (int_doc_id, doc) in sorted(((int(doc.get_id()), doc) for doc in docs), key=lambda x: x[0])]

#	for doc in sorted_docs:
#		sent_dep_list = dep_info_by_doc[doc.get_id()]
#		sync_tokens_between_bbevent_anno_and_stanford_dep(doc, sent_dep_list, parser_type)

    doc_items = load_doc_with_ent_anno_and_dep_parse(data_type, base_tokenization, target_doc_id)

    num_docs = 0
    total_num_pairs = 0
    total_num_predicted = 0

    input_items_per_doc = {}
    #stats = {}

    #auto_triggers_for_intra = load_precollected_triggers(min_trigger_freq_for_intrasent)
    #auto_triggers_filtered = filter_out_non_triggers(auto_triggers_for_intra, min_trigger_freq_for_crosssent)
    auto_triggers_for_intra = []  # NOT NEEDED when the VERSE output is used as intra-sentence events!
    #auto_triggers_filtered = auto_triggers_filtered[:-2]

    auto_triggers_filtered = load_precollected_triggers()


    print "\n------ Context triggers (%d triggers) -----" % len(auto_triggers_filtered)
    for idx, (freq, trigger) in enumerate(auto_triggers_filtered):
        #print "[%d]" "%s\t%s" % (idx+1, trigger, freq)
        print '"%s" (freq=%d)' % (trigger, freq)
    #exit()

    #auto_triggers_for_intra = auto_triggers_filtered
    #auto_triggers_for_intra = filter_out_non_triggers(auto_triggers_for_intra, min_trigger_freq_for_crosssent)
    #auto_triggers_filtered = auto_triggers_for_intra

    #print auto_triggers_filtered
    #exit()

    #auto_collected_triggers_filtered = filter_out_triggers_against_loc_from_all_docs(auto_collected_triggers, doc_items)

    #for doc in sorted_docs:
    #	doc_id = doc.get_id()

    # $$$$$$$$$ START for distribution $$$$$$$$$$
    #if intra_source == 'verse':
    #    if data_type != 'test':
    #       print '[ERROR] VERSE output can only be used with the test data! (current=%s)' % data_type
    #        exit()
    #
    #    print 'Loading VERSE output...'
    #    verse_pairs_per_doc = load_verse_output()
    #    print ' -> VERSE output (%d docs) loaded!' % len(verse_pairs_per_doc)
    #else:
    #    verse_pairs_per_doc = {}
    verse_pairs_per_doc = load_verse_output()
    # $$$$$$$$$ END for distribution $$$$$$$$$$

    policies_forward_search = {#'direction': 'forward',
                               'stop_if_any_bac_in_sent': True,  #
                               'stop_if_all_locs_nonselected_in_sent': False}  #
    policies_backward_search = {#'direction': 'backward',
                                'stop_if_any_bac_in_sent': True,  #
                                'stop_if_all_locs_nonselected_in_sent': True}  #

    for doc_id, doc, sent_dep_list in doc_items:

        if pilot_pairs and doc_id not in pilot_pairs:
            continue

        print_doc_sep(doc_id)

        #stat = analyze_gold_event_properties(doc, sent_dep_list)
        #stats[doc_id] = stat

        if pilot_pairs:
            input_items = get_selected_input_items(doc, sent_dep_list, pilot_pairs)
        else:
            input_items = get_input_items(doc, sent_dep_list, target_sents, is_gold_target)

        hypo_words_per_sent = collect_hypo_words_per_sent(sent_dep_list, doc_id)

        hypo_words_per_sent_for_intra = hypo_words_per_sent if apply_hypo_intra_scope else {}
        hypo_words_per_sent_for_cross = hypo_words_per_sent if apply_hypo_cross_scope else {}

        #    => 'all_pairs' / 'only_one_bac_for_trigger' / 'only_one_trigger_for_bac'
        # trigger_policies = ('all_pairs', 'all_pairs')
        trigger_policies = (mapping_policy_for_direct_triggers,
                            mapping_policy_for_auto_triggers)

        trigger_map = create_trigger_map(doc, sent_dep_list, doc_id, auto_triggers_for_intra,
                                         auto_triggers_filtered,
                                         trigger_policies)

        # $$$$$$$$$ START for distribution $$$$$$$$$$
        #if intra_source == 'gold':
        #    mark_input_items_with_gold_intrasents(input_items, doc)
        #elif intra_source == 'verse':
        #    verse_pairs_in_doc = verse_pairs_per_doc[doc_id]
        #    mark_input_items_with_verse_output(input_items, verse_pairs_in_doc)
        #else:
        #    triggers_in_doc = detect_intrasent_events(input_items, trigger_map, hypo_words_per_sent_for_intra, doc)
        #    collected_triggers.extend(triggers_in_doc)
        verse_pairs_in_doc = verse_pairs_per_doc[doc_id]
        mark_input_items_with_verse_output(input_items, verse_pairs_in_doc)
        # $$$$$$$$$ END for distribution $$$$$$$$$$

        total_num_pairs += len(input_items)
        total_num_predicted += len([i for i in input_items if i.is_predicted()])

        context_window_sizes = forward_context_window_size, backward_context_window_size

        if not target_sents:
            detect_crosssent_events(input_items, trigger_map, min_trigger_freq_for_crosssent,
                                    hypo_words_per_sent_for_cross, policies_forward_search, policies_backward_search,
                                    context_window_sizes, sent_dep_list, doc)

        input_items_per_doc[doc_id] = (input_items, doc)
        num_docs += 1

    #evaluate(input_items_per_doc, target_sents)

    #print '\n', config_note
    print "-----------------------------------\n"
    print 'Start time : %s' % str(start_time)
    print "Finish time: %s" % str(datetime.now())

    print '\nComplete: %d docs, %d %s => %d (%2.1f%%) predicted as events\n' % (
        num_docs, total_num_pairs, 'gold events' if is_gold_target else 'candidate pairs', total_num_predicted,
        total_num_predicted*100/total_num_pairs if total_num_pairs > 0 else 0.0)

    #show_gold_event_properties(stats)

    #for arg_type in policies_forward_search:
    #    value = policies_forward_search[arg_type]
    #    args['forward-search-%s' % arg_type] = value

    #for arg_type in policies_backward_search:
    #    value = policies_backward_search[arg_type]
    #    args['backward-search-%s' % arg_type] = value

    if output_as_file:
        predicted_pairs_per_doc = get_pairs_per_doc(input_items_per_doc)
        export_as_official_output_a2_file(predicted_pairs_per_doc, data_type, start_time_formatted, system_name='')
        #record_config_and_result_as_file(args, start_time_formatted)
        #backup_sourcecode_as_zip_archive(start_time_formatted)


if __name__ == '__main__':
    main()
