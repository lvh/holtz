from twisted.trial import unittest

from holtz import compat, config

basicConfig = """
js/
    *.js: JavascriptSomething()
img/
    *.png: PNGOptimizer()
    *.jpg: JPGOptimizer()
style/
    style.css: LESSMasker() 
""".lstrip("\n")
basicFile = compat.StringIO(basicConfig)
basicFileWithTabs = compat.StringIO(basicConfig.replace(" "*4, "\t"))



class IndentationDetectionTest(unittest.TestCase):
    def _testIndentationDetection(self, f, expected):
        self.assertEqual(config._detectIndentation(f), expected)
        self.assertEqual(f.tell(), 0)


    def test_fourSpaces(self):
        self._testIndentationDetection(basicFile, " "*4)


    def test_tabs(self):
        self._testIndentationDetection(basicFileWithTabs, "\t")


    def test_precedingEmptyLines(self):
        f = compat.StringIO("\n\n\n" + basicConfig)
        self._testIndentationDetection(f, " "*4)


    def test_empty(self):
        self._testIndentationDetection(compat.StringIO(), "")



class IndentLevelTest(unittest.TestCase):
    indent = " " * 4

    def _testIndentLevel(self, depth):
        line = self.indent * depth + "abc"
        self.assertEqual(config._indentLevel(line, self.indent), depth)


    def test_empty(self):
        self.assertEqual(config._indentLevel(""), 0)
    

    def test_zero(self):
        self._testIndentLevel(0)


    def test_one(self):
        self._testIndentLevel(1)
    

    def test_two(self):
        self._testIndentLevel(2)



class TabIndentLevelTest(IndentLevelTest):
    indent = "\t"



class ReadUntilTokenTest(unittest.TestCase):
    def _test(self, string, tokens, expectedIndex, expectedToken, start=0):
        index, token = config._readUntilToken(string, tokens, start)
        self.assertEqual(index, expectedIndex)
        self.assertEqual(token, expectedToken)


    def test_simple(self):
        self._test("a, b", ",", 1, ",")


    def test_missing(self):
        self.assertRaises(config.NoTokens, config._readUntilToken, "", ",")



class EntryLineSplitTest(unittest.TestCase):
    def _testSplit(self, line, expectedHead, expectedTail):
        head, tail = config._splitEntryLine(line)
        self.assertEqual(head, expectedHead)
        self.assertEqual(tail, expectedTail)
        

    def test_simple(self):
        self._testSplit("a: b", "a", "b")
    

    def test_escapedColon(self):
        self._testSplit("ab\:cd: efg", "ab\:cd", "efg")


    def assertSplitRaises(self, line):
        self.assertRaises(config.ParseError, config._splitEntryLine, line)
    

    def test_empty(self):
        self.assertSplitRaises("")
    

    def test_singleBackslash(self):
        """
        A single backslash trips up an algorithm that assumes you can just
        read the next token after the escaping backslash.
        """
        self.assertSplitRaises("\\")
    

    def test_missingSpaceAfterColon(self):
        self.assertSplitRaises("abc:def")
    

    def test_endsInColon(self):
        self.assertSplitRaises("abc:")
    

    def test_onlyEscapedColon(self):
        """
        Tests that the algorithm doesn't accidentally go after the unescaped
        colon.
        """
        self.assertSplitRaises("abc\:def")



class ConditionParseTest(unittest.TestCase):
    def _testCondition(self, condition, trues, falses):
        condition = config._parseCondition(condition)
        for t in trues:
            self.assertTrue(condition(t))
        for f in falses:
            self.assertFalse(condition(f))


    def test_literal(self):
        condition = "abc"
        trues = "abc",
        falses = "def",
        self._testCondition(condition, trues, falses)
    

    def test_withAlternation(self):
        condition = "a{x,y,z}b"
        trues = "axb", "ayb", "azb"
        falses = "axyb", "ax"
        self._testCondition(condition, trues, falses)

    
    def test_wildcard(self):
        condition = "a*b"
        trues = "ab", "aab", "aaaaaaaab"
        falses = "a", "aa", "aaaaaaaa"
        self._testCondition(condition, trues, falses)


    def test_singleCharacterWildcard(self):
        condition = "a?b"
        trues = "aab", "abb"
        falses = "a", "ab"
        self._testCondition(condition, trues, falses)



