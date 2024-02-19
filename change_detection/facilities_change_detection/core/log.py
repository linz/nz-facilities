import logging

LOGGER_NAME = "facilities_change_detection"


def get_logger() -> logging.Logger:
    return logging.getLogger("facilities_change_detection")


def setup_logging() -> None:
    logger = get_logger()
    logger.setLevel(logging.DEBUG)
    log_formatter = logging.Formatter(fmt="{asctime} {levelname:8} {message}", datefmt="%Y-%m-%d %H:%M:%S", style="{")
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(log_formatter)
    logger.addHandler(stream_handler)
