"""Check AND operator in query compilation."""

from . import compile_query, exceptions, raises, test


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


@test
def and_not():
	"""Check contradictory AND/OR with NOT."""

	query = compile_query('a and not b', 'tags')
	assert query == {'$and': [{'tags': 'a'}, {'tags': {'$ne': 'b'}}]}

	query = compile_query('a not b', 'tags')
	assert query == {'$and': [{'tags': 'a'}, {'tags': {'$ne': 'b'}}]}

	with raises(exceptions.Contradiction):
		compile_query('a and not a', 'tags')
		compile_query('not a and a', 'tags')

	query = compile_query('a or not a', 'tags')
	assert query == {}

	query = compile_query('not a or a', 'tags')
	assert query == {}
