def parse_exam_under_categories(self, target_ocr_data, *entire_box):
        # 找出檢測大項
        major_categories = self.parse_major_categories(target_ocr_data, self.major_categories)
        
        middle_label, middle_anchor = self.get_keyword(target_ocr_data, *entire_box, r"台灣優品醫事檢驗所")
        self.syslogger.info(f"\n[{self.img_name}] middle {entire_box}: [{middle_label}], {middle_anchor}")
        if middle_label is None:
            return
        
        major_categories.insert(0, ["左", AnchorSpec(**{"top": 0, "btm": self.hgt, "lft": 0, "rgt": middle_anchor.xmid})])
        major_categories.insert(1, ["右", AnchorSpec(**{"top": 0, "btm": self.hgt, "lft": middle_anchor.xmid, "rgt": self.wid})])
        self.syslogger.info(f"\n[{self.img_name}] major_categories: {major_categories}")
        
        # 依序處理 category
        for idx, (category_str, category_anchor) in enumerate(major_categories):
            self.syslogger.info(f"\n[{self.img_name}] processing category: {category_str}")
            
            # 取出當前 category 下的 exam
            category_exam = self.retData.get_api_key_and_info_by_group(self.major_categories[category_str])
            category_exam_box = category_anchor.boundary
            
            # exam value 上面的標題
            value_top_label, value_top_anchor = self.get_keyword(target_ocr_data, *category_anchor.boundary, r"檢驗結果")
            self.syslogger.info(f"\n[{self.img_name}] value top {entire_box}: [{value_top_label}], {value_top_anchor}")
            if value_top_label is None:
                continue
            
            # 依序處理 category 下的 exam
            for api_key, exam_info in category_exam:
                exam_regex = exam_info.regex
                exam_title_str, exam_title_anchor = self.get_keyword(target_ocr_data, *category_exam_box, exam_regex)
                self.syslogger.info(f"\n[{self.img_name}] Parse {api_key} [{exam_regex}] title result {category_exam_box}: [{exam_title_str}], {exam_title_anchor}")
                
                if exam_title_str is not None:
                    
                    exam_next_title_box = (
                        exam_title_anchor.btm,
                        self.hgt,
                        exam_title_anchor.lft,
                        exam_title_anchor.rgt,
                    )
                    exam_title_str2, exam_title_anchor2 = self.get_keyword(target_ocr_data, *exam_next_title_box, r".+")

                    if exam_title_str2 is not None:
                        exam_value_box = (
                            exam_title_anchor.top - (exam_title_anchor.hgt / 2),
                            exam_title_anchor2.top - (exam_title_anchor2.hgt / 2),
                            value_top_anchor.lft - (value_top_anchor.wid / 2),
                            value_top_anchor.xmid
                        )
                    else:
                        exam_value_box = (
                            exam_title_anchor.top - (exam_title_anchor.hgt / 2),
                            exam_title_anchor.top + (exam_title_anchor.hgt / 2),
                            value_top_anchor.lft - (value_top_anchor.wid / 2),
                            value_top_anchor.xmid
                        )

                    # cand = candidate
                    cand_exam_values = self.get_keywords(target_ocr_data, *exam_value_box, r".+")
                    self.syslogger.info(f"\n[{self.img_name}] Parse {api_key} [{exam_regex}] candidate values {exam_value_box}: {cand_exam_values}")
                    
                    cand_exam_values = self.merge_boxes(cand_exam_values)

                    if len(cand_exam_values) > 0:
                        exam_value_str, exam_value_anchor = self.map_closest_value_of_title_by_y_axis(exam_title_anchor, cand_exam_values, thresh=exam_title_anchor.hgt)
                        exam_info.value = exam_value_str
                        exam_info.rectangle = Rectangle.from_anchor(exam_value_anchor)
                        self.syslogger.info(f"\n[{self.img_name}] Parse {api_key} [{exam_regex}] final values {exam_value_box}: {exam_info.value}")