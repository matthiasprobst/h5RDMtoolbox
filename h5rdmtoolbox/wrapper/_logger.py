from .._logger import create_package_logger

name = __package__
logger, file_handler, stream_handler = create_package_logger(__package__)