class AlternationParseTest(unittest.TestCase):
    def _testAlternationParse(self, string, expectedIndex, expectedOptions):
        index, options = config._parseAlternation(string, 1)
        self.assertEqual(index, expectedIndex)
        self.assertEqual(options, expectedOptions)
    

    def test_single(self):
        self._testAlternationParse("{a}", 2, ["a"])


    def test_multiple(self):
        self._testAlternationParse("{a,b,c}", 6, ["a", "b", "c"])



nestedConfig = """
a/
    b/
        c/
            d/
                e/
                    f*: X()
""".lstrip("\n")
nestedFile = compat.StringIO(nestedConfig)



class ParserTest(unittest.TestCase):
    def setUp(self):
        self.parser = config.Parser()


    def test_empty(self):
        root = self.parser.root
        self.assertEqual(len(root.subdirectories), 0)
        self.assertEqual(len(root.entries), 0)


    def assertBreadcrumbsEqual(self, expected):
        self.assertEqual(self.parser._breadcrumbs, expected)


    def assertExpectingNewBlock(self):
        self.assertTrue(self.parser._expectingNewBlock)
        self.assertRaises(config.IndentationError, lambda: self.parser.root)


    def assertNotExpectingNewBlock(self):
        self.assertFalse(self.parser._expectingNewBlock)
    

    def assertCompleteParse(self):
        """
        Checks if the parse tree is complete.

        This means that the root directory can be taken out of the parser. If
        the parser was still expecting a block or there are still breadcrumbs
        left, an exception will be raised.

        This specifically only checks that the tree is complete (or, to put
        it differently, the parser's breadcrumb list is empty). It will fail
        if the parser raises IndentationError, which is when there's an emtpy
        block.

        Basically, this should be the case if the last thing pushed into the
        parser was a newline.
        """
        self.assertEqual(len(self.parser._breadcrumbs), 0)
        try:
            self.parser.root
        except config.ParseError as e: # pragma: no cover
            if isinstance(e, config.IndentationError):
                raise
            self.fail("Incomplete tree")


    def test_simple(self):
        def push():
            self.parser.push(basicFile.readline())
        
        push()
        self.assertBreadcrumbsEqual(["js"])
        self.assertExpectingNewBlock()

        push()
        self.assertBreadcrumbsEqual(["js"])
        self.assertNotExpectingNewBlock()

        push()
        self.assertBreadcrumbsEqual(["img"])
        self.assertExpectingNewBlock()

        push()
        self.assertBreadcrumbsEqual(["img"])
        self.assertNotExpectingNewBlock()

        push()
        self.assertBreadcrumbsEqual(["img"])
        self.assertNotExpectingNewBlock()

        push()
        self.assertBreadcrumbsEqual(["style"])
        self.assertExpectingNewBlock()

        push()
        self.assertBreadcrumbsEqual(["style"])
        self.assertNotExpectingNewBlock()

        push()
        self.assertCompleteParse()

        basicFile.seek(0, 0)


    def test_nested(self):
        def push():
            self.parser.push(nestedFile.readline())
        
        push()
        self.assertBreadcrumbsEqual(["a"])
        self.assertExpectingNewBlock()

        push()
        self.assertBreadcrumbsEqual(["a", "b"])
        self.assertExpectingNewBlock()

        push()
        self.assertBreadcrumbsEqual(["a", "b", "c"])
        self.assertExpectingNewBlock()

        push()
        self.assertBreadcrumbsEqual(["a", "b", "c", "d"])
        self.assertExpectingNewBlock()

        push()
        self.assertBreadcrumbsEqual(["a", "b", "c", "d", "e"])
        self.assertExpectingNewBlock()

        push()
        self.assertBreadcrumbsEqual(["a", "b", "c", "d", "e"])
        self.assertNotExpectingNewBlock()

        push()
        self.assertCompleteParse()


    def test_multipleIndents(self):
        self.parser.push("js/")

        def push():
            indent = self.parser._indent
            badLine = "{indent}{indent}x: a".format(indent=indent)
            self.parser.push(badLine)

        self.assertRaises(config.IndentationError, push)
    

    def test_emptyBlock(self):
        self.parser.push("js/")
        self.assertRaises(config.ParseError, self.parser.push, "img/")
    

    def test_incomplete(self):
        self.parser.push("js/")
        self.assertRaises(config.ParseError, lambda: self.parser.root)
