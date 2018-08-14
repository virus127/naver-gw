# -*- coding: utf-8 -*-

import logging
import logging.config


def setup_logger():
    logging.config.fileConfig('logging.conf', disable_existing_loggers=False)
