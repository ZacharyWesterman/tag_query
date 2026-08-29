"""Check extra field validation and output."""

import re

from . import Alias, ArrayField, compile_query, exceptions, raises, test


def integer(field: str, val: str) -> int:
	if not re.match(r'^\d+$', val):
		raise exceptions.InvalidFieldValue(field)

	return int(val)


@test
def extra_fields():
	"""Make sure extra fields validate correctly."""

	compile_query('tags:(gt 1)', 'tags')

	with raises(exceptions.InvalidFieldValue):
		compile_query('title:(gt 1)', 'tags', title=None)

	compile_query('title:(gt 1)', 'tags', title=ArrayField(['a', 'b', 'c']))

	with raises(exceptions.InvalidFieldValue):
		compile_query('title:(gt 1 or test)', 'tags', title=ArrayField(['a', 'b', 'c']))

	with raises(exceptions.FieldDoesNotExist):
		compile_query('title:test', 'tags')

	with raises(exceptions.InvalidFieldValue):
		compile_query('title:test', 'tags', title=['a', 'b', 'c'])

	query = compile_query('title:a', 'tags', title=['a', 'b', 'c'])
	assert query == {'title': 'a'}

	query = compile_query('title:(a or b)', 'tags', title=['a', 'b', 'c'])
	assert query == {'$or': [{'title': 'a'}, {'title': 'b'}]}

	query = compile_query('title:a or title:b', 'tags', title=['a', 'b', 'c'])
	assert query == {'$or': [{'title': 'a'}, {'title': 'b'}]}

	with raises(exceptions.InvalidFieldValue):
		compile_query('total:test', 'tags', total=integer)

	query = compile_query('total:123', 'tags', total=integer)
	assert query == {'total': 123}

	query = compile_query('alias:value', 'tags', alias=None)
	assert query == {'alias': 'value'}

	with raises(exceptions.FieldDoesNotExist):
		compile_query('alias:value', 'tags', fieldname=Alias('alias', None))

	query = compile_query('alias:value', 'tags', alias=Alias('fieldname', None))
	assert query == {'fieldname': 'value'}
