from typing import List, Union

from pydantic import BaseModel


class BlackboardData(BaseModel):
    key: str
    value: Union[str, int, float, bool]


class UnlockCondition(BaseModel):
    phase: int
    level: int


class CandidatesData(BaseModel):
    additionalDescription: str
    unlockCondition: UnlockCondition
    requiredPotentialRank: int
    blackboard: List[BlackboardData]
    overrideDescripton: Union[str, None]
    prefabKey: Union[str, None]
    rangeId: Union[str, None]


class Candidates(BaseModel):
    candidates: Union[List[CandidatesData], None]


class UniequipPartData(BaseModel):
    resKey: Union[str, None]
    target: str
    isToken: bool
    addOrOverrideTalentDataBundle: dict
    overrideTraitDataBundle: dict


class CharPhaseData(BaseModel):
    equipLevel: int
    parts: List[UniequipPartData]
    attributeBlackboard: Union[List[BlackboardData], None]
    tokenAttributeBlackboard: Union[dict, None]


class UniequipData(BaseModel):
    phases: List[CharPhaseData]

    def __init__(self, battle_equip_data: dict):
        super().__init__(**battle_equip_data)

    def get(self, key: str):
        return getattr(self, key)
