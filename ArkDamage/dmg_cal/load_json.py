import json

from ..utils.download_resource.RESOURCE_PATH import (
    DPS_ANIMATION_PATH, DPS_OPTIONS_PATH, DPS_SPECIALTAGS_PATH,
    CHARACTER_TABLE_PATH, UNIEQUIP_TABLE_PATH, BATTLE_EQUIP_TABLE_PATH,
    CHARACTERID_CHNAME_MAP_PATH, SKILL_TABLE_PATH,
    CHEQUIPNAME_TO_EQUIPID_MAP_PATH, CHSKILLNAME_TO_SKILLID_MAP_PATH, ENEMYDATA_PATH
)


def load_json_file(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as file:
        return json.load(file)


def load():
    character_id_and_ch_name = load_json_file(CHARACTERID_CHNAME_MAP_PATH)
    ch_equip_name_to_equip_id = load_json_file(CHEQUIPNAME_TO_EQUIPID_MAP_PATH)
    ch_skill_name_to_skill_id = load_json_file(CHSKILLNAME_TO_SKILLID_MAP_PATH)
    anim = load_json_file(DPS_ANIMATION_PATH)
    options = load_json_file(DPS_OPTIONS_PATH)
    special = load_json_file(DPS_SPECIALTAGS_PATH)
    character = load_json_file(CHARACTER_TABLE_PATH)
    uniequip = load_json_file(UNIEQUIP_TABLE_PATH)
    battle_equip = load_json_file(BATTLE_EQUIP_TABLE_PATH)
    skill = load_json_file(SKILL_TABLE_PATH)
    enemy_data = load_json_file(ENEMYDATA_PATH)

    return (
        character_id_and_ch_name,
        ch_equip_name_to_equip_id,
        ch_skill_name_to_skill_id,
        anim,
        options,
        character,
        uniequip,
        battle_equip,
        skill,
        special,
        enemy_data,
    )


(
    character_id_and_ch_name_data,
    ch_equip_name_to_equip_id_data,
    ch_skill_name_to_skill_id_data,
    dps_anim,
    dps_options,
    character_table,
    uniequip_table,
    battle_equip_table,
    skill_table,
    specs,
    enemy_database,
) = load()
