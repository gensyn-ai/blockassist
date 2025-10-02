import logging
import socket
import time

_DATA_DIR = "data"
_DEFAULT_CHECKPOINT = f"{_DATA_DIR}/base_checkpoint"
_DEFAULT_EPISODES_S3_BUCKET = "blockassist-episode"

_MAX_EPISODE_COUNT = 1
_LOG = None


def get_logger() -> logging.Logger:
    global _LOG
    if not _LOG:
        logging.basicConfig(filename="logs/blockassist.log")
        _LOG = logging.getLogger(__name__)
    lib_logger = logging.getLogger("mbag")
    lib_logger.setLevel(logging.ERROR)
    lib_logger.propagate = False
    lib_logger.addHandler(logging.NullHandler())
    return _LOG


def get_hostname() -> str:
    return socket.gethostname()


def get_ip(hostname=get_hostname()) -> str:
    return socket.gethostbyname(hostname)


def get_training_id(address_eoa: str) -> str:
    return f"{address_eoa}_{int(time.time())}"
