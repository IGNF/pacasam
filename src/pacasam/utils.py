import logging
import sys


def get_logger(__name__):
    log = logging.getLogger(__name__)
    handler = logging.StreamHandler(sys.stdout)
    log.setLevel(logging.DEBUG)
    log.addHandler(handler)
    return log
