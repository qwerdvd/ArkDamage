from decimal import Decimal

from .CalAttack import calculate_attack
from .CalCharAttributes import get_blackboard, get_attributes, check_specs
from .CalDps import get_token_atk_hp
from .log import NoLog
from .model.raid_buff import RaidBlackboard


async def calculate_dps_series(base_char_info, char, enemy, key, series):
    log = NoLog()
    raid_buff = {'atk': 0, 'atkpct': 0, 'ats': 0, 'cdr': 0, 'base_atk': 0, 'damage_scale': 0}
    raid_blackboard = RaidBlackboard({
        'atk': raid_buff['atkpct'] / 100,
        'atk_override': raid_buff['atk'],
        'attack_speed': raid_buff['ats'],
        'sp_recovery_per_sec': raid_buff['cdr'] / 100,
        'base_atk': raid_buff['base_atk'] / 100,
        'damage_scale': 1 + raid_buff['damage_scale'] / 100
    })
    char.displayNames["raidBuff"] = ""

    char_id = base_char_info.char_id
    char_data = char.CharData
    skill_data = char.SkillData
    if char.skillLevel == -1:
        char.skillLevel = skill_data.levels.length - 1

    level_data = char.LevelData
    char.blackboard = await get_blackboard(skill_data.levels[base_char_info.skillLevel].blackboard) or {}

    char = await get_attributes(base_char_info, char, log)
    char.blackboard['id'] = skill_data.skillId
    char.buffList["skill"] = char.blackboard

    char.displayNames[char_id] = char_data.name
    char.displayNames[char.skillId] = level_data.name  # add to name cache

    if base_char_info.options.get('token'):
        token_id = await check_specs(char_id, "token") or await check_specs(char.skillId, "token")
        char = await get_token_atk_hp(base_char_info, char, token_id, log)

    # 原本攻击力的修正量
    if raid_blackboard.base_atk != 0:
        delta = char.attributesKeyFrames["atk"] * raid_blackboard.base_atk
        prefix = "+" if delta > 0 else ""
        char.attributesKeyFrames["atk"] = round(char.attributesKeyFrames["atk"] + delta)

    results = {}
    _backup = {
        "basic": dict(char.attributesKeyFrames),
    }

    for x in series:
        enemy[key] = x
        if not await check_specs(base_char_info.skill_id, "overdrive"):
            base_char_info.options["overdrive_mode"] = False
            char.attributesKeyFrames = dict(_backup["basic"])
            skill_attack = await calculate_attack(base_char_info, char, enemy, raid_blackboard, True, log)
            if not skill_attack:
                return

            char.attributesKeyFrames = dict(_backup["basic"])
            normal_attack = await calculate_attack(base_char_info, char, enemy, raid_blackboard, False, log)
            if not normal_attack:
                return
        else:
            char.attributesKeyFrames = dict(_backup["basic"])
            od_p1 = await calculate_attack(base_char_info, char, enemy, raid_blackboard, True, log)

            char.attributesKeyFrames = dict(_backup["basic"])
            base_char_info.options["overdrive_mode"] = True
            od_p2 = await calculate_attack(base_char_info, char, enemy, raid_blackboard, False, log)

            merged = dict(od_p2)
            merged.dur = dict(od_p2["dur"])
            for key in ["totalDamage", "totalHeal", "extraDamage", "extraHeal"]:
                merged[key] += od_p1[key]

            for i in range(len(merged["damagePool"])):
                merged['damagePool'][i] += od_p1['damagePool'][i]
                merged['extraDamagePool'][i] += od_p1['extraDamagePool'][i]
            for key in ["attackCount", "hitCount", "duration", "stunDuration", "prepDuration"]:
                if key in merged["dur"] and key in od_p1["dur"]:
                    setattr(merged['dur'], key, getattr(merged['dur'], key) + getattr(od_p1['dur'], key))
            tm = (merged["dur"]['duration'] + merged["dur"]['stunDuration'] + merged["dur"]['prepDuration'])
            merged["dps"] = merged["totalDamage"] / Decimal(tm)
            merged["hps"] = merged["totalHeal"] / Decimal(tm)
            skill_attack = merged

            char.attributesKeyFrames = dict(_backup["basic"])
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
        results[x] = {
            'normal': normal_attack,
            'skill': skill_attack,
            'skillName': level_data.name,
            'globalDps': global_dps,
            'globalHps': global_hps
        }

    return results
