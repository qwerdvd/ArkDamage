from ...dmg_cal.load_json import ch_equip_name_to_equip_id_data


async def ch_equip_name_to_equip_id(character_id: str, uniequip_id: int) -> str or None:
    if ch_equip_name_to_equip_id_data.get(character_id):
        equip = ch_equip_name_to_equip_id_data.get(character_id)[int(uniequip_id)]
        return equip
    else:
        return None
