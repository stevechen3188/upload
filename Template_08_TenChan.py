import re
import logging
from copy import deepcopy
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

from .ParsingTemplate import ParsingTemplate
from .AnchorSpec import AnchorSpec
from .ReturnDataModule import KeyInfo, Rectangle, ReturnData
from .Approvers import *

# 8.天晟醫院
class Template_TenChan(ParsingTemplate):
    def __init__(self, img_name:str , clinicId: str):
        
        super().__init__()
        self.syslogger = logging.getLogger("ACP")
        self.img_name = img_name
        if '24-3' in self.img_name:
            print('cool!')
        self.clinicId = clinicId
        
        self.retData = ReturnData()
        self.wid = None
        self.hgt = None
    
    def preprocess(self, ocr_return):
        ocr_return = self.remove_width_height(ocr_return)
        
        for k, v in list(ocr_return.items()):
            rm_str = ocr_return[k][0]
            rm_str = self.sub_regular(r"[”·、']", "", rm_str)
            rm_str = self.sub_regular(r"[:]", ".", rm_str)

            # 移除空值 block
            if rm_str == "":
                ocr_return.pop(k)
                continue
            
            # 移除形狀異常 block (這個格式有很多1個數字的方塊, 然後沒有甚麼縱向方框, 就把長寬比限制拿掉)
            anch_obj = AnchorSpec(v[1])
            if anch_obj.hgt is None or anch_obj.wid is None:
                ocr_return.pop(k)
                continue

            # 修正文字
            ocr_return[k][0] = rm_str

        return ocr_return
    
    def parse_process(self, *args):
        ocr_return, azure_return, scoring = args
        target_ocr = azure_return
        # if '18-3' in self.img_name:
        #     print('cool!')
        # else:
        #     return {"clinicId": self.clinicId, "rectangles": self.retData.return_result()} 
        self.syslogger.info(f"\n[{self.img_name}] using azure ocr output")
        self.syslogger.debug(f"\n[{self.img_name}] target_ocr at start: {target_ocr}")
        self.wid = target_ocr["0"][1]
        self.hgt = target_ocr["1"][1]
        # Preprocess
        target_ocr_data = self.preprocess(target_ocr)
        self.syslogger.debug(f"\n[{self.img_name}] target_ocr after preprocess: {target_ocr_data}")
        self.entire_box = (0, self.hgt, 0, self.wid)
        
        try:
            # 體檢人姓名
            self._parse_name(target_ocr_data, *self.entire_box)
            # 出生日期
            self._parse_birth(target_ocr_data, *self.entire_box)
            # 體檢日期
            self._parse_exam_date(target_ocr_data, *self.entire_box)
            # 欄位分類分群
            group_num_map = self._prepare_returndata_regex()
            # 取得大類
            major_categories = self._parse_major_categories(target_ocr_data, group_num_map)
            self.syslogger.info(f'major_categories: {major_categories}')
            # 開始辨識細項
            while major_categories:
                self._parse_update_categoy(target_ocr_data, major_categories, group_num_map)
                
        except Exception as e:
            self.syslogger.error(f"\n[{self.img_name}] unexpected error: ", e)
        
        # 最終結果
        ret_result = self.retData.return_result() if scoring else self.retData.return_result_with_pos()
        self.syslogger.debug(f"\n[{self.img_name}] ret_result: {self.get_formatted_json(ret_result)}")
        self.syslogger.debug(f"\n[{self.img_name}] ret_handover_data: {self.get_formatted_json(self.get_handover_metadata())}")
        
        return {"clinicId": self.clinicId, "rectangles": ret_result}, self.get_handover_metadata()

    
    def _prepare_returndata_regex(self):
        group_num_map = {
            '白血球分類檢查': 0,
            '血脂肪檢查': 1,
            '血液常規檢查': 2,
            '尿沉渣鏡檢': 3,
            '尿液常規檢查': 4,
            '肝功能檢查': 5,
            '肝炎檢驗': 6,
            '腎功能檢查': 7,
            '癌症篩檢': 8,
            '膽功能檢驗': 9,
            '糖尿病篩檢': 10,
        }
        
        def numbers_and_upper_arrow(value: str):
            return re.sub('[^0-9.↑]', '', value)
        
        def padding_upper_arrow(value: str):
            if ')' not in value:
                return value
            quote_idx = value.rfind(")")
            last_char = value[quote_idx+1:]
            if len(last_char) <= 2 and len(last_char) >= 1:
                result = value[:quote_idx+1] + '↑'
                return result
            return value
        
        def light_yellow_with_space(value: str):
            if 'lightyellow' in value.lower():
                return 'Light Yellow'
            return value
        def digit_range(value: str):
            return ''.join(re.findall('\d+-\d+|\d+', value))
        
        # 白血球分類檢查
        self.retData.neutrophils_percent.update_kwargs(regex='分葉中性球', group=0)
        self.retData.eosinophils_percent.update_kwargs(regex='嗜酸性球', group=0)
        self.retData.monocytes_percent.update_kwargs(regex='單核球', group=0)
        self.retData.lymphocytes_percent.update_kwargs(regex='淋巴球', group=0)
        self.retData.basophils_percent.update_kwargs(regex='嗜鹼性球', group=0)
        # 血脂肪檢查
        self.retData.total_cholesterol.update_kwargs(regex='^膽固醇$', group=1)
        self.retData.hdl_c.update_kwargs(regex='高密度脂蛋白膽固醇', group=1)
        self.retData.triglyceride.update_kwargs(regex='三酸甘油脂', group=1)
        
        # 血液常規檢查
        self.retData.hemoglobin.update_kwargs(regex='血色素檢查', group=2)
        self.retData.rbc.update_kwargs(regex='紅血球計數', group=2)
        self.retData.platelet.update_kwargs(regex='血小板計數', group=2)
        self.retData.wbc.update_kwargs(regex='白血球計數', group=2)
        self.retData.hematocrit.update_kwargs(regex='血球比容值測定', group=2)
        
        # 尿沉渣鏡檢
        self.retData.urine_rbc.update_kwargs(regex='紅血球', group=3, value_approver=[digit_range])
        self.retData.epithelial_cells.update_kwargs(regex='上皮細胞', group=3)
        self.retData.urine_wbc.update_kwargs(regex='白血球', group=3, value_approver=[digit_range])
        self.retData.bacteria.update_kwargs(regex='細菌', group=3)
        
        # 尿液常規檢查
        self.retData.urine_protein.update_kwargs(regex='尿蛋白質檢查', group=4)
        self.retData.urine_glucose.update_kwargs(regex='尿糖檢查', group=4)
        self.retData.ph_value.update_kwargs(regex='尿酸鹼度', group=4)
        self.retData.nitrite.update_kwargs(regex='尿亞硝酸鹽', group=4, value_approver=[approver_neg_pos])
        self.retData.urine_bilirubin.update_kwargs(regex='尿膽紅素', group=4)
        self.retData.urine_color.update_kwargs(regex='外觀', group=4, value_approver=[light_yellow_with_space])
        self.retData.occult_blood.update_kwargs(regex='尿潛血檢查', group=4)
        self.retData.specific_gravity.update_kwargs(regex='尿比重檢查', group=4)
        self.retData.leukocyte_esterase.update_kwargs(regex='尿白血球脂酵素', group=4)
        self.retData.ketone.update_kwargs(regex='尿酮體', group=4)
        self.retData.urobilinogen.update_kwargs(regex='尿膽素原', group=4)
        
        # 肝功能檢查
        self.retData.globulin.update_kwargs(regex='Globulin球蛋白', group=5, value_approver=[numbers_and_upper_arrow])
        self.retData.sgpt.update_kwargs(regex='丙酮轉胺基酵素', group=5)
        self.retData.albumin.update_kwargs(regex='白蛋白', group=5)
        self.retData.sgot.update_kwargs(regex='草酸轉胺基酵素', group=5)
        self.retData.gamma_gt.update_kwargs(regex='轉移酵素', group=5)
        
        # 肝炎檢驗
        self.retData.hbsag.update_kwargs(regex='B型肝炎表面抗原', group=6, value_approver=[padding_upper_arrow])
        self.retData.hbeag.update_kwargs(regex='B型肝炎E抗原', group=6, value_approver=[padding_upper_arrow])
        
        # 腎功能檢查
        self.retData.bun.update_kwargs(regex='血中尿素氮', group=7)
        self.retData.uric_acid.update_kwargs(regex='尿酸', group=7)
        self.retData.creatinine.update_kwargs(regex='肌酸酐', group=7)
        
        # 癌症檢查
        self.retData.alphafetoprotein.update_kwargs(regex='胎兒蛋白', group=8)
        
        # 膽功能檢查
        self.retData.total_bilirubin.update_kwargs(regex='總膽紅素', group=9)
        self.retData.direct_bilirubin.update_kwargs(regex='直接膽紅素', group=9)
        
        # 糖尿病篩檢
        self.retData.ac_sugar.update_kwargs(regex='飯前血糖', group=10)
        self.retData.hba1c.update_kwargs(regex='糖化血色素', group=10)
        return group_num_map
            
    def _parse_update_categoy(self, target_ocr_data: dict, major_categories: List[Tuple[str, AnchorSpec]], group_num_map: Dict[str, int]):
        """對所有項目根據大量進行辨識分群, 並將結果更新回KeyInfo

        Args:
            target_ocr_data (dict): 總辨識物件
            major_categories (List[Tuple[str, AnchorSpec]]): 大類項
            group_num_map (Dict[str, int]): 大類的對應號碼 dict

        Raises:
            Exception: '找不到數值錨點!'
        """        
        if len(major_categories) == 0:
            return
        
        # 處理大項
        major_category_label, major_category_anchor = major_categories.pop()
        self.syslogger.info(f'major_category_label: {major_category_label}, major_category_anchor: {major_category_anchor}')
        bottom_boundary = None
        upper_boundary = major_category_anchor.btm
        if len(major_categories) > 0:
            next_category_anchor = major_categories[-1][1]
            bottom_boundary = next_category_anchor.top - next_category_anchor.hgt * 0.3
        else:
            bottom_boundary = self.hgt
        for i in range(2): # 頁面左右邊, 分次處理
            is_left = i == 0
            self.syslogger.info(f'is_left: {is_left}')
            title_bbox = (upper_boundary, bottom_boundary, 0 if is_left else self.wid * 0.5, self.wid * 0.5 if is_left else self.wid)
            self.syslogger.info(f'title_bbox: {title_bbox}')
            title_label, title_anchor = self.get_keyword(target_ocr_data, *title_bbox, '檢查項')
            self.syslogger.info(f'title_label: {title_label}, title_achor: {title_anchor}')
            value_label, value_anchor = self.get_keyword(target_ocr_data, *title_bbox, '檢查結果')
            self.syslogger.info(f'value_label: {value_label}, value_anchor: {value_anchor}')
            value_anchor.lft -= value_anchor.wid / 4
            category_items_box = (title_anchor.btm, bottom_boundary, 0 if is_left else self.wid * 0.4 , title_anchor.rgt)
            self.syslogger.info(f'category_items_box: {category_items_box}')
            category_items = self.get_keywords(target_ocr_data, *category_items_box, '(.*)')
            self.syslogger.info(f'category_items: {category_items}')
            group_num = group_num_map[major_category_label]
            group_items: List[Tuple[str, KeyInfo]]  = self.retData.get_api_key_and_info_by_group(group_num)
            value_items_box = (title_anchor.btm, bottom_boundary, value_anchor.lft, value_anchor.rgt)
            self.syslogger.info(f'value_items_box: {value_items_box}')
            all_values_items = self.get_keywords(target_ocr_data, *value_items_box, '(.+)')
            
            for group_item in group_items:
                keyname, keyinfo = group_item
                match_item: Optional[Tuple[str, AnchorSpec]] = None
                for category_item in category_items:
                    img_item_label, img_item_anchor = category_item
                    if re.search(keyinfo.regex, img_item_label):
                        match_item = (img_item_label, img_item_anchor)
                        break
                self.syslogger.info(f'keyinfo: {keyname} match_item is {match_item}')
                if match_item is None:
                    continue
                item_value_lable, item_value_anchor = self.map_closest_value_of_title_by_y_axis(match_item[1], all_values_items)
                self.syslogger.info(f'item_value_lable: {item_value_lable} item_value_anchor: {item_value_anchor}')
                keyinfo.update_kwargs(value=item_value_lable, default_enable=True, rectangle=Rectangle.from_anchor(item_value_anchor))
                if keyinfo == self.retData.hbeag or keyinfo == self.retData.hbsag or keyinfo == self.retData.urine_color:
                     # [B型肝炎E抗原] | B型肝炎表面抗原 | 尿液外觀, 這些檢測值會分上下2~3行, 直接合併
                    self.syslogger.info(f'{keyinfo.regex} [B型肝炎E抗原] | B型肝炎表面抗原 | 尿液外觀, 這些檢測值會分上下2~3行, 直接合併')
                    item_title_anchor = match_item[1]
                    item_title_anchor.move_y(-item_title_anchor.hgt*1.5)
                    item_title_anchor.hgt *= 3
                    item_title_anchor.lft = value_anchor.lft
                    item_title_anchor.rgt = value_anchor.rgt
                    values_items = self.get_keywords(target_ocr_data, *item_title_anchor.boundary, '(.+)')
                    values_items = [item for item in values_items if '檢查項' not in item[0]]
                    merge_label, merge_anchor = self.merge_boxes(values_items)
                    keyinfo.update_kwargs(value=merge_label, default_enable=True, rectangle=Rectangle.from_anchor(merge_anchor))

    def _parse_name(self, target_ocr_data, *box) -> str:
        matched_str, matched_anchor = self.get_keyword(target_ocr_data, *box, r"^名$")
        self.syslogger.debug(f"_parse_name1: matched_str: {matched_str}, matched_anchor: {matched_anchor}")
        if matched_anchor is not None:
            matched_anchor.move_x(matched_anchor.wid * 2)
            matched_anchor.top -= matched_anchor.hgt * 0.5
            matched_anchor.wid += matched_anchor.wid * 3
            matched_str, matched_anchor = self.get_keyword(target_ocr_data, *matched_anchor.boundary, r".+")
            self.syslogger.debug(f"_parse_name2: matched_str: {matched_str}, matched_anchor: {matched_anchor}")
        if matched_str is None:
            matched_str, matched_anchor = self.get_keyword(target_ocr_data, *box, "姓")
            self.syslogger.debug(f"_parse_name3: matched_str: {matched_str}, matched_anchor: {matched_anchor}")
            matched_anchor.move_x(matched_anchor.wid * 4)
            matched_anchor.top -= matched_anchor.hgt * 0.5
            matched_anchor.wid += matched_anchor.wid * 3
            matched_str, matched_anchor = self.get_keyword(target_ocr_data, *matched_anchor.boundary, r".+")
            self.syslogger.debug(f"_parse_name4: matched_str: {matched_str}, matched_anchor: {matched_anchor}")
        if matched_str is not None:
            self.retData.name_of_examinee.value = matched_str
            self.retData.name_of_examinee.rectangle = Rectangle.from_anchor(matched_anchor)
    
    def _parse_birth(self, target_ocr_data, *box) -> Optional[datetime]:
        self.retData.birth_of_examinee.update_kwargs(value_approver=[approver_roc_date_to_ce_date1])
        
        matched_str, matched_anchor = self.get_keyword(target_ocr_data, *box, r"出生年月日")
        self.syslogger.debug(f"\n [{self.img_name}] parse birthday matched_str: {matched_str}, matched_anchor: {matched_anchor}")
        
        matched_anchor.move_x(matched_anchor.wid)
        matched_anchor.top -= matched_anchor.hgt * 0.5
        rightside_box = matched_anchor.boundary
        matched_str, matched_anchor = self.get_keyword(target_ocr_data, *rightside_box, r".+")
        self.syslogger.debug(f"\n [{self.img_name}] parse birthday matched_str: {matched_str}, matched_anchor: {matched_anchor}")
        
        if matched_str is not None:
            # 民國年
            self.retData.birth_of_examinee.value = matched_str
            self.retData.birth_of_examinee.rectangle = Rectangle.from_anchor(matched_anchor)

    def _parse_exam_date(self, target_ocr_data, *box):
        self.retData.exam_date.update_kwargs(value_approver=[approver_roc_date_to_ce_date1])
        
        matched_str, matched_anchor = self.get_keyword(target_ocr_data, *box, "檢查日期.*")
        self.syslogger.debug(f"_parse_exam_date: matched_str: {matched_str}, matched_anchor: {matched_anchor}")
        
        date_match_result = re.search('\d+/\d+/\d+', matched_str)
        if date_match_result:
            # "檢驗日期"與實際日期同一個辨識框
            matched_str = date_match_result.group()
            
        if not date_match_result:
            # 檢驗日期被拆為兩個辨識框
            matched_anchor.move_x(matched_anchor.wid)
            matched_anchor.move_y(matched_anchor.hgt * -0.3)
            matched_str, matched_anchor = self.get_keyword(target_ocr_data, *matched_anchor.boundary, "(\d+/\d+/\d+)")
            self.syslogger.debug(f"_parse_exam_date 2: matched_str: {matched_str}, matched_anchor: {matched_anchor}")
            
        if matched_str is not None:
            # 民國年
            self.retData.exam_date.value = matched_str
            self.retData.exam_date.rectangle = Rectangle.from_anchor(matched_anchor)

    def _parse_major_categories(self, target_ocr_data, group_num_map: Dict[str, int]) -> List[Tuple[str, AnchorSpec]]:
        # "類別" 應該在中間的部分
        categories_regex = '|'.join(group_num_map.keys()) # 類別1|類別2|...
        categories = self.get_keywords(target_ocr_data, *self.entire_box, categories_regex)
        # # 排序, 以 y 軸逆向排序, 達到 Priority Queue 的效果 (越上方的index後面, 越先處理)
        categories_queue = sorted(categories, key=lambda x: x[1].top, reverse=True)
        return categories_queue
        