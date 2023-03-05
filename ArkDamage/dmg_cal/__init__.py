import json
import os

from nonebot import on_command, logger
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, MessageSegment, permission
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot_plugin_apscheduler import scheduler

from .CalCharAttributes import check_specs
from .CalDps import calculate_dps
from .CalDpsSeries import cal_
from .Character import Character
from .InitChar import InitChar, handle_mes
from .load_json import enemy_database
from .model.enemy_data import EnemyDataBase
from .model.models import Enemy
from ..resource.check_version import get_ark_version
from ..utils.download_resource.RESOURCE_PATH import MAIN_PATH
from ..utils.message.send_msg import send_forward_msg

IsAdmin = permission.GROUP_OWNER | permission.GROUP_ADMIN | SUPERUSER

dmg_cal = on_command("伤害计算", priority=5, block=True)
char_curve = on_command("干员曲线", priority=5, block=True)
set_enemy = on_command("设置敌人", priority=5, block=True, permission=IsAdmin)

dmg_cal_scheduler = scheduler

default_enemy = {'defense': 0, 'magicResistance': 0, 'count': 1, 'hp': 0, 'name': 'default'}


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
    char_info = InitChar(mes)
    char = Character(char_info)
    enemy_dict = await load_json(group_id=event.group_id)
    if enemy_dict:
        logger.info("已找到敌人信息，使用自定义敌人")
        enemy = Enemy(enemy_dict)
    else:
        logger.info("未找到敌人信息，使用默认敌人")
        enemy = Enemy(default_enemy)
    dps = await calculate_dps(char_info, char, enemy)
    base_forward_msg = [
        f"干员：{char.CharData.name}",
        f"潜能：{char_info.potentialRank + 1}",
        f"稀有度：{char_info.rarity + 1} ★",
        f"精英化：{char_info.phase}",
        f"等级：{char_info.level}",
        f"skill: {char_info.skill_id}\n"
        f"level: {char_info.skillLevel}",
        f"equip: {char_info.equip_id}",
        f"enemy: {enemy.name}\n"
        f"defense: {enemy.defense}\n"
        f"magicResistance: {enemy.magicResistance}\n"
        f"maxHp: {enemy.hp}",
    ]
    if await check_specs(char_info.skill_id, "overdrive"):  # 过载
        forward_msg = base_forward_msg + [
            f"攻击力：{dps['skill']['atk']:.2f}",
            f"攻击次数：{dps['skill']['dur']['hitCount']}",
            f"技能伤害：{float(dps['skill']['totalDamage']):.2f}",
            f"持续时间：{dps['skill']['dur']['duration']}",
            f"技能DPS：{float(dps['skill']['dps']):.2f}",
            f"技能HPS：{float(dps['skill']['hps']):.2f}"
        ]
    elif await check_specs(char_info.skill_id, "token"):  # 召唤物
        forward_msg = base_forward_msg + [
            f"攻击力：{dps['skill']['atk']:.2f}",
            f"攻击次数：{dps['skill']['dur']['hitCount']}",
            f"技能伤害：{float(dps['skill']['totalDamage']):.2f}",
            f"持续时间：{dps['skill']['dur']['duration']}",
            f"技能DPS：{float(dps['skill']['dps']):.2f}",
            f"技能HPS：{float(dps['skill']['hps']):.2f}"
        ]
    else:
        forward_msg = base_forward_msg + [
            f"攻击力：{dps['skill']['atk']:.2f}",
            f"攻击次数：{dps['skill']['dur'].hitCount}",
            f"技能伤害：{float(dps['skill']['totalDamage']):.2f}",
            f"持续时间：{dps['skill']['dur'].duration}",
            f"技能DPS：{float(dps['skill']['dps']):.2f}",
            f"技能HPS：{float(dps['skill']['hps']):.2f}"
        ]
    await send_forward_msg(bot, event.group_id, "小小小小真寻", "2673918369", forward_msg)


# 干员曲线
# "干员曲线 能天使 满潜 精二90 三技能 一模"
@char_curve.handle()
async def send_char_curve_msg(
        matcher: Matcher,
        event: GroupMessageEvent,
        args: Message = CommandArg()
):
    logger.info("开始执行[干员伤害曲线绘制]")
    raw_mes = args.extract_plain_text().strip()
    logger.info(f"参数：{raw_mes}")
    mes = await handle_mes(raw_mes.split())
    logger.info(f"参数：{mes}")
    char_info = InitChar(mes)
    char = Character(char_info)
    enemy = Enemy(default_enemy)
    img = await cal_(char_info, char, enemy)
    if img is not None:
        await matcher.finish(MessageSegment.image(img))
    else:
        await matcher.finish("为医疗干员，无法绘制曲线")


# 设置群里敌人
# "设置敌人 杰斯顿 2个"
@set_enemy.handle()
async def send_set_enemy_msg(
        matcher: Matcher,
        event: GroupMessageEvent,
        args: Message = CommandArg()
):
    group_id = event.group_id
    logger.info("开始执行[设置敌人]")
    raw_mes = args.extract_plain_text().strip()
    mes = raw_mes.split()
    logger.info(f"参数：{mes}")
    enemy_name = mes[0]
    mes[1] = mes[1].replace("个", "")
    count = mes[1]
    logger.info(f"参数：{mes}")
    enemy_list = enemy_database['enemies']
    for enemy in enemy_list:
        if enemy['Value'][0]['enemyData']['name']['m_value'] == enemy_name:
            enemy_data = EnemyDataBase(enemy)
            break
    else:
        await matcher.finish("未找到该敌人")
    defense = enemy_data.Value[-1].enemyData.attributes.defense.m_value
    magicResistance = enemy_data.Value[-1].enemyData.attributes.magicResistance.m_value
    count = int(count)
    hp = enemy_data.Value[-1].enemyData.attributes.maxHp.m_value
    enemy_key = enemy_data.Key
    enemy_name = enemy_data.Value[0].enemyData.name.m_value

    enemy_dict = {'defense': defense, 'magicResistance': magicResistance, 'count': count, 'hp': hp, 'name': enemy_key}
    data = await read_json()
    if group_id in data:
        js = data
        js[group_id] = enemy_dict
    else:
        js = {group_id: enemy_dict}
    await save_json(js)
    await matcher.finish(f"已设置敌人为{enemy_name}，数量为{count}个")


async def test(message_list: list):
    mes = await handle_mes(message_list)
    char_info = InitChar(mes)
    char = Character(char_info)
    enemy = Enemy({'defense': 0, 'magicResistance': 0, 'count': 1, 'hp': 0})
    dps = await calculate_dps(char_info, char, enemy)
    print(dps['log'])


filename = MAIN_PATH / 'enemy.json'


async def read_json():
    if os.path.isfile(filename):
        with open(filename, 'r') as f:
            content = f.read()
    else:
        content = "{}"
    return json.loads(content)


async def save_json(js):
    with open(filename, 'w') as f:
        f.write(json.dumps(js))
    f.close()


async def load_json(group_id):
    data = await read_json()
    for key in data:
        if int(key) == group_id:
            return data[key]
    else:
        return None


if __name__ == "__main__":
    import asyncio

    # message = ['早露', '精二90', '二技能', '一模']
    message = ['仇白', '精二90', '三技能', 'None']
    asyncio.run(test(message))
