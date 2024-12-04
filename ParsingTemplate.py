import re
import json
from typing import Dict, List, Optional, Tuple

import numpy as np

from .AnchorSpec import AnchorSpec
from scipy.cluster.hierarchy import fcluster, linkage


class ParsingTemplate:
    
    @staticmethod
    def get_formatted_json(data):
        # 主要是方便想要在 log 中 pring json 格式資料時可以比較漂亮方便閱讀
        return json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True)
    
    def get_handover_metadata(self):
        '''
        提供需要遺留給下一個處理案件的資料, 預設回傳為空字典 {}
            情境: 如果有案件有兩頁以上, 後續頁面需要前面頁面的資訊輔助辨識, 可進行override, 傳給下一張影像
        後續案件可在 __inint__(..., result.key) 取得
        
        注意: 建議使用 result 需自行判斷是否為同一個案件
        '''
        return {}
    
    def remove_width_height(self, ocr_return):
        ocr_data = ocr_return.copy()
        del ocr_data["0"]
        del ocr_data["1"]

        return ocr_data

    def findall_regular(self, regular, word):
        return re.findall(regular, word)
        
    def sub_regular(self, regular, replace, word):
        return re.sub(regular, replace, word)
    
    def check_text_in_box(self, text_pos, box_top, box_btm, box_left, box_right) -> bool:
        """
        input: 
            text_pos = [topLeft_x, topLeft_y, topRight_x, topRight_y, btmRight_x, btmRight_y, btmLeft_x, btmLeft_y]

            coordinate:
                    (0, 0)   -----------    (width, 0)
                            |           |
                            |           |
                            |           |
                (0, height)  -----------    (width, height)

            box:
                               box_top
                             -----------
                            |           |
                 box_left   |           |  box_right
                            |           |
                             -----------
                              box_right

            text_pos:
            topLeft (x, y)   -----------    topRight (x, y)
                            |           |
                            |           |
                            |           |
            btmLeft (x, y)   -----------    btmRight (x, y)
            
        output:
            True or False
        """
        # 這裡還是去撈左上角座標不使用 AnchorSpec 然後取 top & lft, 因為 AnchorSpec 的 top, lft 不只會考慮左上角
        topleft_x, topleft_y = text_pos[0], text_pos[1]
        
        if (box_left < topleft_x < box_right) and (box_top < topleft_y < box_btm):
            return True
        else:
            return False

    def get_keyword(self, ocr_dict: Dict[str, Tuple[str, List[int]]], box_top, box_btm, box_left, box_right, regular) -> Tuple[Optional[str], Optional[AnchorSpec]]:
        """
        input: 
            ocr_dict =
            {
                "2": ["中文", [topLeft_x, topLeft_y, topRight_x, topRight_y, bottomRight_x, bottomRight_y, bottomLeft_x, bottomLeft_y]],
                "3": [...],
                ...
            }
            box_top, box_btm, box_left, box_right: 上下左右邊界座標
            regular: 正則表達式

            先根據 box_* 框出一個上下左右的區域, 查看在這區域內的字串, 第一個符合指定正則的字串, 將 match 到的部分 join 之後與 anchor 一起回傳
            
        output:
            沒找到: None, None
            有找到: matched_str, matched_str_anchor
        """
        box = (box_top, box_btm, box_left, box_right)

        for index, value in ocr_dict.items():
            string = value[0]
            pos = value[1]

            if self.check_text_in_box(pos, *box):
                match_result = self.findall_regular(regular, string)

                if match_result != []:
                    match_word = "".join(match_result)
                    return match_word, AnchorSpec(pos)

        return None, None
    
    def get_keywords(self, ocr_dict: Dict[str, Tuple[str, List[int]]], box_top, box_btm, box_left, box_right, regular) -> List[Tuple[str, AnchorSpec]]:
        """
        input: 
            ocr_dict =
            {
                "2": ["中文", [topLeft_x, topLeft_y, topRight_x, topRight_y, bottomRight_x, bottomRight_y, bottomLeft_x, bottomLeft_y]],
                "3": [...],
                ...
            }
            box_top, box_btm, box_left, box_right: 上下左右邊界座標
            regular: 正則表達式

            先根據 box_* 框出一個上下左右的區域, 查看在這區域內的字串, [所有] 符合指定正則的字串, 將 match 到的部分 join 之後與 anchor 一起回傳
            
        output:
            沒找到: []
            有找到: [
                        [matched_str1, matched_str1_anchor], 
                        [matched_str2, matched_str2_anchor], 
                        ...
                    ]
        """
        box = (box_top, box_btm, box_left, box_right)
        ret = []
        
        for index, value in ocr_dict.items():
            string = value[0]
            pos = value[1]

            if self.check_text_in_box(pos, *box):
                match_result = self.findall_regular(regular, string)

                if match_result != []:
                    match_word = "".join(match_result)
                    ret.append((match_word, AnchorSpec(pos)))

        return ret
    
    def map_closest_value_of_title_by_y_axis(self, title_anchor: AnchorSpec , candidate_values: List[Tuple[str, AnchorSpec]], thresh=20) -> Tuple[Optional[str], Optional[AnchorSpec]]:
        """
        input:
            title_anchor: 測驗項目標題的 anchor
            candidate_values: 複數個 value, 格式: [
                                                    [matched_str1, matched_str1_anchor], 
                                                    [matched_str2, matched_str2_anchor], 
                                                    ...
                                                ]
            thresh: title 的 ymid 跟 value 的 ymid 的最大差值, 超過即不承認
        """
        # 計算每個 value 的 ymid 跟 title 的 ymid 的差值
        y_diff_to_title = np.array([abs(anchor.ymid - title_anchor.ymid) for string, anchor in candidate_values])
        # 找出差異最小的 idx
        min_idx = np.argmin(y_diff_to_title)
        
        if y_diff_to_title[min_idx] < thresh:
            # 確認差異值沒有 > thresh
            return candidate_values[min_idx]
        else:
            # 超過 thresh 不算數
            return None, None
        
    def merge_boxes(self, boxes: List[Tuple[str, AnchorSpec]]) -> Tuple[str, AnchorSpec]:
        """合併傳入的 Text Box 合併為一個 Box, 順序依照傳入進行合併

        Args:
            boxes (List[Tuple[str, AnchorSpec]]): 需要合併的 Text Box

        Returns:
            Tuple[str, AnchorSpec]: 合併後的TextBox
        """
        if not boxes:
            return None
        lable = boxes[0][0]
        spec = boxes[0][1]
        for idx in range(1, len(boxes)):
            merge = boxes[idx]
            lable += merge[0]
            spec.merge(merge[1])
        return (lable, spec)
        
    def merge_horizontal_text_boxes(self, ocr_dict: Dict[str, Tuple[str, List[int]]], top, btm, lft, rgt, y_range) -> Dict[str, Tuple[str, List[int]]]:
        """
        input:
        {
            '29': ['病房費', [163, 757, 305, 754, 306, 801, 163, 803]], '30': ['(Ward', [405, 753, 526, 753, 525, 797, 406, 799]],
            '20': ['藥費', [165, 646, 256, 643, 259, 693, 164, 696]],'21': ['(Medicine',[405, 643, 621, 645, 621, 691, 405, 690]],
        ...
        }
        上面的 2 行其實都應該是同一個 block, 但是被 OCR 切分了, 因此手動把相近 y-axis 的 block 做橫向的合併
        合併後的座標是取最聯集(最大)的 block

        output:
        {
            '20': ['藥費(Medicine', [165, 643, 621, 643, 259, 693, 405, 696]],
            '29': ['病房費(Ward', [163, 753, 526, 753, 306, 801, 406, 803]],
            ...
        }
        """
        ret_dict = {}
        target_dict = {}

        # 把原本的 dict 根據邊界 區分成要合併的 block 跟不用合併的 block
        for idx, val in ocr_dict.items():
            string = val[0]
            pos = val[1]

            if string in ["width", "height"]:
                continue

            if self.check_text_in_box(pos, top, btm, lft, rgt):
                target_dict[idx] = [string, pos]
            else:
                ret_dict[idx] = [string, pos]

        # 實際開始合併
        combine_dict = {}
        target_dict = {k: v for k, v in sorted(target_dict.items(), key=lambda item: (item[1][1][0], item[1][1][1]))}   # 以靠左, 靠上排序
        # self.syslogger.debug(f"\ntarget_dict = {target_dict}")

        done_idx = []
        for idx1, val1 in target_dict.items():
            cur_string = val1[0]
            cur_pos = AnchorSpec(val1[1])
            cur_y_mid = cur_pos.ymid
            # self.syslogger.debug(f"\ncur_string = {cur_string}, cur_y_mid = {cur_y_mid}")

            string = ""
            pos = None

            if idx1 in done_idx:
                 continue

            for idx2, val2 in target_dict.items():
                tar_string = val2[0]
                tar_pos = AnchorSpec(val2[1])

                if idx2 in done_idx:
                    continue

                tar_y_mid = tar_pos.ymid
                # self.syslogger.debug(f"\n       tar_string = {tar_string}, tar_y_mid = {tar_y_mid}")
                
                if cur_y_mid - y_range < tar_y_mid < cur_y_mid + y_range:
                    string += tar_string
                    pos = [
                            min(cur_pos.lft, tar_pos.lft),
                            min(cur_pos.top, tar_pos.top),
                            max(cur_pos.rgt, tar_pos.rgt),
                            min(cur_pos.top, tar_pos.top),
                            max(cur_pos.rgt, tar_pos.rgt),
                            max(cur_pos.btm, tar_pos.btm),
                            min(cur_pos.lft, tar_pos.lft),
                            max(cur_pos.btm, tar_pos.btm),
                            ] if pos is not None else tar_pos.address
                    # self.syslogger.debug(f"\n       concate! string = {string}")

                    done_idx.append(idx2)
            
            combine_dict[idx1] = [string, pos]
            # self.syslogger.debug(f"\n       combine_dict = {combine_dict}")

        ret_dict.update(combine_dict)
        ret_dict = {k: ret_dict[k] for k in sorted(ret_dict, key=int)}   # 根據 key 做排序
        # ret_dict = {k: v for k, v in sorted(ret_dict.items(), key=lambda item: (item[1][1][1], item[1][1][0]))}   # 以靠上, 靠左排序
        return ret_dict

    def group_ocr_anchor_list(self, anchor_list: List[Tuple[str, AnchorSpec]],
                                    threshold=15,
                                    method='average',
                                    group_way='y') \
                -> List[List[Tuple[str, AnchorSpec]]]:
        """
        將近似 x|y 軸 分群為同一行/群, 因此由二維陣列轉為三維陣列
        採用 scipy 實現 Hierarchical Clustering(層次聚類), 由於樹結構使用 threshold(x|y軸距離) 進行分群, 因此不需要指定幾組 
        可以參考 youtube 了解原理 https://youtube.com/watch?v=lNfE-wPsMPw

        Args:
            anchor_list (List[Tuple[str, AnchorSpec]]): OCR辨識框
            threshold (int, optional): 區分區間, 為行與行之間大約的間距. Defaults to 15.
            method (str, optional): 分群方法
                想要有連續性 選 "single" 俗稱 min linkage, 
                想要強調分隔, 選"complete" 俗稱 max linkage, 
                綜合兩者選"average".
            group_way ('y' | 'x'): 使用 y 軸或是 x 軸做區隔
            
        Returns:
            grouped_anchor_list (List[List[Tuple[str, AnchorSpec]]]): 分組好的 OCR辨識框

        Notes:
            如果 從 get_keywords 抓取數值後, 其中容易有多的方框, 可以使用此方法分群後, 再針對每一行進行額外處理
        
        Example:
            以分群示範, 只取分群後每行最後一個矩形框
            
            ```
            values = self.get_keywords(target_ocr_data, *value_box, '.+')
            values_grouped = self.group_ocr_anchor_list(values)
            for idx, same_row_values in enumerate(values_grouped): 
                # 此案例只取最後一個方框, 替換成想要的操作
                if len(same_row_values) > 1:
                    values_grouped[idx] = [same_row_values[-1]]
            # 還原為 anchors 
            values = [same_row_values[0] for same_row_values in values_grouped]
            ```
        """
        if len(anchor_list) == 0:
            return []
        if len(anchor_list) == 1:
            return [anchor_list]
        
        if group_way.lower() == 'y':
            # 建立 y 軸中心點
            way_values_list = [a[1].ymid for a in anchor_list]
            final_sort_method = lambda r:r[1].xmid
        elif group_way.lower() == 'x':
            # 建立 x 軸中心點
            way_values_list = [a[1].xmid for a in anchor_list]
            final_sort_method = lambda r:r[1].ymid
        else:
            raise Exception(f'Unknow Group way: {group_way}')
        
        # 為了符合 linkage 需求整理成二維陣列
        way_values = np.array(way_values_list).reshape(-1, 1)
        
        # 層次聚類, 建立樹
        Z = linkage(way_values, method=method)
        labels = fcluster(Z, t=threshold, criterion='distance')
        
        # 分組
        groups = {}
        for anchor, label in zip(anchor_list, labels):
            if label not in groups:
                groups[label] = []
            groups[label].append(anchor)
        
        # 每一組進行組內排序
        for key in groups:
            groups[key].sort(key=final_sort_method)
            
        return list(groups.values())
        