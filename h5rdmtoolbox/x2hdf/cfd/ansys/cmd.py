import logging
import os

logger = logging.getLogger(__package__)


def call_cmd(cmd, wait=True):
    """Run the cmd with os.system() or subprocess.call()"""
    logger.debug(cmd)
    if os.name == 'nt' and wait:
        import subprocess
        logger.debug('Under windows wait has no effect.'
                     ' The system will always wait until the batch command has finished')
        subprocess.call(cmd)
    else:
        if wait:
            logger.debug(f'Calling command str: {cmd}')
            os.system(f'{cmd}')
        else:
            cmd += ' &'
            logger.debug(f'Calling command str: {cmd}')
            os.system(f'{cmd}')