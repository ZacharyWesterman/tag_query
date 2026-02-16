"""
This module defines the token classes used in the query compiler.
"""

import re
from typing import Self

from . import exceptions

INT = re.compile(r'^[0-9]+$')


class Token:
	"""
	Base class for all tokens in the query compiler.
	Each token represents a part of the query expression and can have children tokens.
	"""

	def __init__(self, text: str):
		self.text: str = text
		self.children: list[Token] = []
		self.negate: bool = False
		self.glob: dict[str, bool] = {
			'left': False,
			'right': False,
		}
		self.delete_me: bool = False
		self.replace_parent: bool = False

	def __str__(self) -> str:
		return debug_print(self)

	def __eq__(self, other) -> bool:
		return (
			isinstance(other, Token) and
			self.type == other.type and
			self.text == other.text and
			self.negate == other.negate
		)

	def __lt__(self, other) -> bool:
		return self.text < other.text

	def __hash__(self) -> int:
		return f'{self.type}:{self.text}:{int(self.negate)}'.__hash__()

	def __repr__(self) -> str:
		return (
			f'{self.__class__.__name__}({self.text}' +
			(f' <{self.children}>' if len(self.children) > 0 else '') +
			')'
		)

	def output(self, field: str = 'tags') -> dict:
		"""
		Output the token as a dictionary representation for MongoDB queries.

		Args:
			field (str): The field to output the token for, default is 'tags'.

		Returns:
			dict: The dictionary representation of the token.

		Raises:
			exceptions.InternalError: If the output method is not implemented for this token type.
		"""
		raise exceptions.InternalError(f'output() method is not implemented for {self.type}.')

	@property
	def type(self) -> str:
		"""
		Get the type of the token.

		Returns:
			str: The type of the token.
		"""
		return self.__class__.__name__

	def coalesce(self) -> None:
		"""
		Coalesce the children of this token.
		This method is used to combine adjacent operator tokens of the same type
		into a single token with multiple children.
		"""

		kids = []
		for child in self.children:
			child.coalesce()

			if child.delete_me:
				continue

			if child.type == 'Operator' and self.text == child.text and not child.negate:
				kids += child.children
			else:
				kids += [child]
		self.children = kids

	def reduce(self) -> Self:
		"""
		Reduce the token and its children to a single token if possible.
		This method is used to simplify the token tree by removing unnecessary tokens.

		Returns:
			Token: The reduced token.
		"""

		return self


def debug_print(tok: Token | list[Token], indent: int = 0) -> str:
	"""
	Recursively prints the token tree for debugging purposes.
	Args:
		tok (Token or list): The token or list of tokens to print.
	"""

	output = ''
	if isinstance(tok, list):
		for i in tok:
			output += '\n' + debug_print(i, indent)
	else:
		output = (
			'  ' * indent +
			f'{tok.__class__.__name__} (' +
			("!" if tok.negate else '') +
			("*" if tok.glob["left"] else '') +
			tok.text +
			("*" if tok.glob["right"] else '') +
			')'
		)
		output += debug_print(tok.children, indent + 1)

	return output


class NoneToken(Token):
	"""A placeholder token used when no expression is found."""

	def __init__(self):
		super().__init__('')

	def output(self, field: str = 'tags') -> dict:
		return {}


class Glob(Token):
	"""
	Glob tokens are used for simple pattern matching in the query.
	They are used to match tags that start or end with a certain string.

	Glob tokens are guaranteed to either reduce or raise an exception.
	They don't have to wait for other exprs to reduce since globs must be adjacent to strings.
	"""


