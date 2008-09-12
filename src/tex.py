# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2008
"""
General-purpose classes for reading TeX code.
Classes and functions from this module can be used without Rubber.
"""

import codecs, re
from StringIO import StringIO

# The catcodes

EOF = -2
CSEQ = -1
ESCAPE = 0
OPEN = 1
CLOSE = 2
MATH = 3
ALIGN = 4
END_LINE = 5
ARGUMENT = 6
SUPER = 7
SUB = 8
IGNORE = 9
SPACE = 10
LETTER = 11
OTHER = 12
ACTIVE = 13
COMMENT = 14
INVALID = 15

# The default categories

catcodes = {
	'\\' : ESCAPE,
	'{' : OPEN,
	'}' : CLOSE,
	'$' : MATH,
	'&' : ALIGN,
	'\n' : END_LINE,
	'#' : ARGUMENT,
	'^' : SUPER,
	'_' : SUB,
	'\000' : IGNORE,
	' ' : SPACE, '\t' : SPACE,
	'~' : ACTIVE,
	'%' : COMMENT,
	'\177' : INVALID
}

for i in range(0,26):
	catcodes[chr(ord('A')+i)] = LETTER
	catcodes[chr(ord('a')+i)] = LETTER


class Token:
	"""
	The class used to represent tokens. Objects contain a catcode, a value
	(for control sequences) and the raw text that represents them in the input
	file.
	"""
	def __init__ (self, cat, val=None, raw=None):
		self.cat = cat
		self.val = val
		self.raw = raw


class ParserBase:
	"""
	This is the base class for parsers. It holds state information like
	catcodes, handles the push-back buffer, and leaves it to derived classes
	to actually read tokens, using the "read_token" method. This class also
	provides high-level functionality like getting macro arguments.
	"""
	def __init__ (self):
		self.catcodes = catcodes.copy()
		self.next = []
		self.math_mode = 0
		self.last_is_math = 0

	def catcode (self, char):
		"""
		Return the catcode of a character.
		"""
		if self.catcodes.has_key(char):
			return self.catcodes[char]
		else:
			return OTHER

	def put_token (self, token):
		"""
		Put back a token in the input.
		"""
		self.next.append(token)

	def put_list (self, list):
		"""
		Put back a token list in the input.
		"""
		arg = list[:]
		arg.reverse()
		self.next.extend(arg)

	def peek_token (self):
		"""
		Return the next token that will be read without updating the state.
		"""
		if len(self.next) > 0:
			return self.next[-1]
		token = self.read_token()
		self.put_token(token)
		return token

	def get_token (self):
		"""
		Get the next token from the input and update the math mode.
		"""
		if len(self.next) > 0:
			token = self.next.pop()
		else:
			token = self.read_token()

		if token.cat == MATH:
			if self.last_is_math:
				if self.math_mode == 1:
					self.math_mode = 2
				self.last_is_math = 0
			else:
				if self.math_mode == 0:
					self.math_mode = 1
				else:
					self.math_mode = 0
				self.last_is_math = 1
		else:
			self.last_is_math = 0

		return token

	def __iter__ (self):
		"""
		Return an iterator over all tokens in the input. The EOF token is not
		returned by this iterator.
		"""
		while 1:
			token = self.get_token()
			if token.cat == EOF:
				break
			yield token

	def skip_space (self):
		"""
		Skip white space in the input.
		"""
		while self.peek_token().cat == SPACE:
			self.get_token()

	def get_group (self):
		"""
		Get the list of tokens up to the next closing brace, and drop the
		closing brace.
		"""
		value = []
		level = 1
		while 1:
			token = self.get_token()
			if token.cat == OPEN:
				level += 1
			elif token.cat == CLOSE:
				level -= 1
				if level == 0:
					break
			elif token.cat == EOF:
				break
			value.append(token)
		return value

	def get_group_text (self):
		"""
		Get the list of tokens up to the next closing brace, and drop the
		closing brace. Return the list as a string.
		"""
		value = ""
		level = 1
		while 1:
			token = self.get_token()
			if token.cat == OPEN:
				level += 1
			elif token.cat == CLOSE:
				level -= 1
				if level == 0:
					break
			elif token.cat == EOF:
				break
			value += token.raw
		return value

	def get_argument (self):
		"""
		Get a macro argument from the input text. Returns a token list with
		the value of the argument, with surrounding braces removed if
		relevant.
		"""
		self.skip_space()
		token = self.get_token()
		if token.cat == EOF:
			return []
		if token.cat != OPEN:
			return [token]
		return self.get_group()

	def get_argument_text (self):
		"""
		Get a macro argument from the input text. Returns a string with
		the text of the argument, with surrounding braces removed if
		relevant.
		"""
		self.skip_space()
		token = self.get_token()
		if token.cat == EOF:
			return None
		if token.cat != OPEN:
			return token.raw
		return self.get_group_text()

	def get_latex_optional_text (self):
		"""
		Check if a LaTeX-style optional argument is present. If such an
		argument is present, return it as text, otherwise return None.
		"""
		next = self.get_token()

		if next.cat != OTHER or next.raw != '[':
			self.put_token(next)
			return None

		level = 0
		text = ""
		while True:
			token = self.get_token()
			if token.cat == EOF:
				break
			if token.cat == OTHER and token.raw == ']' and level == 0:
				break
			if token.cat == OPEN:
				level += 1
			elif token.cat == CLOSE:
				if level == 0:
					break
				level -= 1
			text += token.raw

		return text

