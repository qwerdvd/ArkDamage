from typing import Union

from . import InitChar
from .load_json import character_table, skill_table, battle_equip_table
from .model.battle_equip_data import UniequipData
from .model.char_data import CharacterData, CharPhaseData
from .model.skill_data import SkillData, SkillLevelData

AttributeKeys = [
    'atk',
    'attackSpeed',
    'baseAttackTime',
    'baseForceLevel',
    'blockCnt',
    'cost',
    'defense',
    'hpRecoveryPerSec',
    'magicResistance',
    'massLevel',
    'maxDeckStackCnt',
    'maxDeployCount',
    'maxHp',
    'moveSpeed',
    'respawnTime',
    'spRecoveryPerSec',
    'tauntLevel',
]


def init_buff_frame():
    return {
        'atk_scale': 1,
        'def_scale': 1,
        'heal_scale': 1,
        'damage_scale': 1,
        'maxTarget': 1,
        'times': 1,
        'edef': 0,  # 敌人防御 / 魔抗
        'edef_scale': 1,
        'edef_pene': 0,
        'edef_pene_scale': 0,
        'emr_pene': 0,  # 无视魔抗
        'emr': 0,
        'emr_scale': 1,
        'atk': 0,
        'defense': 0,
        'attackSpeed': 0,
        'maxHp': 0,
        'baseAttackTime': 0,
        'spRecoveryPerSec': 0,
        'spRecoverRatio': 0,
        'spRecoverIntervals': [],
        'applied': {},
    }


class Attributes:
    def __init__(self):
        super().__init__()
        for key in AttributeKeys:
            self.__setattr__(key, 0)


class Character(Attributes):
    CharData: CharacterData
    PhaseData: CharPhaseData
    SkillData: SkillData
    LevelData: SkillLevelData
    UniEquipData: Union[UniequipData, None]
    skillId: str = ''
    blackboard: dict = {}
    attributesKeyFrames: dict = {}
    buffs: dict = {}
    buffList: dict = {}
    displayNames: dict = {}

    def __init__(self, char_info: InitChar):
        super().__init__()
        self.CharData = CharacterData(character_table[char_info.char_id])
        phase = char_info.phase
        self.PhaseData = self.CharData.phases[phase]
        self.attributesKeyFrames = {}
        self.buffs = init_buff_frame()
        self.buffList = {}
        self.SkillData = SkillData(skill_table[char_info.skill_id])
        self.LevelData = self.SkillData.levels[char_info.skillLevel]
        if char_info.equip_id in battle_equip_table.keys():
            self.UniEquipData = UniequipData(
                battle_equip_table[char_info.equip_id])
        else:
            self.UniEquipData = None
