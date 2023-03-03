from ...dmg_cal.load_json import character_id_and_ch_name_data


async def ch_name_to_character_id(name: str) -> str:
    """
    :说明:
      接受角色名称转换为角色ID
    :参数:
      * name (str): 角色名称。
    :返回:
        * avatar_id (str): 角色ID。
    """
    character_id = ""
    for i in character_id_and_ch_name_data:
        if character_id_and_ch_name_data[i] == name:
            character_id = i
            break
    return character_id
