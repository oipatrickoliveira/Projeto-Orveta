"""Local diagnostic logging without links, file paths, cookies or arguments."""
import logging
from logging.handlers import RotatingFileHandler


def create_logger(data_dir):
    logger = logging.getLogger('orveta')
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    logger.propagate = False
    try:
        directory = data_dir / 'logs'
        directory.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(directory / 'orveta.log', maxBytes=262144, backupCount=3, encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        logger.addHandler(handler)
    except OSError:
        logger.addHandler(logging.NullHandler())
    return logger
