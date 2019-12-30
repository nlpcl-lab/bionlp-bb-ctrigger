#!/usr/bin/python
# -*- coding: utf-8 -*-
"""

"""

from concepts import Entity, InputItem
from multibytes import replace_multibytes


if __name__ == '__main__':
	pass


def cal_performance(num_pred, num_gold, num_matched):
	""":rtype: (float, float, float)"""
	p = num_matched * 1.0 / num_pred if num_pred > 0.0 else 0.0
	r = num_matched * 1.0 / num_gold if num_gold > 0.0 else 0.0
	f1 = 2.0 * p * r / (p + r) if (p + r) > 0.0 else 0.0

	return p, r, f1


def print_performance(header, num_pred, num_gold, num_matched, digits, indicators=True):
	# digits: 몇 자리 수인지에 따라 문자열 패딩 조정 (분자, 분모)
	num1_digits, num2_digits = digits
	p, r, f = cal_performance(num_pred, num_gold, num_matched)

	if indicators:
		p_indi, r_indi, f1_indi = 'P:', 'R:', 'F:'
	else:
		p_indi, r_indi, f1_indi = '  ', '  ', '  '

	template = "{header}%s{p:5.1f} ({nm:%dd}/{np:%dd}) %s{r:5.1f} ({nm:%dd}/{ng:%dd}) %s{f:5.1f}" % (
		p_indi, num1_digits, num2_digits, r_indi, num1_digits, num2_digits, f1_indi)

	print template.format(header=header, p=p * 100, r=r * 100, f=f * 100, nm=num_matched, np=num_pred, ng=num_gold)


