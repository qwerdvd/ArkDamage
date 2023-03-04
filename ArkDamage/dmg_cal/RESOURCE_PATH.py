import sys
from pathlib import Path

resVersion = "23-01-30-14-05-02-06c33f"
MAIN_PATH = Path() / "data" / "ArkDamage"

sys.path.append(str(MAIN_PATH))

MAP_PATH = MAIN_PATH / "map"
EXCEL_PATH = MAIN_PATH / "excel"
LEVEL_PATH = MAIN_PATH / "levels"

ENEMY_PATH = LEVEL_PATH / "enemydata"
ENEMYDATA_PATH = ENEMY_PATH / "enemy_database.json"

DPS_ANIM_PATH = MAIN_PATH / "dps_anim.json"
DPS_OPTIONS_PATH = MAIN_PATH / "dps_options.json"
DPS_SPECIALTAGS_PATH = MAIN_PATH / "dps_specialtags.json"

CHARACTER_TABLE_PATH = EXCEL_PATH / "character_table.json"
UNIEQUIP_TABLE_PATH = EXCEL_PATH / "uniequip_table.json"
BATTLE_EQUIP_TABLE_PATH = EXCEL_PATH / "battle_equip_table.json"
SKILL_TABLE_PATH = EXCEL_PATH / "skill_table.json"

CHARACTERID_CHNAME_MAP_PATH = MAP_PATH / f"CharacterId_chName_mapping_{resVersion}.json"
CHEQUIPNAME_TO_EQUIPID_MAP_PATH = MAP_PATH / f"chEquipName_to_EquipId_mapping_{resVersion}.json"
CHSKILLNAME_TO_SKILLID_MAP_PATH = MAP_PATH / f"chSkillName_to_SkillId_mapping_{resVersion}.json"
