import math
from decimal import Decimal

from .CalCharAttributes import check_specs
from .load_json import dps_anim
from .log import Log
from .model import Character
from .model.InitChar import InitChar
from .model.models import BlackBoard, Dur


# 重置普攻判定
async def check_reset_attack(
        key: str, blackboard: BlackBoard, options: dict
):
    if await check_specs(key, "reset_attack") == "false":
        return False
    elif await check_specs(key, "overdrive") and not options.get('overdrive_mode'):
        return False
    else:
        return (
                await check_specs(key, "reset_attack") or
                blackboard.get('base_attack_time') or
                blackboard.get('attack@max_target') or
                blackboard.get('max_target')
        )


async def calc_durations(
        char_info: InitChar, char: Character, is_skill: bool, attack_time: float,
        attack_speed: int, buff_frame: dict, enemy_count: int, log: Log
) -> Dur:
    options = char_info.options
    char_id = char_info.char_id
    display_names = char.displayNames
    buff_list = char.buffList
    char_data = char.CharData
    level_data = char.LevelData
    blackboard = BlackBoard(buff_list['skill'])
    skill_id = blackboard.id
    sp_data = level_data.spData
    # duration = 0
    # attack_count = 0
    stun_duration = 0
    prep_duration = 0
    dps_duration = -1
    start_sp = 0
    rst = await check_reset_attack(skill_id, blackboard, options)
    sub_prof = char_data.subProfessionId

    log.write("\n**【循环计算】**")

    sp_type_tags = {
        1: "time",
        2: "attack",
        4: "hit",
        8: "special"
    }
    tags = [sp_type_tags[sp_data.spType]]  # 技能类型标记

    # 需要模拟的技能（自动回复+自动释放+有充能）
    if await check_specs(skill_id, "sim"):
        log.write_note("模拟120s时间轴")
        tags.append("sim")
        duration = 120
        fps = 30
        now = fps
        sp = sp_data.initSp * fps
        # max_sp = 999 * fps
        last = {}
        timeline = {}
        total = {}
        extra_sp = 0
        timeline_marks = {
            "attack": "-",
            "skill": "+",
            "ifrit": "",
            "archet": "",
            "chen": "",
            "recover_sp": "\\*",
            "recover_overflow": "x",
            "reset_animation": "\\*",
            "cancel_attack": "!"
        }

        # 技能动画(阻回)时间-帧
        cast_time = (await check_specs(skill_id, "cast_time") or
                     await check_specs(skill_id,
                                       "cast_bat") * 100 / attack_speed or attack_time * fps)
        skill_time = max(cast_time, attack_time * fps)

        def time_since(key):
            return now - (last.get(key) or -999)

        def action(key):
            if now not in timeline:
                timeline[now] = []
            timeline[now].append(key)
            last[key] = now
            total[key] = total.get(key, 0) + 1
            # console.log(now, key)

        # def cancelaction(key):
        #     if last[key] and last[key] >= 0:
        #         which = timeline[last[key]].indexOf(key)
        #         if which >= 0:
        #             timeline[last[key]].splice(which, 1)
        #             t = last[key]
        #             while t > 0:
        #                 if timeline[t] and timeline[t].indexOf(key) >= 0:
        #                     break
        #                 t -= 1
        #             last[key] = t
        #             total[key] -= 1
        #             action(f'cancel_{key}')

        # charge
        cast_sp = sp_data.spCost
        if options.get('charge') and check_specs(skill_id, "charge"):
            if skill_id == "skchr_chyue_1":
                cast_sp = sp_data.spCost * blackboard.cnt
            else:
                cast_sp = sp_data.spCost * 2

        # init sp
        if skill_id == "skchr_amgoat_2" and buff_list["tachr_180_amgoat_2"]:
            sp = (buff_list["tachr_180_amgoat_2"]['sp_min'] + buff_list["tachr_180_amgoat_2"]['sp_max']) / 2 * fps
        elif buff_list.get("tachr_222_bpipe_2"):
            sp = buff_list["tachr_222_bpipe_2"]['sp'] * fps
        elif buff_list.get("uniequip_002_archet") and buff_list["uniequip_002_archet"]['talent']["archet_e_t_2.sp"]:
            sp = buff_list["uniequip_002_archet"]['talent']["archet_e_t_2.sp"] * fps
        last["ifrit"] = last["archet"] = last["chen"] = 1  # 落地即开始计算 记为1帧
        start_sp = cast_sp - sp / fps

        # sp barrier
        max_sp = cast_sp * fps
        # if (!options.charge && checkSpecs(skillId, "charge")) max_sp *= 2;  // 充能技能1层直接放的情况
        if blackboard.get('ct'):
            max_sp = sp_data.spCost * fps * blackboard.ct
        if blackboard.get('cnt'):
            max_sp = sp_data.spCost * fps * blackboard.cnt

        log.write(
            f"[模拟]T = 120s, 初始sp = {(sp / fps)}, 技能sp = {cast_sp}, 技能动画时间 = {round(cast_time)}帧, sp上限设为 {max_sp / fps}")
        log.write(f"[模拟]攻击间隔 {attack_time}s")
        log.write_note(f"技能动画 {cast_time}帧")
        attack_anim = await check_specs(skill_id, "attack_animation")

        if attack_anim:
            # 缩放至攻击间隔
            attack_anim = min(round(attack_time * fps), attack_anim)
            log.write(f"[模拟] 攻击动画 = {attack_anim} 帧")

        if sp_data.spType == 1:
            sp = min(sp + fps, max_sp)  # 落地时恢复1sp
            log.write("[模拟] +1落地sp")

        while now <= duration * fps:
            # normal attack
            if sp < cast_sp * fps and time_since("attack") >= attack_time * fps and time_since("skill") >= skill_time:
                action("attack")
                if sp_data.spType == 2:
                    sp += fps
            # 技能已经cd好
            if sp >= cast_sp * fps and time_since("skill") >= skill_time:
                # 正常：普通攻击间隔结束后进入技能
                if time_since("attack") >= attack_time * fps:
                    action("skill")
                # elif skillId == "skchr_judge_1":
                #     # 斥罪：蓄力时，普攻可被打断，但是不蓄力时不会
                #     if options.charge and time_since("attack") < attackAnim:
                #         cancelaction("attack")
                #         action("skill")
                elif attack_anim and time_since("attack") == attack_anim:
                    # W，华法琳：普攻动画结束后进入技能（取消后摇）
                    action("reset_animation")
                    action("skill")
            # sp recover
            if time_since("skill") == 0:
                sp -= cast_sp * fps
            if time_since("skill") >= cast_time and sp < max_sp:
                if sp_data.spType == 1:
                    sp += (1 + buff_frame['spRecoveryPerSec'])

            # 乱火
            if buff_list.get("tachr_134_ifrit_2") and \
                    time_since("ifrit") >= buff_list["tachr_134_ifrit_2"]['interval'] * fps:
                action("ifrit")
                extra_sp = buff_list["tachr_134_ifrit_2"]['sp']

            # 兰登战术/呵斥
            intv_archet = buff_list["tachr_332_archet_1"]['interval'] if "tachr_332_archet_1" in buff_list else 2.5
            intv_chen = buff_list["tachr_010_chen_1"]['interval'] if "tachr_010_chen_1" in buff_list else 4
            if (buff_list.get("tachr_332_archet_1") or options.get('archet')) and time_since(
                    "archet") >= intv_archet * fps:
                action("archet")
                extra_sp += 1
            if (buff_list.get("tachr_010_chen_1") or options.get('chen')) and time_since("chen") >= intv_chen * fps:
                action("chen")
                extra_sp += 1
            if time_since("skill") >= cast_time and extra_sp > 0:
                sp += extra_sp * fps
                if sp <= max_sp:
                    action("recover_sp")
                else:
                    sp = max_sp
                    action("recover_overflow")
            extra_sp = 0
            now += 1

        if is_skill:
            attack_count = total['skill']
            duration = attack_count * skill_time / fps
        else:
            attack_count = total['attack']
            duration -= total['skill'] * skill_time / fps

            # 打印时间轴和特殊动作
            line_str = ""
            for t in timeline:
                line_str += ''.join([timeline_marks[x] for x in timeline[t]])
            log.write("[模拟] 时间轴: ")
            log.write(f"{line_str}")
            log.write("( -: 普攻, +: 技能, *: 取消后摇, x: sp溢出, !: 取消普攻)")

            if total.get("ifrit"):
                log.write(
                    f"[模拟] 莱茵回路(*): "
                    f"触发 {total['recover_sp']} / {total['ifrit']} 次, "
                    f"sp + {buff_list['tachr_134_ifrit_2']['sp'] * total['recover_sp']}")
            if total.get("archet"):
                log.write(f"[模拟] 兰登战术: 触发 {total['archet']} 次")
            if total.get("chen"):
                log.write(f"[模拟] 呵斥: 触发 {total['chen']} 次")
            if total.get("recover_sp"):
                log.write(f"[模拟] sp恢复成功 {total['recover_sp']} 次, 溢出 {total.get('recover_overflow', 0)} 次")
            if total.get("reset_animation"):
                log.write(f"[模拟] 取消攻击间隔(*) {total['reset_animation']}")
    else:
        # 准备时间
        if is_skill:
            match skill_id:
                case "skchr_mudrok_3":
                    prep_duration = blackboard.sleep
                case "skchr_amiya2_2":
                    prep_duration = 3.33
                case "skchr_surtr_3":
                    prep_duration = 0.67
                case "skchr_ash_2" | "skchr_nearl2_2" | "skchr_blemsh_2" | "skchr_ctable_1":
                    prep_duration = 1
                case "skchr_gnosis_3":
                    prep_duration = 1.167
                case "skchr_mint_2":
                    prep_duration = 1.33
                case "skchr_provs_2":
                    prep_duration = 0.767
                case "skchr_red_1":
                    log.write_note("落地1s，不影响技能时间")
                case "skchr_texas2_2":
                    log.write_note("落地1s，不影响技能时间")
                    prep_duration = 0.167

            # 快速估算
            attack_count = math.ceil((level_data.duration - prep_duration) / attack_time)
            duration = attack_count * attack_time
            start_sp = sp_data.spCost - sp_data.initSp

            if "tachr_180_amgoat_2" in buff_list:  # 乱火
                init_sp = sp_data.initSp + (
                        buff_list["tachr_180_amgoat_2"]['sp_min'] + buff_list["tachr_180_amgoat_2"]['sp_max']) / 2
                start_sp = sp_data.spCost - init_sp
            elif "tachr_222_bpipe_2" in buff_list:  # 军事传统
                start_sp = sp_data.spCost - sp_data.initSp - buff_list["tachr_222_bpipe_2"]['sp'] - (
                        buff_list["tachr_222_bpipe_2"]["bpipe_e_2[locate].sp"] or 0)
            elif "tachr_456_ash_2" in buff_list:
                start_sp = sp_data.spCost - sp_data.initSp - buff_list["tachr_456_ash_2"]['sp']
            elif "uniequip_002_archet" in buff_list and "archet_e_t_2.sp" in buff_list["uniequip_002_archet"]['talent']:
                start_sp = sp_data.spCost - sp_data.initSp - buff_list["uniequip_002_archet"]['talent'][
                    "archet_e_t_2.sp"]
            log.write(f"技能启动需要SP: {start_sp:.1f}")

            # 重置普攻
            if rst:
                if duration > (level_data.duration - prep_duration) and rst != "ogcd":
                    if options.get('overdrive_mode'):
                        log.write("[结束时重置普攻] 截断最后一个攻击间隔")
                    else:
                        log.write("[重置普攻] 截断最后一个攻击间隔")
                duration = level_data.duration - prep_duration
                # 抬手时间
                frame_begin = round((await check_specs(skill_id, "attack_begin") or 12))
                if skill_id == "skchr_glaze_2" and options.get('far'):
                    log.write_note("技能前摇增加至27帧")
                    frame_begin = 27
                t = frame_begin / 30
                attack_count = math.ceil((duration - t) / attack_time)
                log.write(f"技能前摇: {t:.3f}s, {frame_begin} 帧")
                if not await check_specs(skill_id, "attack_begin"):
                    log.write("（计算器默认值；请参考动画时间）")
                else:
                    log.write_note(f"技能前摇: {frame_begin} 帧")

            # 技能类型
            if "持续时间无限" in level_data.description or await check_specs(skill_id, "toggle"):
                if skill_id == "skchr_thorns_3" and not options.get('warmup'):
                    pass
                elif skill_id == "skchr_tuye_2":
                    log.write_note("取技能时间=暖机时间")
                    duration = sp_data.spCost / (1 + buff_frame['spRecoveryPerSec'])
                    attack_count = math.ceil(duration / attack_time)
                elif skill_id == "skchr_surtr_3":
                    lock_time = buff_list["tachr_350_surtr_2"]["surtr_t_2[withdraw].interval"]
                    duration = math.sqrt(600) + lock_time
                    attack_count = math.ceil(duration / attack_time)
                    log.write(f"损失100%血量耗时: {math.sqrt(600):.1f}s，锁血时间: {lock_time}s")
                    log.write_note(f"不治疗最大维持 {duration:.1f}s")
                else:
                    d = 180 if options.get('short_mode') else 1000
                    attack_count = math.ceil(d / attack_time)
                    duration = attack_count * attack_time
                    if await check_specs(skill_id, "toggle"):
                        log.write_note(f"切换类技能 (以{d}s计算)")
                        tags.extend(["toggle", "infinity"])
                    else:
                        log.write_note(f"永续技能 (以{d}s计算)")
                        tags.append("infinity")
            elif sp_data.spType == 8:
                if level_data.duration <= 0 and (blackboard.get('duration') and blackboard.duration > 0):
                    # 砾的技能也是落地点火，但是持续时间在blackboard里
                    level_data.duration = blackboard.duration
                    duration = blackboard.duration
                    attack_count = math.ceil(level_data.duration / attack_time)
                if level_data.duration > 0:  # 自动点火
                    tags.append("auto")
                    log.write('落地点火')
                    if prep_duration > 0:
                        duration = level_data.duration - prep_duration
                elif await check_specs(skill_id, "passive"):  # 被动
                    attack_count = 1
                    duration = attack_time
                    tags.append("passive")
                    log.write("被动")
                elif skill_id == "skchr_phatom_2":  # 傀影2
                    attack_count = blackboard.times
                    duration = attack_time * attack_count
                else:  # 摔炮
                    attack_count = 1
                    duration = 0
                    tags.append("auto instant")
                    log.write("落地点火, 瞬发")
            elif level_data.duration <= 0:
                if await check_specs(skill_id, "instant_buff"):  # 瞬发的有持续时间的buff，例如血浆
                    duration = blackboard.get("duration") or await check_specs(skill_id, "duration")
                    attack_count = math.ceil(duration / attack_time)
                    tags.extend(["instant", "buff"])
                    log.write_note("瞬发Buff，技能周期为Buff持续时间")
                elif await check_specs(skill_id, "magazine"):  # 弹药技能
                    mag = await check_specs(skill_id, "magazine")
                    if options.get('charge') and skill_id == "skchr_chen2_2":
                        mag = 20
                    elif skill_id == "skchr_ctable_2":
                        mag = blackboard.get("attack@trigger_time")
                    if "tachr_1013_chen2_1" in buff_list:
                        prob = buff_list["tachr_1013_chen2_1"]["spareshot_chen.prob"]
                        new_mag = math.floor(mag / (1 - prob))
                        log.write_note(f"计入 {new_mag - mag} 发额外弹药")
                        mag = new_mag
                    log.write(f"弹药类技能: {display_names[skill_id]}: 攻击 {mag} 次")
                    attack_count = mag
                    duration = attack_time * attack_count
                    if rst:
                        duration -= attack_time
                elif skill_id == "skchr_blkngt_2" and options.get('token'):
                    duration = blackboard.get("blkngt_s_2.duration")
                    attack_count = math.ceil(duration / attack_time)
                else:  # 普通瞬发
                    attack_count = 1
                    # 不占用普攻的瞬发技能，持续时间等于动画时间。否则持续时间为一次普攻间隔
                    if await check_specs(skill_id, "reset_attack") != "ogcd":
                        duration = attack_time
                    tags.append("instant")
                    log.write("瞬发")
                    # 施法时间-基于动画
                    if await check_specs(skill_id, "anim_key") and await check_specs(skill_id, "anim_cast"):
                        anim_key = await check_specs(skill_id, "anim_key")
                        anim_data = dps_anim[char_id][anim_key]
                        ct = anim_data['duration'] or anim_data

                        log.write(f"技能动画：{anim_key}, 释放时间 {ct} 帧")
                        log.write_note(f"技能动画: {ct} 帧")
                        if (duration < ct / 30 and sp_data.spType == 1) or rst == "ogcd":
                            duration = ct / 30
                    # 施法时间
                    if await check_specs(skill_id, "cast_time"):
                        ct = await check_specs(skill_id, "cast_time")
                        if duration < ct / 30 or rst == "ogcd":
                            log.write(f"技能动画: {ct} 帧(基于动画数据)")
                            log.write_note(f"技能动画: {ct} 帧")
                            if sp_data.spType == 1 or sp_data.spType == 2 or rst == "ogcd":
                                duration = ct / 30
            elif skill_id == "skchr_glady_3":
                attack_count = 6
                attack_time = 1.5
                log.write_note("[特殊] 持续9秒，第7次拖拽无伤害")
            elif options.get('annie'):
                duration = 20
                attack_count = math.ceil(duration / attack_time)
                log.write("傀儡师替身 - 持续20s")

            # 过载
            if await check_specs(skill_id, "overdrive"):
                # 重新估算前半时间
                attack_count_half = math.ceil((level_data.duration - prep_duration) / 2 / attack_time)
                duration_half = attack_count_half * attack_time
                if await check_specs(skill_id, "magazine"):
                    attack_count_half = math.ceil(attack_count / 2)
                    duration_half = attack_count_half * attack_time
                    log.write(f"一半弹药攻击 {attack_count_half} 次")
                if options.get("overdrive_mode"):
                    # 过载: 减去前半部分
                    duration -= duration_half
                    attack_count -= attack_count_half
                    if options["od_trigger"]:
                        # 立即结束
                        log.write_note("立即结束过载")
                        duration = attack_count = 0
                        if skill_id == "skchr_horn_2":
                            duration = 1.066  # 32f
                            attack_count = attack_count_half
                else:
                    # 前半
                    duration = duration_half
                    attack_count = attack_count_half
            # 特判
            if skill_id == "skchr_huang_3":
                attack_count -= 2
                log.write(f"[特殊] {display_names['skchr_huang_3']}: 实际攻击 {attack_count}段+终结")
            elif skill_id == "skchr_sunbr_2":  # 古米2准备时间延长技能时间
                prep_duration = blackboard.disarm
            elif skill_id == "skchr_qiubai_2":
                prep_duration = await check_specs(skill_id, "cast_time") / 30.0
            elif skill_id == "skchr_takila_2" and options.get('charge'):
                duration = blackboard.enhance_duration
                attack_count = math.ceil(duration / attack_time)
            elif char_id == "char_4055_bgsnow" and options.get('token'):
                # 不管精英化等级 统一按25秒计算
                if duration > 25:
                    duration = 25
                    attack_count = math.ceil(duration / attack_time)
                    log.write_note("[打字机]按持续25秒计算")
            elif skill_id == "skchr_ironmn_3" and options["token"]:
                attack_count = 10 if is_skill else 0
                duration = 15
                log.write_note("以攻击10次计算")
            elif skill_id == "skchr_chimes_2":
                attack_count = 1  # 只有一刀
                if options.get('od_trigger'):
                    duration = 0  # 选择立即结束，时间为0
                chimes_s2_cast = await check_specs(skill_id, "cast_time")  # 再加上尾刀时间，以动画时间计
                log.write_note(f"尾刀时间 {chimes_s2_cast} 帧")
                duration += chimes_s2_cast / 30.0
            elif skill_id == "skchr_qiubai_3":  # 仇白3
                # 计算当前普攻攻速
                fps = 30
                base_attack_time = 39  # 原本39帧
                anim_time = 35  # 动画35帧，如果攻击间隔大于这个数字 则补帧
                normal_aspd = attack_speed - Decimal(blackboard.attack_speed * blackboard.max_stack_cnt)

                aspd_list = [normal_aspd + Decimal(blackboard.attack_speed) * x for x in
                             range(int(blackboard.max_stack_cnt) + 1)]
                frame_list = [round(base_attack_time * 100 / x) if round(
                    base_attack_time * 100 / x) <= anim_time + 0.5 else round(base_attack_time * 100 / x) + 1 for x in
                              aspd_list]
                # frame_list = []
                # for x in aspd_list:
                #     f = base_attack_time * 100 / x
                #     if f > anim_time + 0.5:
                #         f = round(f) + 1
                #     else:
                #         f = round(f)
                #     frame_list.append(f)
                stack_frame = sum(frame_list)
                stack_attack_count = len(frame_list)

                stack_predelay = math.ceil(
                    (await check_specs(skill_id, "attack_begin") - 1) * 100 / attack_speed + 1)  # ceil(15 / 204% + 1)
                remain_frame = duration * fps - stack_predelay - stack_frame
                remain_attack_count = math.ceil(remain_frame / (fps * attack_time))
                edge = remain_frame - fps * attack_time * (remain_attack_count - 1)  # 给calcEdges调用
                tags.append(edge)
                attack_count = stack_attack_count + remain_attack_count
                log.write(f"攻速: {aspd_list}...")
                log.write(f"叠层攻击帧数(考虑帧数对齐补正): {frame_list}...")
                log.write(f"叠层时间 {stack_frame} 帧(包括第{stack_attack_count}次攻击)")

            # Jan 26: 处理伤害时间与技能持续时间不同的情况
            if buff_frame.get('dpsDuration'):
                dps_duration = buff_frame['dpsDuration']
                log.write_note(f"技能伤害持续{dps_duration}s")
                tags.append("diff")
            if buff_frame.get('dpsDurationDelta'):
                dps_duration = buff_frame['dpsDurationDelta'] + duration
                log.write_note(f"技能伤害持续{dps_duration}s")
                tags.append("diff")
        else:  # 普攻
            # 眩晕处理
            if skill_id == "skchr_fmout_2":
                stun_duration = blackboard.time
            elif skill_id == "skchr_peacok_2":
                stun_duration = blackboard.value("failure.stun") * (1 - blackboard.prob)
                log.write("[特殊] 计算平均晕眩时间")
            elif skill_id in ["skchr_amiya_2", "skchr_liskam_2", "skchr_ghost_2", "skchr_broca_2", "skchr_serum_1",
                              "skchr_aurora_1"]:
                stun_duration = blackboard.stun
            elif skill_id == "skchr_folivo_2" and options.get('token'):
                stun_duration = blackboard.stun
            elif skill_id == "skchr_rockr_2" and not options.get('od_trigger'):
                stun_duration = 20
            if stun_duration > 0:
                log.write(f"晕眩: {stun_duration}s")
            # 快速估算
            sp_ratio = 1
            if buff_frame['spRecoverRatio'] != 0:
                sp_ratio += buff_frame['spRecoverRatio']
                log.write(f"技力回复 {((1 + buff_frame['spRecoveryPerSec']) * sp_ratio).toFixed(2)} / s")
            attack_duration = sp_data.spCost / ((1 + buff_frame['spRecoveryPerSec']) * sp_ratio) - stun_duration
            if sp_ratio == 0:
                attack_duration = 180
                log.write_note("以180s计算普攻DPS")
            # 施法时间
            if await check_specs(skill_id, "cast_time"):
                ct = await check_specs(skill_id, "cast_time")
                if attack_time > ct / 30 and rst != "ogcd":
                    attack_duration -= (attack_time - ct / 30)
                    log.write(
                        f"[特殊] 技能释放时间: {ct} 帧, 普攻时间偏移 {((ct / 30) - attack_time):.3f}s ({attack_duration:.3f}s)")
                    log.write_note(f"技能动画(阻回): {ct} 帧")
            attack_count = math.ceil(attack_duration / attack_time)
            duration = attack_count * attack_time
            # 重置普攻（瞬发/ogcd除外）
            if rst and rst != "ogcd" and sp_data.spType != 8 and sp_ratio != 0:
                dd = sp_data.spCost / ((1 + buff_frame['spRecoveryPerSec']) * sp_ratio) - stun_duration
                if duration > dd:
                    log.write("[重置普攻] 截断最后一个攻击间隔")
                duration = dd
                # 抬手时间
                frame_begin = round((await check_specs(skill_id, "attack_begin") or 12))
                t = frame_begin / 30
                attack_count = math.ceil((duration - t) / attack_time)
                log.write(f"技能前摇: {t}s, {frame_begin}帧")
                if not await check_specs(skill_id, "attack_begin"):
                    log.write("（计算器默认值；请参考动画时间）")
            # June 20: 额外sp计算mixin
            _args = {
                'buffFrame': buff_frame,
                'buffList': buff_list,
                'spData': sp_data,
                'stunDuration': stun_duration,
                'attackCount': attack_count,
                'attackTime': attack_time,
                'duration': duration,
                'rst': rst,
                'options': options,
                'skill_id': skill_id,
                'enemyCount': enemy_count
            }
            # 技能类型
            match sp_data.spType:
                case 8:
                    if level_data.duration <= 0 and blackboard.get('duration'):
                        # print(f"Duration? l/b {skill_id} {levelData['duration']} {blackboard.duration}")
                        level_data.duration = blackboard.duration
                    if level_data.duration > 0:
                        tags.append("auto")
                        if skill_id == "skchr_nearl2_2":
                            attack_count = 0
                            duration = 1
                            log.write_note("不进行普攻")
                        else:
                            log.write("[特殊] 落地点火 - 取普攻时间=技能持续时间")
                            log.write_note("取普攻时间=技能持续时间")
                            attack_duration = level_data.duration
                            attack_count = math.ceil(attack_duration / attack_time)
                            duration = attack_count * attack_time
                    else:
                        attack_duration = 10
                        attack_count = math.ceil(attack_duration / attack_time)
                        duration = attack_count * attack_time
                        tags += ["auto", "instant"]
                        log.write("[特殊] 落地点火/瞬发 - 以10s普攻计算")
                        log.write_note("以10s普攻计算")
                    if await check_specs(skill_id, "passive"):
                        attack_count = 10
                        duration = attack_count * attack_time
                        tags.append("passive")
                        log.write("[特殊] 被动 - 以10次普攻计算")
                        log.write_note("以10次普攻计算")
                case 4:  # 受击回复
                    log.write("受击回复")
                case 2:  # 攻击恢复
                    log.write('攻击回复')
                    real_sp = sp_data.spCost
                    if options.get('charge') and await check_specs(skill_id, 'charge'):
                        if skill_id == 'skchr_chyue_1':
                            real_sp = sp_data.spCost * blackboard.cnt
                    else:
                        real_sp = sp_data.spCost * 2
                    if skill_id == 'skchr_chyue_3' and options.get('warmup'):
                        real_sp = sp_data.spCost / 2
                    if real_sp != sp_data.spCost:
                        log.write(f'实际需要SP: {real_sp:.1f}')
                    attack_count = real_sp

                    intv_chen = buff_list.get('tachr_010_chen_1', {}).get('interval', 4)
                    intv_archet = buff_list.get('tachr_332_archet_1', {}).get('interval', 2.5)
                    # extra_sp = 0
                    next = True

                    while attack_count > 0 and next:
                        duration = attack_count * attack_time
                        extra_sp = 0
                        if 'tachr_010_chen_1' in buff_list or options.get('chen', False):
                            extra_sp += duration // intv_chen
                        if 'tachr_332_archet_1' in buff_list or options.get('archet', False):
                            extra_sp += duration // intv_archet
                        if 'tachr_301_cutter_1' in buff_list:
                            p = buff_list['tachr_301_cutter_1'].get('prob', 0)
                            if skill_id == 'skchr_cutter_1':
                                extra_sp += (attack_count * 2 + 1) * p
                            else:
                                extra_sp += attack_count * 2 * p
                        next = attack_count + extra_sp >= real_sp
                        if next:
                            attack_count -= 1
                    if not next:
                        attack_count += 1
                    duration = attack_count * attack_time
                    line = []
                    if 'tachr_010_chen_1' in buff_list or options.get('chen', False):
                        line.append(f'呵斥触发 {duration // intv_chen} 次')
                    if 'tachr_332_archet_1' in buff_list or options.get('archet', False):
                        line.append(f'兰登战术触发 {duration // intv_archet} 次')
                    if 'tachr_301_cutter_1' in buff_list:
                        p = buff_list['tachr_301_cutter_1'].get('prob', 0)
                        n = (attack_count * 2 + 1) * p if skill_id == 'skchr_cutter_1' else attack_count * 2 * p
                        line.append(f'光蚀刻痕触发 {n:.2f} 次')
                    if len(line) > 0:
                        log.write('[特殊] ' + ', '.join(line))
                    if rst:
                        duration -= attack_time
                        if await check_specs(char_id, 'attack_begin'):
                            t = await check_specs(char_id, 'attack_begin')
                            duration += t / 30
                            log.write(f'普攻前摇{t}帧，技能取消后摇')
                        else:
                            log.write('不计最后一次普攻时间(需要前摇数据)')
                case 1:  # 普通，前面已经算过一遍了，这里只特判
                    sp_rate = 1 + buff_frame['spRecoveryPerSec']
                    if "tachr_002_amiya_1" in buff_list:  # 情绪吸收
                        attack_count = math.ceil((sp_data.spCost - stun_duration * sp_rate) / (
                                buff_list["tachr_002_amiya_1"]["amiya_t_1[atk].sp"] + attack_time * sp_rate))
                        log.write(
                            f'[特殊] {display_names["tachr_002_amiya_1"]}: '
                            f'attack sp = {attack_count * buff_list["tachr_002_amiya_1"]["amiya_t_1[atk].sp"]}')
                        duration = attack_count * attack_time
                    elif "tachr_134_ifrit_2" in buff_list:  # [莱茵回路]. 需要解出攻击次数
                        i = buff_list["tachr_134_ifrit_2"]['interval']
                        isp = i * sp_rate + buff_list["tachr_134_ifrit_2"]['sp']
                        recover_count = math.ceil((sp_data.spCost - i) / isp)  # recoverCount >= (spCost - i) / isp
                        r = (sp_data.spCost - recover_count * isp) / sp_rate
                        attack_duration = recover_count * i + r
                        attack_count = math.ceil(attack_duration / attack_time)
                        duration = attack_duration
                        log.write(
                            f'[特殊] {display_names["tachr_134_ifrit_2"]}: '
                            f"sp + {recover_count * buff_list['tachr_134_ifrit_2']['sp']}")
                    elif await check_specs(skill_id, "instant_buff"):  # 不稳定血浆: 减去buff持续时间
                        attack_duration -= blackboard.duration if blackboard.get('duration') else await check_specs(
                            skill_id, "duration")
                        attack_count = math.ceil(attack_duration / attack_time)
                        duration = attack_count * attack_time
                        log.write_note("瞬发Buff，技能周期为Buff持续时间")
                    elif "tachr_400_weedy_2" in buff_list and options.get('cannon'):  # 水炮充能，持续20s/cd35
                        m = math.floor(sp_data.spCost / 55)
                        a = m * 6 + m * 55 * sp_rate  # 前m个水炮充能+自然恢复的sp量
                        b = 6 + 20 * sp_rate  # 最后一个水炮持续期间最多恢复的sp
                        c = 6  # 最后一个水炮充的sp
                        # r = 0  # 计算还需要多少时间充满
                        if a + b > sp_data.spCost:  # 技能会在b期间蓄好
                            y = math.floor((sp_data.spCost - a) / (3 * sp_rate + 1.0))
                            z = (sp_data.spCost - a - y) / sp_rate - y * 3
                            r = 3 * y + z
                            c = math.floor(r / 3)
                        else:
                            r = (sp_data.spCost - a - b) / sp_rate + 20
                        attack_duration = m * 55 + r
                        attack_count = math.ceil(attack_duration / attack_time)
                        duration = attack_duration
                        log.write(f"[特殊] {display_names['tachr_400_weedy_2']}: 使用{m + 1}个水炮, 充能sp={m * 6 + c}")
                    elif options.get('charge') and await check_specs(skill_id, "charge"):  # 蓄力
                        charge_duration = sp_data.spCost
                        if buff_list.get('tachr_426_billro_2'):
                            charge_duration /= (1 + buff_frame['spRecoveryPerSec'] + buff_list[
                                "tachr_426_billro_2"]['sp_recovery_per_sec'])
                            log.write(
                                f"[特殊] {display_names['tachr_426_billro_2']}: 二段蓄力时间 {charge_duration:.1f} s")
                        attack_duration += charge_duration
                        duration = attack_duration
                        attack_count = math.ceil(attack_duration / attack_time)
                    elif options.get('equip') and sub_prof == "longrange":  # 守林模组
                        entry = buff_list.get("uniequip_002_milu") or buff_list.get(
                            "uniequip_003_fartth") or buff_list.get(
                            "uniequip_002_lunacu")
                        if entry:
                            log.write_note("每次攻击恢复1sp")
                            attack_count = math.ceil(
                                (sp_data.spCost - stun_duration * sp_rate) / (entry.trait.sp + attack_time * sp_rate))
                            log.write(f"[特殊] 攻击恢复SP = {attack_count * entry.trait.sp}")
                            duration = attack_count * attack_time
                    elif "uniequip_002_leizi" in buff_list and options.get('cond') \
                            and "sp" in buff_list["uniequip_002_leizi"].talent:  # 惊蛰模组
                        log.write_note("每次命中恢复1sp")
                        attack_count = math.ceil(
                            (sp_data.spCost - stun_duration * sp_rate) / (enemy_count + attack_time * sp_rate))
                        log.write(
                            f"[特殊] {display_names['uniequip_002_leizi']}: 攻击恢复SP = {attack_count * enemy_count}")
                        duration = attack_count * attack_time
                    elif buff_list.get("tachr_489_serum_1") and skill_id == "skchr_serum_1":
                        esp = buff_list["tachr_489_serum_1"].sp_recovery_per_sec * (
                                stun_duration - buff_list["tachr_489_serum_1"].delay)
                        log.write(f"眩晕时额外恢复 {esp:.1f}sp")
                        attack_duration = (sp_data.spCost - esp) / (1 + buff_frame['spRecoveryPerSec']) - stun_duration
                        attack_count = math.ceil(attack_duration / attack_time)
                        duration = attack_duration
                    elif buff_list.get("tachr_422_aurora_1"):
                        attack_duration = sp_data.spCost / ((1 + buff_frame['spRecoveryPerSec']) * sp_ratio) / 2
                        if attack_duration < stun_duration:
                            attack_duration = 0
                        attack_count = math.ceil(attack_duration / attack_time)
                        duration = sp_data.spCost / ((1 + buff_frame['spRecoveryPerSec']) * sp_ratio)
                        log.write(
                            f"[特殊] {display_names['tachr_422_aurora_1']}: "
                            f"普攻时间 {attack_duration:.3f}s / {duration:.3f}s, 攻击 {attack_count} 次")
                        log.write("(晕眩期间不回复技力)")
                    elif skill_id == "skchr_blkngt_2" and options.get('token'):
                        duration = attack_duration - blackboard.value("blkngt_s_2.duration")
                        attack_count = math.ceil(duration / attack_time)

            # ogcd穿插收益
            if rst == "ogcd":
                _ct = (await check_specs(skill_id, "cast_time") or 12) / 30
                weaving_gain = (duration - sp_data.spCost - _ct) / duration * 100
                log.write("[提示] 非GCD技能（技能不影响普攻间隔），计算器不计入穿插收益")
                if weaving_gain > 0:
                    log.write_note(f"OGCD技能 / 穿插收益: {weaving_gain} %")

    # 计算实际命中次数
    # attackCount = 发动攻击的次数(swings), hitCount = 命中敌人的次数(hits)
    hit_count = attack_count * buff_frame['times'] * enemy_count
    # 蓝毒2
    if is_skill:
        if skill_id == "skchr_bluep_2":
            hit_count += attack_count * (blackboard.value("attack@times") - 1)
        elif skill_id in ["skcom_assist_cost[2]", "skchr_utage_1", "skchr_tachak_1"]:  # 投降类
            hit_count = 0
        elif skill_id == "skchr_kroos2_2":
            extra_atk_count = attack_count - blackboard.value("attack@max_stack_count") / 2
            if extra_atk_count > 0:
                hit_count += extra_atk_count * 2
                log.write_note(f"4连击次数: {extra_atk_count}")

    # 重岳3
    if not is_skill and skill_id == "skchr_chyue_3" and options.get('warmup'):
        hit_count -= 1
        log.write_note("最后一次普攻只有1段伤害")

    log.write(f"持续: {duration}s")
    log.write(f"攻击次数: {attack_count * buff_frame['times']}({buff_frame['times']}连击x {attack_count})")

    times = buff_frame['times']
    data = {
        'attackCount': attack_count,
        'attackSpeed': attack_speed,
        'times': times,
        'hitCount': hit_count,
        'duration': duration,
        'stunDuration': stun_duration,
        'prepDuration': prep_duration,
        'dpsDuration': dps_duration,
        'tags': tags,
        'startSp': start_sp,
    }
    dur = Dur(data)
    return dur
