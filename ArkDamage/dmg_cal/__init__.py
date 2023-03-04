from nonebot import on_command, logger
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, MessageSegment
from nonebot.internal.matcher import Matcher
from nonebot.params import CommandArg
from nonebot_plugin_apscheduler import scheduler

from src.plugins.ArkDamage.ArkDamage.dmg_cal.CalDpsSeries import cal_
from .CalCharAttributes import check_specs
from .CalDps import calculate_dps
from .Character import Character
from .InitChar import InitChar, handle_mes
from .model.models import Enemy
from ..resource.check_version import get_ark_version
from ..utils.message.send_msg import send_forward_msg

dmg_cal = on_command("伤害计算", priority=5, block=True)
char_curve = on_command("干员曲线", priority=5, block=True)

dmg_cal_scheduler = scheduler


@dmg_cal_scheduler.scheduled_job('cron', hour=0)
async def daily_check_version():
    await get_ark_version()


# 伤害计算
# "伤害计算 能天使 满潜 精二90 三技能 一模"
# 默认满技能满潜模组满级
@dmg_cal.handle()
async def send_dmg_cal_msg(
        bot,
        event: GroupMessageEvent,
        args: Message = CommandArg()
):
    logger.info("开始执行[干员伤害计算]")
    raw_mes = args.extract_plain_text().strip()
    logger.info(f"参数：{raw_mes}")
    mes = await handle_mes(raw_mes.split())
    logger.info(f"参数：{mes}")
    base_char_info = InitChar(mes)
    char = Character(base_char_info)
    enemy = Enemy({'defense': 0, 'magicResistance': 0, 'count': 1, 'hp': 0})
    dps = await calculate_dps(base_char_info, char, enemy)
    if await check_specs(base_char_info.skill_id, "overdrive"):  # 过载
        forward_msg = [
            f"干员：{char.CharData.name}",
            f"潜能：{base_char_info.potentialRank + 1}",
            f"稀有度：{base_char_info.rarity + 1} ★",
            f"精英化：{base_char_info.phase}",
            f"等级：{base_char_info.level}",
            f"技能：{dps['skillName']}",
            f"技能等级：{base_char_info.skillLevel}",
            f"模组：{base_char_info.equip_id}",
            f"攻击力：{dps['skill']['atk']:.2f}",
            f"攻击次数：{dps['skill']['dur']['hitCount']}",
            f"技能伤害：{float(dps['skill']['totalDamage']):.2f}",
            f"持续时间：{dps['skill']['dur']['duration']}",
            f"技能DPS：{float(dps['skill']['dps']):.2f}",
            f"技能HPS：{float(dps['skill']['hps']):.2f}"
        ]
    elif await check_specs(base_char_info.skill_id, "token"):  # 召唤物
        forward_msg = [
            f"干员：{char.CharData.name}",
            f"潜能：{base_char_info.potentialRank + 1}",
            f"稀有度：{base_char_info.rarity + 1} ★",
            f"精英化：{base_char_info.phase}",
            f"等级：{base_char_info.level}",
            f"技能：{dps['skillName']}",
            f"技能等级：{base_char_info.skillLevel}",
            f"模组：{base_char_info.equip_id}",
            f"攻击力：{dps['skill']['atk']:.2f}",
            f"攻击次数：{dps['skill']['dur']['hitCount']}",
            f"技能伤害：{float(dps['skill']['totalDamage']):.2f}",
            f"持续时间：{dps['skill']['dur']['duration']}",
            f"技能DPS：{float(dps['skill']['dps']):.2f}",
            f"技能HPS：{float(dps['skill']['hps']):.2f}"
        ]
    else:
        forward_msg = [
            f"干员：{char.CharData.name}",
            f"潜能：{base_char_info.potentialRank + 1}",
            f"稀有度：{base_char_info.rarity + 1} ★",
            f"精英化：{base_char_info.phase}",
            f"等级：{base_char_info.level}",
            f"技能：{dps['skillName']}",
            f"技能等级：{base_char_info.skillLevel}",
            f"模组：{base_char_info.equip_id}",
            f"攻击力：{dps['skill']['atk']:.2f}",
            f"攻击次数：{dps['skill']['dur'].hitCount}",
            f"技能伤害：{float(dps['skill']['totalDamage']):.2f}",
            f"持续时间：{dps['skill']['dur'].duration}",
            f"技能DPS：{float(dps['skill']['dps']):.2f}",
            f"技能HPS：{float(dps['skill']['hps']):.2f}"
        ]
    await send_forward_msg(bot, event.group_id, "小小小小真寻", "2673918369", forward_msg)


# 曲线绘制
# "曲线绘制 能天使"
@char_curve.handle()
async def send_char_curve_msg(
        matcher: Matcher,
        args: Message = CommandArg()
):
    logger.info("开始执行[干员伤害曲线绘制]")
    raw_mes = args.extract_plain_text().strip()
    logger.info(f"参数：{raw_mes}")
    mes = await handle_mes(raw_mes.split())
    logger.info(f"参数：{mes}")
    base_char_info = InitChar(mes)
    char = Character(base_char_info)
    enemy = Enemy({'defense': 0, 'magicResistance': 0, 'count': 1, 'hp': 0})
    img = await cal_(base_char_info, char, enemy)
    if img is not None:
        await matcher.finish(MessageSegment.image(img))
    else:
        await matcher.finish("为医疗干员，无法绘制曲线")


async def test(message_list: list):
    mes = await handle_mes(message_list)
    base_char_info = InitChar(mes)
    char = Character(base_char_info)
    enemy = Enemy({'defense': 0, 'magicResistance': 0, 'count': 1, 'hp': 0})
    dps = await calculate_dps(base_char_info, char, enemy)
    print(dps['log'])


if __name__ == "__main__":
    import asyncio

    # message = ['早露', '精二90', '二技能', '一模']
    message = ['仇白', '精二90', '三技能', 'None']
    asyncio.run(test(message))
