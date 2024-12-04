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

    # 提取 "檢驗結果" 右側的所有值
    raw_values = self.get_keywords(target_ocr_data, *value_box, '.+')
    self.syslogger.info(f'Raw values: {raw_values}')

    # 合併垂直相鄰的值
    merged_values = []
    combined_text = ""
    combined_anchor = None

    for i, (text, anchor) in enumerate(raw_values):
        if combined_text:
            # 判斷是否應垂直合併
            if abs(combined_anchor.btm - anchor.top) < combined_anchor.hgt * 0.5 and \
                    combined_anchor.lft <= anchor.rgt and combined_anchor.rgt >= anchor.lft:
                combined_text += f" {text}"  # 垂直合併文字
                combined_anchor.merge(anchor)  # 合併錨點
            else:
                # 如果不需要合併，存入當前結果
                merged_values.append((combined_text.strip(), combined_anchor))
                combined_text = text
                combined_anchor = deepcopy(anchor)
        else:
            combined_text = text
            combined_anchor = deepcopy(anchor)

    # 處理最後一組
    if combined_text and combined_anchor:
        merged_values.append((combined_text.strip(), combined_anchor))

    self.syslogger.info(f'Merged values: {merged_values}')

    # 處理檢驗項目
    item_box = (0, self.hgt, 0, value_title_anchor.lft)
    for key, keyinfo in self.retData.get_all_api_key_and_info():
        if keyinfo.regex is None:
            continue

        self.syslogger.info(f'Processing key: {key}, keyinfo: {keyinfo}')

        # 查找檢測項目名稱
        item_label, item_label_anchor = self.get_keyword(
            target_ocr_data, *item_box, keyinfo.regex)
        self.syslogger.info(f'Exam title: {item_label}, anchor: {
                            item_label_anchor}')

        if item_label is not None:
            # 選擇最接近的值
            value_label, value_anchor = self.map_closest_value_of_title_by_y_axis(
                item_label_anchor, merged_values, thresh=item_label_anchor.hgt
            )
            keyinfo.value = value_label
            keyinfo.rectangle = Rectangle.from_anchor(value_anchor)
            self.syslogger.info(f'Final value for {key}: {keyinfo.value}')
