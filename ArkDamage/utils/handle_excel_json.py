import asyncio
import json

from ..dmg_cal.RESOURCE_PATH import MAP_PATH, resVersion, CHARACTER_TABLE_PATH, UNIEQUIP_TABLE_PATH
from ..dmg_cal.load_json import character_table


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
