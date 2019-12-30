def replace_multibytes(text):
	"""
	:type text_unicode: str
	:rtype: (str, list[(int, str)])
	"""
	multibytes = []

	text_unicode = text.decode('utf-8')

	for i, c in enumerate(text_unicode):
		if ord(c) >= 128:
			text_unicode = text_unicode.replace(c, '@')
			multibytes.append((i, c.encode('utf-8')))

	text_replaced = text_unicode.encode('utf-8')

	return text_replaced, multibytes


def refine_multibytes(text, doc_id):
	"""

	:param text:
	:param doc_id:
	:rtype: (str, list[(int, str)])
	"""

	multibytes = None
	#multibyte_table = g_multibyte_table
	multibyte_table = {}

	if doc_id in multibyte_table:
		text_refined = text
		repl_table = multibyte_table[doc_id]
		for original, repl in repl_table:
			#prev_len = len(ext_refined)
			text_refined = text_refined.replace(original, repl)
			#print 'Replacing text! %d => %d' % (prev_len, len(text_refined))
	else:
		text_refined, multibytes = replace_multibytes(text)

	return text_refined, multibytes


if __name__ == '__main__':
	pass