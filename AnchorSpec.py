from typing import Optional, Tuple

from .Serialization import *


class AnchorSpec:
    def __init__(self, input_arg=None, **kwargs):

        self.top = None
        self.btm = None
        self.lft = None
        self.rgt = None

        if isinstance(input_arg, list) or isinstance(input_arg, tuple):
            self.top = min(input_arg[1], input_arg[3])
            self.btm = max(input_arg[5], input_arg[7])
            self.lft = min(input_arg[0], input_arg[6])
            self.rgt = min(input_arg[2], input_arg[4])
        elif ("top", "btm", "lft", "rgt").issubset(kwargs.keys()):
            self.top = kwargs["top"]
            self.btm = kwargs["btm"]
            self.lft = kwargs["lft"]
            self.rgt = kwargs["rgt"]
        else:
            raise Exception(f"illegal input ,input_args:[type = {type(
                input_arg)}][value = {input_arg}],kwargs:[value = {kwargs}]")

    def merge(self, other: 'AnchorSpec'):
        if other is None:
            return
        self.lft = min(other.lft, self.lft)
        self.rgt = max(other.rgt, self.rgt)
        self.top = min(other.top, self.top)
        self.btm = max(other.btm, self.btm)
