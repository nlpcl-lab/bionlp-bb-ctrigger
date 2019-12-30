__author__ = 'jwchung'

import re
from xml.sax.saxutils import escape as xml_escape, quoteattr as xml_quoteattr

def gen_quote_text(text):
	# convert the <, &, and > characters
	text = xml_escape(text)
	text = xml_quoteattr(text)

	return text


def get_unicode_text(text):
	return unicode(text, 'utf8')


def get_alternative_text_for_letter_counting(text):
	return get_unicode_text(text.replace('…', '.'))


def get_text_fragment_with_letter_idx(text, begin=0, end=0):
	"""
	:param text:
	:param begin:
	:param end:
	:return:
	"""

	#text_unicode = get_unicode_text(text)
	text_unicode = get_alternative_text_for_letter_counting(text)

	if begin > 0 and end == 0:
		end = len(text_unicode)

	return text_unicode[begin:end].encode('utf8')


def count_num_letters(text):
	return len(get_alternative_text_for_letter_counting(text))


def count_num_words(text):
	return len(get_word_list(text.strip()))


def get_letter_list(raw_text):
	raw_text_unicode = get_unicode_text(raw_text)

	letter_list = list(raw_text_unicode)

	return [letter.encode('utf8') for letter in letter_list]


def get_word_list(raw_text):
	return raw_text.split()


def get_sent_list(raw_text):
	raw_text = re.sub(r'[\r\n]+', '\n', raw_text)

	return raw_text.split('\n')


def remove_all_tags_from_anno_text(anno_text):
	return re.sub(r'<.+?>', r'', anno_text, flags=re.DOTALL)


def get_num_of_preceding_letters(text_part, whole_text):
	char_idx = whole_text.find(text_part)

	prec_text = whole_text[:char_idx]

	raw_prec_text = remove_all_tags_from_anno_text(prec_text)

	return count_num_letters(raw_prec_text)


def get_num_of_preceding_words(text_part, whole_text):
	char_idx = whole_text.find(text_part)

	prec_text = whole_text[:char_idx]

	raw_prec_text = remove_all_tags_from_anno_text(prec_text)

	if len(raw_prec_text) > 0 and re.match('\s', raw_prec_text[-1]):
		return count_num_words(raw_prec_text)
	elif len(raw_prec_text) == 0:
		return 0
	else:
		return count_num_words(raw_prec_text) - 1


def get_num_of_preceding_sents(text_part, whole_text):
	char_idx = whole_text.find(text_part)

	prec_text = whole_text[:char_idx]

#	raw_prec_text = re.sub(r'<.+?>', '', prec_text)
	raw_prec_text = remove_all_tags_from_anno_text(prec_text)

	raw_prec_text = re.sub(r'[\r\n]+', '\n', raw_prec_text)

	return raw_prec_text.count('\n')


def get_num_of_preceding_words_in_sent(text_part, whole_text):

	char_idx = whole_text.find(text_part)

	prec_text = whole_text[:char_idx]

	raw_prec_text = remove_all_tags_from_anno_text(prec_text)

	leading_text_in_sent = raw_prec_text.split('\n')[-1].lstrip()

	if not leading_text_in_sent:
		return 0
	elif re.match('\s', leading_text_in_sent[-1]):
		return count_num_words(leading_text_in_sent)
	else:
		return count_num_words(leading_text_in_sent) - 1


def extract_field_value_pairs_from_attr_span(attr_span):
	pat1 = r'(\S+)\s*=\s*"(.*?)"'
	pat2 = r'(\S+)\s*=\s*([^">=\s]+)'

	result1 = re.findall(pat1, attr_span)
	result2 = re.findall(pat2, attr_span)

	return result1 + result2

