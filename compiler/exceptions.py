"""Exceptions for the query compiler."""


class InternalError(Exception):
	"""
	Indicates that there is an error with the compiler.
	This is not a user error, but rather an issue with the compiler itself.
	"""

	def __init__(self, message: str):
		super().__init__(f'COMPILER BUG: {message}')


class ParseError(Exception):
	"""Base class for all parse errors in the query compiler."""


class SyntaxError(ParseError):
	"""Raised when there is a syntax error in the query expression."""

	def __init__(self):
		super().__init__('Syntax error.')


class UnterminatedString(ParseError):
	"""Raised when a string in the query expression is not properly terminated."""

	def __init__(self):
		super().__init__('Unterminated string.')


class InvalidSymbol(ParseError):
	"""Raised when an invalid symbol is encountered in the query expression."""

	def __init__(self, char: str):
		super().__init__(f'Invalid symbol "{char}".')


class MissingOperand(ParseError):
	"""Raised when an operator is missing an operand in the query expression."""

	def __init__(self, oper: str):
		super().__init__(f'Missing operand for "{oper}" operator.')


class MissingParam(ParseError):
	"""Raised when a function is missing a required parameter in the query expression."""

	def __init__(self, func: str):
		super().__init__(f'Missing parameter for "{func}" function.')


class EmptyParens(ParseError):
	"""Raised when parentheses are empty in the query expression."""

	def __init__(self):
		super().__init__('Parentheses must contain an expression.')


class MissingLeftParen(ParseError):
	"""Raised when a left parenthesis is expected but not found in the query expression."""

	def __init__(self):
		super().__init__('Missing left parenthesis "("')


class MissingRightParen(ParseError):
	"""Raised when a right parenthesis is expected but not found in the query expression."""

	def __init__(self):
		super().__init__('Missing right parenthesis ")"')


class BadFuncParam(ParseError):
	"""Raised when a function parameter is invalid in the query expression."""


class BadGlob(ParseError):
	"""Raised when a glob operator is not immediately adjacent to a tag in the query expression."""

	def __init__(self):
		super().__init__('Glob "*" must be immediately adjacent to a tag.')


class BadRegex(ParseError):
	"""Raised when a regex is invalid in the query expression."""

	def __init__(self, text: str, message: str):
		super().__init__(f'Invalid regex "{text}": {message}.')
