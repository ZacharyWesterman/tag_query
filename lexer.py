__all__ = ['parse']

import re
from . import exceptions
from . import tokens

SPAC = re.compile(r'[ \t\n\r]*')
OPER = re.compile(r'\band\b|\bor\b|\bnot\b|\+|/|\-')
FUNC = re.compile(r'\b(eq|lt|gt|le|ge)\b')
LPAR = re.compile(r'\(')
RPAR = re.compile(r'\)')
STR1 = re.compile(r'[a-zA-Z0-9_\.]+')
STR2 = re.compile(r'"(\\"|[^"])*"')
ANY  = re.compile(r'[^\&\|\(\)\"a-zA-Z0-9_\-\.]+')
UNTR = re.compile(r'"[^"]*$')

def consume(pattern: re.Pattern, expr: str, group: int = 0) -> str:
	match = pattern.match(expr)
	if match:
		grp = match.group(group)
		return grp, expr[len(match.group(0))::]
	else:
		return None, expr

def parse(expr: str) -> list:
	tok = []
	while len(expr):
		#ignore whitespace
		token, expr = consume(SPAC, expr)

		#glob operator
		if expr[0] == '*':
			expr = expr[1::]
			tok += [ tokens.Glob('*') ]
			continue

		#operators
		token, expr = consume(OPER, expr)
		if token is not None:
			if token == '/': token = 'or'
			if token == '+': token = 'and'
			if token == '-': token = 'not'
			tok += [ tokens.Operator(token) ]
			continue

		#functions
		token, expr = consume(FUNC, expr, group=1)
		if token is not None:
			tok += [ tokens.Function(token) ]
			continue

		#left paren
		token, expr = consume(LPAR, expr)
		if token is not None:
			tok += [ tokens.LParen(token) ]
			continue

		#right paren
		token, expr = consume(RPAR, expr)
		if token is not None:
			tok += [ tokens.RParen(token) ]
			continue

		#non-quoted words
		token, expr = consume(STR1, expr)
		if token is not None:
			tok += [ tokens.String(token) ]
			continue

		#quoted words
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
			tok += [ tokens.String(token[1:-1]) ]
			continue

		#if there's an unterminated string, that's an error
		token, expr = consume(UNTR, expr)
		if token is not None:
			raise exceptions.UnterminatedString

		#if anything else, there's an error in the pattern
		token, expr = consume(ANY, expr)
		if token is not None:
			raise exceptions.InvalidSymbol(token)

	return tok
