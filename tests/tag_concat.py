"""Check that tag concatenation works correctly."""

from . import compile_query, test


@test
def tag_concat():
	"""Check tag concatenation."""

	query = compile_query('a b c', 'tags')
	assert query == {'tags': 'a b c'}

	query = compile_query('a b c and d', 'tags')
	assert query == {'$and': [{'tags': 'a b c'}, {'tags': 'd'}]}

	query = compile_query('a    "b  c"', 'tags')
	assert query == {'tags': 'a b  c'}