class Operator(Token):
	"""
	Operators are used to combine expressions in the query.
	They can be binary (AND/OR) or unary (NOT).
	"""

	def output(self, field: str = 'tags') -> dict:
		if len(self.children) == 0:
			raise exceptions.MissingOperand(self.text)

		neg = {
			'or': 'and',
			'and': 'or',
		}
		text = neg[self.text] if self.negate else self.text
		if self.negate:
			for child in self.children:
				child.negate = not child.negate

		return {
			f'${text}': [i.output(field) for i in self.children]
		}

	def coalesce(self) -> None:
		"""
		If AND or OR operators have redundant children, they are coalesced into a single operator.
		"""

		super().coalesce()

		if self.text == 'not':
			return

		# Collect all text operands and remove duplicates, sorting them for consistency.
		text_tokens = sorted(set(i for i in self.children if i.type in ['String', 'Regex']))

		# Remove redundant text tokens.
		for i in range(len(text_tokens) - 1):
			if text_tokens[i].text == text_tokens[i + 1].text:
				msg = ('not ' if text_tokens[i].negate else '') + f'"{text_tokens[i].text}" and '
				msg += ('not ' if text_tokens[i + 1].negate else '') + f'"{text_tokens[i + 1].text}"'
				if self.text == 'and':
					raise exceptions.Contradiction(msg)
				else:
					self.delete_me = True

		# Collect all function tokens, remove ones whose ranges overlap.
		function_tokens: list[Function] = [i for i in self.children if isinstance(i, Function)]

		# Reduce Ranges
		if len(function_tokens) > 0:
			func_range = None
			for i in function_tokens:
				if func_range is None:
					func_range = Range.from_text(i.text, i.children[0].text)
				else:
					other = Range.from_text(i.text, i.children[0].text)
					if self.text == 'or' and not func_range.overlaps(other):
						# If the ranges do not overlap... too complicated!!!
						func_range = None
						break
					func_range = Range.merge(func_range, other, self.text)

			if func_range is not None:
				if func_range.size() < 0 and self.text == 'or':
					# If "or" operator and the range is negative, invert the range.
					func_range = Range(
						min_tags=0 if func_range.max_tags == float('inf') else int(func_range.max_tags),
						max_tags=func_range.min_tags
					)

				if func_range.size() <= 0 and self.text == 'and':
					# If "and" operator and no valid range, this operator is impossible.
					raise exceptions.ImpossibleRange(func_range.min_tags, func_range.max_tags)

				if func_range.size() == 0:
					# If the range is empty, we have a "eq" function.
					# If start is less than 1, no need to keep the function.
					if func_range.min_tags >= 0:
						func = Function('eq')
						func.children = [Token(str(func_range.min_tags))]
						function_tokens = [func]

				elif func_range.max_tags == float('inf'):
					# If the range is infinite, we have a "ge" function.
					if func_range.min_tags > 0:
						# If start is greater than 0, we can use "ge" function.
						func = Function('ge')
						func.children = [Token(str(func_range.min_tags))]
						function_tokens = [func]
					else:
						self.delete_me = True
				else:
					# If the range is not infinite and not a single value, we have two functions.
					f1 = Function('ge')
					f1.children = [Token(str(func_range.min_tags))]
					f2 = Function('le')
					f2.children = [Token(str(func_range.max_tags))]
					function_tokens = [f1, f2]

		self.children = text_tokens + function_tokens

	def reduce(self) -> Token:
		if self.text == 'not':
			if self.children[0].text == 'not':
				# If this operator is "not" and the first child is also "not", remove both operators.
				return self.children[0].children[0]
			return self

		if len(self.children) == 1:
			# If there's only one child, replace this operator with the child.
			child = self.children[0]
			child.negate = self.negate
			child.glob = self.glob

			return child

		if len(self.children) == 0:
			self.delete_me = True

		return self


class String(Token):
	"""
	String tokens represent a single tag or a string literal in the query.
	They can be concatenated with adjacent strings or globs to form a single tag.
	"""

	def output(self, field: str = 'tags') -> dict:
		globbing = self.glob['left'] or self.glob['right']

		text = re.escape(self.text) if globbing else self.text
		oper = '$not' if globbing else '$ne'

		if globbing:
			if not self.glob['left']:
				text = '^' + text
			elif not self.glob['right']:
				text = text + '$'
			text = re.compile(text)

		return {field: {oper: text}} if self.negate else {field: text}


class Regex(Token):
	"""
	Regex tokens represent a regular expression in the query.
	They are used to match tags that conform to a specific pattern.
	"""

	def output(self, field: str = 'tags') -> dict:
		try:
			return {field: re.compile(self.text)}
		except re.error as e:
			raise exceptions.BadRegex(self.text, str(e))

	def reduce(self):
		"""
		Reduce the regex token to a string token if it matches a simple pattern.
		This is useful for optimizing queries by converting regexes to strings when possible.
		"""

		# If the regex is a simple string, convert it to a String token.
		if self.text.startswith('^') and self.text.endswith('$'):
			text = self.text[1:-1]
			if re.escape(text) == text:
				return String(text)

		return self


class LParen(Token):
	"""
	Left parenthesis tokens are used to group expressions in the query.
	They indicate the start of a sub-expression that should be evaluated together.
	"""


class RParen(Token):
	"""
	Right parenthesis tokens are used to close a group of expressions in the query.
	They indicate the end of a sub-expression that should be evaluated together.
	"""


