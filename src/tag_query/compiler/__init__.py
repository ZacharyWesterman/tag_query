"""
This module compiles a string expression into a MongoDB query dictionary.
"""

__all__ = ['compile_query', 'exceptions']

from . import exceptions, parser, tokens


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

	ast = ast.reduce()
	if ast.delete_me:
		return tokens.NoneToken()

	return ast


def compile_query(expression: str, field: str) -> dict:
	"""
	Compile a string expression into a MongoDB query dictionary.

	Args:
		expression (str): The expression to compile.
		field (str): The field to apply the expression to.

	Returns:
		dict: A dictionary representing the MongoDB query.

	Raises:
		exceptions.ParseError: If the expression cannot be compiled.
			See exceptions.py for specific error types.
	"""
	return parse(expression).output(field)
