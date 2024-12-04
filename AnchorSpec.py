from typing import Optional, Tuple

from .Serialization import *

class AnchorSpec:
    def __init__(self, input_arg=None, **kwargs):
        """
        input_arg = [topLeft_x, topLeft_y, topRight_x, topRight_y, bottomRight_x, bottomRight_y, bottomLeft_x, bottomLeft_y] 或 tuple 版本
                        0          1           2           3             4              5              6             7

        kwargs = {"top": 1, "btm": 2, "lft": 3, "rgt": 4}        

        """
        self.top = None
        self.btm = None
        self.lft = None
        self.rgt = None
        
        if isinstance(input_arg, list) or isinstance(input_arg, tuple):
            self.top = min(input_arg[1], input_arg[3])
            self.btm = max(input_arg[5], input_arg[7])
            self.lft = min(input_arg[0], input_arg[6])
            self.rgt = max(input_arg[2], input_arg[4])
        elif {"top", "btm", "lft", "rgt"}.issubset(kwargs.keys()):
            self.top = kwargs["top"]
            self.btm = kwargs["btm"]
            self.lft = kwargs["lft"]
            self.rgt = kwargs["rgt"]
        else:
            raise Exception(f"illegal input, input_args: [type={type(input_arg)}][value={input_arg}], kwargs: [value={kwargs}]")

    def move_x(self, x: int):
        self.lft += x
        self.rgt += x
      
    def move_y(self, y: int):
        self.top += y
        self.btm += y 
        
    @property
    def xmid(self) -> int:
        return (self.lft + self.rgt) / 2
    
    @property
    def ymid(self) -> int:
        return (self.top + self.btm) / 2
    
    @property
    def wid(self) -> Optional[int]:
        return self.rgt - self.lft
    
    @wid.setter
    def wid(self, value):
        self.rgt = self.lft + value
    
    @property
    def hgt(self) -> Optional[int]:
        return self.btm - self.top
    
    @hgt.setter
    def hgt(self, value):
        self.btm = self.top + value
        
    @property
    def area(self) -> Optional[int]:
        return self.wid * self.hgt if self.wid is not None and self.hgt is not None else None
    
    @property
    def address(self) -> Tuple[int, int, int, int, int, int, int, int]:
        return (
            self.lft, self.top, 
            self.rgt, self.top, 
            self.rgt, self.btm,
            self.lft, self.btm
        )
    
    @property
    def boundary(self) -> Tuple[int, int, int, int]:
        return (
            self.top,
            self.btm,
            self.lft,
            self.rgt,
        )
        
    def merge(self, other: 'AnchorSpec'):
        if other is None:
            return
        self.lft = min(other.lft, self.lft)
        self.rgt = max(other.rgt, self.rgt)
        self.top = min(other.top, self.top)
        self.btm = max(other.btm, self.btm)

    def __str__(self):
        return s__str__(self)
    
    def __repr__(self):
        # 可以透過 eval 重建
        return s__repr__(self)
