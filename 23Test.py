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
    raw_values = self.get_keywords(target_ocr_data, *value_box, '.+')
    self.syslogger.info(f'Raw values: {raw_values}')

    # 垂直合併邏輯
    merged_values = []
    skip_indexes = set()

    for i, (text1, anchor1) in enumerate(raw_values):
        if i in skip_indexes:
            continue

        combined_text = text1
        combined_anchor = deepcopy(anchor1)

        for j, (text2, anchor2) in enumerate(raw_values):
            if j <= i or j in skip_indexes:
                continue

            # 判斷是否應垂直合併（考慮 y 軸接近且 x 軸重疊）
            if abs(anchor1.btm - anchor2.top) < anchor1.hgt * 0.5 and \
               (anchor1.lft < anchor2.rgt and anchor2.lft < anchor1.rgt):
                combined_text += f" {text2}"
                combined_anchor.merge(anchor2)
                skip_indexes.add(j)

        merged_values.append((combined_text.strip(), combined_anchor))

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
            keyinfo.value = exam_value_str
            keyinfo.rectangle = Rectangle.from_anchor(exam_value_anchor)
            self.syslogger.info(f'Final value for {key}: {keyinfo.value}')

    # 保留未匹配項目的預設值
    for key, keyinfo in self.retData.get_all_api_key_and_info():
        if not keyinfo.value:  # 如果欄位沒有值
            keyinfo.value = "-"
            self.syslogger.info(f'Default value set for {
                                key}: {keyinfo.value}')
