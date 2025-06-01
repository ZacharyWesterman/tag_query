"""
This module defines the token classes used in the query compiler.
"""

import re

from . import exceptions

INT = re.compile(r'^[0-9]+$')


class Token:
	"""
	Base class for all tokens in the query compiler.
	Each token represents a part of the query expression and can have children tokens.
	"""

	def __init__(self, text: str):
		self.text = text
		self.children = []
		self.negate = False
		self.glob = {
			'left': False,
			'right': False,
		}

	def __str__(self) -> str:
		return debug_print(self)

	# pylint: disable=unused-argument
	def operate(self, tokens: list, pos: int) -> list:
		"""
		Operate on the token and return the modified list of tokens.

		Args:
			tokens (list): The list of tokens to operate on.
			pos (int): The position of this token in the list.

		Returns:
			list: The modified list of tokens.
		"""
		return tokens
	# pylint: enable=unused-argument

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
			if child.type == 'Operator' and self.text == child.text and not child.negate:
				kids += child.children
			else:
				kids += [child]
		self.children = kids


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
		output = '  ' * indent + f'{tok.__class__.__name__} ({tok.text})'
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

	def operate(self, tokens: list, pos: int) -> list:
		# remove redundant globs
		if pos < (len(tokens) - 1) and tokens[pos + 1].type == 'Glob':
			return tokens[0:pos - 1] + tokens[pos + 1::]

		# if next token is a string, glob on the left (*X)
		if pos < (len(tokens) - 1) and tokens[pos + 1].type == 'String':
			tokens[pos + 1].glob['left'] = True
			return tokens[0:pos] + tokens[pos + 1::]

		# if prev token is a string, glob on the right (X*)
		elif pos > 0 and tokens[pos - 1].type == 'String':
			tokens[pos - 1].glob['right'] = True
			return tokens[0:pos] + tokens[pos + 1::]

		raise exceptions.BadGlob


class Operator(Token):
	"""
	Operators are used to combine expressions in the query.
	They can be binary (AND/OR) or unary (NOT).
	"""

	def operate(self, tokens: list, pos: int) -> list:
		# NOT operator is unary, unless by itself, then it's actually "and not".
		if self.text == 'not' and (pos <= 0 or (
			tokens[pos - 1].type == 'Operator' and
			len(tokens[pos - 1].children) == 0
		)):
			if pos >= (len(tokens) - 1):
				raise exceptions.MissingOperand(self.text)

			rtype = tokens[pos + 1].type
			rkids = len(tokens[pos + 1].children)

			# don't be greedy; let functions or other NOT opers try to get their param if they can.
			if (rtype in ['Function', 'Operator'] and rkids == 0) or rtype == 'LParen':
				return tokens

			if rtype not in ['String', 'Regex'] and rkids == 0:
				raise exceptions.MissingOperand(self.text)

			tokens[pos + 1].negate = not tokens[pos + 1].negate

			return tokens[0:pos] + tokens[pos + 1::]

		# AND/OR operators start here

		if pos == 0 or pos >= (len(tokens) - 1):
			raise exceptions.MissingOperand(self.text)

		ltype = tokens[pos - 1].type
		lkids = len(tokens[pos - 1].children)

		rtype = tokens[pos + 1].type
		rkids = len(tokens[pos + 1].children)

		# don't be greedy; let functions try to get their param if they can.
		if (rtype == 'Function' and rkids == 0) or ltype == 'RParen' or rtype == 'LParen':
			return tokens

		if rtype == 'Operator' and tokens[pos + 1].text == 'not' and rkids == 0:
			return tokens

		if (
			(ltype not in ['String', 'Regex'] and lkids == 0) or
			(rtype not in ['String', 'Regex'] and rkids == 0)
		):
			raise exceptions.MissingOperand(self.text)

		self.children = [tokens[pos - 1], tokens[pos + 1]]

		# A not B -> A and not B
		if self.text == 'not':
			self.text = 'and'
			self.children[1].negate = not self.children[1].negate

		# fold together children for operators of the same type.
		self.coalesce()

		return tokens[0:pos - 1] + [self] + tokens[pos + 2::]

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


class String(Token):
	"""
	String tokens represent a single tag or a string literal in the query.
	They can be concatenated with adjacent strings or globs to form a single tag.
	"""

	def operate(self, tokens: list, pos: int) -> list:
		# Concatenate adjacent strings into a single string separated by spaces
		if pos + 1 < len(tokens) and tokens[pos + 1].type == 'String':
			self.text += f' {tokens[pos + 1].text}'
			return tokens[0:pos + 1] + tokens[pos + 2::]

		return tokens

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


class LParen(Token):
	"""
	Left parenthesis tokens are used to group expressions in the query.
	They indicate the start of a sub-expression that should be evaluated together.
	"""

	def operate(self, tokens: list, pos: int) -> list:
		if pos >= (len(tokens) - 2):
			raise exceptions.MissingRightParen

		ptype = tokens[pos + 1].type
		pkids = len(tokens[pos + 1].children)

		rtype = tokens[pos + 2].type

		# inner expression hasn't been parsed yet, so exit early
		if rtype != 'RParen':
			return tokens

		if ptype != 'String' and pkids == 0:
			raise exceptions.EmptyParens

		# fold together children for operators of the same type.
		if ptype == 'Operator':
			tokens[pos + 1].coalesce()

		return tokens[0:pos] + [tokens[pos + 1]] + tokens[pos + 3::]


class RParen(Token):
	"""
	Right parenthesis tokens are used to close a group of expressions in the query.
	They indicate the end of a sub-expression that should be evaluated together.
	"""


class Function(Token):
	"""
	Function tokens represent functions that operate on a single parameter.
	They are used to filter results based on the number of tags or other criteria.
	"""

	def operate(self, tokens: list, pos: int) -> list:
		if pos >= (len(tokens) - 1):
			raise exceptions.MissingRightParen

		ptype = tokens[pos + 1].type
		pkids = len(tokens[pos + 1].children)

		# inner expression hasn't been parsed yet, so exit early
		if ptype == 'LParen':
			return tokens

		if ptype != 'String' and pkids == 0:
			raise exceptions.MissingParam(self.text)

		# Currently, all functions require a precisely numeric param.
		if ptype != 'String' or not INT.match(tokens[pos + 1].text):
			raise exceptions.BadFuncParam(f'Parameter for "{self.text}" must be an integer.')

		self.children = [tokens[pos + 1]]

		return tokens[0:pos] + [self] + tokens[pos + 2::]

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
