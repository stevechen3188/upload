import re
import logging
from copy import deepcopy
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

from .ParsingTemplate import ParsingTemplate
from .AnchorSpec import AnchorSpec
from .ReturnDataModule import KeyInfo, Rectangle, ReturnData
from .Approvers import *

# 23.聯新國際醫院
class Template_LianXinGuoJi(ParsingTemplate):
    def __init__(self, img_name:str , clinicId: str):
        
        super().__init__()
        self.syslogger = logging.getLogger("ACP")
        self.img_name = img_name
        # if '13-3' in self.img_name:
        #     print('cool!')
        self.clinicId = clinicId
        
        self.retData = ReturnData()
        self.wid = None
        self.hgt = None

    
    def preprocess(self, ocr_return):
        ocr_return = self.remove_width_height(ocr_return)
        
        for k, v in list(ocr_return.items()):
            rm_str = ocr_return[k][0]
            rm_str =  rm_str.replace('‘', '')
            rm_str = rm_str.replace('S/CO', '')
            rm_str = rm_str.replace('N/A', '')
            rm_str = rm_str.replace('*', '')
            
            # 移除空值 block
            if rm_str == "":
                ocr_return.pop(k)
                continue

            # 修正文字
            ocr_return[k][0] = rm_str

        return ocr_return
    
    def parse_process(self, *args):
        ocr_return, azure_return, scoring = args
        target_ocr = azure_return
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
            # 性別
            self._parse_gender(target_ocr_data, *self.entire_box)
            # 體檢日期
            self._parse_exam_date(target_ocr_data, *self.entire_box)
            # 整理正則
            self._prepare_returndata_regex()
            # 開始辨識細項
            self._parse_update_category(target_ocr_data)
        
        except Exception as e:
            self.syslogger.error(f"\n[{self.img_name}] unexpected error: ", e)
        
        # 最終結果
        ret_result = self.retData.return_result() if scoring else self.retData.return_result_with_pos()
        self.syslogger.debug(f"\n[{self.img_name}] ret_result: {self.get_formatted_json(ret_result)}")
        self.syslogger.debug(f"\n[{self.img_name}] ret_handover_data: {self.get_formatted_json(self.get_handover_metadata())}")
        
        return {"clinicId": self.clinicId, "rectangles": ret_result}, self.get_handover_metadata()

    def _prepare_returndata_regex(self):
        self.retData.set_all_key_kwarg(default_enable=False)

        def _digit_approver(value: str):
            return ''.join(re.findall('\d', value))

        def _approver_bool_with_bracket(value: str):
            value = self.sub_regular(r"[一]", "-", value)
            return value
        

        def _space_approver(value: str):
            value = self.sub_regular(r"([a-zA-Z])(\d)", r"\1 \2",value)
            return value

        # 尿液檢查
        self.retData.nicotine_urine.update_kwargs(regex='Nicotine|尼古丁(尿液)')
        self.retData.urine_rbc.update_kwargs(regex='紅血球\(\尿\)')
        self.retData.epithelial_cells.update_kwargs(regex='EPcell|上皮細胞')
        self.retData.casts.update_kwargs(regex='Cast|圓柱體', default='-')
        self.retData.crystals.update_kwargs(regex='Crystal|結晶體', default='-')
        self.retData.urine_other.update_kwargs(regex='Other|其他', default='-', value_approver=[_space_approver] )
        self.retData.bacteria.update_kwargs(regex='Bacteria|細菌', default='-')
        self.retData.ph_value.update_kwargs(regex='PH|酸鹼度反應')
        self.retData.specific_gravity.update_kwargs(regex='S.G.|比重')
        self.retData.urine_protein.update_kwargs(regex='Protein(定性)|^尿蛋白', default='-', value_approver=[_approver_bool_with_bracket])
        self.retData.urine_glucose.update_kwargs(regex='Sugar$|尿糖',  default='-', value_approver=[_approver_bool_with_bracket])
        self.retData.urobilinogen.update_kwargs(regex='Urobilinogen|尿膽素原')
        self.retData.urine_bilirubin.update_kwargs(regex='Bilirubin|尿膽紅素' ,default='-', value_approver=[_approver_bool_with_bracket])
        self.retData.ketone.update_kwargs(regex='Ketone|^酮體',default='-')
        self.retData.leukocyte_esterase.update_kwargs(regex='Leukocyte|白血球脂酶',default='-' , value_approver=[_approver_bool_with_bracket])
        self.retData.nitrite.update_kwargs(regex='Nitrite|^亞硝酸鹽',default='-')
        self.retData.transparency.update_kwargs(regex='Appearance|外觀',value_approver=[approver_add_space_before_uppercase])
        self.retData.occult_blood.update_kwargs(regex='O.B|尿液潛血化學法', default='-', value_approver=[_approver_bool_with_bracket])
        self.retData.urine_wbc.update_kwargs(regex='白血球\(\尿\)')
       
        #肝功能檢查
        self.retData.sgot.update_kwargs(regex='SGOT|麩草酸轉胺基梅')
        self.retData.sgpt.update_kwargs(regex='SGPT|丙酮轉胺基脢' , value_approver=[_digit_approver])
        self.retData.total_bilirubin.update_kwargs(regex='T-BIL|膽紅素總量')
        self.retData.direct_bilirubin.update_kwargs(regex='D-BIL|直接膽紅素')
        self.retData.gamma_gt.update_kwargs(regex='r-GT|麩氨轉酸脢')
        self.retData.albumin.update_kwargs(regex='Albumin|白蛋白')
        self.retData.globulin.update_kwargs(regex='Globulin|球蛋白')
        

        # 肝炎檢查
        self.retData.hbsag.update_kwargs(regex='HBsAg|B型肝炎表面抗原')
        self.retData.hbeag.update_kwargs(regex='HBeAg|B型肝炎e抗原檢查')
        

        # 癌症篩選
        self.retData.alphafetoprotein.update_kwargs(regex='AFP|^胎兒蛋白')
        

        # 腎功能檢查
        self.retData.bun.update_kwargs(regex='BUN|血中尿素氮')
        self.retData.creatinine.update_kwargs(regex='Creatinine|肌酸酐')
        

        # 尿酸檢查
        self.retData.uric_acid.update_kwargs(regex='UA|尿酸')
        

        # 血脂肪檢查
        self.retData.total_cholesterol.update_kwargs(regex='Cholesterol|總膽固醇')
        self.retData.triglyceride.update_kwargs(regex='Triglycerol(TG)|三酸甘油脂')
        self.retData.hdl_c.update_kwargs(regex='HDLCholesterol|高密度脂蛋白-膽固醇')
        

        # 血糖檢查
        self.retData.ac_sugar.update_kwargs(regex='SugarAC$|血糖-飯前')
        self.retData.hba1c.update_kwargs(regex='HbA1C$|醣化血紅素')
        
        # 血液常規檢查
        self.retData.rbc.update_kwargs(regex='紅血球計數')
        self.retData.wbc.update_kwargs(regex='白血球計數')
        self.retData.hemoglobin.update_kwargs(regex='Hb$|血色素')
        self.retData.hematocrit.update_kwargs(regex='Ht|血球比容測定')
        self.retData.platelet.update_kwargs(regex='Plateletcount|血小板計數')
        self.retData.neutrophils_percent.update_kwargs(regex='Seg.|中性球數')
        self.retData.lymphocytes_percent.update_kwargs(regex='Lympocyte|淋巴球數')
        self.retData.monocytes_percent.update_kwargs(regex='Monocyte|單核球數')
        self.retData.eosinophils_percent.update_kwargs(regex='Eosinophil|嗜酸性球數')
        self.retData.basophils_percent.update_kwargs(regex='Basophil|嗜鹼性球數')

        # 甲狀腺功能檢查
        self.retData.t4.update_kwargs(regex='T4|四碘甲狀腺素生化法')
        self.retData.tsh.update_kwargs(regex='TSH|甲狀腺刺激素免疫分析')

        
        
    def _parse_update_category(self, target_ocr_data: dict):
        # 定位 "檢驗結果" 的標題位置
        value_title_label, value_title_anchor = self.get_keyword(
            target_ocr_data, *self.entire_box, '檢驗結果'
        )
        self.syslogger.info(f'\n[{self.img_name}] value_title_label: {value_title_label}, value_title_anchor: {value_title_anchor}')

        if value_title_label is None:  # 如果未找到 "檢驗結果"，直接返回
            return

        # 擴大範圍
        value_title_anchor.move_x(-value_title_anchor.wid * 0.25)

        # 處理檢驗項目
        item_box = (0, self.hgt, 0, value_title_anchor.lft)  # 左側區域範圍，用於檢測項目名稱
        for key, keyinfo in self.retData.get_all_api_key_and_info():
            if keyinfo.regex is None:  # 如果該項目未設置正則表達式，跳過
                continue

            self.syslogger.info(f'\n[{self.img_name}] Processing key: {key}, keyinfo: {keyinfo}')

            # 查找檢測項目名稱
            item_label, item_label_anchor = self.get_keyword(
                target_ocr_data, *item_box, keyinfo.regex)
            self.syslogger.info(f'\n[{self.img_name}] item_label: {item_label}, item_label_anchor: {item_label_anchor}')

            if item_label is not None:  # 如果找到該檢測項目名稱
                keyinfo.default_enable = True  # 將該項目標記為啟用

                if key not in ["transparency", "hbeag", "hbsag"]:
                    new_item_box = (
                        item_label_anchor.btm, 
                        item_label_anchor.btm + item_label_anchor.hgt,
                        item_label_anchor.lft - item_label_anchor.wid / 10,
                        item_label_anchor.rgt
                    )
                    next_item_label, next_item_label_anchor = self.get_keyword(target_ocr_data, *new_item_box, r".+")
                    
                    # TODO: 優化
                    if next_item_label is not None:
                        value_box = (
                            item_label_anchor.top, 
                            item_label_anchor.btm, 
                            value_title_anchor.lft, 
                            value_title_anchor.rgt
                        )
                    else:
                        value_box = (
                            item_label_anchor.top, 
                            next_item_label_anchor.top, 
                            value_title_anchor.lft, 
                            value_title_anchor.rgt
                        )
                        
                # TODO: 優化
                else:
                    value_box = (
                        item_label_anchor.top,
                        item_label_anchor.btm, 
                        value_title_anchor.lft, 
                        value_title_anchor.rgt
                    )
                
                values = self.get_keywords(target_ocr_data, *value_box, '.+')
                exam_value_str, exam_value_anchor = self.merge_boxes(values)
                
                if exam_value_str:  # 如果找到值
                    keyinfo.value = exam_value_str  # 更新檢測項目的值
                    keyinfo.rectangle = Rectangle.from_anchor(
                        exam_value_anchor)  # 更新檢測項目的位置框
                    self.syslogger.info(f'\n[{self.img_name}] Final value for {key}: {keyinfo.value}')


   

    def _parse_name(self, target_ocr_data, *box) -> str:
        matched_str, matched_anchor = self.get_keyword(target_ocr_data, *box, "姓名(.*)")
        self.syslogger.debug(f"\n[{self.img_name}] _parse_name1: matched_str: {matched_str}, matched_anchor: {matched_anchor}")

        if matched_str is not None:
            matched_anchor.move_y(-10)
            matched_anchor.move_x(matched_anchor.wid)
            matched_anchor.wid = matched_anchor.wid * 3

            value_str, value_anchor = self.get_keyword(target_ocr_data, *matched_anchor.boundary, r".+")

            self.retData.name_of_examinee.value = value_str
            self.retData.name_of_examinee.rectangle = Rectangle.from_anchor(value_anchor)

    

    
    def _parse_birth(self, target_ocr_data, *box) -> Optional[datetime]:
         # 西元年yyyy/mm/dd(去斜線)
        self.retData.birth_of_examinee.update_kwargs(value_approver=[approver_ce_date_split1])
        
        matched_str, matched_anchor = self.get_keyword(target_ocr_data, *box, "出生日期(.*)")
        self.syslogger.debug(f"\n[{self.img_name}] matched_str: {matched_str}, matched_anchor: {matched_anchor}")
        if matched_str is not None:
           
            matched_anchor.move_y(-10)
            matched_anchor.move_x(matched_anchor.wid)
            matched_anchor.wid = matched_anchor.wid * 3

            value_str, value_anchor = self.get_keyword(target_ocr_data, *matched_anchor.boundary, r".+")

            self.retData.birth_of_examinee.value =  value_str
            self.retData.birth_of_examinee.rectangle = Rectangle.from_anchor(value_anchor)
        
    def _parse_gender(self, target_ocr_data, *box) -> str:
        matched_str, matched_anchor = self.get_keyword(target_ocr_data, *box, "性別(.*)")
        self.syslogger.debug(f"\n[{self.img_name}] _parse_gender: matched_str: {matched_str}, matched_anchor: {matched_anchor}")
        if matched_str is not None:

            matched_anchor.move_y(-10)
            matched_anchor.move_x(matched_anchor.wid)
            matched_anchor.wid = matched_anchor.wid * 3

            value_str, value_anchor = self.get_keyword(target_ocr_data, *matched_anchor.boundary, r".+")

            self.retData.gender_of_examinee.value = value_str
            self.retData.gender_of_examinee.rectangle = Rectangle.from_anchor(value_anchor)
    
    def _parse_exam_date(self, target_ocr_data, *box) -> str:
        # 西元年yyyy/mm/dd(去斜線)
        self.retData.exam_date.update_kwargs(value_approver=[approver_ce_date_split1])
        _matched_str, _matched_anchor = self.get_keyword(target_ocr_data, *box, r"檢查日期(.*)")
        self.syslogger.debug(f"\n[{self.img_name}] _parse_exam_date: matched_str: {_matched_str}, matched_anchor: {_matched_anchor}")
        
        if _matched_str is not None:
            if len(_matched_str) > 0:
                # 代表一個框, 已經撈到 value 了
                matched_str, matched_anchor = _matched_str, _matched_anchor
            else:
                # 代表兩個框, 要往右撈 value
                _matched_anchor.move_y(-_matched_anchor.hgt / 2)
                _matched_anchor.move_x(_matched_anchor.wid*0.25)
                matched_str, matched_anchor = self.get_keyword(target_ocr_data, *_matched_anchor.boundary, r".+")

            self.retData.exam_date.value =  matched_str
            self.retData.exam_date.rectangle = Rectangle.from_anchor(matched_anchor)