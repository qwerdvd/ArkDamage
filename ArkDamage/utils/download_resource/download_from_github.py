import os
from pathlib import Path
from typing import List, Tuple

import asyncio

from aiohttp import ClientSession
from nonebot import logger

from .download_url import PATH_MAP, download_file

GITHUB_REPO_URL = 'https://api.github.com/repos/Kengxxiao/ArknightsGameData/contents/zh_CN/gamedata/excel/'
BASE_URL = 'https://raw.githubusercontent.com/Kengxxiao/ArknightsGameData/master/zh_CN/gamedata/excel/'
BATTL_EEQUIP_TABLE_URL = BASE_URL + 'battle_equip_table.json'
CHARACTER_TABLE_URL = BASE_URL + 'character_table.json'
SKILL_TABLE_URL = BASE_URL + 'skill_table.json'
UNIEQUIP_TABLE_URL = BASE_URL + 'uniequip_table.json'

FILE_TO_PATH = {
    BATTL_EEQUIP_TABLE_URL: 4,
    CHARACTER_TABLE_URL: 5,
    SKILL_TABLE_URL: 6,
    UNIEQUIP_TABLE_URL: 7,
}

proxy = 'http://127.0.0.1:10809'


async def _get_url(url: str, sess: ClientSession):
    req = await sess.get(url=url, proxy=proxy)
    if req.status != 200:
        return None
    return await req.json()


async def download_all_file_from_github():
    async def _download(tasks: List[asyncio.Task]):
        failed_list.extend(
            list(filter(lambda x: x is not None, await asyncio.gather(*tasks)))
        )
        tasks.clear()
        print('[github.com]下载完成!')

    failed_list: List[Tuple[str, int, str]] = []
    TASKS = []
    async with ClientSession() as sess:
        response_json = await _get_url(GITHUB_REPO_URL, sess)
        if response_json is None:
            logger.error(f'[github.com]获取文件列表失败')
            return
        required_files = [
            'battle_equip_table.json',
            'character_table.json',
            'skill_table.json',
            'uniequip_table.json'
        ]
        files_info = []
        for item in response_json:
            file_name = item['name']
            if file_name in required_files:
                files_info.append(
                    {
                        'file_name': file_name,
                        'sha': item['sha'],
                        'download_url': item['download_url']
                    }
                )
        logger.info(f"[github.com]需要下载 {len(files_info)} 个文件")
        temp_num = 0
        for item in files_info:
            url = item['download_url']
            name = item['file_name']
            sha = item['sha']
            path = Path(PATH_MAP[FILE_TO_PATH[url]])
            if path.exists():
                is_diff = sha == path.read_text()
            else:
                is_diff = True
            if (
                    not path.exists()
                    or not os.stat(path).st_size
                    or not is_diff
            ):
                logger.info(
                    f'[github.com]开始下载[{name}]...'
                )
                temp_num += 1
                TASKS.append(
                    asyncio.wait_for(
                        download_file(sess, url, FILE_TO_PATH[url], name),
                        timeout=60,
                    )
                )
                # await download_file(url, FILE_TO_PATH[file], name)
                if len(TASKS) >= 10:
                    await _download(TASKS)
        else:
            await _download(TASKS)
        if temp_num == 0:
            im = f'[github.com]数据库无需下载!'
        else:
            im = f'[github.com]数据库已下载{temp_num}个内容!'
        temp_num = 0
        logger.info(im)
    if failed_list:
        logger.info(f'[minigg.icu]开始重新下载失败的{len(failed_list)}个文件...')
        for url, file, name in failed_list:
            TASKS.append(
                asyncio.wait_for(
                    download_file(sess, url, file, name),
                    timeout=60,
                )
            )
            if len(TASKS) >= 10:
                await _download(TASKS)
        else:
            await _download(TASKS)
        if count := len(failed_list):
            logger.error(f'[github.com]仍有{count}个文件未下载，请使用命令 `下载全部资源` 重新下载')
