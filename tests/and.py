"""Check AND operator in query compilation."""

from . import compile_query, test


@test
def simple_and():
	"""
	Check AND operator.
	"""
	query = compile_query('a and b', 'tags')

	assert query == {'$and': [{'tags': 'a'}, {'tags': 'b'}]}
