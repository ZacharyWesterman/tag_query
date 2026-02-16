"""
This module parses a string expression into a list of tokens.
"""

__all__ = ['tokenize']

import re
from typing import Generator

from . import exceptions, tokens

SPAC = re.compile(r'[ \t\n\r]*')
OPER = re.compile(r'\band\b|\bor\b|\bnot\b|\+|/|\-')
FUNC = re.compile(
	r'(>=|>|<=|<|=)|\b(eq|lt|gt|le|ge|equals?|exact(ly)?|min(imum)?|max(imum)?|fewer|greater|below|above)\b'
)
LPAR = re.compile(r'\(')
RPAR = re.compile(r'\)')
STR1 = re.compile(r'[a-zA-Z0-9_\.]+')
STR2 = re.compile(r'"(\\"|[^"])*"')
ANY = re.compile(r'[^\&\|\(\)\"a-zA-Z0-9_\-\.]+')
UNTR = re.compile(r'"[^"]*$')
REGX = re.compile(r'\{[^\}]*\}')
UNRG = re.compile(r'\{[^\}]*$')


def consume(pattern: re.Pattern, expr: str, group: int = 0) -> tuple[str | None, str]:
	match = pattern.match(expr)
	if match:
		grp = match.group(group)
		return grp, expr[len(match.group(0))::]
	else:
		return None, expr


def tokenize(expression: str) -> Generator[tokens.Token, None, None]:
	while len(expression):
		# ignore whitespace
		token, expression = consume(SPAC, expression)

		# glob operator
		if len(expression) and expression[0] == '*':
			expression = expression[1::]
			yield tokens.Glob('*')
			continue

		# operators
		token, expression = consume(OPER, expression)
		if token is not None:
			if token == '/':
				token = 'or'
			if token == '+':
				token = 'and'
			if token == '-':
				token = 'not'
			yield tokens.Operator(token)
			continue

		# functions
		token, expression = consume(FUNC, expression)
		if token is not None:
			if token in ['equals', 'exactly', 'exact', 'equal', '=']:
				token = 'eq'
			elif token in ['min', 'minimum', '>=']:
				token = 'ge'
			elif token in ['max', 'maximum', '<=']:
				token = 'le'
			elif token in ['fewer', 'below', '<']:
				token = 'lt'
			elif token in ['greater', 'above', '>']:
				token = 'gt'

			yield tokens.Function(token)
			continue

		# left paren
		token, expression = consume(LPAR, expression)
		if token is not None:
			yield tokens.LParen(token)
			continue

		# right paren
		token, expression = consume(RPAR, expression)
		if token is not None:
			yield tokens.RParen(token)
			continue

		# non-quoted words
		token, expression = consume(STR1, expression)
		if token is not None:
			yield tokens.String(token)
			continue

		# quoted words
		token, expression = consume(STR2, expression)
		if token is not None:
			escs = [
				('\\"', '"'),
				('\\\\', '\\'),
				('\\t', '\t'),
				('\\n', '\n'),
				('\\r', '\r'),
			]
			for esc in escs:
				token = token.replace(esc[0], esc[1])
			yield tokens.String(token[1:-1])
			continue

		# regex
		token, expression = consume(REGX, expression)
		if token is not None:
			yield tokens.Regex(token[1:-1])
			continue

		# if there's an unterminated string, that's an error
		token, expression = consume(UNTR, expression)
		if token is not None:
			raise exceptions.UnterminatedString

		# if there's an unterminated regex, that's an error
		token, expression = consume(UNRG, expression)
		if token is not None:
			raise exceptions.BadRegex(token, 'unterminated regex')

		# if anything else, there's an error in the pattern
		token, expression = consume(ANY, expression)
		if token is not None:
			raise exceptions.InvalidSymbol(token)
