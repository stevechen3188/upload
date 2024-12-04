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

    # 提取範圍內的所有值
    raw_values = self.get_keywords(target_ocr_data, *value_box, '.+')

    # 合併相鄰的值
    merged_values = []
    temp_text = ""
    temp_anchor = None

    for i, (text, anchor) in enumerate(raw_values):
        if temp_text:
            # 判斷是否應合併：y 軸接近且 x 軸相鄰
            if abs(temp_anchor.ymid - anchor.ymid) < temp_anchor.hgt * 1.5 and \
                    abs(temp_anchor.rgt - anchor.lft) < temp_anchor.wid * 0.5:
                temp_text += f" {text}"
                temp_anchor.merge(anchor)
            else:
                # 不合併，存入結果
                merged_values.append((temp_text.strip(), temp_anchor))
                temp_text = text
                temp_anchor = deepcopy(anchor)
        else:
            temp_text = text
            temp_anchor = deepcopy(anchor)

    # 最後一組處理
    if temp_text and temp_anchor:
        merged_values.append((temp_text.strip(), temp_anchor))

    self.syslogger.info(f'Merged values: {merged_values}')

    # 處理檢驗項目
    item_box = (0, self.hgt, 0, value_title_anchor.lft)
    for key, keyinfo in self.retData.get_all_api_key_and_info():
        if keyinfo.regex is None:
            continue

        self.syslogger.info(f'Processing key: {key}, keyinfo: {keyinfo}')

        # 查找檢驗項目名稱
        item_label, item_label_anchor = self.get_keyword(
            target_ocr_data, *item_box, keyinfo.regex)
        self.syslogger.info(f'item_label: {item_label}, item_label_anchor: {
                            item_label_anchor}')

        if item_label is not None:
            keyinfo.default_enable = True

            # 選擇最接近的值
            exam_value_str, exam_value_anchor = self.map_closest_value_of_title_by_y_axis(
                item_label_anchor, merged_values, thresh=item_label_anchor.hgt
            )
            if exam_value_str:
                keyinfo.value = exam_value_str
                keyinfo.rectangle = Rectangle.from_anchor(exam_value_anchor)
                self.syslogger.info(f'Final value for {key}: {keyinfo.value}')
