from .logger import logger, info, warning, success, error, critical
from . import launcher

import os

# Устанавливаем уровень логирования INFO или выше
logger.level("INFO")

if not os.path.exists(path="sessions"):
    os.mkdir(path="sessions")
