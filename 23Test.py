def _parse_update_category(self, target_ocr_data: dict):
    # 定位 "檢驗結果" 的標題位置
    value_title_label, value_title_anchor = self.get_keyword(
        target_ocr_data, *self.entire_box, '檢驗結果'
    )
    self.syslogger.info(f'\n[{self.img_name}] value_title_label: {
                        value_title_label}, value_title_anchor: {value_title_anchor}')

    if value_title_label is None:  # 如果未找到 "檢驗結果"，直接返回
        return

    # 擴大範圍
    value_title_anchor.move_x(-value_title_anchor.wid * 0.25)

    # 處理檢驗項目
    item_box = (0, self.hgt, 0, value_title_anchor.lft)  # 左側區域範圍，用於檢測項目名稱
    for key, keyinfo in self.retData.get_all_api_key_and_info():
        if keyinfo.regex is None:  # 如果該項目未設置正則表達式，跳過
            continue

        self.syslogger.info(f'\n[{self.img_name}] Processing key: {
                            key}, keyinfo: {keyinfo}')

        # 查找檢測項目名稱
        item_label, item_label_anchor = self.get_keyword(
            target_ocr_data, *item_box, keyinfo.regex)
        self.syslogger.info(f'\n[{self.img_name}] item_label: {
                            item_label}, item_label_anchor: {item_label_anchor}')

        if item_label is not None:  # 如果找到該檢測項目名稱
            keyinfo.default_enable = True  # 將該項目標記為啟用

            # 設置範圍
        if key in ["transparency", "hbeag", "hbsag"]:  # 特殊處理項目
            # 優化的範圍設置
            new_item_box = (
                max(0, item_label_anchor.btm),  # 下邊界從當前項目底部開始
                min(self.hgt, item_label_anchor.btm + \
                    item_label_anchor.hgt * 1.5),  # 限制範圍擴展到 1.5 行
                max(0, item_label_anchor.lft - \
                    item_label_anchor.wid / 8),  # 左側稍微擴展
                min(self.wid, item_label_anchor.rgt + \
                    item_label_anchor.wid / 8)  # 右側稍微擴展
            )
            next_item_label, next_item_label_anchor = self.get_keyword(
                target_ocr_data, *new_item_box, r".+")

            # 如果有下一行，擴展範圍
            if next_item_label is not None and next_item_label_anchor:
                value_box = (
                    max(0, item_label_anchor.top -
                        item_label_anchor.hgt * 0.1),  # 上邊界稍微向上擴展
                    next_item_label_anchor.btm,  # 下邊界為下一行的底部
                    max(0, value_title_anchor.lft - \
                        value_title_anchor.wid * 0.1),  # 左邊界稍微擴展
                    min(self.wid, value_title_anchor.rgt + \
                        value_title_anchor.wid * 0.1)  # 右邊界稍微擴展
                )
            else:  # 單行情況
                value_box = (
                    max(0, item_label_anchor.top -
                        item_label_anchor.hgt * 0.1),  # 上邊界稍微向上擴展
                    item_label_anchor.btm,  # 下邊界為當前項目底部
                    max(0, value_title_anchor.lft - \
                        value_title_anchor.wid * 0.1),  # 左邊界稍微擴展
                    min(self.wid, value_title_anchor.rgt + \
                        value_title_anchor.wid * 0.1)  # 右邊界稍微擴展
                )
        else:  # 一般項目
            value_box = (
                max(0, item_label_anchor.top -
                    item_label_anchor.hgt * 0.1),  # 上邊界稍微向上擴展
                item_label_anchor.btm,  # 下邊界為當前項目底部
                max(0, value_title_anchor.lft - \
                    value_title_anchor.wid * 0.1),  # 左邊界稍微擴展
                min(self.wid, value_title_anchor.rgt + \
                    value_title_anchor.wid * 0.1)  # 右邊界稍微擴展
            )

            self.syslogger.debug(f'\n[{self.img_name}] value_box for key {
                                 key}: {value_box}')

            values = self.get_keywords(target_ocr_data, *value_box, '.+')
            if not values:
                self.syslogger.warning(f'\n[{self.img_name}] No values found for key {
                                       key} in value_box: {value_box}')
                continue

            # 檢查合併的值是否過長
            exam_value_str, exam_value_anchor = self.merge_boxes(values)
            if len(exam_value_str) > 50:  # 假設長度超過 50 表示異常
                self.syslogger.warning(f'\n[{self.img_name}] Value too long for key {
                                       key}: {exam_value_str}')
                continue

            self.syslogger.debug(f'\n[{self.img_name}] Merged value: {
                                 exam_value_str}, anchor: {exam_value_anchor}')
            if not exam_value_str or not exam_value_anchor:
                self.syslogger.warning(
                    f'\n[{self.img_name}] Failed to merge boxes for key {key}')
                continue

            # 更新檢測項目值
            keyinfo.value = exam_value_str
            keyinfo.rectangle = Rectangle.from_anchor(exam_value_anchor)
            self.syslogger.info(f'\n[{self.img_name}] Final value for {
                                key}: {keyinfo.value}')
