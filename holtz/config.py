"""
Configuration parsing tools.
"""
import itertools


FOUR_SPACES = " " * 4


def _detectIndentation(f):
    """
    Attempts to detect the indentation of a configuration file.
    
    This consumes lines until it finds one that does not consist entirely of
    whitespace. That line must specify a directory, so the next line must be
    a block indented with by one level.
    """
    # find the first non-whitespace line
    line = ""
    while not line:
        line = f.readline().strip()
        if f.tell() == 0: # empty file
            return ""
    
    # find leading whitespace
    indent = "".join(itertools.takewhile(str.isspace, f.readline()))
    f.seek(0, 0)
    return indent



def _indentLevel(line, indent=FOUR_SPACES):
    """
    Finds the indent level for a given line with the given indentation.
    """
    level = i = 0
    while line.startswith(indent, i):
        level += 1
        i += len(indent)
    
    return level