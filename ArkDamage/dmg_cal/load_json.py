import json

from .RESOURCE_PATH import DPS_ANIM_PATH, DPS_OPTIONS_PATH, DPS_SPECIALTAGS_PATH, \
    CHARACTER_TABLE_PATH, UNIEQUIP_TABLE_PATH, BATTLE_EQUIP_TABLE_PATH, SKILL_TABLE_PATH, CHARACTERID_CHNAME_MAP_PATH, \
    CHEQUIPNAME_TO_EQUIPID_MAP_PATH, CHSKILLNAME_TO_SKILLID_MAP_PATH

resVersion = "23-01-30-14-05-02-06c33f"


def load():
    with open(CHARACTERID_CHNAME_MAP_PATH, "r", encoding="utf8") as fp:
        CharacterId_and_chName_data = json.load(fp)

    with open(CHEQUIPNAME_TO_EQUIPID_MAP_PATH, "r", encoding="utf8") as fp:
        chEquipName_to_EquipId_data = json.load(fp)

    with open(CHSKILLNAME_TO_SKILLID_MAP_PATH, "r", encoding="utf8") as fp:
        chSkillName_to_SkillId_data = json.load(fp)

    with open(DPS_ANIM_PATH, 'r', encoding='utf-8') as f:
        dps_anim = json.load(f)

    with open(DPS_OPTIONS_PATH, 'r', encoding='utf-8') as f:
        dps_options = json.load(f)

    with open(DPS_SPECIALTAGS_PATH, 'r', encoding='utf-8') as f:
        specs = json.load(f)

    with open(CHARACTER_TABLE_PATH, 'r', encoding='utf-8') as f:
        character_table = json.load(f)

    with open(UNIEQUIP_TABLE_PATH, 'r', encoding='utf-8') as f:
        uniequip_table = json.load(f)

    with open(BATTLE_EQUIP_TABLE_PATH, 'r', encoding='utf-8') as f:
        battle_equip_table = json.load(f)

    with open(SKILL_TABLE_PATH, 'r', encoding='utf-8') as f:
        skill_table = json.load(f)

    return CharacterId_and_chName_data, chEquipName_to_EquipId_data, chSkillName_to_SkillId_data, \
        dps_anim, dps_options, character_table, uniequip_table, battle_equip_table, skill_table, specs


CharacterId_and_chName_data, chEquipName_to_EquipId_data, chSkillName_to_SkillId_data, \
    dps_anim, dps_options, character_table, uniequip_table, battle_equip_table, skill_table, specs = load()