class Range:
	"""
	Represents the range of how many tags a blob can have.
	"""

	@staticmethod
	def from_text(operator: str, value: str):
		"""
		Initializes a Range object from a text representation.

		Args:
			operator (str): The operator indicating the type of range (eq, lt, le, gt, ge).
			value (str): The value associated with the operator, expected to be a numeric string.

		Raises:
			exceptions.BadFuncParam: If the operator is invalid or the value is not a valid integer.
		"""

		if operator == 'eq':
			min_tags = int(value)
			max_tags = min_tags
		elif operator == 'lt':
			min_tags = 0
			max_tags = int(value) - 1
		elif operator == 'le':
			min_tags = 0
			max_tags = int(value)
		elif operator == 'gt':
			min_tags = int(value) + 1
			max_tags = float('inf')
		elif operator == 'ge':
			min_tags = int(value)
			max_tags = float('inf')
		else:
			raise exceptions.BadFuncParam(f'Invalid operator "{operator}" for Range.')

		return Range(min_tags, max_tags)

	def __init__(self, min_tags: int, max_tags: int | float):
		"""
		Initializes a Range object from a minimum and maximum tag count.

		Args:
			min_tags (int): The minimum number of tags.
			max_tags (int | float): The maximum number of tags, can be infinite (float('inf')).
		"""

		self.min_tags = min_tags
		self.max_tags = max_tags

	def __str__(self) -> str:
		return f'[{self.min_tags}, {self.max_tags}]'

	def __repr__(self) -> str:
		return f'Range({self.min_tags}, {self.max_tags})'

	def size(self) -> int:
		"""
		Returns the size of the range.
		If the range is infinite, returns a very large number.
		"""

		if self.max_tags == float('inf'):
			return 1_000_000
		return int(self.max_tags) - self.min_tags + 1

	def overlaps(self, other) -> bool:
		"""
		Checks if this range overlaps with another range.

		Args:
			other (Range): The other Range to check for overlap.

		Returns:
			bool: True if the ranges overlap, False otherwise.
		"""
		lhs = Range.norm(self)
		rhs = Range.norm(other)

		if lhs.min_tags - 1 > rhs.max_tags or rhs.min_tags - 1 > lhs.max_tags:
			return False

		return True

	@staticmethod
	def norm(obj):
		"""
		Normalizes the range to ensure min_tags is less than or equal to max_tags.
		If the range is invalid (min_tags > max_tags), it raises an exception.

		Returns:
			Range: The normalized Range object.
		"""
		if obj.min_tags > obj.max_tags:
			return Range(int(obj.max_tags), obj.min_tags)

		return Range(obj.min_tags, obj.max_tags)

	@staticmethod
	def merge(this, other, operator: str):
		"""
		Merges another Range into this one, expanding the range if necessary.

		Args:
			other (Range): The other Range to merge into this one.
			operator (str): The operator that defines how to merge the ranges.
			Valid operators are 'and' or 'or'.

		Raises:
			TypeError: If the other object is not a Range.
			ValueError: If the operator is not 'and' or 'or'.
		"""
		if not isinstance(other, Range):
			raise TypeError(f'Cannot merge {type(other)} into Range.')

		if operator not in ['and', 'or']:
			raise ValueError(f'Invalid operator "{operator}" for merging ranges.')

		if operator == 'and':
			return Range(
				max(this.min_tags, other.min_tags),
				min(this.max_tags, other.max_tags)
			)

		return Range(
			min(this.min_tags, other.min_tags),
			float('inf') if (
				this.max_tags == float('inf') or
				other.max_tags == float('inf')
			) else max(this.max_tags, other.max_tags)
		)


class Function(Token):
	"""
	Function tokens represent functions that operate on a single parameter.
	They are used to filter results based on the number of tags or other criteria.
	"""

	def output(self, field: str = 'tags') -> dict:
		if len(self.children) == 0:
			raise exceptions.MissingParam(self.text)

		# we know that the param will always be numeric, not an expression
		count = int(self.children[0].text)

		if self.text == 'eq':
			if self.negate:
				return {'$or': [
					{f'{field}.{count - 1}': {'$exists': False}},
					{f'{field}.{count}': {'$exists': True}},
				]}
			return {field: {'$size': count}}
		if self.text == 'lt':
			# don't allow filtering for blobs with fewer than 0 tags, that doesn't make sense.
			if count < 1:
				raise exceptions.BadFuncParam(f'Parameter for "{self.text}" must be a positive integer.')
			return {f'{field}.{count - 1}': {'$exists': self.negate}}
		if self.text == 'le':
			return {f'{field}.{count}': {'$exists': self.negate}}
		if self.text == 'gt':
			return {f'{field}.{count}': {'$exists': not self.negate}}
		if self.text == 'ge':
			# don't allow filtering for blobs with at least 0 tags, that's always true.
			if count < 1:
				raise exceptions.BadFuncParam(f'Parameter for "{self.text}" must be a positive integer.')
			return {f'{field}.{count - 1}': {'$exists': not self.negate}}

		raise NotImplementedError(f'Output for function of type "{self.text}" is not implemented.')
