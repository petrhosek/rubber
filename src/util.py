# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2006
"""
This module contains utility functions and classes used by the main system and
by the modules for various tasks.
"""

import hashlib
import os, stat, time
import imp
import re, string
from string import whitespace

from rubber import _, msg

#-- Miscellaneous functions --{{{1

def md5_file (fname):
	"""
	Compute the MD5 sum of a given file.
	"""
	m = hashlib.md5()
	file = open(fname)
	for line in file.readlines():
		m.update(line)
	file.close()
	return m.digest()


#-- Keyval parsing --{{{1

re_keyval = re.compile("\
[ ,]*\
(?P<key>[^ \t\n{}=,]+)\
([ \n\t]*=[ \n\t]*\
(?P<val>({|[^{},]*)))?")

def parse_keyval (str):
	"""
	Parse a list of 'key=value' pairs, with the syntax used in LaTeX's
	standard 'keyval' package. The value returned is simply a dictionary that
	contains all definitions found in the string. For keys without a value,
	the dictionary associates the value None.
	"""
	dict = {}
	while 1:
		m = re_keyval.match(str)
		if not m:
			return dict
		d = m.groupdict()
		str = str[m.end():]
		if not d["val"]:
			dict[d["key"]] = None
		elif d["val"] == '{':
			val, str = match_brace(str)
			dict[d["key"]] = val
		else:
			dict[d["key"]] = string.strip(d["val"])

def match_brace (str):
	"""
	Split the string at the first closing brace such that the extracted prefix
	is balanced with respect to braces. The return value is a pair. If the
	adequate closing brace is found, the pair contains the prefix before the
	brace and the suffix after the brace (not containing the brace). If no
	adequate brace is found, return the whole string as prefix and an empty
	string as suffix.
	"""
	level = 0
	for pos in range(0, len(str)):
		if str[pos] == '{':
			level = level + 1
		elif str[pos] == '}':
			level = level - 1
			if level == -1:
				return (str[:pos], str[pos+1:])
	return (str, "")


#-- Checking for program availability --{{{1

checked_progs = {}

def prog_available (prog):
	"""
	Test whether the specified program is available in the current path, and
	return its actual path if it is found, or None.
	"""
	if checked_progs.has_key(prog):
		return checked_progs[prog]
	for path in os.getenv("PATH").split(":"):
		file = os.path.join(path, prog)
		if os.path.exists(file):
			st = os.stat(file)
			if stat.S_ISREG(st.st_mode) and st.st_mode & 0111:
				checked_progs[prog] = file
				return file
	checked_progs[prog] = None
	return None


#-- Variable handling --{{{1

import UserDict

class Variables (UserDict.DictMixin):
	"""
	This class represent an environment containing variables. It can be
	accessed as a dictionary, except that every key must be declared using the
	method 'new_key' before it can be accessed for reading or writing.

	Environments are stacked, i.e. each environment can have a parent
	environment that contains other variables. The variables declared in an
	environment take precedence over parent environments, but changing the
	value of a variable changes its value in the environment that actually
	defines it.
	"""

	def __init__ (self, parent = None, items = {}):
		"""
		Create an environment, possibly with a parent environment, and initial
		bindings.
		"""
		if parent is not None and not isinstance(parent, Variables):
			raise ValueError()
		self.parent = parent
		self.dict = items

	def __getitem__ (self, key):
		"""
		Get the value of a variable in the environment or its parents.
		"""
		object = self
		while object is not None:
			if object.dict.has_key(key):
				return object.dict[key]
			object = object.parent
		raise KeyError

	def __setitem__ (self, key, value):
		"""
		Set the value of a variable in the environment or its parents,
		assuming it is defined somewhere. Raises 'KeyError' if the variable is
		not declared.
		"""
		object = self
		while object is not None:
			if object.dict.has_key(key):
				object.dict[key] = value
				return
			object = object.parent
		raise KeyError

	def keys (self):
		"""
		Return the set of keys defined in this environment and its parents.
		"""
		if self.parent is None:
			return set(self.dict.keys())
		else:
			return set(self.parent.keys()) | set(self.dict.keys())

	def new_key (self, key, value):
		"""
		Declare a new variable with an initial value in the current
		environment. If the variable already exists in this environment,
		raises 'KeyError'. If the variable exists in a parent environment, it
		is hidden by the new variable.
		"""
		if self.dict.has_key(key):
			raise KeyError
		self.dict[key] = value

#-- Parsing commands --{{{1

re_variable = re.compile("(?P<name>[a-zA-Z]+)")

def parse_line (line, dict):
	"""
	Decompose a string into a list of elements. The elements are separated by
	spaces, single and double quotes allow escaping of spaces (and quotes).
	Elements can contain variable references with the syntax '$VAR' (with only
	letters in the name) or '${VAR}'.

	If the argument 'dict' is defined, it is considered as a hash containing
	the values of the variables. If it is None, elements with variables are
	replaced by sequences of litteral strings or names, as follows:
		parse_line(" foo  bar${xy}quux toto  ")
			--> ["foo", ["'bar", "$xy", "'quux"], "toto"]
	"""
	elems = []
	i = 0
	size = len(line)
	while i < size:
		while i < size and line[i] in whitespace: i = i+1
		if i == size: break

		open = 0	# which quote is open
		arg = ""	# the current argument, so far
		if not dict: composed = None	# the current composed argument

		while i < size:
			c = line[i]

			# Open or close quotes.

			if c in '\'\"':
				if open == c: open = 0
				elif open: arg = arg + c
				else: open = c

			# '$' introduces a variable name, except within single quotes.

			elif c == '$' and open != "'":

				# Make the argument composed, if relevant.

				if not dict:
					if not composed: composed = []
					if arg != "": composed.append("'" + arg)
					arg = ""

				# Parse the variable name.

				if i+1 < size and line[i+1] == '{':
					end = line.find('}', i+2)
					if end < 0:
						name = line[i+2:]
						i = size
					else:
						name = line[i+2:end]
						i = end + 1
				else:
					m = re_variable.match(line, i+1)
					if m:
						name = m.group("name")
						i = m.end()
					else:
						name = ""
						i = i+1

				# Append the variable or its name.

				if dict:
					if dict.has_key(name):
						arg = arg + str(dict[name])
					# Send a warning for undefined variables ?
				else:
					composed.append("$" + name)
				continue

			# Handle spaces.

			elif c in whitespace:
				if open: arg = arg + c
				else: break
			else:
				arg = arg + c
			i = i+1

		# Append the new argument.

		if dict or not composed:
			elems.append(arg)
		else:
			if arg != "": composed.append("'" + arg)
			elems.append(composed)

	return elems

def make_line (template, dict):
	"""
	Instanciate a command template as returned by parse_line using a specific
	dictionary for variables.
	"""
	def one_string (arg):
		if arg.__class__ != list: return arg
		val = ""
		for elem in arg:
			if elem[0] == "'":
				val = val + elem[1:]
			else:
				if dict.has_key(elem[1:]):
					val = val + str(dict[elem[1:]])
		return val
	return map(one_string, template)
