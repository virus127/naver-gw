# -*- coding: utf-8 -*-

import os


def abs_path(filename):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)


def load_module(module_name):
    """Helper function to load modules when running inside at gateway server"""

    import imp

    if not module_name:
        raise Exception(u'Module name is empty')

    root_dir = os.path.dirname(os.path.abspath(__file__))
    module_dir = os.path.join(root_dir, module_name)

    fp, path, desc = imp.find_module(module_name, [module_dir, ])
    try:
        mod = imp.load_module(module_name, fp, path, desc)
    finally:
        if fp:
            fp.close()
    return mod
