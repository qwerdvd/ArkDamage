from typing import Union

from pydantic import BaseModel


class TagDesc(BaseModel):
    type: str
    displaytext: str
    explain: str


class Tags(BaseModel):
    crit: Union[TagDesc, None]
    cond: Union[TagDesc, None]
    ranged_penalty: Union[TagDesc, None]
    token: Union[TagDesc, None]
    stack: Union[TagDesc, None]
    noblock: Union[TagDesc, None]
    cannon: Union[TagDesc, None]
    buff: Union[TagDesc, None]
    warmup: Union[TagDesc, None]
    thorns_ranged: Union[TagDesc, None]
    rosmon_double: Union[TagDesc, None]
    archet: Union[TagDesc, None]
    chen: Union[TagDesc, None]
    charge: Union[TagDesc, None]
    annie: Union[TagDesc, None]
    pallas: Union[TagDesc, None]
    water: Union[TagDesc, None]
    equip: Union[TagDesc, None]
    far: Union[TagDesc, None]
    block: Union[TagDesc, None]
    freeze: Union[TagDesc, None]
    ling_fusion: Union[TagDesc, None]
    od_trigger: Union[TagDesc, None]
    melee: Union[TagDesc, None]
    short_mode: Union[TagDesc, None]
    reed2_fast: Union[TagDesc, None]


class CondInfo(BaseModel):
    pass


class Char(BaseModel):
    pass


class Options(BaseModel):
    tags: Tags
    cond_info: CondInfo
    char: Char
