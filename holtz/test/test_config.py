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