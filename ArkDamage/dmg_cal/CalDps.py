from decimal import Decimal

from . import InitChar, Character
from .CalAttack import calculate_attack
from .CalCharAttributes import check_specs, get_attributes, get_blackboard
from .load_json import uniequip_table, character_table, skill_table
from .log import Log
from .model.raid_buff import RaidBlackboard


async def get_token_atk_hp(base_char_info: InitChar, char: Character, token_id, log):
    old_char = char.attr['basic'].copy()
    token_name = character_table[token_id]["name"]
    char.attr['char']['charId'] = token_id
    token = await get_attributes(base_char_info, char.attr['char'], char.displayNames, log)
    char.attr['basic']['atk'] = token.basic['atk']
    char.attr['basic']['def'] = token.basic['def']
    char.attr['basic']['maxHp'] = token.basic['maxHp']
    char.attr['basic']['baseAttackTime'] = token.basic['baseAttackTime']
    char.attr['basic']['attackSpeed'] = token.basic['attackSpeed']

    # 特判
    if token_id == "token_10027_ironmn_pile3":
        char.attr['basic'].atk = old_char.atk
        # 加入召唤物技能
        skill_data = skill_table["sktok_ironmn_pile3"]
        level_data = skill_data.levels[char.attr['char'].skillLevel]
        blackboard = get_blackboard(level_data["blackboard"]) or {}
        char.attr['buffList']["sktok_ironmn_pile3"] = blackboard
        char.displayNames["sktok_ironmn_pile3"] = level_data["name"]

    # 模组判断
    buff_hp = 0
    buff_atk = 0
    buff_ats = 0
    buff_def = 0

    # blackboard = None
    updated = False
    equip_id = char.attr['char'].equipId
    equip_level = char.attr['char'].equipLevel
    match equip_id:
        case "uniequip_002_deepcl":
            if equip_level == 3:
                buff_hp = char.attr['basic'].maxHp * char.attr['buffList']["uniequip_002_deepcl"].talent.max_hp
                updated = True
        case "uniequip_002_ling":
            if equip_level == 3:
                blackboard = char.attr['buffList']["uniequip_002_ling"].token[token_id]
                buff_hp = blackboard.max_hp
                buff_atk = blackboard.atk
                updated = True
        case "uniequip_003_mgllan":
            if equip_level == 3:
                blackboard = char.attr['buffList']["uniequip_003_mgllan"].token[token_id]
                if "max_hp" in blackboard:
                    buff_hp = blackboard.max_hp
                if "atk" in blackboard:
                    buff_atk = blackboard.atk
                if "attack_speed" in blackboard:
                    buff_ats = blackboard.attack_speed
                updated = True
        case "uniequip_002_bgsnow":
            if equip_level >= 2:
                blackboard = char.attr['buffList']["uniequip_002_bgsnow"].token[token_id]
                buff_atk = blackboard.atk
                updated = True
        case "uniequip_003_dusk":
            if equip_level >= 2:
                blackboard = char.attr['buffList']["uniequip_003_dusk"].token[token_id]
                buff_atk = blackboard.atk
                buff_hp = blackboard.max_hp
                buff_def = blackboard['def']
                updated = True

    if updated:
        char.attr['basic']['maxHp'] += buff_hp
        char.attr['basic']['atk'] += buff_atk
        char.attr['basic']['attackSpeed'] += buff_ats
        char.attr['basic']['def'] += buff_def

        log.write(
            f'[模组] {token_name} maxHp + {round(buff_hp)}, '
            f'atk + {buff_atk}, attack_speed + {buff_ats}, def + {buff_def}')
    log.write(
        f"[召唤物] {token_name} maxHp = {char.attr['basic'].maxHp}, "
        f"atk = {char.attr['basic'].atk}, baseAttackTime = {char.attr['basic'].baseAttackTime}")
    return char.displayNames, char.attr


