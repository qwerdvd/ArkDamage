from nonebot.adapters.onebot.v11 import Message
from nonebot.params import Depends, CommandArg
from nonebot.rule import Rule


async def full_command(arg: Message = CommandArg()) -> bool:
    return not bool(str(arg))


def FullCommand() -> Rule:
    return Rule(full_command)


def FullCommandDepend():
    return Depends(full_command)
