from pydantic import Field

from . import InitChar
from .load_json import character_table, skill_table, battle_equip_table
from src.plugins.ArkDamage.ArkDamage.dmg_cal.model.battle_equip_data import UniequipData
from src.plugins.ArkDamage.ArkDamage.dmg_cal.model.char_data import CharData
from src.plugins.ArkDamage.ArkDamage.dmg_cal.model.skill_data import SkillData

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
        'def': 0,
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
    CharData: CharData
    PhaseData = Field(dict, alias='phaseData', title='干员阶段数据')
    attributesKeyFrames = Field(dict, alias='attributesKeyFrames', title='属性关键帧')
    buffs = Field(dict, alias='buffs', title='buff数据')
    buffList = Field(dict, alias='buffList', title='buff列表')
    SkillData: SkillData
    UniEquipData: UniequipData

    def __init__(self, base_char_info: InitChar):
        super().__init__()
        self.CharData = CharData(character_table[base_char_info.char_id])
        phase = base_char_info.phase
        self.PhaseData = self.CharData.phases[phase]
        self.attributesKeyFrames = {}
        self.buffs = init_buff_frame()
        self.buffList = {}

        self.SkillData = SkillData(skill_table[base_char_info.skill_id])
        self.UniEquipData = UniequipData(
            battle_equip_table[base_char_info.equip_id]) if base_char_info.equip_id else None
