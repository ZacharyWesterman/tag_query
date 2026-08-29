"""
This module compiles a string expression into a MongoDB query dictionary.
"""

__all__ = ['compile_query', 'exceptions']

from typing import Any, Callable

from . import exceptions, parser, tokens
from .array_field import ArrayField


def parse(expression: str) -> tokens.Token:
	"""
	Parse a string expression into a token tree.

	Args:
		expression (str): The expression to parse.

	Returns:
		tokens.Token: The root token of the parsed expression.

	Raises:
		exceptions.SyntaxError: If the expression cannot be parsed.
			See exceptions.py for specific error types.
	"""

	ast = parser.parse(expression.lower())
	if ast.type == 'NoneToken':
		return tokens.NoneToken()

	if ast.delete_me:
		return tokens.NoneToken()

	return ast.reduce()


def compile_query(expression: str, field: str, **kwargs: None | list[str] | Callable[[str, str], Any] | ArrayField) -> dict:
	"""
	Compile a string expression into a MongoDB query dictionary.

	Args:
		expression (str): The expression to compile.
		field (str): The field to apply the expression to.
		kwargs (dict[str, None | list[str] | Callable[[str], bool])]): A dictionary whose keys are
			extra field names, and values are either None (all values are valid); a list of acceptable
			values; or a function that parses the string into a valid value, raising
			exceptions.InvalidFieldValue (ParseError) if invalid.

	Returns:
		dict: A dictionary representing the MongoDB query.

	Raises:
		exceptions.ParseError: If there is any error in the expression.
			See exceptions.py for specific error types.
	"""
	return parse(expression).output(field, **kwargs)
