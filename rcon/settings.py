import os
import re
import socket
from logging.config import dictConfig
from subprocess import PIPE, run

# Определяем SERVER_INFO сразу, до любых других импортов, которые могут вызвать ошибки
# Используем dict без типизации, чтобы избежать циклических импортов
# Это должно быть определено ДО любых других операций, которые могут вызвать ошибки
SERVER_INFO = {
    "host": os.getenv("HLL_HOST"),
    "port": os.getenv("HLL_PORT"),
    "password": os.getenv("HLL_PASSWORD"),
}

# Все остальное оборачиваем в try/except, чтобы гарантировать, что SERVER_INFO всегда определен
try:
    # Импортируем RconServerSettingsUserConfig после определения SERVER_INFO
    try:
        from rcon.user_config.rcon_server_settings import RconServerSettingsUserConfig
    except (ImportError, Exception):
        # Если импорт не удался, используем значения по умолчанию
        RconServerSettingsUserConfig = None

    try:
        TAG_VERSION = (
            run(["git", "describe", "--tags"], stdout=PIPE, stderr=PIPE)
            .stdout.decode()
            .strip()
        )
    except Exception:
        TAG_VERSION = "unknown"

    try:
        if RconServerSettingsUserConfig is not None:
            config = RconServerSettingsUserConfig.load_from_db()
            ENVIRONMENT = re.sub("[^0-9a-zA-Z]+", "", (config.short_name or "default").strip())[
                :64
            ]
        else:
            ENVIRONMENT = "undefined"
    except Exception:
        ENVIRONMENT = "undefined"
except Exception:
    # Если что-то пошло не так, используем значения по умолчанию
    RconServerSettingsUserConfig = None
    TAG_VERSION = "unknown"
    ENVIRONMENT = "undefined"

# TODO: Use a config style that is not required at import time


def check_config():
    for k, v in SERVER_INFO.items():
        if not v:
            raise ValueError(f"{k} environment variable must be set")
    try:
        SERVER_INFO["port"] = int(SERVER_INFO["port"])
    except ValueError as e:
        raise ValueError("HLL_PORT must be an integer") from e


# TODO add sentry
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "console": {
            "format": f"[%(asctime)s][%(levelname)s][{ENVIRONMENT}][{TAG_VERSION}] %(name)s "
            "%(filename)s:%(funcName)s:%(lineno)d | %(message)s",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "console",
        },
        "file": {
            "level": "DEBUG",
            "formatter": "console",
            "class": "logging.FileHandler",
            "filename": os.path.join(
                os.getenv("LOGGING_PATH", ""),
                os.getenv("LOGGING_FILENAME", f"{socket.gethostname()}.log"),
            ),
        },
    },
    "loggers": {
        __package__: {
            "handlers": ["console", "file"],
            "level": os.getenv("LOGGING_LEVEL", "DEBUG"),
            "propagate": False,
        },
        "__main__": {
            "handlers": ["console", "file"],
            "level": os.getenv("LOGGING_LEVEL", "DEBUG"),
            "propagate": False,
        },
        "rcon.rcon": {
            "level": os.getenv("COMMANDS_LOGLEVEL", os.getenv("LOGGING_LEVEL", "INFO"))
        },
        "rcon.commands": {
            "level": os.getenv("COMMANDS_LOGLEVEL", os.getenv("LOGGING_LEVEL", "INFO"))
        },
        # TODO fix that
        "rcon.automods.automod": {
            "handlers": ["console", "file"],
            "level": os.getenv("LOGGING_LEVEL", "DEBUG"),
            "propagate": False,
        },
    },
}

dictConfig(LOGGING)
