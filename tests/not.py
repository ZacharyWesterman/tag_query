"""Check NOT operator in query compilation."""

from . import compile_query, test


@test
def simple_not():
	"""Check the NOT operator."""

	query = compile_query('not a', 'tags')
	assert query == {'tags': {'$ne': 'a'}}

	query = compile_query('a not b not c', 'tags')
	assert query == {'$and': [{'tags': 'a'}, {'tags': {'$ne': 'b'}}, {'tags': {'$ne': 'c'}}]}


@test
def duplicate_not():
	"""Remove duplicate not conditions."""

	query = compile_query('not not a', 'tags')
	assert query == {'tags': 'a'}

	query = compile_query('not not not a', 'tags')
	assert query == {'tags': {'$ne': 'a'}}

	query = compile_query('not not not not a', 'tags')
	assert query == {'tags': 'a'}
