"""Check overlapping ranges."""

from . import compile_query, exceptions, raises, test


@test
def range_overlap():
	"""Reduce overlapping ranges."""

	query = compile_query('> 3 or > 2 or > 1', 'tags')
	assert query == {'tags.1': {'$exists': True}}

	query = compile_query('> 3 and > 2 and > 1', 'tags')
	assert query == {'tags.3': {'$exists': True}}

	with raises(exceptions.ImpossibleRange):
		compile_query('> 3 and < 2', 'tags')

	query = compile_query('> 3 or < 2', 'tags')
	assert query == {'$or': [{'tags.3': {'$exists': True}}, {'tags.1': {'$exists': False}}]}

	# No actionable range
	query = compile_query('> 4 or < 5', 'tags')
	assert query == {}

	with raises(exceptions.ImpossibleRange):
		compile_query('> 4 and < 5', 'tags')
