import warnings
from io import StringIO
from typing import List, Union, Optional

from mytable.ast.base import *
from mytable.config import identifier_length_limits

__all__ = [
    "ScannerException",
    "Scanner",
]

from mytable.ast.expression import Identifier, String, Number


class ScannerException(MyTableException):
    pass


MAXIMUM_STRING_LENGTH = 65000
MAXIMUM_IDENTIFIER_LENGTH = max(identifier_length_limits.values())

COMMENT_STARTS = {"#", "-- "}
DELIMITERS = {"(", ")", "<", ">", "=", ",", ";"}


def is_whitespace(c: str):
    return c in [" ", "\t", "\r", "\n"]

def is_valid_name_char(c: str):
    return c.isalnum() or c.isdigit() or c in {"_", "."}


def is_delimiter(c: str):
    return c.isspace() or c in DELIMITERS


def is_number_initial(c: str):
    return c == "-" or c.isdigit()


def is_java_type_initial(node: Node):
    return isinstance(node, Identifier) and node.value in {"List", "Map"}


class Scanner(object):
    def __init__(
            self,
            *,
            text: Optional[str] = None,
            filename: Optional[str] = None,
            debug_mode: bool = False
    ):
        if text is None and filename is None:
            raise TypeError("`text` and `filename` cannot both be None")

        if text and filename:
            warnings.warn("only one of `text` and `filename` is required, using `text`")

        self.text = text
        self.filename = filename
        self.offset = 0
        self.line = 1
        self.column = 1
        self.debug_mode = debug_mode

        self.content = None
        self.length = None
        self.buffer = None

        if self.text is not None:
            self.content = text
            self.length = len(text)
            self.buffer = StringIO(self.content)
        elif self.filename is not None:
            self.load_file()
        else:
            raise ScannerException("bug, should not happen")

    def load_file(self):
        self.content = open(self.filename, "r").read()
        self.length = len(self.content)
        self.buffer = StringIO(self.content)

    def abort(self, *args):
        msg = f"{args} at {self.line}: {self.column}"
        raise ScannerException(msg)

    def debug(self, x):
        if self.debug_mode:
            print(f"'{x}' line:{self.line} column:{self.column}")

    def peek(self, n=1) -> str:
        """Pick one char or N chars without consuming it/them"""
        s = self.buffer.read(n)
        self.debug(s)
        current_position = self.buffer.tell()
        if current_position == 0 or s == "":
            return ""
        else:
            self.buffer.seek(self.buffer.tell() - n)
            return s

    def forward(self) -> str:
        c = self.buffer.read(1)

        if c == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1

        self.offset += 1

        return c

    def skip_comment(self):
        while True:
            c = self.peek()
            if c == "":
                break
            elif c == "\n":
                self.forward()
                break
            else:
                self.forward()

    def skip_whitespace(self):
        while True:
            c = self.peek()
            if c == "":
                return ""
            elif c.isspace():
                self.forward()
            else:
                break

    def read_string(self) -> String:
        start = self.offset
        start_line = self.line
        start_col = self.column
        self.forward()  # skip the '
        value = ""
        for i in range(MAXIMUM_STRING_LENGTH):
            c = self.peek()
            if c == "":
                raise ScannerException("unexpected eof while reading string")
            elif c == "'":
                self.forward()
                position = Position(start, self.offset, start_line, start_col, self.line, self.column)
                return String(value, file=self.filename, position=position)
            else:
                c = self.forward()
                value += c

        raise ScannerException(f"maximum string length ({MAXIMUM_STRING_LENGTH}) exceeded")

    def read_number(self, negative=False) -> Number:
        start = self.offset
        start_line = self.line
        start_col = self.column
        digits = ""
        for i in range(MAXIMUM_STRING_LENGTH):
            c = self.peek()
            if c.isdigit():
                digits += self.forward()
            else:
                if negative:
                    value = -int(digits)
                else:
                    value = int(digits)
                position = Position(start, self.offset, start_line, start_col, self.line, self.column)
                return Number(value, file=self.filename, position=position)

        raise ScannerException(f"maximum string length ({MAXIMUM_STRING_LENGTH}) exceeded")

    def expect_quasiquote(self):
        start = self.offset
        start_line = self.line
        start_col = self.column
        value = ""
        for i in range(MAXIMUM_IDENTIFIER_LENGTH):
            c = self.peek()
            if c == "":
                self.abort("unexpected eof while reading quoted identifier")
            elif c == "`":
                self.forward()
                position = Position(start, self.offset, start_line, start_col, self.line, self.column)
                return Identifier(value, quoted=True, file=self.filename, position=position)
            elif is_valid_name_char(c):
                c = self.forward()
                value += c
            else:
                self.abort("invalid char while reading quoted identifier", c)

        self.abort(f"maximum string length ({MAXIMUM_IDENTIFIER_LENGTH}) exceeded")

    def read_identifier(self) -> Identifier:
        start = self.offset
        start_line = self.line
        start_col = self.column
        value = ""
        for i in range(MAXIMUM_IDENTIFIER_LENGTH):
            c = self.peek()
            if c == "" or is_delimiter(c):
                position = Position(start, self.offset, start_line, start_col, self.line, self.column)
                return Identifier(value, quoted=False, file=None, position=position)
            elif c == "`":
                self.abort("unmatched quasiquote")
            elif is_valid_name_char(c):
                c = self.forward()
                value += c
            else:
                self.abort("invalid char while reading identifier", c)

        self.abort(f"maximum identifier length ({MAXIMUM_IDENTIFIER_LENGTH}) exceeded")

    def scan(self) -> List[Union[String, Number, Identifier, Delimiter]]:
        result = []
        while True:
            c = self.peek()
            if c == "":
                return result
            elif c.isspace():
                seen = self.skip_whitespace()
                if seen == "":
                    return result
            elif c == "-":
                s = self.peek(2)
                if s == "--":
                    for i in range(2):
                        self.forward()
                    c = self.peek()
                    if c.isspace():
                        self.skip_comment()
                    else:
                        self.abort("'--' style comment must follow a space immediately")
                else:
                    self.forward()
                    c = self.peek()
                    if is_whitespace(c):
                        self.skip_whitespace()
                        result.append(self.read_number(negative=True))
                    elif c.isdigit():
                        result.append(self.read_number(negative=True))
                    else:
                        self.abort("unhandled condition")
            elif c == "#":
                s = self.peek(4)
                if s == "#@@ ":
                    for i in range(4):
                        self.forward()
                else:
                    self.skip_comment()
            elif c == "'":
                result.append(self.read_string())
            elif c.isdigit():
                result.append(self.read_number())
            elif c in DELIMITERS:
                self.forward()
                result.append(Delimiter(c, file=self.filename))
            elif c == "`":
                self.forward()
                result.append(self.expect_quasiquote())
            elif is_valid_name_char(c):
                result.append(self.read_identifier())
            else:
                self.abort(f"unexpected char: {c!r}")
