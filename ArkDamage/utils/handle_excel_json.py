import asyncio
import json
import sys
from pathlib import Path

# from .download_resource.RESOURCE_PATH import MAP_PATH, CHARACTER_TABLE_PATH, UNIEQUIP_TABLE_PATH
# from ..dmg_cal.load_json import character_table
# from ..version import resVersion


MAIN_PATH = Path() / 'data' / 'ArkDamage'

sys.path.append(str(MAIN_PATH))

MAP_PATH = MAIN_PATH / "map"
EXCEL_PATH = MAIN_PATH / "excel"
LEVEL_PATH = MAIN_PATH / "levels"

BATTLE_EQUIP_TABLE_PATH = EXCEL_PATH / 'battle_equip_table.json'
CHARACTER_TABLE_PATH = EXCEL_PATH / 'character_table.json'
SKILL_TABLE_PATH = EXCEL_PATH / 'skill_table.json'
UNIEQUIP_TABLE_PATH = EXCEL_PATH / 'uniequip_table.json'

resVersion = "23-03-04-19-40-05-ed6f46"


def load_json_file(path: Path) -> dict:
    with open(path, 'r', encoding='utf-8') as file:
        return json.load(file)


character_table = load_json_file(CHARACTER_TABLE_PATH)


async def generate_ch_skill_name_to_skill_id_mapping():
    """
    :说明:
        生成chSkillName_to_SkillId_mapping.json
    :参数:
        * 无
    :返回:
        * 无
    """
    ch_skill_name_to_skill_id_data = {}
    for key in character_table:
        skill = []
        for j in character_table[key]['skills']:
            skill.append(j['skillId'])
        ch_skill_name_to_skill_id_data[character_table[key]['name']] = skill

    with open(MAP_PATH / f'chSkillName_to_SkillId_mapping_{resVersion}.json', 'w',
              encoding='utf-8') as f:
        json.dump(ch_skill_name_to_skill_id_data, f, ensure_ascii=False, indent=4)


async def generate_ch_name_character_id():
    """
    :说明:
        生成角色名称与角色ID的对应关系
    :参数:
        * 无
    :返回:
        * 无
    """
    with open(CHARACTER_TABLE_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
        character_id_and_ch_name_data = {}
        for key in data:
            character_id_and_ch_name_data[key] = data[key]['name']

    with open(MAP_PATH / f'CharacterId_chName_mapping_{resVersion}.json', 'w',
              encoding='utf-8') as f:
        json.dump(character_id_and_ch_name_data, f, ensure_ascii=False, indent=4)


async def generate_ch_equip_name_equip_id():
    """
    :说明:
        生成模组名称与模组ID的对应关系
    :参数:
        * 无
    :返回:
        * 无
    """
    with open(UNIEQUIP_TABLE_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
        ch_equip_name_to_equip_id_data = data['charEquip']

    with open(MAP_PATH / f'chEquipName_to_EquipId_mapping_{resVersion}.json', 'w',
              encoding='utf-8') as f:
        json.dump(ch_equip_name_to_equip_id_data, f, ensure_ascii=False, indent=4)


if __name__ == '__main__':
    asyncio.run(generate_ch_skill_name_to_skill_id_mapping())
    asyncio.run(generate_ch_name_character_id())
    asyncio.run(generate_ch_equip_name_equip_id())
