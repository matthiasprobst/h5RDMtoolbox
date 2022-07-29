import logging
import os
import sys

logger = logging.getLogger(__package__)


def call_cmd(cmd, wait=True):
    logger.debug(cmd)
    if sys.platform.lower() == 'windows' and wait:
        logger.debug('Under windows wait has no effect.'
                     ' The system will always wait until the batch command has finished')
    if wait:
        logger.debug(f'Calling command str: {cmd}')
        os.system(f'{cmd}')
    else:
        cmd += ' &'
        logger.debug(f'Calling command str: {cmd}')
        os.system(f'{cmd}')