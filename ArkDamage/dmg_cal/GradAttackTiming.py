async def explain_grad_attack_timing(_, n=7):
    lines = []
    i = 0
    row_time = list(range(_['duration']))
    l1 = [":--:"] * len(row_time)
    row_atk = [round(x) for x in _['atk_by_sec']]
    row_timing = [round(x, 2) for x in _['atk_timing']]
    row_scale = []
    l2 = [":--:"] * len(row_timing)
    row_dmg = [round(x) for x in _['dmg_table']]
    if _.get('scale_table'):
        row_scale = [round(x, 2) for x in _['scale_table']]

    while i < len(row_time):
        r1 = ["时间(s)"] + row_time[i:i + n]
        ls1 = [":--:"] + l1[i:i + n]
        a1 = ["攻击力"] + row_atk[i:i + n]
        lines.append(f"| {' | '.join(str(x) for x in r1)} |")
        lines.append(f"| {' | '.join(str(x) for x in ls1)} |")
        lines.append(f"| {' | '.join(str(x) for x in a1)} |")
        lines.append("\n")
        i += n
    i = 0

    while i < len(row_timing):
        r2 = ["时点(s)"] + row_timing[i:i + n]
        ls2 = [":--:"] + l2[i:i + n]
        s2 = []
        d2 = ["伤害"] + row_dmg[i:i + n]
        lines.append(f"| {' | '.join(str(x) for x in r2)} |")
        lines.append(f"| {' | '.join(str(x) for x in ls2)} |")
        if _.get('scale_table'):
            s2 = ["倍率"] + row_scale[i:i + n]
            lines.append(f"| {' | '.join(str(x) for x in s2)} |")
        lines.append(f"| {' | '.join(str(x) for x in d2)} |")
        lines.append("\n")
        i += n

    return "\n".join(lines)
