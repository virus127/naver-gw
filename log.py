# -*- coding: utf-8 -*-

import logging
import logging.config
import os

LOGS_DIR = os.path.dirname(os.path.abspath(__file__))

LOG_FILE_NAME = 'gwkit.log'
LOG_FORMAT = '%(asctime)s %(levelname)s %(name)-12s %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

DEFAULT_LOG_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': LOG_FORMAT,
            'dmtformat': DATE_FORMAT,
        },
    },
    'handlers': {
        'file': {
            '()': logging.FileHandler,
            'formatter': 'default',
            'filename': os.path.join(LOGS_DIR, LOG_FILE_NAME),
            'mode': 'a',
            'encoding': 'utf-8',
        },
    },
    'loggers': {
        'root': {
            'level': 'DEBUG',
            'handlers': ['file']
        },
    },
}


def setup_logger(log_config=None):
    if not log_config:
        log_config = DEFAULT_LOG_CONFIG

    # TODO: change to use fileConfig only?
    try:
        logging.config.dictConfig(log_config)
    except AttributeError:  # in python 2.6 there is no dictConfig
        logging.config.fileConfig('logging.conf', disable_existing_loggers=False)
