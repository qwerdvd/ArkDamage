from decimal import Decimal

from . import InitChar
from .CalCharAttributes import check_specs
from .Character import init_buff_frame, Character
from .model.models import BlackBoard


async def apply_buff(
        base_char_info: InitChar, char: Character, buff_frm, tag,
        blackbd, is_skill, is_crit, log, enemy
) -> dict:
    display_names = char.displayNames
    char_attr = char.attr

    buff_frame = buff_frm if buff_frm else init_buff_frame()
    blackboard = BlackBoard(blackbd)
    basic = char_attr['basic']
    char_id = base_char_info.char_id
    skill_id = char_attr['buffList']['skill']['id']
    options = base_char_info.options

    # 如果是技能期间，则取得技能ID, 否则不计算技能
    # specialtags里标示的（spType != 8的）被动技能：一直生效
    if tag == 'skill':
        if is_skill or await check_specs(skill_id, "passive"):
            tag = skill_id
        else:
            return buff_frm

    buff_frm['applied'][tag] = True
    done = False

    async def write_buff(text):
        line = ['']
        if tag == skill_id:
            line.append('[技能]')
        elif tag == 'raidBuff' or tag == 'fusion_buff':
            line.append('[团辅/拐]')
        elif "uniequip" in tag:
            line.append('[模组]')
        else:
            line.append('[天赋]')

        if await check_specs(tag, 'cond'):
            if options.get('cond'):
                line.append('[触发]')
            else:
                line.append('[未触发]')
        if await check_specs(tag, 'stack') and options.get('stack'):
            line.append('[满层数]')
        if await check_specs(tag, "ranged_penalty"):
            line.append('[距离惩罚]')
        line.append(display_names[tag] + ':')
        if text:
            line.append(text)
        log.write(" ".join(line))

    # 一般计算
    async def apply_buff_default():
        for tuple_item in blackboard:
            key = tuple_item[0]
            match key:
                case "atk" | "def":
                    prefix = "+" if getattr(blackboard, key) > 0 else ""
                    buff_frame[key] = Decimal(buff_frame[key]) + basic[key] * Decimal(
                        getattr(blackboard, key))
                    if getattr(blackboard, key) != 0:
                        await write_buff(
                            f"{key}: "
                            f"{prefix}{(getattr(blackboard, key) * 100):.1f}% "
                            f"({prefix}{(basic[key] * Decimal(getattr(blackboard, key))):.1f})")
                case "max_hp":
                    prefix = "+" if getattr(blackboard, key) > 0 else ""
                    if abs(getattr(blackboard, key)) > 2:  # 加算
                        buff_frame['maxHp'] += getattr(blackboard, key)
                        await write_buff(f"{key}: {prefix}{getattr(blackboard, key)}")
                    elif getattr(blackboard, key) != 0:  # 乘算
                        buff_frame['maxHp'] = Decimal(buff_frame['maxHp'])
                        buff_frame['maxHp'] += basic["maxHp"] * Decimal(getattr(blackboard, key))
                        await write_buff(
                            f"{key}: "
                            f"{prefix}{getattr(blackboard, key) * 100:.1f}% "
                            f"({prefix}{basic['maxHp'] * Decimal(getattr(blackboard, key)):.1f})")
                case "base_attack_time":
                    if blackboard.base_attack_time < 0:  # 攻击间隔缩短 - 加算
                        buff_frame['baseAttackTime'] += blackboard.base_attack_time
                        await write_buff(f"base_attack_time: {buff_frame['baseAttackTime']:.3f}s")
                    else:  # 攻击间隔延长 - 乘算
                        buff_frame['baseAttackTime'] = Decimal(buff_frame['baseAttackTime']) + basic[
                            "baseAttackTime"] * Decimal(
                            blackboard.base_attack_time)
                        await write_buff(
                            f"base_attack_time: "
                            f"+{(basic['baseAttackTime'] * Decimal(blackboard.base_attack_time)):.3f}s")
                case "attack_speed":
                    if getattr(blackboard, key) != 0:
                        prefix = "+" if getattr(blackboard, key) > 0 else ""
                        buff_frame['attackSpeed'] += blackboard.attack_speed
                        await write_buff(f"attack_speed: {prefix}{blackboard.attack_speed}")
                case "sp_recovery_per_sec":
                    buff_frame['spRecoveryPerSec'] += blackboard.sp_recovery_per_sec
                    prefix = "+" if getattr(blackboard, key) > 0 else ""
                    if blackboard.sp_recovery_per_sec != 0:
                        await write_buff(f"sp: {prefix}{blackboard.sp_recovery_per_sec:.2f}/s")
                case "atk_scale" | "def_scale" | "heal_scale" | "damage_scale":
                    buff_frame[key] *= getattr(blackboard, key)
                    if getattr(blackboard, key) != 1:
                        await write_buff(f"{key}: {getattr(blackboard, key):.2f}%")
                case "attack@atk_scale":
                    buff_frame['atk_scale'] *= blackboard.value('attack@atk_scale')
                    await write_buff(f"atk_scale: {buff_frame['atk_scale']:.2f}")
                case "attack@heal_scale":
                    buff_frame['heal_scale'] *= blackboard.value("attack@heal_scale")
                    await write_buff(f"heal_scale: {buff_frame['heal_scale']:.2f}")
                case "max_target" | "attack@max_target":
                    buff_frame['maxTarget'] = getattr(blackboard, key)
                    await write_buff(f"maxTarget: {getattr(blackboard, key)}")
                case "times" | "attack@times":
                    buff_frame['times'] = getattr(blackboard, key)
                    await write_buff(f"攻击次数: {getattr(blackboard, key)}")
                case "magic_resistance":
                    if getattr(blackboard, key) < -1:
                        buff_frame['emr'] += getattr(blackboard, key)
                        await write_buff(f"敌人魔抗: {getattr(blackboard, key)}% (加算)")
                    elif getattr(blackboard, key) < 0:
                        buff_frame['emr_scale'] *= (1 + getattr(blackboard, key))
                        await write_buff(f"敌人魔抗: {(getattr(blackboard, key) * 100):.1f}% (乘算)")
                case "prob":
                    if not blackboard.get('prob_override'):
                        buff_frame['prob'] = getattr(blackboard, key)
                        await write_buff(f"概率(原始): {round(buff_frame['prob'] * 100)}%")
                # 计算值，非原始数据
                case "edef":  # 减甲加算值（负数）
                    buff_frame['edef'] += getattr(blackboard, key)
                    await write_buff(f'敌人护甲: {getattr(blackboard, key)}')
                case "edef_scale":  # 减甲乘算值
                    buff_frame['edef_scale'] *= (1 + getattr(blackboard, key))
                    await write_buff(f'敌人护甲: {getattr(blackboard, key) * 100}%')
                case "edef_pene":  # 无视护甲加算值
                    buff_frame['edef_pene'] += getattr(blackboard, key)
                    await write_buff(f'无视护甲(最终加算): -{getattr(blackboard, key)}')
                case "edef_pene_scale":  # 无视护甲乘算值
                    buff_frame['edef_pene_scale'] = getattr(blackboard, key)
                    await write_buff(f'无视护甲(最终乘算): -{getattr(blackboard, key) * 100}%')
                case "emr_pene":  # 无视魔抗加算值
                    buff_frame['emr_pene'] += getattr(blackboard, key)
                    await write_buff(f'无视魔抗(加算): -{getattr(blackboard, key)}')
                case "prob_override":  # 计算后的暴击概率
                    buff_frame['prob'] = getattr(blackboard, key)
                    await write_buff(f"概率(计算): {round(buff_frame['prob'] * 100)}%")
                case "atk_override":  # 加算的攻击团辅
                    buff_frame['atk'] += getattr(blackboard, key)
                    prefix = "+" if getattr(blackboard, key) > 0 else ""
                    if getattr(blackboard, key) != 0:
                        await write_buff(f"atk(+): {prefix}{(getattr(blackboard, key) * 100):.1f}")
                case "sp_interval":  # June 20: {sp, interval, ...} -> 每interval秒/攻击x次回复sp点技力，可叠加
                    # interval == "hit" 为每次攻击恢复
                    # 也可以加入prob等额外参数用于特判
                    if getattr(blackboard, key)['interval'] == 'hit':
                        unit = ''
                    else:
                        unit = 's'
                    await write_buff(
                        f'额外技力: {getattr(blackboard, key)["sp"]} / {getattr(blackboard, key)["interval"]}{unit}')
                    getattr(blackboard, key)['tag'] = tag
                    buff_frame['spRecoverIntervals'].append(getattr(blackboard, key))

    # 特判
    # ------------------------d----------------------------------------------------------------
    # 备注信息
    if is_skill and not is_crit and await check_specs(tag, 'note'):
        log.write_note(await check_specs(tag, 'note'))

    if await check_specs(tag, 'cond'):  # 触发天赋类buff
        if not options.get('cond'):
            match tag:
                case 'tachr_348_ceylon_1':
                    blackboard.atk = blackboard.value("ceylon_t_1[common].atk")
                    await apply_buff_default()
                case 'skchr_glacus_2':
                    buff_frame['atk_scale'] = blackboard.value("atk_scale[normal]")
                    await write_buff(f"atk_scale: {buff_frame['atk_scale']} 不受天赋影响")
                case 'tachr_326_glacus_1':
                    if 'sp_recovery_per_sec' in blackboard:
                        del blackboard.sp_recovery_per_sec
                case 'skchr_cutter_2':
                    await apply_buff_default()
                case 'tachr_145_prove_1':  # 普罗旺斯
                    await apply_buff_default()
                case 'tachr_226_hmau_1':
                    del blackboard["heal_scale"]
                    await apply_buff_default()
                case 'tachr_279_excu_trait' | 'tachr_1013_chen2_trait' | 'tachr_440_pinecn_trait':
                    if is_skill and skill_id in ['skchr_excu_1', 'skchr_chen2_1', 'skchr_chen2_3', 'skchr_pinecn_2']:
                        log.write_note('技能享受特性加成(普攻无加成)')
                        await apply_buff_default()
                case 'tachr_113_cqbw_2':
                    if is_skill:
                        log.write_note('假设攻击目标免疫眩晕')
                case 'tachr_1012_skadi2_2':
                    log.write_note('无深海猎人')
                    blackboard.atk = blackboard.value('skadi2_t_2[atk][1].atk')
                    await apply_buff_default()
                case 'skchr_crow_2':
                    await write_buff(f'base_attack_time: {blackboard.base_attack_time}')
                    blackboard.base_attack_time *= basic.baseAttackTime
                    await apply_buff_default()
                case 'tachr_431_ashlok_1':
                    await apply_buff_default()
                case 'tachr_4013_kjera_1':
                    if options.get('freeze'):
                        blackboard.magic_resistance = -15
                        log.write_note("维持冻结: -15法抗")
                    await apply_buff_default()
                case 'tachr_322_lmlee_1':
                    if options.get('block'):
                        blackboard.attack_speed = blackboard.value("lmlee_t_1[self].attack_speed")
                        await apply_buff_default()
                case 'skchr_phenxi_3':
                    blackboard.atk_scale = blackboard.value('attack@atk_scale')
                    blackboard.delete('attack@atk_scale')
                    await apply_buff_default()
                case 'tachr_4009_irene_2':
                    await apply_buff_default()
                case 'tachr_4064_mlynar_1':
                    blackboard.atk_scale = blackboard.value('atk_scale_base')
                    await apply_buff_default()
            done = True
        else:
            match tag:
                case "tachr_348_ceylon_1":  # 锡兰
                    blackboard.atk = blackboard.value('ceylon_t_1[common].atk') + blackboard.value(
                        'celyon_t_1[map].atk')
                case "skchr_glacus_2":
                    buff_frame['atk_scale'] = blackboard.value("atk_scale[drone]")
                    await write_buff(f"atk_scale: {buff_frame['atk_scale']} 不受天赋影响")
                case 'tachr_326_glacus_1':
                    if 'sp_recovery_per_sec' in blackboard:
                        del blackboard.sp_recovery_per_sec
                case 'skchr_cutter_2':
                    buff_frame['maxTarget'] = blackboard.max_target
                    buff_frame['atk_scale'] = blackboard.atk_scale * blackboard.value('cutter_s_2[drone].atk_scale')
                    await write_buff(f"对空 atk_scale = {buff_frame['atk_scale']}")
                    done = True
                case 'tachr_187_ccheal_1':  # 贾维尔
                    buff_frame['defense'] += blackboard.defense
                    blackboard.defense = 0
                    await write_buff(f"def +{buff_frame['defense']}")
                case 'tachr_145_prove_1':
                    blackboard.prob_override = blackboard.value('prob2')
                case 'tachr_333_sidero_1':
                    del blackboard.times
                case 'tachr_197_poca_1' | 'skchr_apionr_1':
                    blackboard.edef_pene_scale = blackboard.def_penetrate
                case 'tachr_358_lisa_2':  # 铃兰2
                    if is_skill and skill_id == 'skchr_lisa_3':
                        del blackboard.damage_scale  # 治疗不计易伤
                case 'tachr_366_acdrop_1':  # 酸糖1: 不在这里计算
                    done = True
                case 'tachr_416_zumama_1':
                    del blackboard.hp_ratio
                case "tachr_347_jaksel_1":
                    blackboard.attack_speed = blackboard.value("charge_atk_speed_on_evade.attack_speed")
                case "tachr_452_bstalk_trait" | "tachr_476_blkngt_trait":
                    if options.get('token'):
                        done = True
                        log.write_note("特性对召唤物无效")
                case "tachr_427_vigil_trait":
                    if options.get('token'):
                        done = True
                        if is_skill:
                            log.write_note("召唤物只攻击阻挡的敌人")
                            log.write_note("但特性不生效")
                case "tachr_402_tuye_1":
                    blackboard.heal_scale = blackboard.value('heal_scale_2')
                case "tachr_457_blitz_1":
                    if is_skill and skill_id == 'skchr_blitz_2':
                        blackboard.atk_scale *= char_attr['buffList']['skill']['talent_scale']
                case "tachr_472_pasngr_1":
                    blackboard.damage_scale = blackboard.value("pasngr_t_1[enhance].damage_scale")
                case "tachr_1012_skadi2_2":
                    log.write_note("有深海猎人")
                    blackboard.atk = blackboard.value("skadi2_t_2[atk][2].atk")
                case "tachr_485_pallas_1":
                    if is_skill and skill_id == 'skchr_pallas_3' and options.get('pallas'):
                        log.write_note("第一天赋被3技能覆盖")
                        done = True
                    else:
                        blackboard.atk = blackboard.value("peak_performance.atk")
                case "skchr_crow_2":
                    blackboard.atk += blackboard.value("crow_s_2[atk].atk")
                    log.write_note("半血斩杀加攻")
                    await write_buff(f"base_attack_time: {blackboard.base_attack_time}x")
                    blackboard.base_attack_time *= basic['baseAttackTime']
                case "tachr_431_ashlok_1":
                    blackboard.atk = blackboard.value("ashlok_t_1.atk")
                    log.write_note("周围四格为地面")
                case "tachr_4013_kjera_1":
                    blackboard.atk = blackboard.value("kjera_t_1[high].atk")
                    log.write_note("存在2格以上的地面")
                    if options.get('freeze'):
                        blackboard.magic_resistance = -15
                        log.write_note("维持冻结: -15法抗")
                case "tachr_322_lmlee_1":
                    if options.get('block'):
                        blackboard.attack_speed = blackboard.value("lmlee_t_1[self].attack_speed") * 2
                case "skchr_phenxi_3":
                    blackboard.atk_scale = blackboard.value("attack@atk_scale")
                    blackboard.delete('attack@atk_scale')
                case "tachr_4039_horn_1":  # 号角2天赋，编号反了
                    blackboard.max_hp *= -1
                    del blackboard.hp_ratio
                case "tachr_4009_irene_2":
                    blackboard.attack_speed *= 2
                    if "atk" in blackboard:
                        blackboard.atk *= 2
                case "tachr_4064_mlynar_1":
                    blackboard.atk_scale = blackboard.value('atk_scale_up')
                    log.write_note("周围有3个敌人")
                case "tachr_363_toddi_1":
                    if char_attr['buffList']["uniequip_002_toddi"] and base_char_info.equipLevel >= 2:
                        blackboard.atk_scale = char_attr['buffList']['uniequip_002_toddi']['talent']['atk_scale']
                case "tachr_4062_totter_1":
                    del blackboard.atk_scale
                case "tachr_2024_chyue_1":
                    log.write_note("假设全程覆盖Debuff")
        # -- cond switch ends here - -
    elif await check_specs(tag, 'ranged_penalty'):  # 距离惩罚类
        if not options.get('ranged_penalty'):
            done = True
    elif await check_specs(tag, 'stack'):  # 叠层类
        if options.get('stack'):  # 叠层天赋类
            match tag:
                case "tachr_300_phenxi_1":
                    del blackboard.hp_ratio
                    blackboard.atk = blackboard.value("phenxi_t_1[peak_2].peak_performance.atk")
                    log.write_note("HP高于80%")
                case "tachr_2015_dusk_1" | "tachr_2023_ling_2":
                    if options.get('token'):
                        done = True
                case "tachr_188_helage_1" | "tachr_337_utage_1" | "tachr_475_akafyu_1":
                    blackboard.attack_speed = blackboard.value('min_attack_speed')
            if not done and blackboard.get('max_stack_cnt'):
                for key in ["atk", "def", "attack_speed", "max_hp"]:
                    if blackboard.get('key'):
                        old_value = getattr(blackboard, key)
                        value = old_value * blackboard.value('max_stack_cnt')
                        setattr(blackboard, key, value)
        else:
            done = True
    else:  # 普通类
        match tag:
            # ---- 天赋 ----
            case "tachr_185_frncat_1":  # 慕斯
                buff_frame['times'] = 1 + blackboard.value('prob')
                await write_buff(f"攻击次数x {buff_frame['times']}")
                done = True
            case "tachr_118_yuki_1":  # 白雪
                buff_frame['atk'] = basic['atk'] * blackboard.atk
                buff_frame['baseAttackTime'] = blackboard.base_attack_time
                await write_buff("攻击间隔+0.2s, atk+0.2x")
                done = True
            case "tachr_144_red_1":  # 红
                await write_buff(f"min_atk_scale: {blackboard.atk_scale}")
                done = True
            case "tachr_117_myrrh_1" | "tachr_2014_nian_2" | "tachr_215_mantic_1":  # 狮蝎，平时不触发
                done = True
            case "tachr_164_nightm_1":  # 夜魔 仅2技能加攻
                if skill_id == "skchr_nightm_1":
                    done = True
            case "tachr_130_doberm_1" | "tachr_308_swire_1":  # 诗怀雅: 不影响自身
                await write_buff("对自身无效")
                done = True
            case "tachr_109_fmout_1":  # 远山
                if skill_id == "skcom_magic_rage[2]":
                    blackboard.attack_speed = 0
                    log.write_note("抽攻击卡")
                elif skill_id == "skchr_fmout_2":
                    blackboard.atk = 0
                    log.write_note("抽攻速卡")
            case "tachr_147_shining_1":  # 闪灵
                await write_buff(f"def +{blackboard.value('def')}")
                buff_frame['def'] += blackboard.value('def')
                blackboard.update('def', 0)
            case "tachr_367_swllow_1":  # 灰喉
                blackboard.attack_speed = 0  # 特判已经加了
            case "tachr_279_excu_1" | "tachr_391_rosmon_1" | "skchr_pinecn_1":  # 送葬
                blackboard.edef_pene = blackboard.value('def_penetrate_fixed')
            case "tachr_373_lionhd_1":  # 莱恩哈特
                blackboard.atk *= min(enemy.count, blackboard.value('max_valid_stack_cnt'))
            # 暴击类
            case "tachr_290_vigna_1":
                blackboard.prob_override = blackboard.value('prob2') if is_skill else blackboard.value('prob1')
                if buff_frame['prob'] and buff_frame['prob'] > blackboard.prob_override:
                    del blackboard.prob_override  # 防止覆盖模组概率
            case "tachr_106_franka_1":  # 芙兰卡
                blackboard.edef_pene_scale = 1
                if is_skill and skill_id == 'skchr_franka_2':
                    blackboard.prob_override = blackboard.value('prob') * char_attr['buffList']['skill']['talent_scale']
            case "tachr_4009_irene_1":
                blackboard.edef_pene_scale = blackboard.value('def_penetrate')
            case "tachr_155_tiger_1":
                blackboard.prob_override = blackboard.value('tiger_t_1[evade].prob')
                blackboard.atk = blackboard.value('charge_on_evade.atk')
            case "tachr_340_shwaz_1":
                if is_skill:
                    blackboard.prob_override = char_attr['buffList']['skill']['talent@prob']
                blackboard.edef_scale = blackboard.value('def')
                blackboard.delete('defense')
            case "tachr_225_haak_1":
                blackboard.prob_override = 0.25
            case "tachr_2013_cerber_1":
                del blackboard.atk_scale
            case "tachr_401_elysm_1":
                del blackboard.attack_speed
            case "tachr_345_folnic_1":
                del blackboard["damage_scale"]
            case "tachr_344_beewax_trait" | "tachr_388_mint_trait" | "tachr_388_mint_1" | "tachr_4080_lin_trait":
                if is_skill:
                    done = True
            case "tachr_426_billro_2":
                done = True
            case "tachr_426_billro_trait":
                if is_skill and not (skill_id == "skchr_billro_1" and options.get('charge')):
                    done = True
            case "tachr_411_tomimi_1":
                if not is_skill:
                    done = True
            case "tachr_509_acast_1" | "tachr_350_surtr_1" | "tachr_377_gdglow_2":
                blackboard.emr_pene = blackboard.value('magic_resist_penetrate_fixed')
            # ---- 技能 ----
            case ("skchr_swllow_1" | "skchr_helage_1" | "skchr_helage_2"
                  | "skchr_akafyu_1" | "skchr_excu_2" | "skchr_bpipe_2" | "skchr_acdrop_2" | "skchr_spikes_1"):
                buff_frame['times'] = 2
                await write_buff(f"攻击次数 = {buff_frame['times']}")
            case "skchr_excu_1":
                del blackboard.atk_scale
            case "skchr_texas_2" | "skchr_flamtl_2":
                buff_frame['times'] = 2
                buff_frame['maxTarget'] = 999
                await write_buff(f"攻击次数 = {buff_frame['times']}最大目标数 = {buff_frame['maxTarget']}")
            case "skchr_swllow_2" | "skchr_bpipe_3":
                buff_frame['times'] = 3
                await write_buff(f"攻击次数 = {buff_frame['times']}")
            case "skchr_milu_2":  # 守林(茂名版)
                buff_frame['times'] = min(enemy.count, blackboard.value('max_cnt'))
                log.write_note(f"核弹数量: {buff_frame['times']}(按全中计算)")
                buff_frame['maxTarget'] = 999
            case "skchr_cqbw_3":  # D12(茂名版)
                buff_frame['times'] = min(enemy.count, blackboard.max_target)
                blackboard.max_target = 999
                log.write_note(f"炸弹数量: {buff_frame['times']}(按全中计算)")
            case "skchr_iris_2":  # 爱丽丝2
                buff_frame['times'] = min(enemy.count, blackboard.max_target)
                blackboard.max_target = 999
                log.write_note(f"睡眠目标数量: {buff_frame['times']}\n其余目标按全中计算")
            case "skchr_lava2_1":  # sp炎熔1
                del blackboard["attack@max_target"]
                buff_frame['times'] = min(2, enemy.count)
                log.write_note("按全中计算")
            case "skchr_lava2_2":
                buff_frame['times'] = 2
                log.write_note("按火圈叠加计算")
            case "skchr_slbell_1" | "skchr_shining_2" | "skchr_cgbird_2":  # 不结算的技能
                done = True
            # 多段暖机
            case "skchr_iris_1":
                if options.get("warmup"):
                    blackboard.atk = blackboard.value("amgoat_s_1[b].atk")
                    blackboard.attack_speed = blackboard.value("amgoat_s_1[b].attack_speed")
                    if is_skill:
                        log.write_note("暖机完成")
                else:
                    blackboard.attack_speed = blackboard.value("amgoat_s_1[a].attack_speed")
                    log.write_note("首次启动时")
            case "skchr_thorns_3":
                if options.get("warmup"):
                    blackboard.atk = blackboard.value("thorns_s_3[b].atk")
                    blackboard.attack_speed = blackboard.value("thorns_s_3[b].attack_speed")
                    if is_skill:
                        log.write_note("暖机完成")
                else:
                    log.write_note("首次启动时")
                if options.get("ranged_penalty"):
                    buff_frame["atk_scale"] = 1
                    if is_skill:
                        log.write_note("技能不受距离惩罚")
            case "skchr_pinecn_2":
                if options.get("warmup"):
                    blackboard.atk = blackboard.value("pinecn_s_2[d].atk")
                    if is_skill:
                        log.write_note("按攻击力叠满计算")
                else:
                    blackboard.atk = blackboard.value("pinecn_s_2[a].atk")
                    if is_skill:
                        log.write_note("首次启动时")
            case "skchr_amgoat_2":
                blackboard.atk_scale = blackboard.value('fk')
            case "skchr_breeze_2":
                buff_frame["maxTarget"] = 1
            case ("skchr_snsant_2" | "skchr_demkni_2" | "skchr_demkni_3"
                  | "skchr_hsguma_3" | "skchr_waaifu_2" | "skchr_sqrrel_2"
                  | "skchr_panda_2" | "skchr_red_2" | "skchr_phatom_3"
                  | "skchr_weedy_3" | "skchr_asbest_2" | "skchr_folnic_2"
                  | "skchr_chiave_2" | "skchr_mudrok_2" | "skchr_siege_2"
                  | "skchr_glady_3" | "skchr_gnosis_2" | "skchr_ebnhlz_2"
                  | "skchr_doroth_2" | "skchr_doroth_3"):
                buff_frame['maxTarget'] = 999
                await write_buff(f"最大目标数 = {buff_frame['maxTarget']}")
            case "skchr_durnar_2":
                buff_frame['maxTarget'] = 3
                await write_buff(f"最大目标数 = {buff_frame['maxTarget']}")
            case "skchr_aprot_1" | "skchr_aprot2_1":
                buff_frame['maxTarget'] = 3
                await write_buff(f"最大目标数 = {buff_frame['maxTarget']}")
                await write_buff(f"base_attack_time: {blackboard.base_attack_time}x")
                blackboard.base_attack_time *= basic['baseAttackTime']
            case "skchr_saga_2":
                buff_frame['maxTarget'] = 6
                await write_buff(f"最大目标数 = {buff_frame['maxTarget']}")
            case "skchr_huang_3":  # 可变攻击力技能，计算每段攻击力表格以和其他buff叠加
                buff_frame['maxTarget'] = 999
                buff_frame['atk_table'] = [(i + 1) * blackboard.atk / 8 for i in range(8)]
                await write_buff(f"技能攻击力加成: {[round(x, 2) for x in buff_frame['atk_table']]}")
            case "skchr_phatom_2":
                buff_frame['atk_table'] = list(
                    reversed([blackboard.atk * (x + 1) for x in range(int(blackboard.times))]))
                await write_buff(
                    f"技能攻击力加成: {[x for x in map(lambda x: format(x, '.2f'), buff_frame['atk_table'])]}")
                del blackboard.times
            case "skchr_bluep_2":  # 蓝毒2: 只对主目标攻击多次
                buff_frame['maxTarget'] = 3
                await write_buff(
                    f"最大目标数 = {buff_frame['maxTarget']}, 主目标命中 {blackboard.value('attack@times')}次")
            case ("skchr_bluep_1" | "skchr_breeze_1" | "skchr_grani_2"
                  | "skchr_astesi_2" | "skchr_hpsts_2" | "skchr_myrrh_1"
                  | "skchr_myrrh_2" | "skchr_whispr_1" | "skchr_ling_2"):
                buff_frame['maxTarget'] = 2
                await write_buff(f"最大目标数 = {buff_frame['maxTarget']}")
            case "skchr_folivo_1" | "skchr_folivo_2" | "skchr_deepcl_1":
                if not options.get('token'):
                    blackboard.atk = 0  # 不增加本体攻击
                    blackboard.defense = 0
            case "skchr_otter_2":
                if options.get('token'):
                    log.write_note("结果无意义，应去掉召唤物选项")
                    done = True
            case "skchr_kalts_2":
                if options.get('token'):
                    del blackboard.attack_speed
                    blackboard.atk = blackboard.value("attack@atk")
                    buff_frame['maxTarget'] = 3
                # else attack_speed ok, attack @ atk no effect.
            case "skchr_kalts_3":
                if options.get('token'):
                    blackboard.atk = blackboard.value("attack@atk")
                    blackboard.defense = blackboard.value("attack@def")
            case "skchr_skadi2_3":
                del blackboard.atk_scale
            case "skchr_sora_2" | "skchr_skadi2_2" | "skchr_heidi_1" | "skchr_heidi_2":
                blackboard.atk = 0  # 不增加本体攻击
                blackboard.defense = 0
                blackboard.max_hp = 0
                log.write_note("自身不受鼓舞影响")
            case "skchr_swire_1":
                blackboard.atk = 0  # 1技能不加攻击
            case "skchr_ccheal_2":  # hot记为额外治疗，不在这里计算
                buff_frame['dpsDuration'] = blackboard.value('duration')
            case "skchr_ccheal_1":
                del blackboard["heal_scale"]
            case ("skchr_hmau_2" | "skchr_spot_1" | "tachr_193_frostl_1"
                  | "skchr_mantic_2" | "skchr_glaze_2" | "skchr_zumama_2"
                  | "skchr_shwaz_3"  # 攻击间隔延长，但是是加算
                  | "fusion_buff" | "skchr_windft_2" | "skchr_mlynar_2"
                  | "skchr_judge_3" | "skchr_lin_1"):
                buff_frame['baseAttackTime'] += blackboard.base_attack_time
                await write_buff(f"base_attack_time + {blackboard.base_attack_time}s")
                blackboard.base_attack_time = 0
            case ("skchr_brownb_2"  # 攻击间隔缩短，但是是乘算负数
                  | "skchr_whispr_2" | "skchr_indigo_1" | "skchr_pasngr_2" | "skchr_ashlok_2"):
                await write_buff(f"base_attack_time: {blackboard.base_attack_time}x")
                blackboard.base_attack_time = Decimal(blackboard.base_attack_time) * basic['baseAttackTime']
            case "skchr_mudrok_3":
                await write_buff(f"base_attack_time: {blackboard.base_attack_time}x")
                blackboard.base_attack_time = Decimal(blackboard.base_attack_time) * basic['baseAttackTime']
                buff_frame['maxTarget'] = basic['blockCnt']
            case "skchr_rosmon_3":
                await write_buff("base_attack_time: {blackboard.base_attack_time}x")
                blackboard.base_attack_time = Decimal(blackboard.base_attack_time) * basic['baseAttackTime']
                if options.get('cond'):
                    blackboard.edef = -160
                    log.write_note("计算战术装置阻挡减防")
                if options.get('rosmon_double'):
                    blackboard.times = 2
                    log.write_note("按2次攻击都命中所有敌人计算")
            case ("skchr_aglina_2"  # 攻击间隔缩短，但是是乘算正数
                  | "skchr_cerber_2" | "skchr_finlpp_2" | "skchr_jaksel_2"
                  | "skchr_iris_1" | "skchr_indigo_2" | "skchr_ebnhlz_1"
                  | "skchr_hamoni_1" | "skchr_hamoni_2" | "skchr_mberry_2"
                  | "skchr_flamtl_3"):
                await write_buff(f"base_attack_time: {blackboard.base_attack_time}x")
                blackboard.base_attack_time = Decimal(blackboard.base_attack_time - 1) * basic['baseAttackTime']
            case "skchr_angel_3":
                await write_buff("攻击间隔双倍减算")
                blackboard.base_attack_time *= 2
            case "skchr_whitew_2" | "skchr_spikes_2":
                buff_frame['maxTarget'] = 2
                await write_buff(f"最大目标数 = {buff_frame['maxTarget']}")
                if options.get('ranged_penalty'):
                    buff_frame['atk_scale'] /= 0.8
                    if is_skill:
                        log.write_note("技能不受距离惩罚")
            case "skchr_ayer_2":
                del blackboard.atk_scale  # 断崖2记为额外伤害
            case "skchr_ayer_1" | "skchr_svrash_2" | "skchr_svrash_1" | "skchr_frostl_1":
                if options.get('ranged_penalty'):
                    buff_frame['atk_scale'] = 1
                    if is_skill:
                        log.write_note("技能不受距离惩罚")
            case "skchr_svrash_3":
                if options.get('ranged_penalty'):
                    buff_frame['atk_scale'] = 1
                    if is_skill:
                        log.write_note("技能不受距离惩罚")
                blackboard.def_scale = 1 + blackboard.value("def")
                blackboard.delete("def")
            case "skchr_ceylon_1":
                if options.get('ranged_penalty'):
                    buff_frame['atk_scale'] /= 0.7
                    if is_skill:
                        log.write_note("技能不受距离惩罚")
            case "skchr_nightm_1":
                await write_buff(f"治疗目标数 {blackboard.value('attack@max_target')}")
                del blackboard["attack@max_target"]
            case ("skchr_shotst_1"  # 破防类
                  | "skchr_shotst_2"):
                blackboard.edef_scale = blackboard.defense
                blackboard.defense = 0
            case "skchr_meteo_2":
                blackboard.edef = blackboard.defense
                blackboard.defense = 0
            case "skchr_slbell_2":  # 初雪
                blackboard.edef_scale = blackboard.defense
                blackboard.defense = 0
            case "skchr_ifrit_2":
                blackboard.edef = blackboard.value('def')
                blackboard.defense = 0
            case "skchr_nian_3":
                blackboard.atk = blackboard.value("nian_s_3[self].atk")
            case "skchr_nian_2" | "skchr_hsguma_2":
                await write_buff("计算反射伤害，而非DPS")
            case "skchr_yuki_2":
                # blackboard.attack@atk_scale *= 3
                value = blackboard.vlaue('attack@atk_scale')
                blackboard.update('attack@atk_scale', value)
                await write_buff(f"总倍率: {blackboard.value('attack@atk_scale')}")
            case "skchr_waaifu_1":
                blackboard.atk = blackboard.value("waaifu_s_1[self].atk")
            case "skchr_peacok_1":
                blackboard.prob_override = blackboard.value("peacok_s_1[crit].prob")
                if is_crit:
                    blackboard.atk_scale = blackboard.value('atk_scale_fake')
            case "skchr_peacok_2":
                if is_crit:
                    await write_buff(f"成功 - atk_scale = {blackboard.value('success.atk_scale')}")
                    blackboard.atk_scale = blackboard.value("success.atk_scale")
                    buff_frame['maxTarget'] = 999
                else:
                    await write_buff("失败时有一次普攻")
            case "skchr_vodfox_1":
                buff_frame['damage_scale'] = 1 + (buff_frame['damage_scale'] - 1) * \
                                             blackboard.value('scale_delta_to_one')
            case "skchr_elysm_2":
                del blackboard["def"]
                del blackboard["max_target"]
            case "skchr_asbest_1":
                del blackboard["damage_scale"]
            case "skchr_beewax_2" | "skchr_mint_2":
                del blackboard.atk_scale
            case "skchr_tomimi_2":
                blackboard.prob_override = blackboard.value("attack@tomimi_s_2.prob") / 3
                del blackboard.base_attack_time
                if is_crit:
                    blackboard.atk_scale = blackboard.value("attack@tomimi_s_2.atk_scale")
                    log.write_note(f"每种状态概率:{(blackboard.prob_override * 100)} %")
            case "skchr_surtr_2":
                if enemy.count == 1:
                    blackboard.atk_scale = blackboard.value("attack@surtr_s_2[critical].atk_scale")
                    log.write_note(f"对单目标倍率 {blackboard.atk_scale}x")
            case "skchr_surtr_3":
                del blackboard.hp_ratio
            case "tachr_381_bubble_1":
                del blackboard.atk
            case "tachr_265_sophia_1":
                if is_skill:
                    ts = char_attr['buffList']["skill"]['talent_scale']
                    if skill_id == "skchr_sophia_1":
                        blackboard.defense = blackboard.value("sophia_t_1_less.def") * ts
                        blackboard.attack_speed = blackboard.value("sophia_t_1_less.attack_speed") * ts
                        await write_buff("1技能 - 自身享受一半增益")
                    elif skill_id == "skchr_sophia_2":
                        blackboard.defense *= ts
                        blackboard.attack_speed *= ts
                        blackboard.max_target = basic['blockCnt']
                        await write_buff("2技能 - 自身享受全部增益")
                else:
                    del blackboard.defense
                    del blackboard.attack_speed
                    await write_buff("非技能期间天赋对自身无效")
            case "tachr_346_aosta_1":
                del blackboard.atk_scale
            case "skchr_blemsh_1":
                del blackboard.heal_scale
            case "skchr_rosmon_2":
                del blackboard["attack@times"]
            case "tachr_1001_amiya2_1":
                if is_skill:
                    blackboard.atk *= char_attr['buffList']["skill"]['talent_scale']
                    blackboard.defense *= char_attr['buffList']["skill"]['talent_scale']
            case "skchr_amiya2_2":
                del blackboard.times
                del blackboard.atk_scale
                if options.get('stack'):
                    blackboard.atk = blackboard.value("amiya2_s_2[kill].atk") * blackboard.value(
                        "amiya2_s_2[kill].max_stack_cnt")
                    log.write_note("斩击伤害全部以叠满计算")
                    log.write_note("包括前三刀")
            case "tachr_214_kafka_1":
                if is_skill:
                    await apply_buff_default()
                done = True
            case "skchr_kafka_2":
                del blackboard.atk_scale
            case "skchr_f12yin_2":
                blackboard.def_scale = 1 + blackboard.defense
                buff_frame['maxTarget'] = 2
                del blackboard.defense
            case "skchr_f12yin_3":
                blackboard.prob_override = blackboard.value("talent@prob")
            case "tachr_264_f12yin_1":
                if blackboard.get('atk'):
                    del blackboard.atk
            case "tachr_264_f12yin_2":
                if blackboard.get('prob'):
                    # print(blackboard)
                    del blackboard['prob']
            case "skchr_archet_1":
                del blackboard.max_target
            case ("tachr_338_iris_trait" | "tachr_469_indigo_trait" | "tachr_338_iris_1"
                  | "tachr_362_saga_2" | "tachr_4046_ebnhlz_trait" | "tachr_4046_ebnhlz_1" | "tachr_297_hamoni_trait"):
                done = True
            case "tachr_4046_ebnhlz_2":
                del blackboard.atk_scale
                if "attack_speed" in blackboard:
                    if (options.get('equip') and
                            not (skill_id == "skchr_ebnhlz_3" and is_skill)):
                        log.write_note("触发-模组攻速增加")
                    else:
                        done = True
                        log.write_note("不触发攻速增加")
                else:
                    done = True
            case "skchr_tuye_1" | "skchr_tuye_2":
                del blackboard.heal_scale
                del blackboard.atk_scale
            case "skchr_saga_3":
                buff_frame['maxTarget'] = 2
                await write_buff(f"最大目标数 = {buff_frame['maxTarget']}")
                if options.get('cond'):
                    buff_frame['times'] = 2
                    log.write_note("半血2连击")
            case "skchr_dusk_1" | "skchr_dusk_3":
                if options.get('token'):
                    done = True
            case "skchr_dusk_2":
                if options.get('token'):
                    done = True
                else:
                    if options.get('cond'):
                        log.write_note("触发半血增伤")
                    else:
                        del blackboard.damage_scale
            case "skchr_weedy_2":
                if options.get('token'):
                    del blackboard.base_attack_time
                else:
                    buff_frame['maxTarget'] = 999
            case "tachr_455_nothin_1":
                done = True
            case "skchr_nothin_2":
                del blackboard['prob']
                if not options.get('cond'):
                    del blackboard.attack_speed
                    log.write_note("蓝/紫Buff")
                else:
                    log.write_note("红Buff(攻速)")
            case "skchr_ash_2":
                if options.get('cond'):
                    blackboard.atk_scale = blackboard.value("ash_s_2[atk_scale].atk_scale")
            case "skchr_ash_3":
                buff_frame['maxTarget'] = 999
            case "skchr_blitz_2":
                del blackboard.atk_scale
            case "skchr_tachak_1":
                blackboard.edef_pene = blackboard.value('def_penetrate_fixed')
                del blackboard.atk_scale
                buff_frame['dpsDuration'] = blackboard.value('projectile_delay_time')
            case "skchr_tachak_2":
                await write_buff("base_attack_time: {blackboard.base_attack_time}x")
                blackboard.base_attack_time = Decimal(blackboard.base_attack_time) * basic['baseAttackTime']
                if not is_crit:
                    del blackboard.atk_scale
            case "skchr_pasngr_1":
                blackboard.max_target = blackboard.value('pasngr_s_1.max_target')
                blackboard.atk_scale = blackboard.value('pasngr_s_1.atk_scale')
            case "skchr_pasngr_3":
                buff_frame['dpsDuration'] = 4
                done = True
            case "skchr_toddi_1":
                blackboard.edef_scale = blackboard.defense
                del blackboard.defense
            case "skchr_tiger_1" | "skchr_bena_1":
                blackboard.edef_pene_scale = blackboard.value('def_penetrate')
                if options.get('annie'):
                    log.write_note("替身模式")
                    done = True
            case "skchr_bena_2" | "skchr_kazema_1":
                if options.get('annie'):
                    log.write_note("替身模式")
                    done = True
            case "skchr_ghost2_1" | "skchr_ghost2_2":
                if options.get('annie'):
                    log.write_note("替身模式")
                    buff_frame['maxTarget'] = 999
                    done = True
            case "skchr_ghost2_3":
                if options.get('annie'):
                    log.write_note("替身模式")
                    buff_frame['maxTarget'] = 999
                    done = True
                else:
                    buff_frame['baseAttackTime'] += blackboard.base_attack_time
                    await write_buff(f"base_attack_time + {blackboard.base_attack_time}s")
                    blackboard.base_attack_time = 0
                    buff_frame['maxTarget'] = 2
                    await write_buff(f"最大目标数 = {buff_frame['maxTarget']}")
            case "skchr_kazema_2":
                if options.get('annie'):
                    log.write_note("替身模式")
                    done = True
            case "skchr_billro_2":
                if not options.get('charge'):
                    del blackboard.atk
            case "tachr_485_pallas_trait" | "tachr_308_swire_trait" | "tachr_265_sophia_trait":
                if not options.get('noblock'):
                    done = True
            case "uniequip_002_pallas" | "uniequip_002_sophia" | "uniequip_002_swire":
                if not options.get('noblock'):
                    done = True
            case "tachr_130_doberm_trait":
                if not options.get('noblock'):
                    done = True
            case "skchr_pallas_3":
                if options.get('pallas'):
                    blackboard.defense = blackboard.value("attack@def")
                    blackboard.atk += blackboard.value("attack@peak_performance.atk")
            case "tachr_486_takila_1":
                done = True
            case "tachr_486_takila_trait":
                if not options.get('charge'):
                    blackboard.atk = 1
                    log.write_note("未蓄力-按100%攻击加成计算")
                else:
                    log.write_note("蓄力-按蓄满40秒计算")
            case "skchr_takila_2":
                if options.get('charge'):
                    buff_frame['maxTarget'] = blackboard.value("attack@plus_max_target")
                else:
                    buff_frame['maxTarget'] = 2
            case "skchr_chen2_2" | "skchr_chen2_3":
                blackboard.edef = blackboard.value("attack@def")
            case "skchr_chen2_1":
                del blackboard.atk_scale
            case "tachr_1013_chen2_1":
                blackboard.prob_override = blackboard.value("spareshot_chen.prob")
            case "tachr_1013_chen2_2":
                blackboard.attack_speed = blackboard.value("chen2_t_2[common].attack_speed")
                if options.get('water'):
                    blackboard.attack_speed += blackboard.value("chen2_t_2[map].attack_speed")
            case "tachr_479_sleach_1":
                # value = blackboard.value('sleach_t_1[ally].attack_speed')
                blackboard.attack_speed = blackboard.value('sleach_t_1[ally].attack_speed')
            case "skchr_fartth_3":
                if not options.get('far'):
                    del blackboard.damage_scale
            case "tachr_1014_nearl2_1":
                del blackboard.atk_scale
            case "tachr_1014_nearl2_2":
                blackboard.edef_pene_scale = blackboard.value('def_penetrate')
            case "skchr_nearl2_2":
                del blackboard.times
            case "tachr_489_serum_1":
                done = True
            case "skchr_glider_1":
                buff_frame['maxTarget'] = 2
            case "skchr_aurora_2":
                blackboard.prob_override = 0.1  # any value
                if not is_crit:
                    del blackboard.atk_scale
            case "tachr_206_gnosis_1":
                if (options.get('freeze') or
                        (skill_id == "skchr_gnosis_2" and is_skill and options.get('charge'))):
                    blackboard.damage_scale = blackboard.value('damage_scale_freeze')
                    blackboard.magic_resistance = -15
                    if options.get('freeze'):
                        log.write_note("维持冻结 -15法抗/脆弱加强")
                else:
                    blackboard.damage_scale = blackboard.value('damage_scale_cold')
            case "skchr_gnosis_3":
                if not options.get('freeze'):
                    log.write_note("攻击按非冻结计算\n终结伤害按冻结计算")
                del blackboard.atk_scale
            case "skchr_blkngt_1":
                if options.get('token'):
                    blackboard.atk = blackboard.value("blkngt_hypnos_s_1[rage].atk")
                    blackboard.attack_speed = round(blackboard.value("blkngt_hypnos_s_1[rage].attack_speed") * 100)
            case "skchr_blkngt_2":
                if options.get('token'):
                    blackboard.atk_scale = blackboard.value("blkngt_s_2.atk_scale")
                    buff_frame['maxTarget'] = 999
            case "skchr_ling_3":
                del blackboard.atk_scale
            case "tachr_377_gdglow_1":
                blackboard.prob_override = 0.1
            case "tachr_4016_kazema_1":
                done = True
            case "tachr_300_phenxi_2":
                if is_skill:
                    blackboard.attack_speed = blackboard.value("phenxi_e_t_2[in_skill].attack_speed") or 0
            case "skchr_chnut_2":
                blackboard.heal_scale = blackboard.value("attack@heal_continuously_scale")
                log.write_note("以连续治疗同一目标计算")
            case "tachr_4045_heidi_1":
                if skill_id == "skchr_heidi_1":
                    blackboard.delete('defense')
                if skill_id == "skchr_heidi_2":
                    del blackboard.atk
            case "skchr_horn_1":
                if not options.get('melee'):
                    buff_frame['maxTarget'] = 999
            case "skchr_horn_2":
                buff_frame['maxTarget'] = 999
                blackboard.atk_scale = blackboard.value("attack@s2.atk_scale")
            case "skchr_horn_3":
                if not options.get('melee'):
                    buff_frame['maxTarget'] = 999
                if options.get('overdrive_mode'):
                    blackboard.atk = blackboard.value("horn_s_3[overload_start].atk")
            case "skchr_rockr_2":
                if not options.get('overdrive_mode'):
                    del blackboard.atk
            case "tachr_108_silent_1":
                if options.get('token'):
                    done = True
            case "skchr_silent_2":
                if options.get('token'):
                    buff_frame['maxTarget'] = 999
            case "skchr_windft_1":
                buff_frame['maxTarget'] = 999
            case "tachr_433_windft_1":
                if options.get('stack'):
                    blackboard.atk *= 2
                    if skill_id == "skchr_windft_2" and is_skill:
                        blackboard.atk *= char_attr['buffList']["skill"]['talent_scale']
                        log.write_note(f"装备2个装置\n攻击力提升比例:{(blackboard.atk * 100).toFixed(1)} % ")
                else:
                    done = True
                    log.write_note("不装备装置")
            case "tachr_4042_lumen_1" | "tachr_4042_lumen_2":
                done = True
            case "skchr_lumen_3":
                del blackboard.heal_scale
            case "tachr_1023_ghost2_1":
                if not options.get('annie'):
                    done = True
            case "skchr_irene_1" | "skchr_irene_2":
                blackboard.prob_override = 1
            case "skchr_irene_3":
                blackboard.prob_override = 1
                buff_frame['maxTarget'] = 999
                await write_buff(f"最大目标数 = {buff_frame['maxTarget']}")
            case "tachr_4043_erato_1":
                del blackboard.atk_scale
                if options.get('cond'):
                    blackboard.edef_pene_scale = blackboard.value('def_penetrate')
                else:
                    done = True
            case "skchr_pianst_2":
                del blackboard.atk_scale
                blackboard.atk *= blackboard.value('max_stack_cnt')
            case "tachr_4047_pianst_1":
                del blackboard.atk_scale
            case "tachr_258_podego_1":
                if "sp_recovery_per_sec" in blackboard:
                    del blackboard.sp_recovery_per_sec
            case "tachr_195_glassb_1":
                if is_skill and "glassb_e_t_1[skill].attack_speed" in blackboard:
                    blackboard.attack_speed += blackboard.value("glassb_e_t_1[skill].attack_speed")
            case "tachr_135_halo_trait" | "tachr_4071_peper_trait":
                blackboard.max_target = blackboard.value("attack@chain.max_target")
            case "skchr_halo_1":
                blackboard.times = min(blackboard.max_target, enemy.count)
                del blackboard.max_target
            case "skchr_halo_2":
                blackboard.times = min(blackboard.value("attack@max_target"), enemy.count)
                del blackboard["attack@max_target"]
            case "skchr_greyy2_2":
                buff_frame['dpsDuration'] = blackboard.value('projectile_delay_time')
                done = True
            case "skchr_doroth_1":
                blackboard.edef_scale = blackboard.defense
                del blackboard.defense
            case "tachr_129_bluep_1":
                done = True
            case "tachr_1026_gvial2_1":
                if options.get('block'):
                    # 确认阻挡数
                    gvial2_blk = 5 if skill_id == "skchr_gvial2_3" and is_skill else 3
                    ecount = min(enemy.count, gvial2_blk)
                    atk_add = blackboard.value('atk_add') * ecount
                    blackboard.atk += atk_add
                    value = blackboard.value('def') + atk_add
                    blackboard.update('def', value)
                    await write_buff(f"阻挡数: {ecount}, 额外加成 +{atk_add}")
                    log.write_note(f"按阻挡{ecount}个敌人计算")
            case "skchr_gvial2_3":
                blackboard.max_target = 5
            case "tachr_4055_bgsnow_2":  # 判断value。具体值存在召唤物的talent里，本体判断只能写死
                bgsnow_t2_value = -0.18
                if base_char_info.potentialRank >= 4:
                    bgsnow_t2_value = -0.2
                if options.get('cond_near'):  # 周围4格
                    bgsnow_t2_value -= 0.05
                # 判断是否减防
                if options.get('token') or options.get('cond_def'):
                    blackboard.edef_scale = bgsnow_t2_value
            case "skchr_bgsnow_1":
                if not is_crit:
                    del blackboard.atk_scale
            case "skchr_bgsnow_3":
                if options.get('cond_front') or options.get('token'):
                    blackboard.atk_scale = blackboard.value("bgsnow_s_3[atk_up].atk_scale")
                    log.write_note("正前方敌人")
            case "tachr_497_ctable_1":
                if options.get('noblock'):
                    del blackboard.atk
                    log.write_note("未阻挡")
                else:
                    del blackboard.attack_speed
                    log.write_note("阻挡")
            case "tachr_472_pasngr_2":
                if not options.get('cond_2'):
                    done = True
            case "skchr_provs_2":
                del blackboard.atk_scale
            case "tachr_4032_provs_1":  # 模组覆盖到这里，在这里判断
                if not options.get('equip'):
                    del blackboard.sp_recovery_per_sec
            case "tachr_4064_mlynar_2":
                done = True
            case "tachr_4064_mlynar_trait":
                atk_rate = 1 if options.get('stack') else 0.5
                if is_skill and skill_id == "skchr_mlynar_3":
                    atk_rate *= char_attr['buffList']["skill"]['trait_up']
                blackboard.atk *= atk_rate
                log.write_note(f"以 {round(blackboard.atk * 100)} % 计算特性 ")
            case "skchr_mlynar_3":
                del blackboard.atk_scale
            case "tachr_136_hsguma_1":
                if "atk" in blackboard:
                    if not options.get('equip'):
                        del blackboard.atk
                        log.write_note("不触发抵挡加攻")
                    else:
                        log.write_note("触发抵挡加攻")
            case "tachr_325_bison_1":
                char_attr['basic']['defense'] += blackboard.defense
                await write_buff(f"防御力直接加算: +{blackboard.defense}")
                done = True
            case "skchr_lolxh_1":
                buff_frame['maxTarget'] = 2
                await write_buff(f"最大目标数 = {buff_frame['maxTarget']}")
                if options.get('ranged_penalty'):
                    buff_frame['atk_scale'] = 1
                    log.write_note("技能不受距离惩罚")
            case "skchr_lolxh_2":
                buff_frame.maxTarget = 2
                await write_buff(f"最大目标数 = {buff_frame['maxTarget']}")
                if options.get('ranged_penalty'):
                    buff_frame['atk_scale'] = 1
                    log.write_note("技能不受距离惩罚")
            case "skchr_qanik_2":
                blackboard.atk_scale = blackboard.value('trigger_atk_scale')
            case "skchr_totter_2":
                blackboard.max_target = blackboard.value("attack@s2n.max_target")
                if enemy.count == 1:
                    blackboard.atk_scale = blackboard.value("attack@s2c.atk_scale")
                    log.write_note(f"单体倍率 {(blackboard.atk_scale * buff_frame['atk_scale']).toFixed(1)}x")
            case "tachr_157_dagda_1":
                if options.get('stack'):
                    blackboard.atk_scale = blackboard.value('atk_up_max_value')
                    log.write_note("爆伤叠满")
                if is_skill and skill_id == "skchr_dagda_2":
                    blackboard.prob_override = char_attr['buffList']['skill']["talent@prob"]
            case "skchr_quartz_2":
                del blackboard.damage_scale
                if options.get('crit'):
                    blackboard.prob_override = blackboard.value("attack@s2_buff_prob")
                blackboard.atk_scale = blackboard.value("attack@s2_atk_scale")
            case "skchr_peper_2":
                blackboard.max_target = 4
            case "tachr_4014_lunacu_1":
                if is_skill:
                    await write_buff("base_attack_time:{blackboard.base_attack_time}x")
                    blackboard.base_attack_time *= basic['baseAttackTime']
            case "tachr_4065_judge_2":
                done = True
            case "skchr_judge_1":
                if options.get('charge'):
                    blackboard.atk_scale = blackboard.value("judge_s_1_enhance_checker.atk_scale")
                    log.write_note("不考虑蓄力打断普攻的特殊情况")
            case "skchr_judge_2":
                blackboard.max_target = 999
            case "tachr_1028_texas2_1":
                if not is_skill:
                    done = True
            case "skchr_texas2_2":
                del blackboard.atk_scale
            case "tachr_427_vigil_1":
                if options.get('stack') and options.get('token'):
                    blackboard.times = 3
                    if is_skill:
                        log.write_note("以3连击计算")
                else:
                    blackboard.times = 1
            case "tachr_427_vigil_2":
                if options.get('cond'):
                    blackboard.edef_pene = blackboard.value('def_penetrate_fixed')
            case "skchr_vigil_2":
                if options.get('token'):
                    blackboard.atk_scale = blackboard.value('vigil_wolf_s_2.atk_scale')
                    blackboard.hp_ratio = blackboard.value('vigil_wolf_s_2.hp_ratio')
            case "skchr_vigil_3":
                if not options.get('token'):
                    blackboard.times = 3
            case "skchr_ironmn_1":
                if options.get('token'):
                    done = True
            case "skchr_ironmn_2":
                if options.get('token'):
                    done = True
                else:
                    buff_frame['maxTarget'] = 2
                    await write_buff(f"最大目标数 = {buff_frame['maxTarget']}")
            case "skchr_ironmn_3":
                if options.get('token'):
                    done = True
            case "sktok_ironmn_pile3":
                del blackboard.hp_ratio
            case "tachr_420_flamtl_1+":
                blackboard.atk_scale = blackboard.value("attack@atkscale_t1+.atk_scale") or 1
            case "skchr_texas2_3":
                done = True
                log.write_note("落地1s，不影响技能时间")
            case "tachr_1020_reed2_1":
                del blackboard.atk
                log.write_note("假设法术脆弱一直生效")
            case "skchr_reed2_2":
                done = True
            case "skchr_reed2_3":
                blackboard.atk = blackboard.value("reed2_skil_3[switch_mode].atk")
            case "tachr_4017_puzzle_1":
                done = True
            case "tachr_493_firwhl_1":
                if options.get('noblock'):
                    blackboard.delete('defense')
                else:
                    del blackboard.atk
            case "tachr_4080_lin_1":
                done = True
            case "skchr_chyue_1":
                if not options.get('charge'):
                    del blackboard.times
            case "skchr_chyue_2":
                if options.get('cond'):
                    log.write_note("只对主目标触发第一天赋和二段伤害")
                else:
                    log.write_note("不触发浮空和二段伤害")
                del blackboard.max_target
            case "skchr_apionr_1":
                blackboard.edef_pene_scale = blackboard.value('def_penetrate')
            case "skchr_firwhl_1":
                buff_frame['dpsDuration'] = blackboard.value('burn_duration')
            case "skchr_firwhl_2":
                buff_frame['dpsDurationDelta'] = blackboard.value('projectile_life_time') - 1
            case "skchr_podego_2":
                buff_frame['dpsDuration'] = blackboard.value('projectile_delay_time')
            case "skchr_lumen_1":
                buff_frame['dpsDuration'] = blackboard.value("aura.projectile_life_time")
            case "skchr_chimes_2":
                if options.get('od_trigger'):
                    del blackboard.atk
                buff_frame['maxTarget'] = 999
            case "tachr_4082_qiubai_1":
                done = True
            case "skchr_qiubai_1":
                if options.get('ranged_penalty'):
                    buff_frame['atk_scale'] = 1
                    log.write_note("技能不受距离惩罚")
            case "skchr_qiubai_3":
                blackboard.attack_speed *= blackboard.value('max_stack_cnt')
                buff_frame['maxTarget'] = 3
                if options.get('ranged_penalty'):
                    buff_frame['atk_scale'] = 1
                    log.write_note("技能不受距离惩罚")

    # --- applyBuff switch ends here ---

    if tag == "skchr_thorns_2":
        log.write_note("反击按最小间隔计算")
        blackboard.base_attack_time = Decimal(blackboard.value('cooldown')) - (
                basic['baseAttackTime'] + buff_frame['baseAttackTime'])
        buff_frame['attackSpeed'] = 0
        blackboard.attack_speed = 0

    # 决战者阻回
    if char_id in ["char_416_zumama", "char_422_aurora"] and not options.get('block') \
            and buff_frame['spRecoverRatio'] == 0:
        buff_frame['spRecoverRatio'] = -1

    # 模组判定
    # options.get('equip') 指满足模组额外效果的条件
    # 条件不满足时，面板副属性加成依然要计算blackboard.damage_scale
    match tag:
        case "uniequip_002_cuttle" | "uniequip_002_glaze" | "uniequip_002_fartth":
            if options.get('equip'):
                # blackboard = blackboard.trait
                if blackboard.trait['damage_scale'] < 1:
                    blackboard.trait['damage_scale'] += 1
                log.write_note("距离>4.5")
            else:
                blackboard.trait['damage_scale'] = 1
        case "uniequip_002_sddrag":
            if options.get('equip'):
                blackboard.atk_scale = blackboard.trait['atk_scale']
                if options.get('cond_spd'):
                    blackboard.attack_speed = blackboard.talent['attack_speed']
                    log.write_note("受到持续法术伤害")
        case "uniequip_002_vigna":
            if options.get('equip'):
                blackboard.atk_scale = blackboard.trait['atk_scale']
            if "prob1" in blackboard.talent:
                blackboard.prob_override = blackboard.talent['prob2'] if is_skill else blackboard.talent[
                    'prob1']
        case "uniequip_002_chen" | "uniequip_002_tachak" | "uniequip_002_bibeak":
            if not is_skill:
                print(f"blackboard_chen: {blackboard}")
                del blackboard.trait['damage_scale']
        case ("uniequip_002_cutter" | "uniequip_002_phenxi" | "uniequip_002_meteo"
              | "uniequip_002_irene" | "uniequip_002_bdhkgt"):
            blackboard = blackboard.trait
            blackboard['edef_pene'] = blackboard['def_penetrate_fixed']
        case "uniequip_002_yuki":
            bb_yuki = dict(blackboard.trait)
            bb_yuki['edef_pene'] = bb_yuki['def_penetrate_fixed']
            if blackboard.talent['sp_recovery_per_sec']:
                bb_yuki['sp_recovery_per_sec'] = blackboard.talent['sp_recovery_per_sec']
            blackboard = bb_yuki
        case ("uniequip_002_nearl2" | "uniequip_002_franka" | "uniequip_002_peacok"
              | "uniequip_002_cqbw" | "uniequip_002_sesa" | "uniequip_003_skadi"):
            if options.get('equip'):
                blackboard = blackboard.trait
        case "uniequip_002_skadi" | "uniequip_002_flameb" | "uniequip_002_gyuki":
            if options.get('equip'):
                blackboard.attack_speed = blackboard.trait['attack_speed']
        case "uniequip_002_lisa":
            if "atk" in blackboard.talent:
                blackboard.atk = blackboard.talent['atk']
        case "uniequip_002_podego" | "uniequip_002_glacus":
            if options.get('equip'):
                blackboard.sp_recovery_per_sec = 0.2  # 覆盖1天赋数值，但是在模组里计算技力回复
        case "uniequip_003_aglina":
            if options.get('equip'):
                blackboard = blackboard.talent  # 不覆盖1天赋数值
        case "uniequip_002_lumen" | "uniequip_002_ceylon" | "uniequip_002_whispr":
            done = True
        case "uniequip_002_finlpp":
            if is_skill:
                blackboard = blackboard.talent
        case "uniequip_002_ghost2" | "uniequip_002_kazema" | "uniequip_002_bena":
            blackboard = blackboard.trait
            if not options.get('annie') or options.get('token'):
                done = True
        case "uniequip_002_zumama" | "uniequip_002_aurora":
            if not options.get('block'):
                buff_frame['spRecoverRatio'] = blackboard.trait['sp_recover_ratio']
                log.write("技力回复系数 {buffFrame.spRecoverRatio.toFixed(2)}x")
        case "uniequip_002_doberm":
            if options.get('equip'):
                blackboard = blackboard.talent
                log.write_note("有三星干员")
        case "uniequip_002_plosis":
            if options.get('equip') and "sp_recovery_per_sec" in blackboard.talent:
                blackboard.sp_recovery_per_sec = blackboard.talent['sp_recovery_per_sec'] - 0.3
        case "uniequip_002_red" | "uniequip_002_kafka" | "uniequip_002_texas2":
            if options.get('equip'):
                blackboard = blackboard.trait
                log.write_note("周围4格没有队友")
        case "uniequip_002_waaifu":
            if options.get('equip'):
                blackboard = blackboard.talent
                log.write_note("对感染生物")
        case "uniequip_002_pasngr":
            if options.get('cond_2'):
                blackboard = blackboard.talent
        case "uniequip_002_nearl" | "uniequip_002_sunbr" | "uniequip_002_demkni":
            if options.get('equip') or skill_id == "skchr_demkni_1":
                blackboard.heal_scale = blackboard.trait['heal_scale']
        case ("uniequip_002_ash" | "uniequip_002_archet" | "uniequip_002_aprl"
              | "uniequip_002_swllow" | "uniequip_002_bluep" | "uniequip_002_jesica"):
            if options.get('equip'):
                blackboard.attack_speed = 8  # 写死。避免同名词条问题
        case ("uniequip_002_angel" | "uniequip_002_kroos2" | "uniequip_002_platnm"
              | "uniequip_002_mm" | "uniequip_002_clour" | "uniequip_003_archet"):
            if options.get('equip'):
                blackboard.atk_scale = blackboard.trait['atk_scale']
        case "uniequip_002_shotst":
            if options.get('cond'):  # 流星直接用cond判断
                blackboard.atk_scale = blackboard.trait['atk_scale']
        case "uniequip_002_bgsnow":
            if options.get('cond_front') and not options.get('token'):
                # 模组效果对token不生效
                blackboard.atk_scale = blackboard.trait['atk_scale']
        case "uniequip_003_shwaz":
            if options.get('equip') or (skill_id == "skchr_shwaz_3" and is_skill):
                log.write_note("攻击正前方敌人")
                blackboard.atk_scale = blackboard.trait['atk_scale']
        case "uniequip_003_zumama":
            if options.get('block'):
                blackboard.atk = blackboard.trait['atk']
                blackboard.defense = blackboard.trait['def']
        case "uniequip_002_nian":
            blackboard.defense = blackboard.trait['def'] if options.get('block') else 0
            if blackboard.talent.get('atk'):
                blackboard.atk = blackboard.talent['atk'] * blackboard.talent['max_stack_cnt']
                blackboard.defense += blackboard.talent['def'] * blackboard.talent['max_stack_cnt']
                log.write_note("按模组效果叠满计算")
        case "uniequip_002_bison" | "uniequip_002_bubble" | "uniequip_002_snakek":
            if options.get('block'):
                blackboard.defense = blackboard.trait['def']
        case "uniequip_003_hsguma":
            if options.get('equip'):
                blackboard.defense = blackboard.trait['def']
        case "uniequip_002_shining" | "uniequip_002_folnic":
            if options.get('equip'):
                blackboard = blackboard.trait
                log.write_note("治疗地面目标")
        case "uniequip_002_silent":
            if options.get('equip') and not options.get('token'):
                blackboard = blackboard.trait
                log.write_note("治疗地面目标")
        case ("uniequip_002_kalts" | "uniequip_002_tuye" | "uniequip_002_bldsk"
              | "uniequip_002_susuro" | "uniequip_002_myrrh"):
            if options.get("equip"):
                blackboard.heal_scale = blackboard.trait['heal_scale']
                log.write_note("治疗半血目标")
        case "uniequip_002_siege":
            equip_atk = blackboard.trait['atk'] if options.get('equip') else 0
            talent_atk = blackboard.talent['atk'] or 0
            blackboard.atk = blackboard.defense = equip_atk + talent_atk
            await write_buff(f"特性 +{equip_atk * 100} %, 天赋 +{talent_atk * 100} % ")
        case "uniequip_002_blackd" | "uniequip_002_scave" | "uniequip_002_headbr":
            if options.get('equip'):
                blackboard = blackboard.trait
        case "uniequip_002_texas":
            if is_skill:
                blackboard = blackboard.talent
        case "uniequip_002_toddi" | "uniequip_002_erato" | "uniequip_002_totter":
            if options.get('equip'):
                blackboard.atk_scale = 1.15  # 写死
        case "uniequip_002_utage":
            if options.get('equip'):
                blackboard.atk = blackboard.talent['atk'] or 0
                blackboard.defense = blackboard.talent['def'] or 0
        case "uniequip_002_amgoat" | "uniequip_002_cerber" | "uniequip_002_absin" | "uniequip_002_nights":
            blackboard.emr_pene = blackboard.trait['magic_resist_penetrate_fixed']

    # -- uniequip switch ends here --

    if not done:
        await apply_buff_default()

    return buff_frame
