"""Check OR operator in query compilation."""

from . import compile_query, test


@test
def simple_or():
	"""Check the OR operator."""

	query = compile_query('a or b', 'tags')
	assert query == {'$or': [{'tags': 'a'}, {'tags': 'b'}]}

	query = compile_query('a or b or c', 'tags')
	assert query == {'$or': [{'tags': 'a'}, {'tags': 'b'}, {'tags': 'c'}]}

	query = compile_query('a or (b or c)', 'tags')
	assert query == {'$or': [{'tags': 'a'}, {'tags': 'b'}, {'tags': 'c'}]}


@test
def duplicate_or():
	"""Remove duplicate OR conditions."""

	query = compile_query('a or a or b or a or b', 'tags')
	assert query == {'$or': [{'tags': 'a'}, {'tags': 'b'}]}
