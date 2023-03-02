from pathlib import Path
from pkgutil import iter_modules

from nonebot.log import logger
from nonebot import require, load_all_plugins, get_plugin_by_module_name

require('nonebot_plugin_apscheduler')

if get_plugin_by_module_name("ArkDamage"):
    logger.info("推荐直接加载 ArkDamage 仓库文件夹")
    load_all_plugins(
        [
            f"{module.name}"
            for module in iter_modules([str(Path(__file__).parent)])
        ],
        [],
    )
