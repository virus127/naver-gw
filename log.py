# -*- coding: utf-8 -*-

import logging
import logging.config

from helper import abs_path


def setup_logger():
    config_path = abs_path('logging.conf')
    logging.config.fileConfig(config_path, disable_existing_loggers=False)
