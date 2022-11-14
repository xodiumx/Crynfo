import logging
import sys


def logs():
    """Настройки логгирования."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s, %(levelname)s, %(filename)s,'
               '%(lineno)s, %(message)s',
        stream=sys.stdout
    )
