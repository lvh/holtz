"""
Configuration parsing tools.
"""
import ast
import itertools
import re

from twisted.protocols import basic

from holtz import structure


FOUR_SPACES = " " * 4



class Parser(object):
    def __init__(self, indent=FOUR_SPACES):
        self._root = structure.Directory()
        self._breadcrumbs = []
        self._indent = indent
        self._expectingNewBlock = False


    @property
    def _indentLevel(self):
        return len(self._breadcrumbs)
    

    @property
    def _currentDirectory(self):
        # Yes, looking this up every time is inefficient. This is not a
        # problem until proven otherwise. -- lvh
        d = self._root
        for b in self._breadcrumbs:
            d = d.subdirectories[b]
        return d


    @property
    def root(self):
        if self._expectingNewBlock:
            message = "Expecting a block line: empty block at end?"
            raise IndentationError(message)
        if self._breadcrumbs:
            message = "Incomplete tree: missing newline at end?"
            raise ParseError(message)
        return self._root


    def push(self, line):
        delta = _indentLevel(line, self._indent) - self._indentLevel

        if delta > 0:
            message = "+{} indent levels, expected at most +0".format(delta)
            raise IndentationError(message, line)
        
        if delta < 0:
            if self._expectingNewBlock:
                raise ParseError("Preceding block is empty!")
            del self._breadcrumbs[delta:]

        line = line.strip()
        if not line:
            return
        
        if line.endswith("/"):
            self._parseDirectory(line)
        else:
            self._parseEntry(line)


    def _parseDirectory(self, line):
        name = line.rstrip("/")
        directory = structure.Directory()
        self._currentDirectory.subdirectories[name] = directory

        self._breadcrumbs.append(name)
        self._expectingNewBlock = True


    def _parseEntry(self, line):
        conditionString, effectString = _splitEntryLine(line)

        condition = _parseCondition(conditionString)
        effect = _parseEffect(effectString)

        entry = structure.Entry(condition, effect)
        self._currentDirectory.entries.append(entry)

        self._expectingNewBlock = False



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


def _readUntilToken(string, tokens, start=0):
    """
    Reads the string until one of the given tokens is found.
    """
    it = itertools.islice(enumerate(string), start, None)
    for i, x in it:
        if x == "\\":
            try:
                it.next()
            except StopIteration:
                raise ParseError("Lone backslash at end", string)
        elif x in tokens:
            break
    else:
        raise NoTokens(tokens, string)

    return i, x


def _unescape(string):
    def unescaped():
        it = iter(string)
        for x in it:
            if x == "\\":
                yield it.next()
            else:
                yield x

    return "".join(unescaped())


def _splitEntryLine(line):
    """
    Splits an entry line into strings representing its condition and effect
    clauses.

    Effectively, this splits at the first unescaped colon and verifies that
    the colon has a space directly following it.
    """
    i, _ = _readUntilToken(line, ":")

    try:
        if line[i + 1] != " ":
            raise ParseError("Missing space after colon", line)
    except IndexError:
        raise ParseError("Entry ends with unescaped colon", line)
    
    return line[:i], line[i+2:]


def _parseCondition(string):
    index, parts = 0, []
    try:
        while True:
            oldIndex = index
            index, token = _readUntilToken(string, "{*?", index)

            parts.append(re.escape(string[oldIndex:index]))

            if token == "{":
                index, options = _parseAlternation(string, index + 1)
                part = "({})".format("|".join(map(re.escape, options)))
                parts.append(part)
            if token == "*":
                parts.append(".*")
            if token == "?":
                parts.append(".")
            
            index += 1
    except NoTokens:
        if parts:
            parts.append(string[index:])
            return re.compile("".join(parts)).match
        else:
            return string.__eq__


def _parseAlternation(string, start):
    oldIndex, token = start, "{"

    options = []
    while token != "}":
        newIndex, token = _readUntilToken(string, ",}", oldIndex)
        options.append(string[oldIndex:newIndex])
        oldIndex = newIndex + 1

    return newIndex, map(_unescape, options)


def _parseEffect(string):
    expr = ast.parse(string, mode="eval").body
    
    if isinstance(expr, ast.Name) and expr.id == "None":
        expr = None
    elif not isinstance(expr, ast.Call):
        exprType = expr.__class__
        message = "Effect expr must be a call or None, was {}".format(exprType)
        raise ParseError(message)
    elif not isinstance(expr.func, ast.Name):
        callee = expr.func.__class__
        message = "Effect must call names, was {}".format(callee)
        raise ParseError(message)
    
    # expr is None or a valid call expr
    
    def effect(filePath, request, registry, resolver):
        if expr is not None:
            processorClass = registry[expr.func.id]
            contentType = processorClass.producer.contentType
            expression = ast.Expression(expr)
        else:
            contentType = resolver(filePath)

        request.setHeader("Content-Type", contentType)

        producer = basic.FileSender()        
        producer.beginFileTransfer(filePath.open(), request)
    
    return effect



class ParseError(Exception):
    """
    Raised when an error occurred parsing a configuration file.
    """
    def __init__(self, message, line=None, lineNumber=None):
        self.message = message
        self.line = line
        self.lineNumber = lineNumber
        Exception.__init__(self, message, line, lineNumber)



class IndentationError(ParseError):
    """
    Raised when a configuration file has faulty indentation.
    """



class NoTokens(ParseError):
    """
    Raised when an expected token was not found in a string.
    """
    def __init__(self, tokens, line):
        tokens = ", ".join(tokens)
        message = "No unescaped tokens (expecting one of {})".format(tokens)
        ParseError.__init__(self, message, line)