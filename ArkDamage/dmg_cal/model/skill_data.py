from typing import Union, List

from pydantic import BaseModel


class SpData(BaseModel):
    spType: int
    levelUpCost: Union[int, None]
    maxChargeTime: int
    spCost: int
    initSp: int
    increment: float


class BlackboardData(BaseModel):
    key: str
    value: float


class SkillLevelData(BaseModel):
    name: str
    rangeId: Union[str, None]
    description: str
    skillType: int
    durationType: int
    spData: SpData
    prefabId: str
    duration: float
    blackboard: List[BlackboardData]


class SkillData(BaseModel):
    skillId: str
    iconId: Union[str, None]
    hidden: bool
    levels: List[SkillLevelData]

    def __init__(self, skill_data: dict):
        super().__init__(**skill_data)
