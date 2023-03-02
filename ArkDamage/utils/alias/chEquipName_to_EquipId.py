from ...dmg_cal.load_json import chEquipName_to_EquipId_data


async def ch_equip_name_to_equip_id(character_id: str, uniequip_id: int) -> str or None:
    if chEquipName_to_EquipId_data.get(character_id):
        equip = chEquipName_to_EquipId_data.get(character_id)[int(uniequip_id)]
        return equip
    else:
        return None
