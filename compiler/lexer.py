"""
This module parses a string expression into a list of tokens.
"""

__all__ = ['parse']

import re

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


def parse(expr: str) -> list:
	tok = []
	while len(expr):
		# ignore whitespace
		token, expr = consume(SPAC, expr)

		# glob operator
		if len(expr) and expr[0] == '*':
			expr = expr[1::]
			tok += [tokens.Glob('*')]
			continue

		# operators
		token, expr = consume(OPER, expr)
		if token is not None:
			if token == '/':
				token = 'or'
			if token == '+':
				token = 'and'
			if token == '-':
				token = 'not'
			tok += [tokens.Operator(token)]
			continue

		# functions
		token, expr = consume(FUNC, expr, group=1)
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

			tok += [tokens.Function(token)]
			continue

		# left paren
		token, expr = consume(LPAR, expr)
		if token is not None:
			tok += [tokens.LParen(token)]
			continue

		# right paren
		token, expr = consume(RPAR, expr)
		if token is not None:
			tok += [tokens.RParen(token)]
			continue

		# non-quoted words
		token, expr = consume(STR1, expr)
		if token is not None:
			tok += [tokens.String(token)]
			continue

		# quoted words
		token, expr = consume(STR2, expr)
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
			tok += [tokens.String(token[1:-1])]
			continue

		# regex
		token, expr = consume(REGX, expr)
		if token is not None:
			tok += [tokens.Regex(token[1:-1])]
			continue

		# if there's an unterminated string, that's an error
		token, expr = consume(UNTR, expr)
		if token is not None:
			raise exceptions.UnterminatedString

		# if there's an unterminated regex, that's an error
		token, expr = consume(UNRG, expr)
		if token is not None:
			raise exceptions.BadRegex(token, 'unterminated regex')

		# if anything else, there's an error in the pattern
		token, expr = consume(ANY, expr)
		if token is not None:
			raise exceptions.InvalidSymbol(token)

	return tok
