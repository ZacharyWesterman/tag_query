"""Check for invalid syntax in query compilation."""

from . import compile_query, exceptions, raises, test


@test
def invalid_syntax():
	"""Confirm invalid syntax."""
	with raises(exceptions.ParseError):
		compile_query('a and b or', 'tags')

	with raises(exceptions.ParseError):
		compile_query('a and b or c and', 'tags')

	with raises(exceptions.ParseError):
		compile_query('a and b or c and d or', 'tags')

	with raises(exceptions.ParseError):
		compile_query('and and and', 'tags')
