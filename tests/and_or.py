"""Check AND and OR operator precedence."""

from . import compile_query, test


@test
def left_to_right():
	"""Make sure expressions parse from left to right."""

	query = compile_query('a and b or c', 'tags')
	# Note that simple operands always come BEFORE complex operands!
	assert query == {'$or': [{'tags': 'c'}, {'$and': [{'tags': 'a'}, {'tags': 'b'}]}]}
