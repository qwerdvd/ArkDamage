import json
import math
from decimal import Decimal

from . import InitChar
from .ApplyBuff import apply_buff
from .CalAnimation import calculate_animation
from .CalCharAttributes import check_specs, get_attributes
from .CalDurations import calc_durations, check_reset_attack
from .CalGradDamage import calculate_grad_damage
from .Character import init_buff_frame, AttributeKeys, Character
from .load_json import battle_equip_table
from .log import NoLog
from .model.models import Dur, BlackBoard


# 计算边缘情况
async def calc_edges(blackboard: BlackBoard, frame, dur: Dur, log) -> None:
    skill_id = blackboard.id
    attack_begin = await check_specs(skill_id, "attack_begin") or 12  # 抬手时间
    attack_begin = math.ceil((attack_begin - 1) * 100 / dur.attackSpeed + 1)
    duration_frame = round(30 * dur.duration)
    remain_frame = attack_begin + frame * dur.attackCount - duration_frame
    pass_frame = frame - remain_frame

    if 'edge' in dur.tags:
        pass_frame = dur.tags.edge
        remain_frame = frame - pass_frame

    log.write("**【边缘情况估算(测试)】**")
    log.write(
        f"技能持续时间: {duration_frame} 帧,攻速 {dur.attackSpeed}%, 抬手 {attack_begin} 帧(受攻速影响), 攻击间隔 {frame} 帧")
    log.write(f"技能结束时，前一次攻击经过: **{pass_frame} 帧**")
    log.write(f"技能结束时，下一次攻击判定还需: **{remain_frame} 帧**")
    if remain_frame <= attack_begin:
        log.write('** 技能结束时，可能正在抬手 **')

    dur.remain_frame = remain_frame


async def get_buffed_attributes(basic, buffs) -> dict:
    final = basic.copy()
    for key in AttributeKeys:
        if key in buffs:
            final[key] += Decimal(buffs[key])

    final["atk"] *= Decimal(buffs["atk_scale"])
    final["defense"] *= Decimal(buffs["def_scale"])

    return final


async def extract_damage_type(base_char_info: InitChar, char: Character, is_skill, skill_blackboard, options) -> int:
    char_data = char.CharData
    skill_desc = char.LevelData.description
    char_id = base_char_info.char_id
    sp_id = char_data.subProfessionId
    skill_id = base_char_info.skill_id
    ret = 0

    if char_data.profession == 'MEDIC' and sp_id != 'incantationmedic':
        ret = 2
    elif sp_id == 'bard':
        ret = 2
    elif options.get('annie'):
        ret = 1
    elif '法术伤害' in char_data.description and sp_id != 'artsprotector':
        ret = 1

    if is_skill:
        if any(x in skill_desc for x in ['法术伤害', '法术</>伤害', '伤害类型变为']):
            ret = 1
        elif any(x in skill_desc for x in ['治疗', '恢复', '每秒回复']) and not skill_blackboard.get(
                "hp_recovery_per_sec_by_max_hp_ratio"):
            ret = 2

        # special character/skill overrides
        ret = await check_specs(char_id, "damage_type") or await check_specs(skill_id, "damage_type") or ret
        if skill_id == "skchr_nearl2_3":
            ret = 3 if options["block"] else 0
        if options.get("token"):
            _r = await check_specs(skill_id, "token_damage_type")
            if _r is not None:
                ret = _r
            if skill_id == "skchr_ling_3" and base_char_info.options.get("ling_fusion"):
                ret = 1

    elif base_char_info.options.get('token'):
        ret = await check_specs(char_id, "token_damage_type") or ret
        if skill_id in ["skchr_mgllan_3"]:
            ret = 0
        elif skill_id == "skchr_ling_2" or (skill_id == "skchr_ling_3" and base_char_info.options.get("ling_fusion")):
            ret = 1

    return int(ret)


