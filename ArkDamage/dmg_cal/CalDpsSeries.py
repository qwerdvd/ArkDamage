import io
from decimal import Decimal

import matplotlib.pyplot as plt
import numpy as np
from nonebot import logger
from scipy.interpolate import griddata

from .CalAttack import calculate_attack, extract_damage_type
from .CalCharAttributes import get_blackboard, get_attributes, check_specs
from .CalDps import get_token_atk_hp
from .load_json import uniequip_table
from .log import NoLog
from .model.Character import Character
from .model.InitChar import InitChar
from .model.models import Enemy, BlackBoard
from .model.raid_buff import RaidBlackboard

EnemySeries = {
    "defense": [x * 50 for x in range(51)],
    "magicResistance": [x * 2 for x in range(51)],
    "def_mag": [(x * 60, y * 2) for x in range(51) for y in range(51)],
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


async def cal_3d(
        char_info: InitChar, char: Character, enemy: Enemy
):
    def_mag_plot_data = await calculate_dps_series(
        char_info, char, enemy, 'def_mag', EnemySeries['def_mag']
    )
    data = []
    for i in range(0, len(def_mag_plot_data), 2):
        tup = (def_mag_plot_data[i][0], def_mag_plot_data[i][1], def_mag_plot_data[i + 1])
        data.append(tup)
    data = np.array(data)

    fig = plt.figure(dpi=500)
    ax = fig.add_subplot(111, projection='3d')

    x, y, z = data[:, 0], data[:, 1], data[:, 2]
    X, Y = np.meshgrid(np.linspace(np.min(x), np.max(x), 150), np.linspace(np.min(y), np.max(y), 150))
    Z = griddata((x, y), z, (X, Y), method='cubic')

    ax.plot_surface(X, Y, Z, rstride=1, cstride=1, cmap='coolwarm', alpha=0.5)

    ax.view_init(30, 115)
    # Label the axes
    ax.set_xlabel('Defense')
    ax.set_ylabel('magicResistance')
    ax.set_zlabel('DPS')

    # Convert the plot to bytes
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    return buf


async def cal_(
        char_info: InitChar, char: Character, enemy: Enemy
):
    backup_defense = enemy.defense
    backup_magic_resistance = enemy.magicResistance
    def_plot_data = await calculate_dps_series(
        char_info, char, enemy, 'defense', EnemySeries['defense']
    )
    enemy.change('defense', backup_defense)  # reset defense
    mag_plot_data = await calculate_dps_series(
        char_info, char, enemy, 'magicResistance', EnemySeries['magicResistance']
    )
    enemy.change('magicResistance', backup_magic_resistance)  # reset magicResistance

    damage_type = await extract_damage_type(
        char_info, char, True, BlackBoard(char.buffList['skill']), char_info.options
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
    fig, ax = plt.subplots(dpi=500)
    plt.grid(True)
    x_dps, y_dps = [], []
    x_damage, y_damage = [], []
    for k, v in plot_data['dps_plot_data'].items():
        x_dps.append(v[0])
        y_dps.append(v[1])
    for k, v in plot_data['damage_plot_data'].items():
        x_damage.append(v[0])
        y_damage.append(v[1])

    # Plot the DPS data on the left Y-axis
    ax.plot(x_dps, y_dps, '-o', label='DPS', color='blue')
    if damage_type == 1:
        plt.xlabel('magicResistance')
    else:
        plt.xlabel('defense')
    ax.set_ylabel('DPS')
    ax.tick_params(axis='y', labelcolor='blue')

    # Create a secondary Y-axis for the Damage data
    ax2 = ax.twinx()
    ax2.plot(x_damage, y_damage, '-o', label='Damage', color='orange')
    ax2.set_ylabel('Damage')
    ax2.tick_params(axis='y', labelcolor='orange')

    # Automatically adjust the range of both Y-axes
    ax.set_ylim(bottom=0, top=max(y_dps) * Decimal(1.1))
    ax2.set_ylim(bottom=0, top=max(y_damage) * Decimal(1.1))

    # Set the legend for both axes
    lines, labels = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labels + labels2, loc='upper right')

    # Adjust the plot margins
    plt.subplots_adjust(left=0.2, right=0.8)

    # Convert the plot to bytes
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    return


async def calculate_dps_series(
        char_info: InitChar, char: Character, enemy: Enemy,
        _key: str, series: list
) -> dict or None:
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

    char_id = char_info.char_id
    char_data = char.CharData
    skill_data = char.SkillData
    if char_info.equip_id != 'None' and char_info.equip_id is not None:
        equip_data = uniequip_table["equipDict"][char_info.equip_id]
        char.displayNames[char_info.equip_id] = equip_data['uniEquipName']
    if char_info.skillLevel == -1:
        char_info.skillLevel = len(skill_data.levels) - 1

    level_data = char.LevelData
    char.blackboard = await get_blackboard(skill_data.levels[char_info.skillLevel].blackboard) or {}

    char.displayNames[char_id] = char_data.name
    char.displayNames[char_info.skill_id] = level_data.name  # add to name cache

    char = await get_attributes(char_info, char, log)
    char.blackboard['id'] = skill_data.skillId
    char.buffList["skill"] = {}
    for key, value in char.blackboard.items():
        char.buffList['skill'][key] = value
    char.skillId = char.blackboard['id']

    if char_info.options.get('token'):
        token_id = await check_specs(char_id, "token") or await check_specs(char.skillId, "token")
        char = await get_token_atk_hp(char_info, char, token_id, log)

    # 原本攻击力的修正量
    if raid_blackboard.base_atk != 0:
        delta = char.attributesKeyFrames["atk"] * raid_blackboard.base_atk
        prefix = "+" if delta > 0 else ""
        char.attributesKeyFrames["atk"] = round(char.attributesKeyFrames["atk"] + delta)

    if _key == "def_mag":
        results = []
    else:
        results = {'dps_plot_data': {}, 'damage_plot_data': {}}

    _backup = {
        "basic": dict(char.attributesKeyFrames),
    }
    for x in series:
        enemy.change(_key, x)
        if not await check_specs(char_info.skill_id, "overdrive"):
            char_info.options["overdrive_mode"] = False
            char.attributesKeyFrames = dict(_backup["basic"])
            skill_attack = await calculate_attack(char_info, char, enemy, raid_blackboard, True, log)
            if not skill_attack:
                return None

            char.attributesKeyFrames = dict(_backup["basic"])
            normal_attack = await calculate_attack(char_info, char, enemy, raid_blackboard, False, log)
            if not normal_attack:
                return None
        else:
            char.attributesKeyFrames = dict(_backup["basic"])
            od_p1 = await calculate_attack(char_info, char, enemy, raid_blackboard, True, log)

            char.attributesKeyFrames = dict(_backup["basic"])
            char_info.options["overdrive_mode"] = True
            od_p2 = await calculate_attack(char_info, char, enemy, raid_blackboard, False, log)

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
            char_info.options["overdrive_mode"] = False
            normal_attack = await calculate_attack(char_info, char, enemy, raid_blackboard, False, log)
            if not normal_attack:
                return None

        global_dps = round((Decimal(normal_attack['totalDamage']) + Decimal(skill_attack['totalDamage'])) /
                           Decimal(normal_attack['dur'].duration + normal_attack['dur'].stunDuration +
                                   skill_attack['dur']['duration'] + skill_attack['dur']['prepDuration']))
        if _key == "def_mag":
            dps_singe_plot = tuple([x, global_dps])
            results += dps_singe_plot
        else:
            dps_singe_plot = [x, global_dps]
            damage_singe_plot = [x, skill_attack['totalDamage']]
            results['dps_plot_data'][x] = dps_singe_plot
            results['damage_plot_data'][x] = damage_singe_plot

    return results
