"""Check AND operator in query compilation."""

from . import compile_query, test


@test
def simple_and():
	"""Check the AND operator."""

	query = compile_query('a and b', 'tags')
	assert query == {'$and': [{'tags': 'a'}, {'tags': 'b'}]}

	query = compile_query('a and b and c', 'tags')
	assert query == {'$and': [{'tags': 'a'}, {'tags': 'b'}, {'tags': 'c'}]}

	query = compile_query('a and (b and c)', 'tags')
	assert query == {'$and': [{'tags': 'a'}, {'tags': 'b'}, {'tags': 'c'}]}


@test
def duplicate_and():
	"""Remove duplicate AND conditions."""

	query = compile_query('a and a and b and a and b', 'tags')
	assert query == {'$and': [{'tags': 'a'}, {'tags': 'b'}]}
