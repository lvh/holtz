"""
Representations of the structure of a static directory being served by holtz.
"""
from holtz import compat


class Directory(object):
    """
    A directory being served.
    """
    def __init__(self):
        self.subdirectories = compat.OrderedDict()
        self.entries = []



class Entry(object):
    """
    An entry in a directory.
    """
    def __init__(self, condition, effect):
        self.condition = condition
        self.effect = effect