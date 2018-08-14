# -*- coding: utf-8 -*-


def load_module(module_name):
    """Helper function to load modules when running inside at gateway server"""

    import imp
    import os

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
