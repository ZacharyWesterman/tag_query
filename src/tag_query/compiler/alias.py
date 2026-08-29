"""Alias specs for field renaming."""

from typing import Any, Callable

from .array_field import ArrayField


class Alias:
	"""
	When enabling extra fields, this class specifies that the outputted MongoDB
	field name is different from the name used to query the field.
	"""

	def __init__(self, name: str, values: None | list[str] | Callable[[str, str], Any] | ArrayField):
		self.name = name
		self.values = values
