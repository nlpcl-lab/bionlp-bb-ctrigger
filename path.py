from os.path import join
from os.path import dirname
from os.path import realpath

g_root_path = dirname(realpath(__file__))

g_dir_path_to_data = join(g_root_path, 'data')
g_dir_path_to_official_data = join(g_dir_path_to_data, 'bb3-event_official_data')
g_dir_path_to_corenlp_output = join(g_dir_path_to_data, "corenlp_output")

g_dir_path_to_supp_res = join(g_dir_path_to_data, 'supporting_resources')
g_dir_path_to_bb_tokenization = join(g_dir_path_to_supp_res, 'BB3_tokenization_resources')

g_file_path_to_triggers = join(g_dir_path_to_data, "triggers-45.txt")

g_dir_path_to_prediction_official_format = join(g_dir_path_to_data, 'predicted_output_in_official_format')
g_dir_path_to_verse_output = join(g_dir_path_to_prediction_official_format, 'prediction-test-VERSE-F=55.33')



