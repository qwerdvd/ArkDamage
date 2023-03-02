import math

from .CalCharAttributes import check_specs
from .load_json import character_table, dps_anim


async def calculate_animation(char_id, skill_id, is_skill, attack_time, attack_speed, log):
    _fps = 30
    char_data = character_table[str(char_id)]
    anim_data = dps_anim.get(char_id, {})
    anim_key = "Attack"
    attack_key = await check_specs(char_id, "anim_key")
    if not attack_key:
        attack_key = next((x for x in ["Attack", "Attack_Loop", "Combat"] if anim_data.get(x)), None)
    tags = []
    count = 0

    if not is_skill:
        anim_key = attack_key
    else:
        anim_key = await check_specs(skill_id, "anim_key")
        if not anim_key:
            sk_index = int(skill_id.split("_")[2])
            sk_count = len(char_data['skills'])

            candidates = [k for k in anim_data.keys() if
                          isinstance(anim_data.get("OnAttack"), int) and
                          "Skill" in k and "Begin" not in k and "End" not in k]
            # candidates = [k for k, v in anim_data.items() if
            #               isinstance(v, dict) and isinstance(v.get('OnAttack'), int) and
            #               'Skill' in k and 'Begin' not in k and 'End' not in k]

            if isinstance(anim_data.get("Skill"), int):
                candidates.append("Skill")

            if len(candidates) == 0:
                anim_key = attack_key
            else:
                for k in candidates:
                    for t in k.split("_"):
                        value = int(t, 10) if t.isdigit() else t
                        if value not in tags:
                            tags.append(value)
                        if value is int and value > count:
                            count = value

                if sk_count > count:
                    sk_index -= 1

                if sk_index == 0 or count == 0:
                    anim_key = next((k for k in candidates if "Skill" in k), None)
                else:
                    anim_key = next((k for k in candidates if str(sk_index) in k), None)
                if not anim_key:
                    anim_key = attack_key

    attack_frame = attack_time * _fps
    real_attack_frame = round(attack_frame)
    real_attack_time = real_attack_frame / _fps
    anim_frame = 0
    event_frame = -1
    scale = 1
    scaled_anim_frame = 0
    pre_delay = 0
    post_delay = 0

    if not anim_key or not anim_data.get(anim_key):
        pass
    else:
        spec_key = char_id if "Attack" in anim_key else skill_id
        is_loop = "Loop" in anim_key
        max_scale = 99

        if isinstance(anim_data[anim_key], int):
            # 没有OnAttack，一般是瞬发或者不攻击的技能
            anim_frame = anim_data[anim_key]
        elif is_loop and not anim_data[anim_key].get("OnAttack"):
            # 名字为xx_Loop的动画且没有OnAttack事件，则为引导型动画
            # 有OnAttack事件的正常处理
            log.write("Loop animation, event frame equals to attack frame")
            anim_frame = attack_frame
            event_frame = attack_frame
            scale = 1
        else:
            anim_frame = anim_data[anim_key]["duration"]
            event_frame = anim_data[anim_key].get("OnAttack", -1)
            # 计算缩放比例
            if await check_specs(spec_key, "anim_max_scale"):
                max_scale = await check_specs(spec_key, "anim_max_scale")
                log.write(f"Max animation scale: {max_scale}")
            scale = max(min(attack_frame / anim_frame, max_scale), 0.1)

        if event_frame >= 0:
            # 计算前后摇。后摇至少1帧
            pre_delay = max(round(event_frame * scale), 1)
            post_delay = max(round(anim_frame * scale - pre_delay - real_attack_frame), 1)

        scaled_anim_frame = round(anim_frame * scale)
        # 帧数补正
        if attack_frame - scaled_anim_frame > 0.5:
            #  console.log("[补正] 动画时间 < 攻击间隔-0.5帧: 理论攻击帧数向上取整且+1");
            real_attack_frame = math.ceil(attack_frame) + 1
        else:
            #  console.log("[补正] 四舍五入");
            real_attack_frame = max(scaled_anim_frame, round(attack_frame))

        real_attack_time = real_attack_frame / _fps

    return real_attack_time, real_attack_frame, pre_delay, post_delay, scaled_anim_frame
