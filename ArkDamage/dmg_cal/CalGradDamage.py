import math
from decimal import Decimal

from .CalCharAttributes import check_specs
from .GradAttackTiming import explain_grad_attack_timing
from .load_json import character_table


async def calculate_grad_damage(_):
    ret = 0
    dmg_table = []
    _seq = list(range(int(_['dur'].attackCount)))  # [0, 1, ..., attackCount-1]
    sub_prof = character_table[_['charId']]['subProfessionId']
    if sub_prof == "funnel":
        # 驭蟹术士
        # 基于当前伤害直接乘算atk_scale倍率即可
        base_scale = 0 if (_['skillId'] == "skchr_gdglow_3" and _['isSkill']) else 1
        base_table = [0, 1, 2, 3, 4, 5, 6]
        max_funnel_scale = 1.1
        if _['skillId'] == "skchr_rockr_2" and _['options'].get('overdrive_mode'):
            # 洛洛 - 过载模式
            _['log'].write_note("假设进入过载时是满倍率1.1")
            start = 1.1
            max_funnel_scale = _['blackboard']['scale'] * 1.1
            stacks = math.ceil((_['blackboard']['scale'] * 1.1 - start) / 0.15 + 1)
            base_table = [x + 6 for x in range(stacks)]

        funnel = 1
        if _['isSkill']:
            funnel = await check_specs(_['skillId'], "funnel") or 1

        tb = [base_scale + min(max_funnel_scale, 0.2 + 0.15 * x) * funnel for x in base_table]
        acount = _['dur'].attackCount
        if _['charId'] == "char_377_gdglow" and _['dur'].critHitCount > 0 and _['isSkill']:
            acount -= _['dur'].critHitCount
            _['log'].write(f"每个浮游炮平均爆炸 {_['dur'].critHitCount} 次, 从攻击次数中减去")
        _['log'].write(f"攻击 {acount} 次，命中 {(base_scale + funnel) * acount * _['buffFrame']['times']}")
        dmg_table = [round(_['hitDamage'] * Decimal(tb[len(tb) - 1])) if x >= len(tb) else round(
            _['hitDamage'] * Decimal(tb[x])) for x in
                     range(acount * _['buffFrame']['times'])]
        _['log'].write(
            f"倍率: {[round(x * _['buffFrame']['atk_scale'], 2) for x in tb]} (本体: {base_scale}, 浮游炮: {funnel})")
        _['log'].write(f"单次伤害: {dmg_table[:len(tb) - 1]}, {dmg_table[len(tb) - 1]} * {acount - len(tb) + 1}")
    elif _['skillId'] == "skchr_kalts_3":
        # 凯尔希: 每秒改变一次攻击力, finalFrame.atk为第一次攻击力
        _range = _['basicFrame'].atk * _['blackboard']["attack@atk"]
        n = int(_['dur'].duration)
        atk_by_sec = [_['finalFrame'].atk - _range * x / n for x in range(n + 1)]
        # 抬手时间
        atk_begin = round((await check_specs(_['skillId'], "attack_begin") or 12) / 30)
        atk_timing = [atk_begin + _['attackTime'] * i for i in _seq]

        dmg_table = [atk_by_sec[math.floor(x)] * _['buffFrame'].damage_scale for x in atk_timing]
        _['log'].write(await explain_grad_attack_timing(
            {'duration': n,
             'atk_by_sec': atk_by_sec,
             'atk_timing': atk_timing,
             'dmg_table': dmg_table
             })
                       )
    elif _['skillId'] == "skchr_billro_3":
        # 卡涅利安: 每秒改变一次攻击力（多一跳），蓄力时随攻击次数改变damage_scale倍率, finalFrame.atk为最后一次攻击力
        _range = _['basicFrame']['atk'] * Decimal(_['blackboard'].atk)
        n = int(_['dur'].duration)
        # rate = (x-1)/(n-1), thus t=0, x=n, rate=1; t=(n-1), x=1, rate=0
        atk_by_sec = [_['finalFrame']['atk'] - _range * (x - 1) / (n - 1) for x in range(n + 1)][::-1]
        # 抬手时间
        atk_begin = round((await check_specs(_['skillId'], "attack_begin") or 12) / 30)
        atk_timing = [_seq[i] * _['attackTime'] + atk_begin for i in range(len(_seq))]
        # damage_scale
        sc = [1.2, 1.4, 1.6, 1.8, 2]
        scale_table = [sc[i] if i < len(sc) else 2 for i in range(len(_seq))]

        # print({'atk_by_sec': atk_by_sec, 'atk_timing': atk_timing, 'scale_table': scale_table})
        dmg_table = [atk_by_sec[math.floor(x)] * Decimal(_['ecount'] * max(1 - _['emrpct'], 0.05) *
                                                         _['buffFrame']['damage_scale'])
                     for x in atk_timing]
        kwargs = {'duration': n, 'atk_by_sec': atk_by_sec, 'atk_timing': atk_timing, 'dmg_table': dmg_table}
        if _['options'].get("charge"):
            dmg_table = [dmg_table[i] * Decimal(scale_table[i]) for i in range(len(_seq))]
            kwargs['scale_table'] = [x * _['buffFrame']['damage_scale'] for x in scale_table]
            kwargs['dmg_table'] = dmg_table
        _['log'].write(await explain_grad_attack_timing(kwargs))
    else:
        # 一般处理（煌，傀影）：攻击加成系数在buffFrame.atk_table预先计算好，finalFrame.atk为最后一次攻击的攻击力
        # 由finalFrame.atk计算之前每次攻击的实际攻击力，同时不影响其他buff
        a = list(map(lambda x: _['basicFrame']['atk'] * Decimal(x), _['buffFrame']['atk_table']))
        pivot = a[-1]
        a = list(map(lambda x: (_['finalFrame']['atk'] - pivot + x), a))

        # 计算每次伤害
        if _['damageType'] == 0:
            dmg_table = list(
                map(lambda x: max(x - _['edef'], Decimal(x) * Decimal(0.05)) * _['buffFrame'][
                    'damage_scale'], a))
        elif _['damageType'] == 3:
            dmg_table = list(map(lambda x: x * _['buffFrame']['damage_scale'], a))

        _['log'].write(f"单次伤害: {list(map(lambda x: round(x, 1), dmg_table))}")

    if len(dmg_table) > 0:
        ret = sum(dmg_table)

    # 至简暴击（均摊计算）
    if "tachr_4054_malist_1" in _['buffList'] and _['options'].get('crit'):
        entry = _['buffList']["tachr_4054_malist_1"]
        crit_scale = 1 + entry['prob'] * (entry['atk_scale'] - 1)
        _['log'].write(f"原本伤害 {round(ret, 2)}, 均摊暴击倍率 {round(crit_scale, 2)}x")
        ret *= crit_scale

    return ret
