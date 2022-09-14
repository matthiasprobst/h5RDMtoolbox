from ._logger import logger, file_handler, stream_handler


def set_loglevel(level):
    """setting the logging level of sub-package h5wrapper"""
    logger.setLevel(level.upper())
    file_handler.setLevel(level.upper())
    stream_handler.setLevel(level.upper())


__all__ = ['set_loglevel', ]
