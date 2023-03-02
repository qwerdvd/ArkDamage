import json

import aiohttp
from nonebot import logger
from pydantic import BaseModel

from ..version import clientVersion, resVersion


class ArknightsVersion(BaseModel):
    resVersion: str
    clientVersion: str


async def get_ark_version() -> tuple[ArknightsVersion, bool]:
    async with aiohttp.ClientSession() as session:
        async with session.get("https://ak-conf.hypergryph.com/config/prod/official/Android/version") as response:
            response.raise_for_status()  # raises an exception for 4xx or 5xx status codes
            data = await response.text()
    json_data = json.loads(data)
    ark_version = ArknightsVersion(**json_data)
    if ark_version.clientVersion == clientVersion and ark_version.resVersion == resVersion:
        logger.info("Arknights and resource version are consistent")
        return ark_version, True
    else:
        logger.warning("Arknights and resource version are inconsistent")
        logger.warning(f"Current Arknights version: {clientVersion}")
        logger.warning(f"Current resource version: {resVersion}")
        return ark_version, False
