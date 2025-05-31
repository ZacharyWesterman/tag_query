"""Validate that an empty query returns an empty result set."""

from . import compile_query, test


@test
def empty_query():
	"""Validate empty queries."""
	query = compile_query('', 'tags')
	assert query == {}

	query = compile_query(' ', 'tags')
	assert query == {}

	query = compile_query('   ', 'tags')
	assert query == {}
