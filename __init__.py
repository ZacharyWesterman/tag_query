from . import lexer
from . import exceptions
from . import tokens

def parse(expression: str) -> tokens.Token:
	prev_len = -1
	tok = lexer.parse(expression.lower())

	#first pass to condense any globs and strings
	pos = 0
	while pos < len(tok):
		prev_len = len(tok)

		if tok[pos].type() in ['Glob', 'String']:
			tok = tok[pos].operate(tok, pos)
		
		if len(tok) == prev_len:
			pos += 1

	#then operate on all other tokens
	while len(tok) > 1:
		pos = 0
		while pos < len(tok):
			#only operate on tokens that haven't already been operated on
			if len(tok[pos].children) == 0:
				tok = tok[pos].operate(tok, pos)
			if len(tok) != prev_len:
				break
			pos += 1

		#if this round of parsing did not condense the expression,
		#then some other syntax error happened.
		if prev_len == len(tok):
			raise exceptions.SyntaxError

		prev_len = len(tok)

	return tok[0] if len(tok) else tokens.NoneToken()