async def calculate_attack(base_char_info: InitChar, char: Character, enemy, raid_blackboard, is_skill, log):
    display_names = char.displayNames
    char_data = char.CharData
    level_data = char.LevelData
    char_id = base_char_info.char_id
    buff_list = char.buffList
    blackboard = BlackBoard(buff_list['skill'])
    basic_frame = char.attributesKeyFrames
    options = base_char_info.options

    # 备注信息
    if is_skill and await check_specs(char_id, 'note'):
        log.write_note(await check_specs(char_id, 'note'))
    if options.get('equip') and base_char_info.equip_id:
        log.write_note('满足模组触发条件')

    # 计算面板属性
    log.write('**【Buff计算】**')
    buff_frame = init_buff_frame()
    for buff in buff_list:
        buff_name = buff_list[buff]['id'] if buff == "skill" else buff
        if not await check_specs(buff_name, 'crit'):
            buff_frame = await apply_buff(base_char_info, char, buff_frame, buff, buff_list[buff],
                                          is_skill, False, log, enemy)

    # 计算团辅
    # log.write('**【团辅计算】**')
    if options.get('buff'):
        buff_frame = await apply_buff(base_char_info, char, buff_frame, 'raidBuff', raid_blackboard,
                                      is_skill, False, log, enemy)

    # 攻击类型
    # log.write('**【攻击类型】**')
    damage_type = await extract_damage_type(base_char_info, char, is_skill, blackboard, options)
    if damage_type == 2:
        buff_frame['atk_scale'] *= buff_frame['heal_scale']

    # 灰喉-特判
    if "tachr_367_swllow_1" in buff_list:
        buff_frame['attackSpeed'] += buff_list["tachr_367_swllow_1"]["attack_speed"]
        log.write(
            f"[特殊] {display_names['tachr_367_swllow_1']}: "
            f"attack_speed + {buff_list['tachr_367_swllow_1']['attack_speed']}")

    # 泡泡
    if is_skill and blackboard.id == "skchr_bubble_2":
        buff_frame['atk'] = basic_frame['defense'] + buff_frame['defense'] - basic_frame['atk']

        log.write(
            f"[特殊] {display_names['skchr_bubble_2']}: 攻击力以防御计算({basic_frame['defense'] + buff_frame['defense']})")

    # 迷迭香
    if char_id in ["char_391_rosmon", "char_1027_greyy2", "char_421_crow", "char_431_ashlok", "char_4066_highmo",
                   "char_4039_horn"]:
        if char_id == "char_4039_horn" and options['melee']:
            pass
        else:
            buff_frame['maxTarget'] = 999
            log.write(f"[特殊] {display_names[char_id]}: maxTarget = 999")

    # 连击特判
    if not is_skill and await check_specs(char_id, "times"):
        t = await check_specs(char_id, "times")
        buff_frame['times'] = t
    if is_skill and await check_specs(blackboard.id, "times"):
        t = await check_specs(blackboard.id, "times")
        buff_frame['times'] = t
    if blackboard.id == "skchr_chyue_3" and options.get('warmup'):
        # 重岳3：暖机后普攻/技能均攻击2次
        buff_frame['times'] = 2
    if buff_frame['times'] > 1:
        log.write(f" [连击] {display_names[char_id]} - 攻击 {buff_frame['times']} 次")

    # 瞬发技能的实际基础攻击间隔
    # if isSkill and checkSpecs(blackboard.id, "cast_bat"):
    #     f = checkSpecs(blackboard.id, "cast_bat")
    #     basicFrame.baseAttackTime = f / 30
    #     log.write(f"[特殊] {displayNames[blackboard.id]} - 技能动画时间 {(f / 30):.3f}s, {f}帧")

    final_frame = await get_buffed_attributes(basic_frame, buff_frame)
    crit_buff_frame = init_buff_frame()
    crit_frame = {}
    # 暴击面板
    if options.get("crit"):
        log.write("**【暴击Buff计算】**")
        for buff in buff_list:
            # buff_name = blackboard.id if buff == "skill" else buff
            crit_buff_frame = await apply_buff(base_char_info, char, crit_buff_frame, buff,
                                               buff_list[buff], is_skill, True, log, enemy)
        # 计算团辅
        if options.get('buff'):
            crit_buff_frame = await apply_buff(base_char_info, char, crit_buff_frame, "raidBuff",
                                               raid_blackboard, is_skill, True, log, enemy)
        crit_frame = await get_buffed_attributes(basic_frame, crit_buff_frame)

    # ---- 计算攻击参数
    # 最大目标数
    if '阻挡的<@ba.kw>所有敌人' in char_data.description and buff_frame['maxTarget'] < basic_frame['blockCnt']:
        buff_frame["maxTarget"] = basic_frame['blockCnt']
    elif any(kw in char_data.description for kw in ["所有敌人", "群体法术伤害", "群体物理伤害"]):
        buff_frame["maxTarget"] = 999
    elif "恢复三个" in char_data.description and not (is_skill and char_id == "char_275_breeze"):
        buff_frame["maxTarget"] = max(buff_frame["maxTarget"], 3)
    if options.get("token"):
        if blackboard.id == "skchr_mgllan_3" or (is_skill and blackboard.id == "skchr_mgllan_2"):
            buff_frame["maxTarget"] = 999
        if blackboard.id == "skchr_ling_3":
            buff_frame["maxTarget"] = 4 if options["ling_fusion"] else 2

    # 计算最终攻击间隔，考虑fps修正
    fps = 30
    # 攻速上下界
    _spd = min(max(10, final_frame["attackSpeed"]), 600)
    if final_frame["attackSpeed"] != _spd:
        final_frame["attackSpeed"] = _spd
        log.write_note("达到攻速极限")
    # sec spec
    if ((await check_specs(blackboard.id, "sec") and is_skill) or
            (options.get('annie') and char_id == "char_1023_ghost2")):
        intv = 1
        if await check_specs(blackboard.id, "interval"):
            intv = await check_specs(blackboard.id, "interval")
        final_frame['baseAttackTime'] = intv
        final_frame['attackSpeed'] = 100
        buff_frame['attackSpeed'] = 0
        log.write_note(f"每 {intv} 秒造成一次伤害 / 治疗")

    real_attack_time = final_frame['baseAttackTime'] * 100 / final_frame['attackSpeed']
    frame = real_attack_time * fps
    # 额外帧数补偿 https://bbs.nga.cn/read.php?tid=20555008
    corr = await check_specs(char_id, "frame_corr") or 0
    corr_s = await check_specs(blackboard.id, "frame_corr")
    if corr_s is not False and is_skill:
        corr = corr_s
    if corr != 0:
        real_frame = math.ceil(frame)  # 有误差时，不舍入而取上界，并增加补正值(一般为1)
        real_frame += int(corr)
        # prefix = "+" if int(corr) > 0 else ""
        if is_skill:
            log.write_note("帧数补正")
            log.write("[补帧处理] 攻击间隔帧数 > 攻击动画帧数，实际攻击间隔需要补帧（参考动画帧数表）")
            log.write(f"[补帧处理] 技能理论 {round(frame)} 帧 / 实际 {real_frame} 帧")
        else:
            log.write("[补帧处理] 攻击间隔帧数 > 攻击动画帧数，实际攻击间隔需要补帧")
            log.write(f"[补帧处理] 普攻理论 {round(frame)} 帧 / 实际 {real_frame} 帧")
        frame = real_frame
    else:
        frame = round(frame)  # 无误差时，舍入成帧数
    frame_attack_time = frame / fps
    attack_time = frame_attack_time
    real_attack_time, real_attack_frame, pre_delay, \
        post_delay, scaled_anim_frame = await calculate_animation(char_id, blackboard.id, is_skill,
                                                                  real_attack_time, final_frame['attackSpeed'], log)
    # 根据最终攻击间隔，重算攻击力
    if is_skill and blackboard.id == "skchr_platnm_2":  # 白金
        rate = (attack_time - 1) / (buff_list["tachr_204_platnm_1"]["attack@max_delta"] - 1)
        # 熔断
        rate = min(max(rate, 0), 1)
        buff_frame['atk_scale'] = 1 + rate * (buff_list["tachr_204_platnm_1"]["attack@max_atk_scale"] - 1)
        final_frame = get_buffed_attributes(basic_frame, buff_frame)  # 重算
        log.write(
            f"[特殊] {display_names['tachr_204_platnm_1']}: atk_scale = {buff_frame.atk_scale:.3f} ({rate * 100:.1f}%蓄力)")
    elif buff_list.get("tachr_215_mantic_1") and attack_time >= buff_list["tachr_215_mantic_1"].delay:  # 狮蝎
        atk = basic_frame['atk'] * buff_list["tachr_215_mantic_1"].atk
        log.write(f"[特殊] {display_names['tachr_215_mantic_1']}: atk + {atk}")
        final_frame['atk'] += atk
        buff_frame['atk'] = final_frame['atk'] - basic_frame['atk']

    # 敌人属性
    def decimal_default(obj):
        if isinstance(obj, Decimal):
            return float(obj)
        raise TypeError

    enemy_buff_frame = json.loads(json.dumps(buff_frame, default=decimal_default))
    # 处理对普攻也生效的debuff
    for b in buff_list:
        buff_name = buff_list[b]['id'] if b == 'skill' else b
        if await check_specs(buff_name, "keep_debuff") and buff_name not in enemy_buff_frame:
            log.write_note("假设全程覆盖Debuff")
            enemy_buff_frame = await apply_buff(base_char_info, char, enemy_buff_frame, buff_name,
                                                buff_list[b], True, False, log, enemy)
    edef = max(0, ((enemy.defense + enemy_buff_frame['edef']) * enemy_buff_frame['edef_scale'] - enemy_buff_frame[
        'edef_pene']) * (1 - enemy_buff_frame['edef_pene_scale']))
    emr = min((enemy.magicResistance + enemy_buff_frame['emr']) * enemy_buff_frame['emr_scale'], 100)
    emr = max(emr - enemy_buff_frame['emr_pene'], 0)
    emrpct = emr / 100
    ecount = min(buff_frame['maxTarget'], enemy.count)
    if blackboard.id == "skchr_pudd_2" and is_skill and ecount > 1:
        ecount = buff_frame['maxTarget']
        log.write_note(f"相当于命中 {ecount} 个敌人")

    # 平均化链法伤害
    if char_data.subProfessionId in ['chain', 'chainhealer']:
        scale = 0.85
        s = 1
        tot = 1
        sks = [1]
        if is_skill and blackboard.id == "skchr_leizi_2":
            scale = 1
        elif base_char_info.equip_id and battle_equip_table[base_char_info.equip_id]:
            scale = basic_frame["equip_blackboard"]["trait"]["attack@chain.atk_scale"]
        elif char_data.subProfessionId == "chainhealer":
            prefab_id = char_id.replace("char", "tachr") + "_trait"
            scale = buff_list[prefab_id]["attack@chain.atk_scale"]
        for i in range(ecount - 1):
            s *= scale
            tot += s
            sks.append(s)

        log.write(f"[特殊] 链式攻击: 原本伤害倍率: {buff_frame['damage_scale']:.2f}")
        buff_frame['damage_scale'] *= tot / ecount
        sks_str = ", ".join(["{:.2f}".format(x) for x in sks])
        log.write("[特殊] 链式攻击: 连锁倍率: [{}], 平均伤害倍率 {:.2f}x".format(sks_str, buff_frame['damage_scale']))

    # 计算攻击次数和持续时间
    dur = await calc_durations(base_char_info, char, is_skill, attack_time, final_frame['attackSpeed'],
                               buff_frame, ecount, log)

    # 计算边缘情况
    rst = await check_reset_attack(blackboard.id, blackboard, options)
    if rst and rst != "ogcd" and is_skill:
        await calc_edges(blackboard, frame, dur, log)

    # 暴击次数
    if options.get('crit') and crit_buff_frame.get("prob"):
        if damage_type != 2:
            if buff_list.get("tachr_155_tiger_1"):
                dur.critCount = dur.duration / 3 * crit_buff_frame['prob']
            elif char_id == "char_420_flamtl":
                dur.critCount = math.floor(dur.duration / 5)
                match blackboard.id:
                    case "skchr_flamtl_1" | "skchr_flamtl_2":
                        if not is_skill:
                            dur.critCount += 1
                    case "skchr_flamtl_3":
                        if is_skill:
                            dur.critCount += 2
                print(f"按闪避 {dur.critCount}次计算")
            elif blackboard.id == "skchr_aurora_2" and is_skill:
                dur.critCount = options['freeze'] if 9 else 3
                log.write_note(f"按 {dur.critCount}次暴击计算")
            else:
                dur.critCount = dur.attackCount * crit_buff_frame['prob']

            if dur.critCount > 1:
                dur.critCount = math.floor(dur.critCount)
            # 折算为命中次数
            if buff_list.get("tachr_222_bpipe_1"):
                dur.critHitCount = dur.critCount * dur.times * min(enemy.count, 2)
            elif char_id == "char_420_flamtl":
                dur.critHitCount = dur.critCount * 2 * enemy.count
            else:
                dur.critHitCount = dur.critCount * dur.times * ecount

            if char_id == "char_1021_kroos2":
                dur.critHitCount = math.floor(dur.hitCount * crit_buff_frame['prob'])
                dur.hitCount -= dur.critHitCount
            else:
                dur.hitCount = (dur.attackCount - dur.critCount) * dur.times * ecount
        else:
            dur.critCount = 0
            dur.critHitCount = 0
    else:
        dur.critCount = 0
        dur.critHitCount = 0

    # 输出面板数据
    log.write("\n**【最终面板】**")
    atk_line = f"({basic_frame['atk']} + {buff_frame['atk']}) * {buff_frame['atk_scale']}"
    # if (buffFrame.damage_scale != 1) {atk_line += " * {buffFrame.damage_scale.toFixed(2)}";}
    log.write(f"攻击力 / 倍率:  {final_frame['atk']} = {atk_line}")
    log.write(f"攻击间隔: {final_frame['baseAttackTime']}s")
    log.write(f"攻速: {final_frame['attackSpeed']} % ")
    log.write(f"最终攻击间隔: {(real_attack_time * 30)}帧, {real_attack_time}s")
    if corr != 0:
        log.write(f" ** 帧数补正后攻击间隔: {frame}帧, {frame_attack_time}s ** ")
    else:
        log.write(f" ** 帧对齐攻击间隔: {frame}帧, {frame_attack_time}s ** ")

    if edef != enemy.defense:
        log.write(f"敌人防御:{edef}({(edef - enemy.defense)})")
    if emr != enemy.magicResistance:
        rate = (emr - enemy.magicResistance) / enemy.magicResistance
        log.write(f"敌人魔抗: {emr} % ({(rate * 100)} % )")
    if ecount > 1 or enemy.count > 1:
        log.write("目标数: {ecount} / {enemy.count}")

    # 计算伤害
    log.write("\n**【伤害计算】**")
    log.write(f"伤害类型: {['物理', '法术', '治疗', '真伤'][damage_type]}")
    dmg_prefix = "治疗" if damage_type == 2 else "伤害"
    # hit_damage = final_frame['atk']
    crit_damage = 0
    damage_pool = [0, 0, 0, 0, 0]  # 物理，魔法，治疗，真伤，盾
    extra_damage_pool = [0, 0, 0, 0, 0]
    # move = 0

    async def calculate_hit_damage(frame, scale):
        min_rate = 0.05
        # ret = 0
        if buff_list.get("tachr_144_red_1"):
            min_rate = buff_list["tachr_144_red_1"]['atk_scale']
        if buff_list.get("tachr_366_acdrop_1"):
            min_rate = options.get('cond') if buff_list["tachr_366_acdrop_1"]['atk_scale_2'] else buff_list[
                "tachr_366_acdrop_1"].atk_scale
        if damage_type == 0:
            ret = max(frame['atk'] - edef, frame['atk'] * Decimal(min_rate))
        elif damage_type == 1:
            ret = max(frame['atk'] * Decimal(1 - emrpct), frame['atk'] * Decimal(min_rate))
        else:
            ret = frame['atk']
        if ret <= frame['atk'] * Decimal(min_rate):
            log.write("[抛光]")
        if scale != 1:
            ret *= Decimal(scale)
            log.write(f"攻击增伤: {scale}x")
        return ret

    hit_damage = await calculate_hit_damage(final_frame, buff_frame['damage_scale'])
    damage_pool[damage_type] += hit_damage * Decimal(dur.hitCount)
    log.write(
        f"{dmg_prefix} {hit_damage} * 命中 {dur.hitCount} = {(hit_damage * Decimal(dur.hitCount))}直接{dmg_prefix}")

    # 计算额外伤害
    # 暴击
    if options.get('crit'):
        # console.log(critBuffFrame)
        if blackboard.id == "skchr_peacok_2":
            dur.critHitCount = 0
            if is_skill:
                log.write("创世纪 - 成功（暴击）为全体法术伤害")
                damage_type = 1
                ecount = enemy.count
                dur.critHitCount = enemy.count
        edef = max(0, ((enemy.defense + crit_buff_frame['edef']) * crit_buff_frame['edef_scale'] - crit_buff_frame[
            'edef_pene']) * (1 - crit_buff_frame['edef_pene_scale']))
        if edef != enemy.defense:
            log.write(f"[暴击]敌人防御: {edef}({(edef - enemy.defense)})")
        crit_damage = await calculate_hit_damage(crit_frame, crit_buff_frame['damage_scale'])
        if crit_damage > 0 and dur.critHitCount > 0:
            log.write(f"暴击{dmg_prefix}: {crit_damage}, 命中 {dur.critHitCount}")
        damage_pool[damage_type] += crit_damage * Decimal(dur.critHitCount)

    # 空(被动治疗没有写在天赋中)
    if char_id in ["char_1012_skadi2", "char_101_sora", "char_4045_heidi"]:
        ratio_sora = 0.1
        if is_skill and blackboard.id == "skchr_skadi2_3":
            ratio_sora = 0
        elif is_skill and blackboard.get("attack@atk_to_hp_recovery_ratio"):
            ratio_sora = blackboard.value("attack@atk_to_hp_recovery_ratio")
        extra_damage_pool[2] = \
            Decimal(ratio_sora) * final_frame['atk'] * Decimal(dur.duration * enemy.count)
        damage_pool[2] = 0
        damage_pool[3] = 0
        log.write("[特殊] 伤害为0 （以上计算无效），可以治疗召唤物")
        log.write_note("可以治疗召唤物")

    # 反射类-增加说明
    if await check_specs(blackboard.id, "reflect") and is_skill:
        log.write_note(f"技能伤害为反射 {dur.attackCount} 次的伤害")

    # 可变攻击力-重新计算
    if await check_specs(char_id, "grad") or (await check_specs(blackboard.id, "grad") and is_skill):
        if blackboard.id == "skchr_kalts_3" and not options['token']:
            pass
        else:
            skill_id = blackboard.id
            kwargs = {
                'charId': char_id,
                'skillId': skill_id,
                'isSkill': is_skill,
                'options': options,
                'basicFrame': basic_frame,
                'buffFrame': buff_frame,
                'finalFrame': final_frame,
                'buffList': buff_list,
                'blackboard': blackboard,
                'dur': dur,
                'attackTime': attack_time,
                'hitDamage': hit_damage,
                'damageType': damage_type,
                'edef': edef,
                'ecount': ecount,
                'emrpct': emrpct,
                'log': log
            }
            log.write("[特殊] 可变技能，重新计算伤害 ----")
            damage_pool[damage_type] = await calculate_grad_damage(kwargs)

    # 额外伤害
    for buff in buff_list:
        buff_name = buff
        bb = buff_list[buff]  # blackboard
        if buff_name == "skill":
            buff_name = bb['id']
        pool = [0, 0, 0, 0, 0]  # 物理，魔法，治疗，真伤，盾
        damage = 0
        # heal = 0
        atk = 0

        if not is_skill:  # 只在非技能期间生效
            match buff_name:
                case "skchr_ethan_1":
                    pool[1] += bb["attack@poison_damage"] * dur.duration * (1 - emrpct) * ecount
                case ("skchr_aglina_2" | "skchr_aglina_3" | "skchr_beewax_1" | "skchr_beewax_2" | "skchr_billro_1"
                      | "skchr_billro_2" | "skchr_billro_3" | "skchr_mint_1" | "skchr_mint_2" | "skchr_lin_1"
                      | "skchr_lin_2" | "skchr_lin_3"):
                    damage_pool[1] = 0
                    log.write(f"[特殊] {display_names[buff_name]}: 不普攻，伤害为0")
                case "skchr_takila_1" | "skchr_takila_2" | "skchr_mlynar_1" | "skchr_mlynar_2" | "skchr_mlynar_3":
                    damage_pool[0] = damage_pool[3] = 0
                    log.write(f"[特殊] {display_names[buff_name]}: 不普攻，伤害为0")
                case "skcom_heal_up[3]":
                    if options.get('token'):
                        damage_pool[0] = damage_pool[2] = 0
                    log.write(f"[特殊] {display_names[buff_name]}: 伤害/治疗为0 （以上计算无效）")
                case "skchr_silent_2":
                    if options.get('token'):
                        damage_pool[2] = 0
                    log.write(f"[特殊] {display_names[buff_name]}: 治疗为0 （以上计算无效）")
                case "skchr_ghost2_1", "skchr_ghost2_2", "skchr_ghost2_3":
                    if options.get('annie'):
                        damage_pool[1] = 0
                    log.write(f"[特殊] {display_names[buff_name]}: 伤害为0 （以上计算无效）")
                case "skchr_ironmn_1" | "skchr_ironmn_2" | "skchr_ironmn_3":
                    if options.get('token'):
                        damage_pool[0] = 0
                    log.write("不普攻")
                case _:
                    if buff == "skill":
                        continue  # 非技能期间，跳过其他技能的额外伤害判定
        match buff_name:
            case "tachr_129_bluep_1":
                damage = max(bb.poison_damage * (1 - emrpct), bb.poison_damage * 0.05)
                total_damage = damage * dur.duration * ecount
                if is_skill and blackboard.id == "skchr_bluep_1" and ecount > 1:
                    damage2 = damage * blackboard.value('atk_scale')
                    total_damage = damage * dur.duration + damage2 * 3
                    log.write(f"[特殊] {display_names['skchr_bluep_1']}: 副目标毒伤 {damage2} * 3s")
                pool[1] += total_damage
                log.write_note("毒伤按循环时间计算")
            case "tachr_293_thorns_1":
                poison = bb["damage[ranged]"] if options['thorns_ranged'] else bb["damage[normal]"]
                damage = max(poison * (1 - emrpct), poison * 0.05) * dur.duration * ecount
                pool[1] = damage
                if is_skill:
                    log.write_note("毒伤按循环时间计算")
            case "tachr_346_aosta_1":
                poison = final_frame['atk'] / buff_frame['atk_scale'] * bb['atk_scale']
                if blackboard.id == "skchr_aosta_2":
                    poison *= blackboard.value('talent_scale')
                log.write(f"流血伤害/秒: {poison:.1f}")
                damage = max(poison * (1 - emrpct), poison * 0.05) * dur.duration * ecount
                pool[1] = damage
                if is_skill:
                    log.write_note("毒伤按循环时间计算")
            case "tachr_181_flower_1":
                pool[2] += bb['atk_to_hp_recovery_ratio'] * final_frame['atk'] * dur.duration * enemy.count
                if is_skill:
                    log.write_note("可以治疗召唤物")
            case "tachr_436_whispr_1":
                if options["cond"]:
                    ts = blackboard.value('talent_scale') if blackboard.id == "skchr_whispr_2" else 1
                    extra_hps = bb["atk_to_hp_recovery_ratio"] * final_frame["atk"] * ts
                    pool[2] += extra_hps * dur.duration * enemy.count
                    log.write(f"天赋hps: {extra_hps:.1f}")
                    if is_skill:
                        log.write_note("天赋可以治疗召唤物")
            case ["tachr_188_helage_trait", "tachr_337_utage_trait", "tachr_475_akafyu_trait"]:
                pool[2] += bb["value"] * dur.hitCount
            case "tachr_485_pallas_2":
                pool[2] += bb["value"] * dur.hitCount
                if "pallas_e_t_2.value" in bb:
                    pool[2] += bb["pallas_e_t_2.value"] * dur.hitCount
            case ["tachr_421_crow_trait", "tachr_4066_highmo_trait"]:
                pool[2] += bb["value"] * dur.attackCount * min(ecount, 2)
            case "tachr_2013_cerber_1":
                cerber_t1_scale = bb["atk_scale"]
                cerber_t1_loss = 0
                if "max_atk_scale" in bb:
                    cerber_t1_scale = bb["max_atk_scale"]
                    cerber_t1_loss = 0.75
                damage = cerber_t1_scale * edef * (1 - emrpct) * buff_frame["damage_scale"]
                damage_loss = cerber_t1_loss * edef * (1 - emrpct) * buff_frame["damage_scale"]
                pool[1] += damage * dur.hitCount - damage_loss
                log.write(f"{display_names[buff_name]}: 额外法伤 {damage:.1f}, 命中 {dur.hitCount}")
                if damage_loss:
                    log.write(f"叠层损失伤害: {damage_loss:.1f} (75%防御)")
            case "tachr_391_rosmon_trait" | "tachr_1027_greyy2_trait":
                ntimes = 1
                if is_skill and blackboard.id == "skchr_rosmon_2":
                    ntimes = 3
                quake_atk = final_frame['atk'] / buff_frame['atk_scale'] * Decimal(bb["attack@append_atk_scale"])
                quake_damage = max(quake_atk - edef, quake_atk * Decimal(0.05))

                damage = quake_damage * dur.hitCount * ntimes
                log.write(
                    f"{display_names[buff_name]}: 余震攻击力 {quake_atk:.1f}, 单次伤害 {quake_damage:.1f}, 次数 {ntimes}")
                log.write(f"{display_names[buff_name]}: 余震命中 {dur.hitCount * ntimes}, 总伤害 {damage:.1f}")
                pool[0] += damage
            # 技能
            # 伤害类
            case "skchr_ifrit_2":
                damage = basic_frame['atk'] * Decimal(bb["burn.atk_scale"] * math.floor(bb['duration'])
                                                      * (1 - emrpct) * buff_frame['damage_scale'])
                log.write(f"[特殊] {display_names[buff_name]}: 灼烧伤害 {damage:.1f}, 命中 {ecount}")
                pool[1] += damage * dur.attackCount * ecount
            case "skchr_amgoat_2":
                damage = final_frame['atk'] / Decimal(2) * Decimal(
                    1 - enemy.magicResistance / 100) * Decimal(buff_frame['damage_scale'])
                log.write(
                    f"[特殊] {display_names[buff_name]}: 溅射伤害 {damage:.1f}, 命中 {dur.attackCount * (enemy.count - 1)}")
                pool[1] += damage * dur.attackCount * (enemy.count - 1)
            case "skchr_nightm_2":
                move = bb['duration'] / 4
                log.write_note(f"以位移{move:.1f}格计算")
                pool[3] += bb['value'] * move * ecount * buff_frame['damage_scale']
            case "skchr_weedy_3":
                if options.get('token'):
                    move = bb['force'] * bb['force'] / 3 + bb['duration'] / 5
                    log.write_note("召唤物伤害计算无效")
                    log.write_note("应为本体技能伤害")
                else:
                    move = bb['force'] * bb['force'] / 4 + bb['duration'] / 5
                log.write_note(f"以位移{move:.1f}格计算")
                pool[3] += bb['value'] * move * ecount * buff_frame['damage_scale']
            case "skchr_huang_3":
                finish_atk = final_frame['atk'] * Decimal(bb["damage_by_atk_scale"])
                damage = max(finish_atk - enemy.defense, finish_atk * Decimal(0.05)) * buff_frame['damage_scale']
                log.write(f"[特殊] {display_names[buff_name]}: 终结伤害 = {damage:.1f}, 命中 {ecount}")
                pool[0] += damage * ecount
            case "skchr_chen_2":
                damage = final_frame['atk'] * Decimal(1 - emrpct) * Decimal(buff_frame['damage_scale'])
                pool[1] += damage * dur.hitCount
                log.write(f"[特殊] {display_names[buff_name]}: 法术伤害 = {damage:.1f}, 命中 {dur.hitCount}")
            case "skchr_bibeak_1":
                if enemy.count > 1:
                    damage = final_frame['atk'] * (1 - emrpct) * buff_frame['damage_scale']
                    pool[1] += damage
                    log.write(f"[特殊] {display_names[buff_name]}: 法术伤害 = {damage:.1f}")
            case "skchr_ayer_2":
                damage = final_frame['atk'] * bb["atk_scale"] * (1 - emrpct) * buff_frame['damage_scale']
                pool[1] += damage * enemy.count * dur.hitCount
                log.write(
                    f"[特殊] {display_names[buff_name]}: 法术伤害 = {damage:.1f}, 命中 {enemy.count * dur.hitCount}")
                log.write("假设断崖的当前攻击目标也被阻挡")
            case ["skcom_assist_cost[2]", "skcom_assist_cost[3]", "skchr_myrtle_2",
                  "skchr_elysm_2", "skchr_skgoat_2", "skchr_utage_1", "skchr_snakek_2",
                  "skchr_blitz_1", "skchr_robrta_2"]:
                damage_pool[0] = 0
                damage_pool[1] = 0
                log.write(f"[特殊] {display_names[buff_name]}: 伤害为0 （以上计算无效）")
            case "skchr_zebra_1":
                damage_pool[2] = 0
                log.write(f"[特殊] {display_names[buff_name]}: 治疗为0 （以上计算无效）")
            case "skchr_sddrag_2":
                damage = final_frame['atk'] * bb["attack@skill.atk_scale"] * (1 - emrpct) * buff_frame['damage_scale']
                log.write(f"[特殊] {display_names[buff_name]}: 法术伤害 = {damage:.1f}, 命中 {dur.hitCount}")
                pool[1] += damage * dur.hitCount
            case ["skchr_haak_2", "skchr_haak_3"]:
                log.write_note("攻击队友15次(不计入自身dps)")
            case "skchr_podego_2":
                log.write(
                    f"[特殊] {display_names[buff_name]}: 直接伤害为0 （以上计算无效）, 效果持续{bb['projectile_delay_time']}秒")
                damage = final_frame['atk'] * Decimal(bb['projectile_delay_time'] * (1 - emrpct) *
                                                      enemy.count * buff_frame['damage_scale'])
                pool[1] = damage
                damage_pool[1] = 0
            case ["skchr_beewax_2", "skchr_mint_2"]:
                if is_skill:
                    damage = final_frame['atk'] * bb['atk_scale'] * (1 - emrpct) * ecount * buff_frame['damage_scale']
                    pool[1] = damage
            case "skchr_tomimi_2":
                if is_skill and options['crit']:
                    damage = max(final_frame['atk'] - enemy.defense, final_frame['atk'] * 0.05)
                    log.write(
                        f"[特殊] {display_names[buff_name]}: "
                        f"范围伤害 {damage:.1f}, 命中 {dur.critHitCount * (enemy.count - 1)}")
                    log.write(
                        f"[特殊] {display_names[buff_name]}: "
                        f"总共眩晕 {(dur.critHitCount * bb['attack@tomimi_s_2.stun']):.1f} 秒")
                    pool[0] += damage * dur.critHitCount * (enemy.count - 1)
            case "skchr_archet_1":
                atk = final_frame['atk'] / bb['atk_scale'] * bb['atk_scale_2']
                hit = min(enemy.count - 1, bb['show_max_target']) * dur.hitCount
                damage = max(atk - enemy.defense, atk * 0.05) * buff_frame['damage_scale']
                log.write(f"[特殊] {display_names[buff_name]}: 分裂箭伤害 {damage.toFixed(1)}, 命中 {hit}")
                pool[0] += damage * hit
            case "skchr_archet_2":
                n = min(4, enemy.count - 1)
                if n > 0:
                    hit = (9 - n) * n / 2
                    log.write(f"[特殊] {display_names[buff_name]}: 弹射箭额外命中 {hit}({n}额外目标)")
                    pool[0] += hit_damage * hit
            case ["tachr_338_iris_trait", "tachr_469_indigo_trait", "tachr_4046_ebnhlz_trait",
                  "tachr_297_hamoni_trait"]:
                if is_skill and blackboard.id in ["skchr_iris_2", "skchr_ebnhlz_2"]:
                    pass
                else:
                    talent_key = char_id.replace("char", "tachr") + "_1"
                    # 倍率
                    scale = buff_list[talent_key].get("atk_scale", 1)
                    if is_skill and blackboard.id == "skchr_ebnhlz_3":
                        scale *= buff_list['skill']['talent_scale_multiplier']
                    # 个数
                    n_balls = bb['times']
                    if talent_key == "tachr_4046_ebnhlz_1" and options['cond_elite']:
                        n_balls += 1
                    # 伤害
                    extra_scale = 0
                    if "tachr_4046_ebnhlz_2" in buff_list and enemy.count == 1:
                        extra_scale = buff_list["tachr_4046_ebnhlz_2"].get("atk_scale", 0)
                    damage = hit_damage * (scale + extra_scale)  # hitDamage已经包含了damage_scale和法抗
                    md = damage * n_balls + hit_damage * (1 + extra_scale)
                    delta = md - hit_damage * (1 + extra_scale) * (1 + n_balls)
                    log.write(
                        f"[特殊] {display_names[buff_name]}: "
                        f"蓄力倍率 {scale:.2f}, 每层伤害 {damage:.1f}, 最大层数 {n_balls}。"
                        f"满蓄力+普攻伤害 {md:.1f}, 比连续普攻多 {delta:.1f}")
                    log.write_note(f"满蓄力伤害 {md:.1f}")
                    if is_skill:
                        log.write_note("DPS按满蓄力1次计算")
                    pool[1] += delta
            case "skchr_ash_3":
                atk = final_frame['atk'] / Decimal(bb['atk_scale']) * Decimal(
                    options['cond'] and bb['hitwall_scale'] or bb['not_hitwall_scale'])
                damage = max(atk - enemy.defense, atk * Decimal(0.05)) * buff_frame['damage_scale']
                pool[0] += damage * enemy.count
                log.write(f"[特殊] {display_names[buff_name]}: 爆炸伤害 {damage:.1f}, 命中 {enemy.count}")
            case "skchr_blitz_2":
                atk = final_frame['atk'] * bb['atk_scale']
                damage = max(atk - enemy.defense, atk * Decimal(0.05)) * buff_frame['damage_scale']
                pool[0] += damage * enemy.count
                log.write(f"[特殊] {display_names[buff_name]}: 范围伤害 {damage:.1f}, 命中 {enemy.count}")
            case "skchr_rfrost_2":
                atk = final_frame['atk'] / bb['atk_scale'] * bb['trap_atk_scale']
                damage = max(atk - enemy.defense, atk * Decimal(0.05)) * buff_frame['damage_scale']
                pool[0] += damage
                log.write(f"[特殊] {display_names[buff_name]}: 陷阱伤害 {damage:.1f}")
            case "skchr_tachak_1":
                atk = final_frame['atk'] * bb['atk_scale']
                damage = max(atk * (1 - emrpct), atk * Decimal(0.05)) * buff_frame['damage_scale']
                pool[1] += damage * bb['projectile_delay_time'] * enemy.count
                log.write(
                    f"[特殊] {display_names[buff_name]}: "
                    f"燃烧伤害 {damage:.1f}, 命中 {bb['projectile_delay_time'] * enemy.count}")
            case "skchr_pasngr_3":
                atk = final_frame['atk'] * Decimal(bb['atk_scale'])
                damage = max(atk * Decimal(1 - emrpct), atk * Decimal(0.05)) * Decimal(
                    buff_frame['damage_scale'])
                pool[1] += damage * ecount * 8
                log.write("[特殊] {}: 雷击区域伤害 {} (平均倍率 {}), 命中 {}".format(
                    display_names[buff_name],
                    damage,
                    buff_frame['damage_scale'],
                    8 * ecount)
                )
            case "skchr_toddi_2":
                atk = final_frame['atk'] / Decimal(bb["attack@atk_scale"]) * Decimal(
                    bb["attack@splash_atk_scale"])
                damage = max(atk - enemy.defense, atk * Decimal(0.05)) * buff_frame['damage_scale']
                pool[0] += damage * enemy.count * dur.hitCount
                log.write("[特殊] {}: 爆炸伤害 {}, 命中 {}".format(
                    display_names[buff_name],
                    damage,
                    enemy.count * dur.hitCount)
                )
            case "skchr_indigo_2":
                if options.get('cond'):
                    atk = final_frame['atk'] * bb["indigo_s_2[damage].atk_scale"]
                damage = max(atk * (1 - emrpct), atk * Decimal(0.05)) * buff_frame['damage_scale']
                pool[1] += damage * enemy.count * dur.duration * 2
                log.write("[特殊] {}: 法术伤害 {}, 命中 {}".format(
                    display_names[buff_name],
                    damage,
                    enemy.count * dur.duration * 2)
                )
                log.write_note("触发束缚伤害")
            case "tachr_426_billro_1":
                if is_skill:
                    damage = Decimal(bb['heal_scale']) * final_frame['maxHp']
                if options.get('charge'):
                    damage *= 2
                pool[2] += damage
            case "tachr_486_takila_1":
                if not is_skill:
                    damage = final_frame['atk'] * Decimal(
                        bb['atk_scale'] * (1 - emrpct) * buff_frame['damage_scale'])
                log.write_note("技能未开启时反弹法伤最高为 {}".format(damage))
            case "tachr_437_mizuki_1":
                scale = bb["attack@mizuki_t_1.atk_scale"]
                if blackboard.id == "skchr_mizuki_1" and is_skill:
                    scale *= buff_list['skill']['talent_scale']
                log.write(f"法伤倍率: {scale:.2f}x")
                damage = final_frame['atk'] / Decimal(buff_frame['atk_scale']) * Decimal(
                    scale) * Decimal(
                    1 - emrpct) * buff_frame['damage_scale']
                n_hit = bb["attack@max_target"]
                if is_skill:
                    if blackboard.id == "skchr_mizuki_2":
                        n_hit += 1
                    elif blackboard.id == "skchr_mizuki_3":
                        n_hit += 2
                n_hit = dur.attackCount * min(ecount, n_hit)
                pool[1] += damage * n_hit
                log.write(f"[特殊] {display_names[buff_name]}: 法术伤害 {damage:.1f}, 命中 {n_hit}")
            case "tachr_1014_nearl2_1":
                _scale = bb['atk_scale']
                _nHit = 2 if options['cond'] else 1
                damage = final_frame['atk'] * Decimal(_scale * buff_frame['damage_scale'])
                match blackboard.id:
                    case "skchr_nearl2_1":
                        if not is_skill:
                            log.write(f"本体落地伤害 {damage:.1f}, 不计入总伤害")
                    case "skchr_nearl2_2":
                        if is_skill:
                            pool[3] += damage * ecount * _nHit
                            log.write(
                                f"[特殊] {display_names[buff_name]}: 落地伤害 {damage:.1f}, 命中 {ecount * _nHit}")
                    case "skchr_nearl2_3":
                        if not is_skill:
                            log.write(f"本体落地伤害 {damage:.1f}, 不计入总伤害")
                        else:
                            _scale = buff_list['skill']['value']
                            damage = final_frame['atk'] * _scale * buff_frame['damage_scale']
                            pool[3] += damage * ecount * _nHit
                            log.write(
                                f"[特殊] {display_names[buff_name]}: 落地伤害 {damage:.1f}, 命中 {ecount * _nHit}")
            case "skchr_lmlee_2":
                lmlee_2_scale = bb["default_atk_scale"] + bb["factor_atk_scale"] * bb["max_stack_cnt"]
                damage = final_frame["atk"] * Decimal(lmlee_2_scale * (1 - emrpct) * buff_frame["damage_scale"])
                # pool[1] += damage * ecount
                log.write(f"[特殊] {display_names[buff_name]}: 满层数爆炸伤害 {damage:.1f}, 命中 {ecount}")
                log.write_note(f"满层数爆炸伤害 {damage:.1f}")
            case ["uniequip_002_rope", "uniequip_002_slchan", "uniequip_002_snsant", "uniequip_002_glady"]:
                if is_skill:
                    force = buff_list["skill"].get("force", buff_list["skill"].get("attack@force"))
                    move = force + 1
                    log.write_note(f"以位移{move}格计算")
                    pool[1] += bb["trait"]["value"] * move * (1 - emrpct) * ecount * buff_frame["damage_scale"]
            # 间接治疗
            case "skchr_tiger_2":
                pool[2] += damage_pool[1] * bb['heal_scale']
            case "skchr_strong_2":
                pool[2] += damage_pool[0] * Decimal(bb['scale'])
            case "skcom_heal_self[1]" | "skcom_heal_self[2]":
                damage_pool[2] = 0
                pool[2] += bb['heal_scale'] * final_frame['maxHp']
            case "skchr_nightm_1":
                pool[2] += damage_pool[1] * bb["attack@heal_scale"] * min(enemy.count, bb["attack@max_target"])
            case "tachr_1024_hbisc2_trait" | "tachr_1020_reed2_trait":
                pool[2] += damage_pool[1] * Decimal(bb['scale'])
            case "skchr_folnic_2":
                pool[2] += Decimal(bb["attack@heal_scale"]) * Decimal(
                    final_frame['atk']) / Decimal(buff_frame['atk_scale']) * Decimal(dur.hitCount)
            case "skchr_breeze_2":
                damage = final_frame['atk'] / 2
                log.write(
                    f"[特殊] {display_names[buff_name]}: 溅射治疗 {damage:.1f}, 命中 {dur.attackCount * (enemy.count - 1)}")
                pool[2] += damage * dur.attackCount * (enemy.count - 1)
            case "skchr_ccheal_1":
                heal = final_frame['atk'] * bb['heal_scale'] * bb['duration'] * dur.duration / attack_time
                log.write(f"[特殊] {display_names[buff_name]}: HoT {heal:.1f}")
                pool[2] += heal
            case "skchr_ccheal_2":
                heal = final_frame['atk'] * bb['heal_scale'] * bb['duration']
                log.write(f"[特殊] {display_names[buff_name]}: HoT {heal:.1f}, 命中 {enemy.count}")
                pool[2] += heal * enemy.count
            case "skchr_shining_2" | "skchr_tuye_1":
                heal = final_frame['atk'] * bb.atk_scale
                log.write(f"[特殊] {display_names[buff_name]}: 护盾量 {heal}")
                pool[4] += heal
            case "skchr_cgbird_2":
                heal = final_frame['atk'] * Decimal(bb['atk_scale'])
                log.write(f"[特殊] {display_names[buff_name]}: 护盾量 {heal}, 命中 {ecount}")
                pool[4] += heal * ecount
            case "skchr_tknogi_2" | "skchr_lisa_3":
                heal = final_frame['atk'] * Decimal(bb["attack@atk_to_hp_recovery_ratio"]) * Decimal(
                    enemy.count) * Decimal(dur.duration - 1)
                log.write(f"[特殊] {display_names[buff_name]}: HoT {heal:.1f}，可以治疗召唤物")
                log.write_note("可以治疗召唤物")
                log.write_note("第一秒无治疗效果（待确认）")
                pool[2] += heal
                damage_pool[2] = 0
                log.write("[特殊] 直接治疗为0")
            case "skchr_blemsh_1":
                heal = final_frame['atk'] * bb['heal_scale'] / buff_frame['atk_scale']
                pool[2] += heal
            case "skchr_blemsh_2":
                heal = final_frame['atk'] * Decimal(bb["attack@atk_to_hp_recovery_ratio"]) / Decimal(
                    buff_frame['atk_scale'])
                log.write(f"每秒单体治疗: {heal:.1f}")
                log.write_note("可以治疗召唤物")
                pool[2] += heal * Decimal(dur.duration) * Decimal(enemy.count)
            case "skchr_blemsh_3":
                damage = final_frame['atk'] * Decimal(bb["attack@blemsh_s_3_extra_dmg[magic].atk_scale"])
                damage = max(damage * Decimal(1 - emrpct), damage * Decimal(0.05))
                heal = final_frame['atk'] / Decimal(buff_frame['atk_scale']) * Decimal(bb['heal_scale'])
                log.write(f"每次攻击额外法伤：{damage:.1f} （计算天赋加成），额外治疗: {heal:.1f}")
                pool[1] += damage * dur.attackCount
                pool[2] += heal * dur.attackCount
            case "skchr_rosmon_1":
                damage = final_frame['atk'] * bb['extra_atk_scale']
                damage = max(damage * (1 - emrpct), damage * 0.05) * dur.hitCount
                pool[1] += damage
                log.write(f"{display_names[buff_name]}: 法术伤害 {damage:.1f}")
            case "skchr_kirara_1":
                damage = final_frame['atk'] * bb["kirara_s_1.atk_scale"]
                damage = max(damage * (1 - emrpct), damage * 0.05) * dur.hitCount
                pool[1] += damage
                log.write(f"{display_names[buff_name]}: 法术伤害 {damage:.1f}")
            case "skchr_amiya2_2":
                arts_atk = final_frame['atk'] * bb['atk_scale']
                real_atk = final_frame['atk'] * bb['atk_scale_2']
                arts_dmg = max(arts_atk * (1 - emrpct), arts_atk * 0.05)
                log.write(f"[斩击] 法术伤害 {arts_dmg:.1f}, 命中 9, 真实伤害 {real_atk:.1f}, 命中 1")
                pool[1] += arts_dmg * 9
                pool[3] += real_atk
            case "skchr_kafka_1":
                log.write(f"[特殊] {display_names[buff_name]}: 直接伤害为0 （以上计算无效）, 效果持续{bb.duration}秒")
                damage = final_frame['atk'] * (1 - emrpct) * enemy.count
                pool[1] = damage
                damage_pool[1] = 0
            case "skchr_kafka_2":
                damage = final_frame['atk'] * bb['atk_scale'] * (1 - emrpct) * enemy.count
                pool[1] = damage
            case "skchr_tuye_2":
                pool[2] = final_frame['atk'] * bb['heal_scale']
                log.write(f"[特殊] {display_names[buff_name]}: 瞬间治疗 {pool[2]:.1f}, 最多3次")
                log.write_note(f"瞬间治疗量 {pool[2]:.1f}")
                pool[2] *= 3
            case ("skchr_nothin_1", "skchr_nothin_2"):
                a = final_frame['atk'] * buff_list["tachr_455_nothin_1"]['atk_scale']
                damage = max(a - edef, a * 0.05)
                log.write_note(f"首次攻击伤害 {damage:.1f}")
            case ("skchr_heidi_1", "skchr_heidi_2", "skchr_skadi2_2", "skchr_sora_2"):
                if bb.max_hp:
                    buff_hp = final_frame['maxHp'] * bb['max_hp']
                    log.write_note(f"队友HP增加 {buff_hp:.1f}")
                if bb['defense']:
                    buff_def = final_frame['defense'] * bb['defense']
                    log.write_note(f"队友防御力增加 {buff_def:.1f}")
                if bb.atk:
                    buff_atk = final_frame['atk'] * bb['atk']
                    log.write_note(f"队友攻击力增加 {buff_atk:.1f}")
            case "skchr_skadi2_3":
                buff_atk = final_frame['atk'] * Decimal(bb['atk'])
                damage = final_frame['atk'] * Decimal(bb['atk_scale']) * buff_frame['damage_scale']
                pool[3] += damage * Decimal(enemy.count * dur.duration)
                log.write_note(f"队友攻击力增加 {buff_atk:.1f}")
                log.write_note(f"每秒真实伤害 {damage:.1f}, 总伤害 {pool[3]:.1f}")
                log.write_note("叠加海嗣时真伤x2，不另行计算")
            case "skchr_mizuki_3":
                if ecount < 3:
                    damage = Decimal(bb["attack@hp_ratio"]) * final_frame['maxHp']
                    log.write_note(f"目标数<3，自身伤害 {damage:.1f}")
                    pool[2] -= damage * dur.attackCount
            case ["tachr_473_mberry_trait", "tachr_449_glider_trait", "tachr_4041_chnut_trait"]:
                ep_ratio = bb['ep_heal_ratio']
                ep_scale = 1
                if is_skill:
                    if blackboard.id == "skchr_mberry_1":
                        ep_ratio = buff_list['skill']['ep_heal_ratio']
                    elif blackboard.id == "skchr_glider_1":
                        ep_ratio = buff_list['skill']["glider_s_1.ep_heal_ratio"]
                        ep_scale = 3
                        log.write_note("计算3秒内总元素回复量")
                    elif blackboard.id == "skchr_chnut_1":
                        ep_scale = buff_list['skill']['trait_scale']
                    elif blackboard.id == "skchr_chnut_2":
                        ep_scale = buff_list['skill']["attack@heal_continuously_scale"]
                if buff_list["tachr_4041_chnut_1"] and options.get("cond"):
                    ep_scale *= buff_list["tachr_4041_chnut_1"]['ep_heal_scale']
                log.write(f"元素治疗系数: {ep_ratio:.2f}x")
                if ep_scale != 1:
                    log.write(f"元素治疗倍率: {ep_scale:.2f}x")
                damage = final_frame['atk'] / buff_frame['heal_scale'] * ep_ratio * ep_scale
                ep_total = damage * dur.hitCount
                log.write_note(f"元素治疗 {damage:.1f} ({(ep_ratio * ep_scale):.2f} x)")
                log.write_note(f"技能元素HPS {(ep_total / dur.duration):.1f}")
            case "skchr_sleach_2":
                damage_pool[0] = 0
                damage_pool[1] = 0
                damage_pool[2] = 0
                log.write("伤害为0（以上计算无效）")
                pool[2] += final_frame['atk'] * Decimal(bb['atk_to_hp_recovery_ratio'] * dur.duration)
                log.write_note("可以治疗召唤物")
            case "skchr_sleach_3":
                damage_pool[0] = 0
                damage_pool[1] = 0
                damage_pool[2] = 0
                log.write("伤害为0（以上计算无效）")
                damage = max(final_frame['atk'] - edef, final_frame['atk'] * Decimal(0.05)) * Decimal(
                    buff_frame['damage_scale'])
                pool[0] += damage * ecount
                log.write(f"摔炮伤害 {damage:.1f} (damage_scale={buff_frame['damage_scale']:.3f}), 命中 {ecount}")
            case "skchr_gnosis_1":
                scale_mul_g1 = 1 if options.get("freeze") else buff_list["tachr_206_gnosis_1"].damage_scale_freeze / \
                                                               buff_list[
                                                                   "tachr_206_gnosis_1"].damage_scale_cold
                damage = final_frame['atk'] * (1 - emrpct) * buff_frame['damage_scale'] * scale_mul_g1
                pool[1] += damage * dur.hitCount
                log.write(
                    f"冻结伤害 {damage.toFixed(1)}"
                    f"(damage_scale={(buff_frame['damage_scale'] * scale_mul_g1).toFixed(2)}), 命中 {dur.hitCount}")
            case "skchr_gnosis_3":
                scale_mul_g3 = (1 if options["freeze"] else
                                buff_list["tachr_206_gnosis_1"]['damage_scale_freeze'] / buff_list[
                                    "tachr_206_gnosis_1"]['damage_scale_cold'])
                damage = final_frame['atk'] * Decimal(
                    (1 - emrpct) * bb['atk_scale'] * buff_frame['damage_scale'] * scale_mul_g3)
                pool[1] += damage * ecount
                log.write(
                    f"终结伤害 {damage:.1f} "
                    f"(damage_scale={(buff_frame['damage_scale'] * scale_mul_g3):.2f}), 命中 {ecount}, 按冻结计算")
            case "skchr_ling_3":
                if options["token"]:
                    log.write_note("不计算范围法伤")
                    log.write_note("(去掉“计算召唤物数据”才能计算范围伤害)")
                else:
                    damage = final_frame['atk'] * Decimal(
                        (1 - emrpct) * bb['atk_scale'] * buff_frame['damage_scale'])
                    pool[1] += damage * Decimal(ecount * dur.duration) * 2
                    log.write_note(f"召唤物范围法术伤害 {(damage * 2):.1f}/s")
            case "tachr_377_gdglow_1":
                if dur.critHitCount > 0 and is_skill:
                    damage = final_frame['atk'] * Decimal(1 - emrpct) * Decimal(
                        bb["attack@atk_scale_2"]) * Decimal(buff_frame['damage_scale'])
                    funnel = await check_specs(blackboard.id, "funnel") or 1
                    pool[1] += damage * enemy.count * funnel * dur.critHitCount
                    log.write_note(f"爆炸 {dur.critHitCount * funnel} 次, 爆炸伤害 {damage:.1f}")
            case "skchr_bena_1" | "skchr_bena_2":
                if options["annie"] and is_skill:
                    damage_pool[0] = 0
                    damage_pool[1] = 0
            case "skchr_kazema_1":
                if options["annie"]:
                    kazema_scale = buff_list['tachr_4016_kazema_1']['damage_scale']
                    if ('uniequip_002_kazema' in buff_list and
                            'damage_scale' in buff_list['uniequip_002_kazema'].talent and
                            not options["token"]):
                        kazema_scale = buff_list['uniequip_002_kazema'].talent['damage_scale']
                    damage = final_frame['atk'] / buff_frame.atk_scale * kazema_scale * (1 - emrpct) * buff_frame[
                        'damage_scale']
                    pool[1] += damage * ecount
                    log.write_note(f"替身落地法伤 {damage:.1f} ({kazema_scale:.2f}x)，命中 {ecount}")
                    if is_skill:
                        damage_pool[0] = 0
                        damage_pool[1] = 0
            case "skchr_kazema_2":
                kazema_scale = buff_list["tachr_4016_kazema_1"]['damage_scale']
                kz_name = "[纸偶]"
                kz_invalid = False
                if options.get("annie"):
                    kz_name = "[替身]"
                    if "uniequip_002_kazema" in buff_list \
                            and "damage_scale" in buff_list["uniequip_002_kazema"]['talent'] \
                            and not options.get('token'):
                        kazema_scale = buff_list["uniequip_002_kazema"]['talent']['damage_scale']
                elif not options.get('token'):
                    log.write_note("落地伤害需要勾选\n[替身]或[召唤物]进行计算")
                    kz_invalid = True
                if not kz_invalid:
                    damage = final_frame['atk'] * kazema_scale * (1 - emrpct) * buff_frame['damage_scale']
                    pool[1] += damage * ecount
                    log.write_note(f"{kz_name}落地法伤 {damage:.1f} ({kazema_scale:.2f}x)，命中 {ecount}")
                if options.get('annie') and is_skill:
                    damage_pool[0] = 0
                    damage_pool[1] = 0
            case "skchr_phenxi_2":
                ph_2_atk = final_frame['atk'] / Decimal(buff_frame['atk_scale']) \
                           * Decimal(bb['atk_scale_2'])
                damage = max(ph_2_atk - edef, ph_2_atk * Decimal(0.05)) * Decimal(buff_frame['damage_scale'])
                pool[0] += damage * 2 * dur.hitCount
                log.write_note(f"子爆炸伤害 {damage:.1f}\n以2段子爆炸计算")
            case "skchr_horn_2":
                if options.get('overdrive_mode'):
                    damage = final_frame['atk'] / Decimal(bb["attack@s2.atk_scale"]) * Decimal(
                        bb["attack@s2.magic_atk_scale"]) * Decimal(
                        1 - emrpct) * Decimal(buff_frame['damage_scale'])
                    pool[1] += damage * dur.hitCount
                    log.write(f"法术伤害 {damage:.1f}, 命中 {dur.hitCount}")
            case "skchr_horn_3":
                if options.get('overdrive_mode') and not options.get('od_trigger'):
                    horn_3_pct = dur.duration * (dur.duration - 0.2) / 2  # 0.4, 1.4,...,11.4
                    damage = final_frame['maxHp'] * Decimal(horn_3_pct) / Decimal(100)
                    pool[2] -= damage
                    log.write_note(f"生命流失 {damage:.1f}")
            case "skcom_heal_up[3]":
                if options.get('token'):
                    damage_pool[0] = damage_pool[2] = 0
                    log.write(f"[特殊] {display_names[buff_name]}: 伤害/治疗为0 （以上计算无效）")
            case "skchr_irene_3":
                irene_3_edef = max(0, (enemy.defense - enemy_buff_frame['edef_pene']) * (
                        1 - buff_list["tachr_4009_irene_1"]['def_penetrate']))
                irene_3_atk = final_frame['atk'] / Decimal(buff_frame['atk_scale']) * Decimal(
                    bb['multi_atk_scale'])
                damage = max(irene_3_atk - irene_3_edef, irene_3_atk * Decimal(0.05)) * buff_frame[
                    'damage_scale']
                pool[0] += damage * Decimal(bb['multi_times'] * ecount)
                log.write(f"[特殊] {display_names[buff_name]} 额外伤害-敌人防御 {irene_3_edef:.1f}")
                log.write(f"[特殊] {display_names[buff_name]} 轰击伤害 {damage:.1f} 命中 {bb['multi_times'] * ecount}")
            case "skchr_lumen_1":
                heal = final_frame['atk'] * bb["aura.heal_scale"]
                lumen_1_hitcount = bb["aura.projectile_life_time"] * dur.attackCount * enemy.count
                log.write(f"[特殊] {display_names[buff_name]}: HoT {heal:.1f}/s, 命中 {lumen_1_hitcount}")
                pool[2] += heal * lumen_1_hitcount
            case "skchr_ghost2_3":
                if is_skill and not options.get('annie'):
                    if options.get('cond'):
                        ghost2_3_atk = final_frame['atk'] * Decimal(bb["attack@atk_scale_ex"])
                        damage = max(ghost2_3_atk - edef, ghost2_3_atk * Decimal(0.05)) * buff_frame[
                            'damage_scale']
                        pool[0] += damage * dur.hitCount
                        log.write(f"[特殊] {display_names[buff_name]} 额外伤害 {damage:.1f} 命中 {dur.hitCount}")
                    else:
                        damage = final_frame['maxHp'] * bb["attack@hp_ratio"]
                        pool[2] -= damage * dur.hitCount
            case "skchr_pianst_2":
                damage = final_frame['atk'] * bb.atk_scale * (1 - emrpct) * buff_frame.damage_scale
                pool[1] += damage * enemy.count
                log.write(f"[特殊] {display_names[buff_name]} 额外伤害 {damage:.1f} 命中 {enemy.count}")
            case "tachr_4047_pianst_1":
                damage = final_frame['atk'] * Decimal(
                    bb['atk_scale'] * (1 - emrpct) * buff_frame['damage_scale'])
                log.write_note(f"反弹伤害 {damage:.1f}, 不计入DPS")
            case "tachr_4046_ebnhlz_2":
                if enemy.count == 1:
                    damage = Decimal(final_frame['atk']) / Decimal(buff_frame['atk_scale']) * \
                             Decimal(Decimal(bb['atk_scale']) * Decimal(1 - emrpct) *
                                     Decimal(buff_frame['damage_scale']))
                    pool[1] += damage * dur.hitCount
                    log.write(f"[特殊] {display_names[buff_name]} 额外伤害 {damage:.1f} 命中 {dur.hitCount}")
                elif enemy.count > 1 and "atk_scale_2" in bb:
                    damage = final_frame['atk'] / buff_frame['atk_scale'] * bb['atk_scale_2'] * (
                            1 - emrpct) * buff_frame['damage_scale']
                    pool[1] += damage * dur.attackCount * (enemy.count - 1)
                    log.write(
                        f"[特殊] {display_names[buff_name]} 额外伤害 {damage:.1f} "
                        f"命中 {dur.attackCount * (enemy.count - 1)}")
            case "skchr_greyy2_2":
                greyy2_2_count = bb.projectile_delay_time / bb.interval
                damage = final_frame['atk'] * bb['atk_scale'] * (1 - emrpct) * buff_frame['damage_scale']
                pool[1] += damage * greyy2_2_count * enemy.count
                damage_pool[1] = 0
                extra_damage_pool[0] = 0
                log.write("[特殊] {}: 直接伤害为0 （以上计算无效）".format(display_names[buff_name]))
                log.write("[特殊] {}: 额外伤害 {:.1f} 命中 {}".format(
                    display_names[buff_name],
                    damage,
                    enemy.count * greyy2_2_count)
                )
            case "skchr_gvial2_1":
                gvial2_scale = 1
                if "tachr_1026_gvial2_2" in buff_list:
                    if options.get('cond'):
                        gvial2_scale = buff_list["tachr_1026_gvial2_2"].heal_scale_2
                    else:
                        gvial2_scale = buff_list["tachr_1026_gvial2_2"].heal_scale_1
                pool[2] = damage_pool[0] * bb.heal_scale * gvial2_scale
                log.write("治疗倍率: {} * {:.2f}".format(bb.heal_scale, gvial2_scale))
            case "skchr_provs_2":
                damage = final_frame['atk'] * bb.atk_scale * (1 - emrpct) * buff_frame.damage_scale
                pool[1] += damage * enemy.count
                log.write("[特殊] {}: 额外伤害 {:.1f} 命中 {}".format(display_names[buff_name], damage, enemy.count))
            case "tachr_4064_mlynar_2":
                mlynar_t2_scale = bb['atk_scale']
                if is_skill and blackboard.id == "skchr_mlynar_3":
                    mlynar_t2_scale += buff_list["skill"]['atk_scale']
                    log.write_note("额外真伤对反弹也生效")
                damage = final_frame['atk'] / Decimal(buff_frame['atk_scale']) * Decimal(
                    mlynar_t2_scale) * Decimal(buff_frame['damage_scale'])
                log.write("反弹伤害 {:.1f}".format(damage))
                if is_skill:
                    log.write_note("反弹伤害 {:.1f}".format(damage))
            case "skchr_mlynar_3":
                if is_skill:
                    damage = final_frame['atk'] / Decimal(buff_frame['atk_scale']) * Decimal(
                        bb['atk_scale']) * Decimal(buff_frame['damage_scale'])
                    pool[3] += damage * dur.hitCount
                    log.write(f"[特殊] {display_names[buff_name]}: 额外伤害 {damage} 命中 {dur.hitCount}")
            case "skchr_lolxh_2":
                if is_skill and options['cond']:
                    lolxh_2_edef = max(0, edef - bb["attack@def_penetrate_fixed"])
                    damage = max(final_frame['atk'] - lolxh_2_edef, final_frame['atk'] * 0.05) * buff_frame[
                        'damage_scale']
                    log.write(f"[特殊] {display_names[buff_name]}: 额外攻击伤害 {damage:.1f} 命中 {dur.hitCount}")
                    log.write_note("半血敌人")
                    pool[0] += damage * dur.hitCount
            case "tachr_117_myrrh_1":
                if not is_skill:
                    heal = final_frame['atk'] * bb['heal_scale']
                    pool[2] += heal * enemy.count
                    log.write(f"[特殊] {display_names[buff_name]}: 瞬发治疗 {heal:.1f} 命中 {enemy.count}")
            case "skchr_qanik_2":
                qanik_2_damage_scale = buff_frame.damage_scale / buff_list[
                    "tachr_466_qanik_1"]['damage_scale'] if options['cond'] else buff_frame['damage_scale']
                damage = final_frame['atk'] / buff_frame['atk_scale'] * bb['critical_damage_scale'] * (
                        1 - emrpct) * qanik_2_damage_scale
                pool[1] += damage * ecount * enemy.count
                log.write(f"[特殊] {display_names[buff_name]}: 落地伤害 {damage:.1f}（不享受法术脆弱）")
                log.write(f"落地伤害倍率 {qanik_2_damage_scale:.2f}x，命中 {ecount * enemy.count}")
            case "tachr_157_dagda_2":
                if options.get('cond'):
                    pool[2] += damage_pool[0] * bb['heal_scale']
            case "skchr_dagda_1":
                dagda_1_atk = final_frame['atk'] * bb["attack@defensive_atk_scale"]
                damage = max(dagda_1_atk - enemy.defense, dagda_1_atk * 0.05) * buff_frame['damage_scale']
                log.write_note(f"反击伤害 {damage:.1f}/不计入dps")
            case "skchr_judge_1":
                damage = final_frame['atk'] / buff_frame['atk_scale'] * bb['atk_scale_2'] * (1 - emrpct) * buff_frame[
                    'damage_scale']
                pool[1] += damage * dur.hitCount
                log.write(f"法术伤害 {damage:.1f}, 命中 {dur.hitCount}")
            case "tachr_4065_judge_1":
                judge_shield_1 = final_frame['maxHp'] * Decimal(bb['born_hp_ratio'])
                judge_shield_2 = final_frame['maxHp'] * Decimal(bb['kill_hp_ratio'])
                if is_skill:
                    if blackboard.id == "skchr_judge_2":
                        judge_shield_2 = judge_shield_2 * Decimal(1 + buff_list['skill']['shield_scale'])
                    log.write_note(f"初始护盾 {judge_shield_1:.1f}")
                    log.write_note(f"技能击击杀护盾 {judge_shield_2}")
            case "tachr_4065_judge_2":
                if not final_frame.get('atk_scale'):
                    final_frame['atk_scale'] = 1
                if not final_frame.get('damage_scale'):
                    final_frame['damage_scale'] = 1
                damage = final_frame['atk'] / Decimal(final_frame['atk_scale']) * Decimal(
                    bb['atk_scale']) * Decimal(1 - emrpct) * Decimal(final_frame[
                                                                         'damage_scale'])
                if is_skill:
                    log.write_note(f"反弹伤害 {damage:.1f}")
            case "skchr_texas2_1":
                texas2_s1_dur = dur.duration + bb["attack@texas2_s_1[dot].duration"] - 1
                if not final_frame.get('damage_scale'):
                    final_frame['damage_scale'] = 1
                damage = bb["attack@texas2_s_1[dot].dot_damage"] * (1 - emrpct) * final_frame['damage_scale']
                log.write(f"持续法伤 {damage:.1f}, 按持续 {texas2_s1_dur:.1f}s计算")
                pool[1] += damage * texas2_s1_dur
            case "skchr_texas2_2":
                damage = final_frame['atk'] * bb['atk_scale'] * (1 - emrpct) * final_frame['damage_scale']
                pool[1] += damage * enemy.count
                log.write(f"落地法伤 {damage:.1f}, 命中 {enemy.count}")
            case "skchr_texas2_3":
                if not final_frame.get('damage_scale'):
                    final_frame['damage_scale'] = 1
                texas2_s3_aoe = final_frame['atk'] * Decimal(
                    bb["appear.atk_scale"] * (1 - emrpct) * final_frame['damage_scale'])
                texas2_s3_target = min(enemy.count, bb['max_target'])
                damage = final_frame['atk'] * Decimal(
                    bb['atk_scale'] * (1 - emrpct) * final_frame['damage_scale'])
                pool[1] += texas2_s3_aoe * Decimal(enemy.count * 2) + damage * Decimal(
                    texas2_s3_target) * Decimal(dur.duration)
                log.write(f"落地法伤 {texas2_s3_aoe:.1f}, 命中 {enemy.count * 2}")
                log.write(f"剑雨法伤 {damage:.1f}, 命中 {texas2_s3_target * dur.duration}")
            case "skchr_vigil_2":
                if options.get('token'):
                    pool[2] += final_frame['maxHp'] * bb["vigil_wolf_s_2.hp_ratio"]
            case "skchr_vigil_3":
                if options.get('cond') or options.get("token"):
                    # 计算本体属性。狼的法伤不享受特性加成
                    vigil_final_atk = final_frame['atk']
                    if options.get("token"):
                        token_id = base_char_info.char_id
                        base_char_info.char_id = "char_427_vigil"
                        vigil = await get_attributes(base_char_info, char, NoLog())
                        vigil_final = await get_buffed_attributes(vigil.attributesKeyFrames, buff_frame)
                        base_char_info.char_id = token_id
                        vigil_final_atk = vigil_final['atk']
                        if not options['cond']:
                            log.write_note("必定满足阻挡条件")
                    damage = \
                        vigil_final_atk * \
                        Decimal(bb["attack@vigil_s_3.atk_scale"] * (1 - emrpct)) * buff_frame['damage_scale']
                    pool[1] += damage * dur.hitCount
                    log.write(f"额外法伤 {damage}, 命中 {dur.hitCount}")
            case "skchr_ironmn_1":
                if not options.get('token'):
                    ironmn_s1_atk = 12 * bb.fake_scale
                    log.write_note(f"常态加攻+12%, 技能加攻+{ironmn_s1_atk}%")
                else:
                    damage_pool[0] = 0
                    log.write_note("召唤物结果无效")
            case "skchr_ironmn_2":
                if not options.get('token'):
                    ironmn_s2_skill_hp = 24  # 30s * 0.8%/s
                    ironmn_s2_normal_time = (100 - ironmn_s2_skill_hp * 2) / 0.4
                    ironmn_s2_skill_sp = ironmn_s2_skill_hp // (bb.fake_interval * 0.8)
                    ironmn_s2_normal_sp = ironmn_s2_normal_time // (3.5 * 0.8)
                    log.write_note("以开2次技能计算")
                    log.write_note(f"技能恢复SP: {ironmn_s2_skill_sp} / 30s")
                    log.write_note(f"常态恢复SP: {ironmn_s2_normal_sp} / {ironmn_s2_normal_time}s")
                else:
                    damage_pool[0] = 0
                    log.write_note("召唤物结果无效")
            case "skchr_ironmn_3":
                if not is_skill and options.get('token'):
                    damage_pool[0] = 0
                    log.write("不普攻")
            case "sktok_ironmn_pile3":
                if is_skill:
                    pile3_atk = final_frame['atk'] / 2
                    damage = max(pile3_atk - edef, pile3_atk * 0.05) * buff_frame.damage_scale
                    log.write(f"范围伤害 {damage:.1f}, 命中 {enemy.count * dur.hitCount}")
                    pool[0] += damage * enemy.count * dur.hitCount
            case "skchr_reed2_2":
                if is_skill:
                    damage = final_frame['atk'] * Decimal(bb['atk_scale']) * Decimal(
                        1 - emrpct) * Decimal(buff_frame['damage_scale'])
                    heal = damage * Decimal(buff_list["tachr_1020_reed2_trait"]['scale'])
                    reed2_interval = 1.567 if options.get('reed2_fast') else 0.8
                    reed2_hit_count = math.ceil((dur.duration - 0.167) / reed2_interval)  # 减去抬手时间
                    if options.get('reed2_fast'):
                        log.write_note("理想情况, 火球立即引爆")
                        log.write_note(f"每{reed2_interval:.3f}s命中三个火球")
                        reed2_hit_count = math.ceil((dur.duration - 0.167) / reed2_interval) * 3
                    else:
                        log.write_note(f"每{reed2_interval:.3f}s命中一个火球")
                    if options.get('rosmon_double'):
                        log.write_note("计算两组火球伤害")
                        reed2_hit_count *= 2

                    log.write(f"火球伤害 {damage:.1f}, 治疗 {heal:.1f}, 命中 {reed2_hit_count}")
                    pool[1] += damage * reed2_hit_count
                    pool[2] += heal * reed2_hit_count
            case "skchr_reed2_3":
                damage = final_frame['atk'] * Decimal(bb["talent@s3_atk_scale"]) * Decimal(
                    1 - emrpct) * Decimal(buff_frame['damage_scale'])
                reed2_boom_damage = final_frame['atk'] * Decimal(bb["talent@aoe_scale"]) * Decimal(
                    1 - emrpct) * Decimal(buff_frame['damage_scale'])
                pool[1] += damage * Decimal(dur.duration) * Decimal(ecount)
                log.write(f"灼痕伤害 {damage:.1f}, 命中 {dur.duration * ecount}")
                log.write_note(f"爆炸伤害 {reed2_boom_damage:.1f}, 半径1.7")
            case "skchr_puzzle_2":
                damage = final_frame['atk'] * bb["attack@atk_scale_2"] * (1 - emrpct) * buff_frame.damage_scale
                puzzle_hit_count = 15 * 10 + 6 * (dur.attackCount - 10)
                puzzle_hit_count_skill = 55
                pool[1] += damage * puzzle_hit_count_skill
                log.write_note("法伤按8s/60跳估算")
                log.write_note(f"总法伤 {(damage * puzzle_hit_count):.1f}/{puzzle_hit_count}跳估算")
            case "skchr_hamoni_2":
                damage = bb['damage_value'] * (1 - emrpct) * buff_frame['damage_scale']
                pool[1] += damage * dur.duration * enemy.count
                log.write(f"范围伤害 {damage:.1f}, 命中 {dur.duration * enemy.count}")
            case "tachr_197_poca_1":
                if options.get('cond') and "extra_atk_scale" in bb:
                    poca_t1_atk = final_frame['atk'] * Decimal(bb['extra_atk_scale'])
                    damage = max(poca_t1_atk - edef, poca_t1_atk * Decimal(0.05)) * Decimal(
                        buff_frame['damage_scale'])
                    log.write(f"额外伤害 {damage:.1f}, 命中 {dur.hitCount}")
                    pool[0] += damage * Decimal(dur.hitCount)
            case "skchr_firwhl_1":
                damage = final_frame['atk'] / Decimal(buff_frame['atk_scale']) * Decimal(
                    bb["burn.atk_scale"] * (
                            1 - emrpct) * buff_frame['damage_scale'])
                pool[1] += damage * Decimal(bb['burn_duration'] * ecount)
            case "skchr_firwhl_2":
                firwhl_burn_time = dur.duration + bb['projectile_life_time'] - 1
                damage = final_frame['atk'] * Decimal(
                    bb["attack@burn.atk_scale"] * (1 - emrpct) * buff_frame['damage_scale'])
                pool[1] += damage * Decimal(firwhl_burn_time * ecount)
                log.write_note(f"燃烧时间以{firwhl_burn_time:.1f}s计算")
                log.write(f"燃烧伤害 {damage:.1f}, 命中 {firwhl_burn_time * ecount}")
            case "tachr_4080_lin_1":
                damage = final_frame['atk'] * Decimal(
                    bb['atk_scale'] * (1 - emrpct) * buff_frame['damage_scale'])
                log.write_note(f"破壁伤害 {damage:.1f}")
                lin_shield = bb['value']
                if blackboard.id == "skchr_lin_3" and is_skill:
                    lin_shield *= buff_list["skill"]['talent_scale']
                log.write_note(f"琉璃璧抵挡伤害 {lin_shield:.1f}")
            case "skchr_chyue_2":
                # 第一段aoe, 不计第一天赋
                if enemy.count > 1:
                    chyue_t1_scale = buff_list["tachr_2024_chyue_1"].damage_scale if options.get('cond') else 1
                    damage = max(final_frame['atk'] * Decimal(0.05),
                                 final_frame['atk'] - edef) * buff_frame['damage_scale'] / chyue_t1_scale
                    chyue_s2_hitc = min(enemy.count - 1, bb.max_target - 1)
                    pool[0] += damage * chyue_s2_hitc
                    log.write(f"范围伤害 {damage:.1f} (不计第一天赋), 命中 {chyue_s2_hitc}")
                # 第二段伤害，只计算主目标
                if options.get('cond'):
                    chyue_s2_atk = final_frame['atk'] / Decimal(bb['atk_scale']) * Decimal(
                        bb['atk_scale_down'])
                    damage = max(chyue_s2_atk * Decimal(0.05), chyue_s2_atk - edef) * Decimal(
                        buff_frame['damage_scale'])
                    log.write(f"落地伤害 {damage:.1f}, 命中 {ecount}")
                    pool[0] += damage
            case "skchr_chyue_3":
                if enemy.count > 1:
                    chyue_t1_scale = buff_list["tachr_2024_chyue_1"].damage_scale if options.get('cond') else 1
                    damage = max(final_frame['atk'] * Decimal(0.05),
                                 final_frame['atk'] - edef) * Decimal(
                        buff_frame['damage_scale']) / chyue_t1_scale
                    pool[0] += damage * (enemy.count - 1) * dur.hitCount
                    log.write(f"范围伤害 {damage:.1f} (不计第一天赋), 命中 {(enemy.count - 1) * dur.hitCount}")
            case "tachr_4082_qiubai_1":
                qiubai_t1_hit_skill = 0
                qiubai_t1_hit_extra = 0
                qiubai_t1_atk_extra = final_frame['atk']
                talent_scale = 1
                if is_skill:
                    # 根据技能和触发选项，设定攻击次数
                    # s1 不触发：技能攻击1 结束伤害 不计
                    # s1 触发：技能1 结束伤害 enemy.count
                    # s2 无论触发与否都计额外伤害 技能 hitCount，额外伤害 enemy.count*2
                    # 但是额外伤害不计攻击加成
                    # s3 不触发：不计，触发：计
                    match blackboard.id:
                        case "skchr_qiubai_1":
                            qiubai_t1_hit_skill = dur.hitCount
                            qiubai_t1_hit_extra = int(enemy.count) if options.get('cond') else 0
                            log.write("技能伤害触发第一天赋，范围伤害跟随选项")
                        case "skchr_qiubai_2":
                            log.write_note("全程触发第一天赋")
                            qiubai_t1_hit_skill = dur.hitCount
                            qiubai_t1_hit_extra = int(enemy.count) * 2
                        case "skchr_qiubai_3":
                            if options.get('cond'):
                                qiubai_t1_hit_skill = dur.hitCount
                                log.write_note("全程触发第一天赋")
                            else:
                                log.write_note("不计第一天赋伤害")
                            if buff_list['skill']['talent_scale']:
                                talent_scale = buff_list['skill']['talent_scale']
                    damage_atk = final_frame['atk'] / buff_frame['atk_scale'] * Decimal(
                        bb['atk_scale']) * Decimal(talent_scale) * Decimal(
                        1 - emrpct) * Decimal(buff_frame['damage_scale'])
                    damage_extra = qiubai_t1_atk_extra * Decimal(bb['atk_scale']) * Decimal(
                        talent_scale) * Decimal(
                        1 - emrpct) * Decimal(buff_frame['damage_scale'])
                    pool[1] += damage_atk * qiubai_t1_hit_skill + damage_extra * qiubai_t1_hit_extra

                    log.write(f"{display_names[buff_name]}: 额外伤害 {damage_atk} (天赋倍率 {talent_scale})")
                    if blackboard.id == "skchr_qiubai_2":
                        log.write(
                            f"{display_names[buff_name]}: 首尾刀额外伤害 {damage_extra.toFixed(1)}(不计攻击力加成)")
                    log.write(
                        f"{display_names[buff_name]}: 额外伤害次数: 攻击 {qiubai_t1_hit_skill} 额外 {qiubai_t1_hit_extra}")
                elif options.get('cond'):
                    damage = final_frame['atk'] * Decimal(bb['atk_scale']) * Decimal(
                        1 - emrpct) * Decimal(buff_frame['damage_scale'])
                    pool[1] += damage * dur.hitCount
            case "skchr_qiubai_1":
                damage = final_frame['atk'] * bb['aoe_scale'] * (1 - emrpct) * buff_frame['damage_scale']
                pool[1] += damage * enemy.count
            case "skchr_qiubai_2":
                qiubai_s2_a1 = final_frame['atk'] / buff_frame.atk_scale - bb.atk * basic_frame['atk']
                qiubai_s2_a2 = final_frame['atk'] / buff_frame.atk_scale * bb.sword_end_atk_scale
                qiubai_s2_d1 = qiubai_s2_a1 * bb.sword_begin_atk_scale * (1 - emrpct) * buff_frame.damage_scale
                qiubai_s2_d2 = max(qiubai_s2_a2 - edef, qiubai_s2_a2 * 0.05) * buff_frame.damage_scale
                log.write(f"{display_names[buff_name]}: 初始伤害攻击力 {qiubai_s2_a1:.1f}")
                log.write(
                    f"{display_names[buff_name]}: 初始伤害-法术: {qiubai_s2_d1:.1f}, 收尾伤害-物理: {qiubai_s2_d2:.1f}")
                pool[1] += qiubai_s2_d1 * enemy.count
                pool[0] += qiubai_s2_d2 * enemy.count
            # extraDamage switch ends here

        # 百分比/固定回血
        hpratiosec = bb.get("hp_recovery_per_sec_by_max_hp_ratio")
        hpsec = bb.get("hp_recovery_per_sec")
        if hpratiosec:
            if buff_name == "tachr_478_kirara_1":
                if options.get('cond'):
                    hpratiosec = bb["kirara_t_2.hp_recovery_per_sec_by_max_hp_ratio"]
                if is_skill and blackboard.id == "skchr_kirara_2":
                    hpratiosec *= buff_list["skill"]['talent_scale']
                log.write(f"天赋回血比例: {hpratiosec * 100} % / s")

            if buff_name == "tachr_344_beewax_1" and is_skill:
                pass
            elif buff_name == "tachr_362_saga_2":
                pass
            elif buff_name == "tachr_293_thorns_2":
                if blackboard.id == "skchr_thorns_2" and is_skill:
                    pool[2] += Decimal(hpratiosec) * Decimal(final_frame['maxHp']) * \
                               Decimal(dur.duration + dur.stunDuration - 2)
                    log.write_note("治疗从2秒后开始计算")
                else:
                    pass
            elif buff_name == "tachr_422_aurora_1":
                if not is_skill:
                    aurora_hp_time = level_data.spData.spCost / (
                            (1 + buff_frame.spRecoveryPerSec) * (1 + buff_frame.spRecoverRatio)) / 2 + dur.stunDuration
                    aurora_hps = hpratiosec * final_frame['maxHp']
                    pool[2] += aurora_hps * aurora_hp_time
                    log.write(f"HP恢复时间: {aurora_hp_time}s, HPS {aurora_hps}")
            elif buff_name == "skchr_blkngt_1":
                if is_skill and options.get('token'):
                    blkngt_hps = hpratiosec * final_frame['maxHp']
                    log.write_note(f"HPS: {blkngt_hps}")
                # else {}
            else:
                pool[2] += Decimal(hpratiosec) * Decimal(final_frame['maxHp']) * Decimal(
                    dur.duration + dur.stunDuration)
        if hpsec:
            if ((buff_name == "tachr_291_aglina_2" and is_skill) or
                    (buff_name == "tachr_188_helage_2" and not options.get('noblock'))):
                pass
            else:
                pool[2] += hpsec * (dur.duration + dur.stunDuration)
        # 自身血量百分比相关的治疗/伤害
        if bb.get("hp_ratio"):
            match buff_name:
                case "skchr_huang_3" | "skchr_utage_2" | "skchr_akafyu_2" | "skchr_kazema_2":  # 自爆
                    if not options.get('annie') and not options.get('token'):
                        damage = Decimal(bb['hp_ratio']) * final_frame['maxHp']
                        pool[2] -= damage
                        log.write_note(f"对自身伤害 {damage}")

        dmg = pool[0] + pool[1] + pool[3]
        if dmg > 0:
            log.write(f"[特殊] {display_names[buff_name]}: 额外伤害 {dmg}")
        if pool[2] > 0:
            log.write(f"[特殊] {display_names[buff_name]}: 额外治疗 {pool[2]}")
        elif pool[2] < 0:
            log.write(f"[特殊] {display_names[buff_name]}: 自身伤害 {pool[2]}")
        for i in range(5):
            extra_damage_pool[i] += pool[i]

    # 整理返回
    total_damage = sum(Decimal(damage_pool[i]) + Decimal(extra_damage_pool[i]) for i in [0, 1, 3])
    total_heal = sum(Decimal(damage_pool[i]) + Decimal(extra_damage_pool[i]) for i in [2, 4])
    extra_damage = sum(extra_damage_pool[i] for i in [0, 1, 3])
    extra_heal = sum(extra_damage_pool[i] for i in [2, 4])

    log.write(f"总伤害: {total_damage}")
    if total_heal != 0:
        log.write(f"总治疗: {total_heal}")

    dps_duration = dur.dpsDuration if dur.dpsDuration > 0 else dur.duration
    dps_duration += dur.prepDuration + dur.stunDuration
    if dps_duration != dur.duration:
        log.write(f"以 {dps_duration:.1f}s 计算DPS/HPS")
    if dps_duration == 0:
        dps_duration = 1
    dps = Decimal(total_damage) / Decimal(dps_duration)
    hps = Decimal(total_heal) / Decimal(dps_duration)
    # 均匀化重置普攻时的普攻dps
    if not is_skill and await check_reset_attack(blackboard.id, blackboard, options):
        d = Decimal(dur.attackCount) * Decimal(attack_time)
        log.write(f"以 {d}s ({dur.attackCount} 个攻击间隔) 计算普攻dps")
        if d != 0:
            dps = Decimal(total_damage) / Decimal(d)
            hps = Decimal(total_heal) / Decimal(d)
    log.write(f"DPS: {dps}, HPS: {hps}")
    log.write("----")

    return {
        'atk': final_frame['atk'],
        'dps': dps,
        'hps': hps,
        'dur': dur,
        'damageType': damage_type,
        'hitDamage': hit_damage,
        'critDamage': crit_damage,
        'extraDamage': extra_damage,
        'extraHeal': extra_heal,
        'totalDamage': total_damage,
        'totalHeal': total_heal,
        'maxTarget': ecount,
        'damagePool': damage_pool,
        'extraDamagePool': extra_damage_pool,
        'attackTime': attack_time,
        'frame': frame,
        'attackCount': dur.attackCount,
        'spType': level_data.spData.spType,
    }
