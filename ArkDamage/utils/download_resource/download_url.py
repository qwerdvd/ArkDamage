from typing import Tuple, Optional

import aiofiles
from nonebot.log import logger
from aiohttp.client import ClientSession
from aiohttp.client_exceptions import ClientConnectorError

from .RESOURCE_PATH import (
    DPS_ANIMATION_PATH,
    DPS_OPTIONS_PATH,
    DPS_SPECIALTAGS_PATH,
    BATTLE_EQUIP_TABLE_PATH,
    CHARACTER_TABLE_PATH,
    SKILL_TABLE_PATH,
    UNIEQUIP_TABLE_PATH,
)

PATH_MAP = {
    1: DPS_ANIMATION_PATH,
    2: DPS_OPTIONS_PATH,
    3: DPS_SPECIALTAGS_PATH,
    4: BATTLE_EQUIP_TABLE_PATH,
    5: CHARACTER_TABLE_PATH,
    6: SKILL_TABLE_PATH,
    7: UNIEQUIP_TABLE_PATH,
}

proxy = "http://127.0.0.1:10809"


async def download(
        url: str,
        path: int,
        name: str,
) -> Optional[Tuple[str, int, str]]:
    """
    :说明:
      下载URL保存入目录
    :参数:
      * url: `str`
            资源下载地址。
      * path: `int`
            资源保存路径
        '''
        1: DPS_ANIMATION_PATH,
        2: DPS_OPTIONS_PATH,
        3: DPS_SPECIALTAGS_PATH,
        4: BATTLE_EQUIP_TABLE_PATH,
        5: CHARACTER_TABLE_PATH,
        6: SKILL_TABLE_PATH,
        7: UNIEQUIP_TABLE_PATH,
        '''
      * name: `str`
            资源保存名称
    :返回(失败才会有返回值):
        url: `str`
        path: `int`
        name: `str`
    """
    async with ClientSession() as sess:
        return await download_file(sess, url, path, name)


async def download_file(
        sess: ClientSession,
        url: str,
        path: int,
        name: str,
) -> Optional[Tuple[str, int, str]]:
    try:
        async with sess.get(url, proxy=proxy) as res:
            content = await res.read()
    except ClientConnectorError:
        logger.warning(f"[github.com]{name}下载失败")
        return url, path, name
    async with aiofiles.open(PATH_MAP[path], "wb") as f:
        await f.write(content)
