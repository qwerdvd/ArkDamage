import asyncio

from .download_from_github import download_all_file_from_github


async def download_all_resource():
    ret = await asyncio.gather(download_all_file_from_github())
    ret = [str(x) for x in ret if x]
    if ret:
        return '\n'.join(ret)
    return '全部资源下载完成!'
