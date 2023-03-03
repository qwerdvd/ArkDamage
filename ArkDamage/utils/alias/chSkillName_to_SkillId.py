from ...dmg_cal.load_json import ch_skill_name_to_skill_id_data


async def ch_skill_name_to_skill_id(character_id: str, ch_skill_name: int) -> str:
    skill = ch_skill_name_to_skill_id_data.get(character_id)[int(ch_skill_name)]
    return skill