def re_set (set, complement=False):
	"""
	Returns a string that contains a regular expression matching a given set
	of characters, or its complement if the optional argument is true. The set
	must not be empty.
	"""
	if len(set) == 0:
		raise RuntimeError('argument of re_set must not be empty')
	if not complement and len(set) == 1:
		c = set[0]
		if c in '.^$*+?{}\\[]|()':
			return '\\' + c
		else:
			return c
	expr = '['
	if complement:
		expr += '^'
	for c in set:
		if c in ']-\\':
			expr += '\\' + c
		else:
			expr += c
	return expr + ']'

class Parser (ParserBase):
	"""
	A parser for TeX code that reads its input from a file object.

	The class also provides a hook feature: the method 'set_hooks' declares a
	set of control sequence names, and the method 'next_hook' parses the input
	until it finds a control sequence from this set, ignoring all other
	tokens. This advantage of this method is that is is much faster than
	reading tokens one by one.
	"""
	def __init__ (self, input, coding=None):
		"""
		Initialise the parser with a file as input. If the argument 'coding'
		is used, then the input is translated from this coding to Unicode
		before parsing. If 'input' is None, then input can only be provided by
		the 'put_token' and 'put_list' methods.
		"""
		ParserBase.__init__(self)
		if coding is None:
			self.input = input
		else:
			self.input = codecs.lookup(coding).streamreader(input)
		self.line = ""
		self.pos_line = 1
		self.pos_char = 1
		self.next_char = None

	def read_line (self):
		"""
		Reads a line of input and sets the attribute 'line' with it. Returns
		True if reading succeeded and False if it failed.
		"""
		if self.input is None:
			return False
		self.line = self.input.readline()
		if self.line == "":
			return False
		return True

	def read_char (self):
		"""
		Get the next character from the input and its catcode (without parsing
		control sequences).
		"""
		if self.next_char is not None:
			t = self.next_char
			self.next_char = None
			return t

		while self.line == "":
			if not self.read_line():
				return Token(EOF)
		c = self.line[0]
		self.line = self.line[1:]

		if c == '\n':
			self.pos_line += 1
			self.pos_char = 1
		else:
			self.pos_char += 1

		return Token(self.catcode(c), raw=c)

	def read_token (self):
		"""
		Get the next token from the input.
		"""
		token = self.read_char()
		if token.cat != ESCAPE:
			if token.cat in (LETTER, OTHER):
				token.val = token.raw
			return token
		raw = token.raw
		token = self.read_char()
		if token.cat != LETTER:
			token.cat = CSEQ
			token.val = token.raw
			token.raw = raw + token.raw
			return token
		name = ""
		while token.cat == LETTER:
			raw += token.raw
			name += token.raw
			token = self.read_char()
		while token.cat == SPACE:
			raw += token.raw
			token = self.read_char()
		self.next_char = token
		return Token(CSEQ, name, raw)

	def re_cat (self, *cat):
		"""
		Returns a regular expression that maches characters whose category is
		in given list.
		"""
		return re_set([char for char,code in self.catcodes.items() if code in cat])

	def re_nocat (self, *cat):
		"""
		Returns a regular expression that maches characters whose category is
		not in a given list.
		"""
		return re_set([char for char,code in self.catcodes.items() if code in cat], True)

	def set_hooks (self, names):
		"""
		Define the set of hooks for 'next_hook'.
		"""
		expr = '(' \
			+ self.re_nocat(ESCAPE, COMMENT) + '|' \
			+ self.re_cat(ESCAPE) + self.re_cat(ESCAPE, COMMENT) + ')*' \
			+ '(?P<raw>' + self.re_cat(ESCAPE) \
			+ '(?P<val>' + '|'.join(names) + ')' \
			+ '(' + self.re_cat(SPACE) + '+|(?=' + self.re_nocat(LETTER) + ')|$))'
		self.regex = re.compile(expr)

	def next_hook (self):
		"""
		Ignore input until the next control sequence from the set defined by
		'set_hooks'. Returns the associated token, or the EOF token if no hook
		was found.
		"""
		while self.line == "":
			if not self.read_line():
				return Token(EOF)
		while True:
			match = self.regex.match(self.line)
			if match is not None:
				self.pos_char = match.end('raw') + 1
				self.line = self.line[match.end('raw'):]
				return Token(CSEQ, match.group('val'), match.group('raw'))
			if not self.read_line():
				return Token(EOF)
			self.pos_line += 1
			self.pos_char = 1

class ListParser (ParserBase):
	"""
	A parser that reads its input from a token list (or any iterable object
	that contains tokens) instead of parsing anything.
	"""
	def __init__ (self, input):
		ParserBase.__init__(self)
		self.input = iter(input)
	def read_token (self):
		try:
			return self.input.next()
		except StopIteration:
			return Token(EOF)

def parse_string (text):
	"""
	Factory function for parsing TeX code from a string.
	"""
	return Parser(StringIO(text))
