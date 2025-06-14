"""Check tag count functions."""

from . import compile_query, test


@test
def tag_count():
	"""Check tag count functions."""

	query = compile_query('> 3', 'tags')
	assert query == {'tags.3': {'$exists': True}}

	query = compile_query('< 2', 'tags')
	assert query == {'tags.1': {'$exists': False}}

	query = compile_query('>= 1', 'tags')
	assert query == {'tags.0': {'$exists': True}}

	query = compile_query('<= 5', 'tags')
	assert query == {'tags.5': {'$exists': False}}

	query = compile_query('= 3', 'tags')
	assert query == {'tags': {'$size': 3}}
