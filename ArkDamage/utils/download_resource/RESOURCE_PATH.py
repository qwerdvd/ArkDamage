import sys
from pathlib import Path

MAIN_PATH = Path() / 'data' / 'ArkDamage'
sys.path.append(str(MAIN_PATH))

DPS_ANIMATION_PATH = MAIN_PATH / 'dps_anim.json'
DPS_OPTIONS_PATH = MAIN_PATH / 'dps_options.json'
DPS_SPECIALTAGS_PATH = MAIN_PATH / 'dps_specialtags.json'

EXCEL_PATH = MAIN_PATH / 'excel'
BATTLE_EQUIP_TABLE_PATH = EXCEL_PATH / 'battle_equip_table.json'
CHARACTER_TABLE_PATH = EXCEL_PATH / 'character_table.json'
SKILL_TABLE_PATH = EXCEL_PATH / 'skill_table.json'
UNIEQUIP_TABLE_PATH = EXCEL_PATH / 'uniequip_table.json'

MAP_PATH = MAIN_PATH / 'map'


def init_dir():
    for i in [MAIN_PATH, MAP_PATH, EXCEL_PATH]:
        if not i.exists():
            i.mkdir(parents=True, exist_ok=True)


init_dir()
