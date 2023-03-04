import io
from decimal import Decimal

import matplotlib.pyplot as plt
from nonebot import logger

from .CalAttack import calculate_attack, extract_damage_type
from .CalCharAttributes import get_blackboard, get_attributes, check_specs
from .CalDps import get_token_atk_hp
from .load_json import uniequip_table
from .log import NoLog
from .model.models import Enemy, BlackBoard
from .model.raid_buff import RaidBlackboard

EnemySeries = {
    "defense": [x * 100 for x in range(31)],
    "magicResistance": [x * 5 for x in range(21)],
    "count": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
}

LabelNames = {
    "defense": "防御",
    "magicResistance": "法抗",
    "count": "数量",
    "dps": "平均DPS",
    "s_dps": "技能DPS",
    "s_dmg": "技能总伤害"
}


async def cal_(base_char_info, char, enemy):
    def_plot_data = await calculate_dps_series(
        base_char_info, char, enemy, 'defense', EnemySeries['defense']
    )
    enemy.change('defense', 0)  # reset defense
    mag_plot_data = await calculate_dps_series(
        base_char_info, char, enemy, 'magicResistance', EnemySeries['magicResistance']
    )
    enemy.change('magicResistance', 0)  # reset magicResistance

    damage_type = await extract_damage_type(
        base_char_info, char, True, BlackBoard(char.buffList['skill']), base_char_info.options
    )
    logger.info(f'CalDpsSeries: damage_type: {damage_type}')

    if damage_type == 0:
        plot_data = def_plot_data
    elif damage_type == 1:
        plot_data = mag_plot_data
    elif damage_type == 2:  # 治疗
        return None
    else:  # 真实伤害时取防御
        plot_data = def_plot_data

    # Plot DPS and Damage data
    fig, ax = plt.subplots(dpi=300)
    x_dps, y_dps = [], []
    x_damage, y_damage = [], []
    for k, v in plot_data['dps_plot_data'].items():
        x_dps.append(v[0])
        y_dps.append(v[1])
    for k, v in plot_data['damage_plot_data'].items():
        x_damage.append(v[0])
        y_damage.append(v[1])
    plt.grid(True)
    plt.plot(x_dps, y_dps, '-o', label='DPS')
    plt.plot(x_damage, y_damage, '-o', label='Damage')
    if damage_type == 1:
        plt.xlabel('magicResistance')
    else:
        plt.xlabel('defense')
    plt.ylabel('DPS and Damage')
    plt.legend(loc='upper right')
    plt.subplots_adjust(left=0.15)  # Adjust the left margin

    # Convert the plot to bytes
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    return buf


async def calculate_dps_series(base_char_info, char, enemy: Enemy, _key: str, series) -> dict:
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
    if base_char_info.equip_id != 'None' and base_char_info.equip_id is not None:
        equip_data = uniequip_table["equipDict"][base_char_info.equip_id]
        char.displayNames[base_char_info.equip_id] = equip_data['uniEquipName']
    if base_char_info.skillLevel == -1:
        base_char_info.skillLevel = len(skill_data.levels) - 1

    level_data = char.LevelData
    char.blackboard = await get_blackboard(skill_data.levels[base_char_info.skillLevel].blackboard) or {}

    char.displayNames[char_id] = char_data.name
    char.displayNames[base_char_info.skill_id] = level_data.name  # add to name cache

    char = await get_attributes(base_char_info, char, log)
    char.blackboard['id'] = skill_data.skillId
    char.buffList["skill"] = {}
    for key, value in char.blackboard.items():
        char.buffList['skill'][key] = value
    char.skillId = char.blackboard['id']

    if base_char_info.options.get('token'):
        token_id = await check_specs(char_id, "token") or await check_specs(char.skillId, "token")
        char = await get_token_atk_hp(base_char_info, char, token_id, log)

    # 原本攻击力的修正量
    if raid_blackboard.base_atk != 0:
        delta = char.attributesKeyFrames["atk"] * raid_blackboard.base_atk
        prefix = "+" if delta > 0 else ""
        char.attributesKeyFrames["atk"] = round(char.attributesKeyFrames["atk"] + delta)

    results = {'dps_plot_data': {}, 'damage_plot_data': {}}
    # plot_data = {}
    _backup = {
        "basic": dict(char.attributesKeyFrames),
    }
    for x in series:
        enemy.change(_key, x)
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
        # global_hps = round((Decimal(normal_attack['totalHeal']) + Decimal(skill_attack['totalHeal'])) /
        #                    Decimal(normal_attack['dur'].duration + normal_attack['dur'].stunDuration +
        #                            skill_attack['dur']['duration'] + skill_attack['dur']['prepDuration']))
        # results[x] = {
        #     'normal': normal_attack,
        #     'skill': skill_attack,
        #     'skillName': level_data.name,
        #     'globalDps': global_dps,
        #     'globalHps': global_hps
        # }
        dps_singe_plot = [x, global_dps]
        damage_singe_plot = [x, skill_attack['totalDamage']]
        results['dps_plot_data'][x] = dps_singe_plot
        results['damage_plot_data'][x] = damage_singe_plot

    return results
