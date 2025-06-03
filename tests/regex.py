"""Check regex patterns."""

import re

from . import compile_query, test


@test
def simple_not():
	"""Check regex matching."""

	# Regex that coerces to a plain string
	query = compile_query(r'{^text$}', 'tags')
	assert query == {'tags': 'text'}

	query = compile_query(r'{[a-z]+}', 'tags')
	assert query == {'tags': re.compile('[a-z]+')}
