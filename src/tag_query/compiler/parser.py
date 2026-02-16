import re
from typing import Callable

from . import exceptions, lexer, tokens


def plaintext(peek: Callable[[], tokens.Token], get: Callable[[], tokens.Token]) -> tokens.Token:
	items: list[tokens.Token] = []

	while peek().type == 'String':
		items += [get()]

	if len(items) == 0:
		return tokens.NoneToken()

	return tokens.String(' '.join([i.text for i in items]))


def func(peek: Callable[[], tokens.Token], get: Callable[[], tokens.Token]) -> tokens.Token:
	fn = get()  # Can assume this is a function

	# Require an integer tag count
	if peek().type != 'String' or not re.match(r'^[0-9]+$', peek().text):
		raise exceptions.MissingParam(fn.text)

	fn.children = [get()]
	return fn


def value(peek: Callable[[], tokens.Token], get: Callable[[], tokens.Token]) -> tokens.Token:
	if peek().type == 'Glob':
		get()
		middle = plaintext(peek, get)
		if middle.type != 'String':
			raise exceptions.BadGlob()

		middle.glob['left'] = True
		if peek().type == 'Glob':
			get()
			middle.glob['right'] = True

		return middle

	if peek().type == 'String':
		middle = plaintext(peek, get)
		if peek().type == 'Glob':
			get()
			middle.glob['right'] = True
		return middle

	if peek().type == 'LParen':
		get()
		middle = expr(peek, get)
		if peek().type != 'RParen':
			raise exceptions.MissingRightParen()
		get()
		return middle

	if peek().type == 'Regex':
		return get()

	if peek().type == 'Function':
		return func(peek, get)

	if peek().type == 'Operator' and peek().text == 'not':
		get()
		val = value(peek, get)
		val.negate = not val.negate
		return val

	return tokens.NoneToken()


def binary(peek: Callable[[], tokens.Token], get: Callable[[], tokens.Token]) -> tokens.Token:
	lhs = value(peek, get)

	if peek().type != 'Operator':
		return lhs

	if peek().text == 'not':
		op = tokens.Operator('and')
	else:
		op = get()

	rhs = binary(peek, get)

	if rhs.type == 'NoneToken':
		raise exceptions.MissingOperand(op.text)

	op.children = [lhs]

	same_op = rhs.type == 'Operator' and rhs.text == op.text
	op.children += rhs.children if same_op else [rhs]

	op.coalesce()
	return op


def expr(peek: Callable[[], tokens.Token], get: Callable[[], tokens.Token]) -> tokens.Token:
	return binary(peek, get)


def parse(expression: str) -> tokens.Token:
	gen = lexer.tokenize(expression)
	current_token = None

	def peek() -> tokens.Token:
		nonlocal current_token
		if current_token is None:
			try:
				current_token = next(gen)
			except StopIteration:
				current_token = tokens.NoneToken()
		return current_token

	def get() -> tokens.Token:
		nonlocal current_token
		this_token = peek()
		current_token = None
		return this_token

	tok = expr(peek, get)
	if peek().type != 'NoneToken':
		raise exceptions.SyntaxError()

	return tok
