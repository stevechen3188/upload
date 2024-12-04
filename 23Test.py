def _parse_update_category(self, target_ocr_data: dict):
    # 定位 "檢驗結果" 的標題位置
    value_title_label, value_top_anchor = self.get_keyword(
        target_ocr_data, *self.entire_box, '檢驗結果')
    self.syslogger.info(f'value_title_label: {
                        value_title_label}, value_top_anchor: {value_top_anchor}')

    if value_title_label is None:
        return

    # 擴大 "檢驗結果" 的值範圍
    value_top_anchor.move_x(-value_top_anchor.wid * 0.25)
    value_box = (value_top_anchor.btm, self.hgt,
                 value_top_anchor.lft, value_top_anchor.xmid)

    # 提取右側值，並嘗試垂直合併
    raw_values = self.get_keywords(target_ocr_data, *value_box, r'.+')
    self.syslogger.info(f'Raw values extracted: {raw_values}')
    raw_values = self.merge_boxes(raw_values)  # 合併相近的 Box

    # 檢驗項目框
    item_box = (0, self.hgt, 0, value_top_anchor.lft)

    for key, keyinfo in self.retData.get_all_api_key_and_info():
        if keyinfo.regex is None:
            continue

        # 查找項目名稱
        exam_title_str, exam_title_anchor = self.get_keyword(
            target_ocr_data, *item_box, keyinfo.regex)
        self.syslogger.info(f'Exam title: {exam_title_str}, anchor: {
                            exam_title_anchor}')

        if exam_title_str is not None:
            # 確定下一行是否有關聯值
            exam_next_title_box = (
                exam_title_anchor.btm,
                self.hgt,
                exam_title_anchor.lft,
                exam_title_anchor.rgt
            )
            exam_title_str2, exam_title_anchor2 = self.get_keyword(
                target_ocr_data, *exam_next_title_box, r'.+')

            if exam_title_str2 is not None:
                # 如果有下一行，擴展範圍
                exam_value_box = (
                    exam_title_anchor.top - (exam_title_anchor.hgt / 2),
                    exam_title_anchor2.top - (exam_title_anchor2.hgt / 2),
                    value_top_anchor.lft - (value_top_anchor.wid / 2),
                    value_top_anchor.xmid
                )
            else:
                # 單行範圍
                exam_value_box = (
                    exam_title_anchor.top - (exam_title_anchor.hgt / 2),
                    exam_title_anchor.top + (exam_title_anchor.hgt / 2),
                    value_top_anchor.lft - (value_top_anchor.wid / 2),
                    value_top_anchor.xmid
                )

            # 抓取該範圍內的值
            cand_exam_values = self.get_keywords(
                target_ocr_data, *exam_value_box, r'.+')
            self.syslogger.info(f'Candidate values for {
                                key}: {cand_exam_values}')

            cand_exam_values = self.merge_boxes(cand_exam_values)

            # 選擇與標題最近的值
            if len(cand_exam_values) > 0:
                exam_value_str, exam_value_anchor = self.map_closest_value_of_title_by_y_axis(
                    exam_title_anchor, cand_exam_values, thresh=exam_title_anchor.hgt
                )
                keyinfo.value = exam_value_str
                keyinfo.rectangle = Rectangle.from_anchor(exam_value_anchor)
                self.syslogger.info(f'Final value for {key}: {keyinfo.value}')
