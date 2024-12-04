import re

def approver_digit_range(value: str):
    '''格式: {數字}-{數字} | {數字}'''
    return ''.join(re.findall('\d+-\d+|\d+', value))

def approver_float_number(value: str):
    '''格式: {含有小數的數字}'''
    match = re.search('\d+(\.\d+)?', value)
    if match:
        return match.group()
    return None

def approver_number(value: str):
    '''格式: {純數字}'''
    match = re.search('\d+', value)
    if match:
        return match.group()
    return None

def approver_not_found(value):
    '''將 NotFound 轉換為 NOT FOUND'''
    if 'notfoun' in value.strip().lower().replace(' ', '').replace('-', ''):
        return 'NOT FOUND'
    return value

def approver_not_found2(value):
    '''將 NotFound 轉換為 Not found'''
    if 'notfoun' in value.strip().lower().replace(' ', '').replace('-', ''):
        return 'Not found'
    return value

def approver_not_found3(value):
    '''將 NotFound 轉換為 Not Found'''
    if 'notfoun' in value.strip().lower().replace(' ', '').replace('-', ''):
        return 'Not Found'
    return value

def approver_none_found(value):
    '''將 Nonefound 轉換為 None found'''
    if 'nonefoun' in value.strip().lower().replace(' ', '').replace('-', ''):
        return 'None found'
    return value

def approver_only_sub_or_plus_with_parentheses(value):
    '''只能包含 () +-'''
    value = re.sub('[^()\-+]', '', value)
    if value == '()' or value == '':
        return None
    return value

def approver_parentheses_closed(value):
    ''' 確保 () 閉合, 若無閉合嘗試閉合, 否則移除該字元 e.g. "(-" -> "(-)", ")" -> "" '''
    stack = []
    res = ''
    
    for char in value:
        if char == ')':
            if len(stack) == 0 or stack[-1] != '(':
                continue
            else:
                stack.pop()
        elif char == '(':
            stack.append(char)
        res += char
        
    while len(stack) != 0:
        if stack.pop() == '(':
            res += ')'
            
    return res

def approver_parentheses_and_numbers(value):
    '''([+-]){1,5}numbers, e.g. (++++)25, 不符合回傳 None'''
    match = re.match('(\([+-]{1,5}\)\d+)', value)
    if match:
        return match.group(1)
    return None

def approver_numbers_and_parentheses(value):
    """number/float([+-]){1,5}, e.g. 0.096(+)"""
    match = re.match("(\d+(\.\d+)?\([+-]{1,5}\))", value)
    if match:
        return match.group(1)
    return None

def approver_neg_pos(value: str):
    # 只會有 Negative 跟 Positive
    if 'negative' in value.lower().strip():
        return 'Negative'
    if 'positive' in value.lower().strip():
        return 'Positive'
    return value

def approver_add_space_before_uppercase(value: str):
    """
    在字串中的每個大寫前加上空格, 若連續出現大寫則不處理
        "LightYellow" -> "Light Yellow"
        "YELLOW" -> "YELLOW"
        "rGT" -> "r GT"
        "RgT" -> "Rg T"
    """
    result = ""
    trans_upper = False
    for char in value:
        if char.isupper() and len(result) > 0 and trans_upper:
            result += ' '
            trans_upper = False
        if char.islower():
            trans_upper = True
        result += char
    return result

def approver_roc_date_to_ce_date1(value: str):
    try:
        year, month, day = value.split("/")
        year = re.sub("\D", "", year)
        month = re.sub("\D", "", month)
        day = re.sub("\D", "", day)
        return f"{int(year) + 1911}{int(month):02d}{int(day):02d}"
    except Exception as e:
        return None
    
def approver_roc_date_to_ce_date2(value: str):
    try:
        year, month, day = value.split(".")
        year = re.sub("\D", "", year)
        month = re.sub("\D", "", month)
        day = re.sub("\D", "", day)
        return f"{int(year) + 1911}{int(month):02d}{int(day):02d}"
    except Exception as e:
        return None

def approver_ce_date_split1(value: str):
    """
    2024/11/14 -> 20241114
    2024/1/1 -> 20240101
    """
    try:
        year, month, day = value.split("/")
        year = re.sub("\D", "", year)
        month = re.sub("\D", "", month)
        day = re.sub("\D", "", day)
        return f"{int(year)}{int(month):02d}{int(day):02d}"
    except Exception as e:
        return None

def approver_ce_date_split2(value: str):
    """
    2024.11.14 -> 20241114
    2024.1.1 -> 20240101
    """
    try:
        year, month, day = value.split(".")
        year = re.sub("\D", "", year)
        month = re.sub("\D", "", month)
        day = re.sub("\D", "", day)
        return f"{int(year)}{int(month):02d}{int(day):02d}"
    except Exception as e:
        return None
