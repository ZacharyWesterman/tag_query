from . import exceptions
import re

INT = re.compile(r'^[0-9]+$')

class Token:
	def __init__(self, text: str):
		self.text = text
		self.children = []
		self.negate = False
		self.glob = {
			'left': False,
			'right': False,
		}

	def operate(self, tokens: list, pos: int) -> list:
		return tokens

	def output(self):
		raise NotImplementedError(f'output() method is not implemented for {self.type()}.')

	def type(self):
		return self.__class__.__name__

	def coalesce(self) -> list:
		#fold together children for operators of the same type.
		kids = []
		for child in self.children:
			child.coalesce()
			if child.type() == 'Operator' and self.text == child.text and not child.negate:
				kids += child.children
			else:
				kids += [child]
		self.children = kids

class NoneToken(Token):
	def output(self) -> dict:
		return {}

#Glob tokens are guaranteed to either reduce or raise an exception.
#They don't have to wait for other exprs to reduce since globs must be adjacent to strings.
class Glob(Token):
	def operate(self, tokens: list, pos: int) -> list:
		#remove redundant globs
		if pos < (len(tokens) - 1) and tokens[pos+1].type() == 'Glob':
			return tokens[0:pos-1] + tokens[pos+1::]

		#if next token is a string, glob on the left (*X)
		if pos < (len(tokens) - 1) and tokens[pos+1].type() == 'String':
			tokens[pos+1].glob['left'] = True
			return tokens[0:pos] + tokens[pos+1::]

		#if prev token is a string, glob on the right (X*)
		elif pos > 0 and tokens[pos-1].type() == 'String':
			tokens[pos-1].glob['right'] = True
			return tokens[0:pos] + tokens[pos+1::]

		raise exceptions.BadGlob

class Operator(Token):
	def operate(self, tokens: list, pos: int) -> list:
		#NOT operator is unary, unless by itself, then it's actually "and not".
		if self.text == 'not' and (pos <= 0 or (tokens[pos-1].type() == 'Operator' and len(tokens[pos-1].children) == 0)):
			if pos >= (len(tokens) - 1):
				raise exceptions.MissingOperand(self.text)

			rtype = tokens[pos+1].type()
			rkids = len(tokens[pos+1].children)

			#don't be greedy; let functions or other NOT opers try to get their param if they can.
			if ((rtype == 'Function' or rtype == 'Operator') and rkids == 0) or rtype == 'LParen':
				return tokens

			if rtype != 'String' and rkids == 0:
				raise exceptions.MissingOperand(self.text)

			tokens[pos+1].negate = not tokens[pos+1].negate

			return tokens[0:pos] + tokens[pos+1::]

		#AND/OR operators start here

		if pos == 0 or pos >= (len(tokens) - 1):
			raise exceptions.MissingOperand(self.text)

		ltype = tokens[pos-1].type()
		lkids = len(tokens[pos-1].children)

		rtype = tokens[pos+1].type()
		rkids = len(tokens[pos+1].children)

		#don't be greedy; let functions try to get their param if they can.
		if (rtype == 'Function' and rkids == 0) or ltype == 'RParen' or rtype == 'LParen':
			return tokens

		if rtype == 'Operator' and tokens[pos+1].text == 'not' and rkids == 0:
			return tokens

		if (ltype != 'String' and lkids == 0) or (rtype != 'String' and rkids == 0):
			raise exceptions.MissingOperand(self.text)

		self.children = [ tokens[pos-1], tokens[pos+1] ]

		# A not B -> A and not B
		if self.text == 'not':
			self.text = 'and'
			self.children[1].negate = not self.children[1].negate

		#fold together children for operators of the same type.
		self.coalesce()

		return tokens[0:pos-1] + [self] + tokens[pos+2::]

	def output(self) -> dict:
		neg = {
			'or': 'and',
			'and': 'or',
		}
		text = neg[self.text] if self.negate else self.text
		if self.negate:
			for child in self.children:
				child.negate = not child.negate

		return {
			f'${text}': [ i.output() for i in self.children ]
		}

class String(Token):
	def output(self) -> str:
		text = self.text
		if self.glob['left'] and self.glob['right']:
			text = re.compile(text)
		elif self.glob['left']:
			text = re.compile(text + '$')
		elif self.glob['right']:
			text = re.compile('^' + text)

		return {'tags': {'$ne': text }} if self.negate else { 'tags': text }

class LParen(Token):
	def operate(self, tokens: list, pos: int) -> list:
		if pos >= (len(tokens) - 2):
			raise exceptions.MissingRightParen

		ptype = tokens[pos+1].type()
		pkids = len(tokens[pos+1].children)

		rtype = tokens[pos+2].type()

		# inner expression hasn't been parsed yet, so exit early
		if rtype != 'RParen':
			return tokens

		if ptype != 'String' and pkids == 0:
			raise exceptions.EmptyParens

		#fold together children for operators of the same type.
		if ptype == 'Operator':
			tokens[pos+1].coalesce()

		return tokens[0:pos] + [tokens[pos+1]] + tokens[pos+3::]

class RParen(Token):
	pass

class Function(Token):
	def operate(self, tokens: list, pos: int) -> list:
		if pos >= (len(tokens) - 1):
			raise exceptions.MissingRightParen

		ptype = tokens[pos+1].type()
		pkids = len(tokens[pos+1].children)

		# inner expression hasn't been parsed yet, so exit early
		if ptype == 'LParen':
			return tokens

		if ptype != 'String' and pkids == 0:
			raise exceptions.MissingParam(self.text)

		#Currently, all functions require a precisely numeric param.
		if ptype != 'String' or not INT.match(tokens[pos+1].text):
			raise exceptions.BadFuncParam(f'Parameter for "{self.text}" must be an integer.')

		self.children = [ tokens[pos+1] ]

		return tokens[0:pos] + [self] + tokens[pos+2::]

	def output(self) -> dict:
		if len(self.children) == 0:
			raise exceptions.MissingParam(self.text)

		#we know that the param will always be numeric, not an expression
		count = int(self.children[0].text)

		if self.text == 'eq':
			if self.negate:
				return {'$or': [
					{ f'tags.{count-1}': { '$exists': False } },
					{ f'tags.{count}': { '$exists': True } },
				]}
			else:
				return { 'tags': { '$size': count } }

		elif self.text == 'lt':
			#don't allow filtering for blobs with fewer than 0 tags, that doesn't make sense.
			if count < 1:
				raise exceptions.BadFuncParam(f'Parameter for "{self.text}" must be a positive integer.')
			return { f'tags.{count-1}': { '$exists': self.negate } }
		elif self.text == 'le':
			return { f'tags.{count}': { '$exists': self.negate } }
		elif self.text == 'gt':
			return { f'tags.{count}': { '$exists': not self.negate } }
		elif self.text == 'ge':
			#don't allow filtering for blobs with at least 0 tags, that's always true.
			if count < 1:
				raise exceptions.BadFuncParam(f'Parameter for "{self.text}" must be a positive integer.')
			return { f'tags.{count-1}': { '$exists': not self.negate } }

		raise NotImplementedError(f'Output for function of type "{self.text}" is not implemented.')
