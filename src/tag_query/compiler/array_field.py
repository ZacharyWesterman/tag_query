"""Array specs for extra fields."""

from typing import Any, Callable


class ArrayField:
	"""
	When enabling extra fields, this class specifies that this field may be an array.
	"""

	def __init__(self, values: None | list[str] | Callable[[str, str], Any]):
		self.values = values