def evaluate(input_items_per_doc, target_sents=None):
	"""

	:type input_items_per_doc: dict[str, (list[InputItem], Doc)]
	:return:
	"""

	result_per_doc = {}  # 문장별 성능 통계는 따로 모으기

	debug_print = False
	debug_print = True

	for doc_idx, doc_id in enumerate(sorted(input_items_per_doc, key=lambda x: int(x))):
		input_items, gold_doc = input_items_per_doc[doc_id]

		# 살펴보고자 하는 문장이 지정된 경우, 해당 문장 내 관계인 경우만 살펴봄
		if target_sents:
			pred_input_items = [i for i in input_items
								if i.is_predicted() and i.is_intra_sent() and i.get_sent_offsets()[0] in target_sents]
			target_gold_events = [e for e in gold_doc.iter_events()
								  if e.is_intra_sent() and e.get_bacteria().get_sent_offset() in target_sents]
		else:
			# 처음에 주어졌던 모든 후보 입력 쌍 중,
			# 시스템이 정답이라고 예측했던 것만 살펴보기
			pred_input_items = [i for i in input_items if i.is_predicted()]
			target_gold_events = list(gold_doc.iter_events())

		print '=====' * 10, '\n[#%d] Evaluation for doc %s\n' % (doc_idx, doc_id)

		num_matched1 = 0 		# 예측한 것 중에서 정답과 맞는 것 (전체)
		num_matched1_cross = 0  # 예측한 것 중에서 정답과 맞는 것 (문장 밖)
		num_matched2 = 0 		# 정답 중에서 예측에 성공한 것 (전체)
		num_matched2_cross = 0  # 정답 중에서 예측에 성공한 것 (문장 밖)
		matched_event_ids = []

		# ==========================================================================
		# [Precision] 전체 predicted pairs 중에서 몇 개가 gold events와 일치하는지
		for pred_pair in pred_input_items:  # type: InputItem

			input_id = pred_pair.get_id()
			bac_id, loc_id = pred_pair.get_bac_id(), pred_pair.get_loc_id()

			# 확인: 예측된 입력쌍에 포함된 모든 박테리아 및 공간 객체는
			# 주석된 객체(gold entity) 중 하나와 정확히 일치해야 함
			# (BB3-event에서는 객체 식별(NER)은 안 하고 객체 간 관계 성립 여부만 파악하므로)
			assert gold_doc.get_bacteria_by_id(bac_id) and gold_doc.get_location_by_id(loc_id)

			is_pred_success = gold_doc.has_event(bac_id, loc_id)

			# [예측 성공] True positive
			if is_pred_success:
				num_matched1 += 1
				if pred_pair.is_cross_sent():
					num_matched1_cross += 1
				matched_event_ids.append(gold_doc.get_event_id(bac_id, loc_id))
			# [예측 실패] False positive
			else:
				bac_id, loc_id = pred_pair.get_bac_id(), pred_pair.get_loc_id()
				bac_text_replaced, _ = replace_multibytes(pred_pair.get_bac_text())
				loc_text_replaced, _ = replace_multibytes(pred_pair.get_loc_text())
				#is_bac_in_title, is_loc_in_title = pred_pair.is_in_title()
				bac_sent_offset, loc_sent_offset = pred_pair.get_sent_offsets()
				#bac_sent_offset = 'T' if is_bac_in_title else bac_sent_offset
				#loc_sent_offset = 'T' if is_loc_in_title else loc_sent_offset


				is_crosssent = pred_pair.is_cross_sent()
				print '  {mark1}FP-{id}{mark2} ({sent}) "{b_text}" ({b_id};s{b_so};h{b_to}) | "{l_text}" ({l_id};s{l_so};h{l_to}) {type}'.format(
					id=input_id, sent='%s->%s' % (bac_sent_offset, loc_sent_offset) if is_crosssent else bac_sent_offset,
					mark1='{!}' if not is_pred_success else '   ', mark2='*' if is_crosssent else ' ',
					b_text=bac_text_replaced, b_id=bac_id, b_so=bac_sent_offset, b_to=pred_pair.get_bac_head_token_idx_in_sent(),
					l_text=loc_text_replaced, l_id=loc_id, l_so=loc_sent_offset, l_to=pred_pair.get_loc_head_token_idx_in_sent(),
					type='[cross]' if is_crosssent else '')

		print '  ', '----' * 8
		#print '@@!@!', matched_event_ids
		#print '$$Target gold events:', [e.get_id() for e in target_gold_events]

		# ==========================================================================
		# [Recall] 전체 gold events 중에서 몇 개가 predicted 되었는지
		for gold_event in target_gold_events:
			bac = gold_event.get_bacteria()  # type: Entity
			loc = gold_event.get_location()  # type: Entity
			is_crosssent = gold_event.is_cross_sent()

			is_pred_success = gold_event.get_id() in matched_event_ids

			# [예측 성공] True positive
			if is_pred_success:
				num_matched2 += 1
				if gold_event.is_cross_sent():
					num_matched2_cross += 1
			# [예측 실패] False negative
			else:
				pass
				#print 'False negative!'
				#raw_input()

			bac_sent_offset = bac.get_sent_offset()
			loc_sent_offset = loc.get_sent_offset()

			print '  {mark1}Gold-{id}{mark2} ({sent}) {b_id}-{l_id} "{b_text}" (s{b_so};h{b_to}) | "{l_text}" (s{l_so};h{l_to}) {type}'.format(
				id=gold_event.get_id(),
				sent='%s->%s' % (bac_sent_offset, loc_sent_offset) if is_crosssent else bac_sent_offset,
				mark1='{!}' if not is_pred_success else '   ', mark2='*' if is_crosssent else ' ',
				b_text=bac.get_text(), b_id=bac.get_id(), b_so=bac_sent_offset, b_to=bac.get_head_token_idx_in_sent(),
				l_text=loc.get_text(), l_id=loc.get_id(), l_so=bac_sent_offset, l_to=loc.get_head_token_idx_in_sent(),
				type='[cross]' if is_crosssent else '')

		#print '##!!##', num_matched1, num_matched2
		assert num_matched1 == num_matched2
		assert num_matched1_cross == num_matched2_cross

		num_matched = num_matched1
		num_matched_cross = num_matched1_cross
		num_matched_intra = num_matched - num_matched1_cross

		num_pred = len(pred_input_items)
		num_pred_cross = len([i for i in pred_input_items if i.is_cross_sent()])
		num_pred_intra = num_pred - num_pred_cross

		#num_gold = gold_doc.get_num_events()
		#num_gold_cross = gold_doc.get_num_crst_events()
		num_gold = len(target_gold_events)
		num_gold_cross = len([e for e in target_gold_events if e.is_cross_sent()])
		num_gold_intra = num_gold - num_gold_cross

		# 문서별 성능 계산 및 출력 (전체, 문장내, 문장밖)
		print '  ', '----' * 8
		numerator_digits = len(str(num_matched))  # 분자 자리수
		denominator_digits = max(len(str(num_pred)), len(str(num_gold)))  # 분모 자리수
		print_performance('   [INTRA] ', num_pred_intra, num_gold_intra, num_matched_intra, digits=(numerator_digits, denominator_digits))
		print_performance('   [CROSS] ', num_pred_cross, num_gold_cross, num_matched_cross, digits=(numerator_digits, denominator_digits))
		print_performance('   [TOTAL] ', num_pred, num_gold, num_matched, digits=(numerator_digits, denominator_digits))

		precision, recall, f1 = cal_performance(num_pred, num_gold, num_matched)
		result_per_doc[doc_id] = {'num_gold': num_gold, 'num_gold_cross': num_gold_cross,
								  'num_pred': num_pred, 'num_pred_cross': num_pred_cross,
								  'num_matched': num_matched1, 'num_matched_cross': num_matched1_cross,
								  'precision': precision, 'recall': recall, 'f1': f1}

	total_num_gold    = total_num_gold_cross    = total_num_gold_intra = 0
	total_num_pred    = total_num_pred_cross    = total_num_pred_intra = 0
	total_num_matched = total_num_matched_cross = total_num_matched_intra = 0

	print
	print '====' * 15
	print 'PER-DOC RESULTS:'

	# 문서별 통계 취합
	for doc_id in sorted(result_per_doc, key=lambda x: int(x)):
		result = result_per_doc[doc_id]
		num_gold = result['num_gold']
		num_gold_cross = result['num_gold_cross']
		num_pred = result['num_pred']
		num_pred_cross = result['num_pred_cross']
		num_matched = result['num_matched']
		num_matched_cross = result['num_matched_cross']

		total_num_gold += num_gold
		total_num_gold_cross += num_gold_cross
		total_num_gold_intra = total_num_gold - total_num_gold_cross
		total_num_pred += num_pred
		total_num_pred_cross += num_pred_cross
		total_num_pred_intra = total_num_pred - total_num_pred_cross
		total_num_matched += num_matched
		total_num_matched_cross += num_matched_cross
		total_num_matched_intra = total_num_matched - total_num_matched_cross

		numerator_digits = 2  # 분자 자리수
		denominator_digits = 2  # 분모 자리수
		print_performance('  %8s [TOTAL] ' % doc_id, num_pred, num_gold, num_matched,
						  digits=(numerator_digits, denominator_digits))
		print_performance('  %8s [CROSS] ' % '', num_pred_cross, num_gold_cross, num_matched_cross,
						  digits=(numerator_digits, denominator_digits), indicators=False)

	print
	print '====' * 15
	print 'TOTAL RESULTS:'
	numerator_digits = len(str(total_num_matched))  # 분자 자리수
	denominator_digits = max(len(str(total_num_pred)), len(str(total_num_gold)))  # 분모 자리수
	print_performance('    [INTRA] ', total_num_pred_intra, total_num_gold_intra, total_num_matched_intra, digits=(numerator_digits, denominator_digits))
	print_performance('    [CROSS] ', total_num_pred_cross, total_num_gold_cross, total_num_matched_cross, digits=(numerator_digits, denominator_digits))
	print_performance('    [TOTAL] ', total_num_pred, total_num_gold, total_num_matched, digits=(numerator_digits, denominator_digits))


if __name__ == '__main__':
	pass