from typing import List, Union

from pydantic import Field, BaseModel


class AtomBlackboard(BaseModel):
    key: str
    value: float


class UnlockCondition(BaseModel):
    phase: int
    level: int


class TraitCandidate(BaseModel):
    unlockCondition: UnlockCondition
    requiredPotentialRank: int
    blackboard: List[AtomBlackboard]
    overrideDescripton: Union[str, None]
    prefabKey: Union[str, None]
    rangeId: Union[str, None]
    name: Union[str, None] = Field(default=None)


class CharTraitData(BaseModel):
    candidates: List[TraitCandidate]


class CharAttrKeyFrameData(BaseModel):
    maxHp: int
    atk: int
    defense: int = Field(alias='def')
    magicResistance: float
    cost: int
    blockCnt: int
    moveSpeed: float
    attackSpeed: float
    baseAttackTime: float
    respawnTime: int
    hpRecoveryPerSec: float
    spRecoveryPerSec: float
    maxDeployCount: int
    maxDeckStackCnt: int
    tauntLevel: int
    massLevel: int
    baseForceLevel: int
    stunImmune: bool
    silenceImmune: bool
    sleepImmune: bool
    frozenImmune: bool
    levitateImmune: bool

    def get(self, key: str):
        return getattr(self, key)


class CharAttrKeyFrame(BaseModel):
    level: int
    data: CharAttrKeyFrameData


class CharEvolveCost(BaseModel):
    id: str
    count: int
    type: str


class CharPhaseData(BaseModel):
    characterPrefabKey: str
    rangeId: str
    maxLevel: int
    attributesKeyFrames: List[CharAttrKeyFrame]
    evolveCost: Union[List[CharEvolveCost], None]


class LevelUpCost(BaseModel):
    id: str
    count: int
    type: str


class CharSkillLevelUpCostCond(BaseModel):
    unlockCond: UnlockCondition
    lvlUpTime: int
    levelUpCost: List[LevelUpCost]


class CharSkillData(BaseModel):
    skillId: str
    overridePrefabKey: Union[str, None]
    overrideTokenKey: Union[str, None]
    levelUpCostCond: List[CharSkillLevelUpCostCond]


class TalentCandidate(BaseModel):
    unlockCondition: UnlockCondition
    requiredPotentialRank: int
    prefabKey: str
    name: str
    description: str
    rangeId: Union[str, None]
    blackboard: List[AtomBlackboard]


class CharTalentsData(BaseModel):
    candidates: List[TalentCandidate]


class PotentialAttrModifier(BaseModel):
    attributeType: int
    formulaItem: int
    value: float
    loadFromBlackboard: bool
    fetchBaseValueFromSourceEntity: bool


class PotentialAttributes(BaseModel):
    abnormalFlags: Union[str, None]
    abnormalImmunes: Union[str, None]
    abnormalAntis: Union[str, None]
    abnormalCombos: Union[str, None]
    abnormalComboImmunes: Union[str, None]
    attributeModifiers: List[PotentialAttrModifier]


class CharPotentialAttributes(BaseModel):
    attributes: PotentialAttributes


class CharPotentialData(BaseModel):
    type: int
    description: str
    buff: Union[CharPotentialAttributes, None]
    equivalentCost: Union[int, None]


class CharFavorKeyFrames(BaseModel):
    level: int
    data: CharAttrKeyFrameData


class CharAllSkillLvlup(BaseModel):
    unlockCond: UnlockCondition
    lvlUpCost: List[LevelUpCost]


class CharacterData(BaseModel):
    name: str
    description: str
    canUseGeneralPotentialItem: bool
    canUseActivityPotentialItem: bool
    potentialItemId: str
    activityPotentialItemId: Union[str, None]
    nationId: str
    groupId: Union[str, None]
    teamId: Union[str, None]
    displayNumber: str
    tokenKey: Union[str, None]
    appellation: str
    position: str
    tagList: List[str]
    itemUsage: str
    itemDesc: str
    itemObtainApproach: str
    isNotObtainable: bool
    isSpChar: bool
    maxPotentialLevel: int
    rarity: int
    profession: str
    subProfessionId: str
    trait: Union[CharTraitData, None]
    phases: List[CharPhaseData]
    skills: List[CharSkillData]
    talents: List[CharTalentsData]
    potentialRanks: List[CharPotentialData]
    favorKeyFrames: List[CharFavorKeyFrames]
    allSkillLvlup: List[CharAllSkillLvlup]
    has_trait: bool = Field(default=False)

    def __init__(self, char_dict: dict):
        super().__init__(**char_dict)

    def get(self, key: str):
        return getattr(self, key) if hasattr(self, key) else None