async def calculate_dps(base_char_info: InitChar, char: Character, enemy) -> dict or None:
    log = Log()
    raid_buff = {'atk': 0, 'atkpct': 0, 'ats': 0, 'cdr': 0, 'base_atk': 0, 'damage_scale': 0}
    raid_blackboard = RaidBlackboard({
        'atk': raid_buff['atkpct'] / 100,
        'atk_override': raid_buff['atk'],
        'attack_speed': raid_buff['ats'],
        'sp_recovery_per_sec': raid_buff['cdr'] / 100,
        'base_atk': raid_buff['base_atk'] / 100,
        'damage_scale': 1 + raid_buff['damage_scale'] / 100
    })
    char.displayNames["raidBuff"] = "团辅"

    char_id = base_char_info.char_id
    char_data = char.CharData
    skill_data = char.SkillData
    equip_data = char.UniEquipData
    if base_char_info.equip_id and len(base_char_info.equip_id) > 0:
        equip_data = uniequip_table["equipDict"][base_char_info.equip_id]
        char.displayNames[base_char_info.equip_id] = equip_data['uniEquipName']
    if base_char_info.skillLevel == -1:
        base_char_info.skillLevel = len(skill_data.levels) - 1

    # level_data = skill_data.levels[base_char_info.skillLevel]
    level_data = char.LevelData
    blackboard = await get_blackboard(skill_data.levels[base_char_info.skillLevel].blackboard) or {}
    char.blackboard = blackboard

    log.write("说明：计算结果可能存在因为逻辑错误或者数据不全导致的计算错误，作者会及时修正。")
    log.write("　　　计算结果仅供参考，请仔细核对以下的计算过程：")
    log.write("| 角色 | 等级 | 技能 | 模组 |")
    log.write("| :--: | :--: | :--: | :--: |")
    uni_equip_name = equip_data.get('uniEquipName') if equip_data is not None else ''
    log.write(
        f"{char_data.name} {char_id} 潜能 {base_char_info.potentialRank + 1} 精英 {base_char_info.phase}, "
        f"等级 {base_char_info.level} {level_data.name} 等级 {base_char_info.skillLevel + 1} "
        f"{uni_equip_name} 等级 {base_char_info.equipLevel}")
    log.write('')
    log.write("----")
    char.displayNames[char_id] = char_data.name
    char.displayNames[base_char_info.skill_id] = level_data.name  # add to name cache

    # calculate basic attribute package
    char.attr = await get_attributes(base_char_info, char, char.displayNames, log)
    char.displayNames = char.attr['displayNames']
    blackboard['id'] = skill_data.skillId
    char.attr['buffList']["skill"] = {}
    for key, value in blackboard.items():
        char.attr['buffList']['skill'][key] = value
    # attr['buffList']["skill"] = blackboard
    char.attr['skillId'] = blackboard['id']

    if base_char_info.options.get('token') and (
            await check_specs(char_id, "token") or await check_specs(base_char_info.skill_id, "token")):
        log.write("\n")
        log.write_note("**召唤物dps**")
        token_id = await check_specs(char_id, "token") or await check_specs(base_char_info.skill_id, "token")
        char.displayNames, char.attr = await get_token_atk_hp(base_char_info, char, token_id, log)

    # 原本攻击力的修正量
    if raid_blackboard.base_atk != 0:
        delta = char.attr["basic"]["atk"] * raid_blackboard.base_atk
        prefix = "+" if delta > 0 else ""
        char.attr["basic"]["atk"] = round(char.attr["basic"]["atk"] + delta)
        log.write(f"[团辅] 原本攻击力变为 {char.attr['basic']['atk']} ({prefix}{delta:.1f})")
    log.write("")
    log.write("----")
    _backup = {
        "basic": dict(char.attr["basic"]),
        # "enemy": dict(enemy),
        # "chr": dict(charData),
        # "level": dict(levelData),
    }

    _note = ""
    # normal_attack = None
    # skill_attack = None

    if not await check_specs(base_char_info.skill_id, "overdrive"):
        log.write("【技能】")
        log.write("----------")
        skill_attack = await calculate_attack(base_char_info, char, enemy, raid_blackboard, True, log)

        if not skill_attack:
            return
        _note = f"{log.note}"

        log.write("----")
        char.attr['basic'] = _backup['basic']

        log.write("【普攻】")
        log.write("----------")
        normal_attack = await calculate_attack(base_char_info, char, enemy, raid_blackboard, False, log)
        if not normal_attack:
            return

        global_dps = round((Decimal(normal_attack['totalDamage']) + Decimal(skill_attack['totalDamage'])) /
                           Decimal(normal_attack['dur'].duration + normal_attack['dur'].stunDuration +
                                   skill_attack['dur'].duration + skill_attack['dur'].prepDuration))
        global_hps = round((Decimal(normal_attack['totalHeal']) + Decimal(skill_attack['totalHeal'])) /
                           Decimal(normal_attack['dur'].duration + normal_attack['dur'].stunDuration +
                                   skill_attack['dur'].duration + skill_attack['dur'].prepDuration))

    else:
        # 22.4.15 过载模式计算
        log.write("- **技能前半**\n")
        od_p1 = await calculate_attack(base_char_info, char, enemy, raid_blackboard, True, log)
        # _note = f"{log.note}"

        log.write("----")
        log.write("- **过载**\n")
        char.attr["basic"] = dict(_backup["basic"])
        base_char_info.options["overdrive_mode"] = True  # 使用options控制，这个options不受UI选项影响
        od_p2 = await calculate_attack(base_char_info, char, enemy, raid_blackboard, True, log)
        _note = f"{log.note}"

        # merge result
        merged = dict(od_p2)
        merged["dur"] = dict(od_p2["dur"])
        for key in ["totalDamage", "totalHeal", "extraDamage", "extraHeal"]:
            merged[key] += od_p1[key]
        for i in range(len(merged["damagePool"])):
            merged["damagePool"][i] += od_p1["damagePool"][i]
            merged["extraDamagePool"][i] += od_p1["extraDamagePool"][i]
        for key in ["attackCount", "hitCount", "duration", "stunDuration", "prepDuration"]:
            if key in merged["dur"] and key in od_p1["dur"]:
                setattr(merged['dur'], key, getattr(merged['dur'], key) + getattr(od_p1['dur'], key))
        tm = (merged["dur"]['duration'] + merged["dur"]['stunDuration'] + merged["dur"]['prepDuration'])
        merged["dps"] = merged["totalDamage"] / Decimal(tm)
        merged["hps"] = merged["totalHeal"] / Decimal(tm)
        skill_attack = merged

        log.write("----")
        log.write("- **普攻**\n")
        char.attr["basic"] = dict(_backup["basic"])
        base_char_info.options["overdrive_mode"] = False
        normal_attack = await calculate_attack(base_char_info, char, enemy, raid_blackboard, False, log)
        if not normal_attack:
            return

        global_dps = round((Decimal(normal_attack['totalDamage']) + Decimal(skill_attack['totalDamage'])) /
                           Decimal(normal_attack['dur'].duration + normal_attack['dur'].stunDuration +
                                   skill_attack['dur']['duration'] + skill_attack['dur']['prepDuration']))
        global_hps = round((Decimal(normal_attack['totalHeal']) + Decimal(skill_attack['totalHeal'])) /
                           Decimal(normal_attack['dur'].duration + normal_attack['dur'].stunDuration +
                                   skill_attack['dur']['duration'] + skill_attack['dur']['prepDuration']))

    kill_time = 0
    return {
        'normal': normal_attack,
        'skill': skill_attack,
        'skillName': level_data.name,
        'killTime': kill_time,
        'globalDps': global_dps,
        'globalHps': global_hps,
        'log': log,
        'note': _note
    }
