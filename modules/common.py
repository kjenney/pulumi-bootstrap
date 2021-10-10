import importlib

def dynamic_import(module):
    """Import a module by path"""
    return importlib.import_module(module)