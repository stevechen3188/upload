def _parse_update_category(self, target_ocr_data: dict):
    # 定位 "檢驗結果" 的標題位置
    value_title_label, value_title_anchor = self.get_keyword(
        target_ocr_data, *self.entire_box, '檢驗結果'
    )
    self.syslogger.info(f'value_title_label: {
                        value_title_label}, value_title_anchor: {value_title_anchor}')

    if value_title_label is None:
        return

    # 擴大範圍
    value_title_anchor.move_x(-value_title_anchor.wid * 0.25)
    value_box = (value_title_anchor.btm, self.hgt,
                 value_title_anchor.lft, value_title_anchor.rgt)

    # 提取 "檢驗結果" 右側所有值
    raw_values = self.get_keywords(target_ocr_data, *value_box, r'.+')
    self.syslogger.info(f'Raw values: {raw_values}')

    # 分組邏輯
    grouped_values = self.group_ocr_anchor_list(
        raw_values, threshold=15, method='average', group_way='y')
    self.syslogger.info(f'Grouped values: {grouped_values}')

    # 垂直合併邏輯
    merged_values = []
    for group in grouped_values:
        if len(group) > 1:
            merged_text, merged_anchor = self.merge_boxes(group)
            merged_values.append((merged_text.strip(), merged_anchor))
        else:
            # 單一元素也加入，保留原始值（包括 "-"）
            merged_values.append(group[0])

    self.syslogger.info(f'Merged values: {merged_values}')

    # 處理檢驗項目
    item_box = (0, self.hgt, 0, value_title_anchor.lft)
    for key, keyinfo in self.retData.get_all_api_key_and_info():
        if keyinfo.regex is None:
            continue

        self.syslogger.info(f'Processing key: {key}, keyinfo: {keyinfo}')

        # 查找檢測項目名稱
        exam_title_str, exam_title_anchor = self.get_keyword(
            target_ocr_data, *item_box, keyinfo.regex)
        self.syslogger.info(f'Exam title: {exam_title_str}, anchor: {
                            exam_title_anchor}')

        if exam_title_str is not None:
            # 選擇最接近的值
            exam_value_str, exam_value_anchor = self.map_closest_value_of_title_by_y_axis(
                exam_title_anchor, merged_values, thresh=exam_title_anchor.hgt
            )
            if exam_value_str:  # 確保有找到匹配的值
                keyinfo.value = exam_value_str
                keyinfo.rectangle = Rectangle.from_anchor(exam_value_anchor)
                self.syslogger.info(f'Final value for {key}: {keyinfo.value}')
