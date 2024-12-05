def _parse_update_category(self, target_ocr_data: dict):
    # 定位 "檢驗結果" 的標題位置
    # 使用正則表達式在 OCR 資料中尋找 "檢驗結果" 的標題位置和文字
    value_title_label, value_title_anchor = self.get_keyword(
        target_ocr_data, *self.entire_box, '檢驗結果'
    )
    self.syslogger.info(f'value_title_label: {
                        value_title_label}, value_title_anchor: {value_title_anchor}')

    if value_title_label is None:  # 如果未找到 "檢驗結果"，直接返回
        return

    # 擴大範圍
    # 將"檢驗結果"右側的值進行擴大範圍抓取，便於後續提取右側的數據
    value_title_anchor.move_x(-value_title_anchor.wid * 0.25)
    value_box = (value_title_anchor.btm, self.hgt,
                 value_title_anchor.lft, value_title_anchor.rgt)

    # 提取範圍內的所有值
    # 抓取"檢驗結果"右側範圍內的所有文字框
    raw_values = self.get_keywords(target_ocr_data, *value_box, '.+')

    # 合併相鄰的值
    # 用於合併垂直或水平相鄰的文字框，例如 "Positive" 和 "(3671.26)" 或 "Light Yellow" 和 "Clear"
    merged_values = []
    temp_text = ""  # 暫存合併的文字
    temp_anchor = None  # 暫存合併的框

    for i, (text, anchor) in enumerate(raw_values):  # 遍歷抓取到的文字框
        if temp_text:  # 如果已經有暫存的值
            # 處理括號開頭的值 (如 "(3671.26)")
            if text.startswith("("):  # 判斷是否以括號開頭
                temp_text += f"{text}"  # 直接合併到暫存文字
                temp_anchor.merge(anchor)  # 合併框位置
            # 判斷是否應合併：y 軸接近且 x 軸相鄰
            elif abs(temp_anchor.ymid - anchor.ymid) < temp_anchor.hgt * 1.5 and \
                    abs(temp_anchor.rgt - anchor.lft) < temp_anchor.wid * 0.5:
                temp_text += f" {text}"  # 合併到暫存文字
                temp_anchor.merge(anchor)  # 合併框位置
            else:
                # 不合併，將暫存的文字與框存入結果
                merged_values.append((temp_text.strip(), temp_anchor))
                temp_text = text  # 將當前文字設為新的暫存文字
                temp_anchor = deepcopy(anchor)  # 更新暫存框
        else:
            # 初次進入時初始化暫存文字和框
            temp_text = text
            temp_anchor = deepcopy(anchor)

    # 最後一組處理
    # 如果暫存文字和框還未存入，將其存入結果
    if temp_text and temp_anchor:
        merged_values.append((temp_text.strip(), temp_anchor))

    self.syslogger.info(f'Merged values: {merged_values}')

    # 處理檢驗項目
    # 依次處理每個需要檢測的項目
    item_box = (0, self.hgt, 0, value_title_anchor.lft)  # 左側區域範圍，用於檢測項目名稱
    for key, keyinfo in self.retData.get_all_api_key_and_info():
        if keyinfo.regex is None:  # 如果該項目未設置正則表達式，跳過
            continue

        self.syslogger.info(f'Processing key: {key}, keyinfo: {keyinfo}')

        # 查找檢測項目名稱
        # 根據正則表達式尋找左側對應的檢測項目名稱
        item_label, item_label_anchor = self.get_keyword(
            target_ocr_data, *item_box, keyinfo.regex)
        self.syslogger.info(f'item_label: {item_label}, item_label_anchor: {
                            item_label_anchor}')

        if item_label is not None:  # 如果找到該檢測項目名稱
            keyinfo.default_enable = True  # 將該項目標記為啟用

            # 選擇最接近的值
            # 根據檢測項目名稱的位置，尋找與之 y 軸最接近的值
            exam_value_str, exam_value_anchor = self.map_closest_value_of_title_by_y_axis(
                item_label_anchor, merged_values, thresh=item_label_anchor.hgt
            )
            if exam_value_str:  # 如果找到值
                keyinfo.value = exam_value_str  # 更新檢測項目的值
                keyinfo.rectangle = Rectangle.from_anchor(
                    exam_value_anchor)  # 更新檢測項目的位置框
                self.syslogger.info(f'Final value for {key}: {keyinfo.value}')
