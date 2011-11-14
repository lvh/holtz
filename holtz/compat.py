"""
Compatibility module.

This module exports a bunch of third party classes that are available under
different names with a consistent name.
"""
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict