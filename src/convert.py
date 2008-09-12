"""
This module contains code for file conversion, including implicit conversion
rule management.
"""

import re, imp, os.path
from ConfigParser import *

from rubber import _, msg
import rubber.converters
from rubber.util import Variables

re_variable = re.compile('[a-zA-Z]+')

def expand_cases (string, vars):
	"""
	Expand variables and cases in a template string. Variables must occur as
	$VAR (with only letters in the name) or ${VAR}, their values are taken
	from the dictionary-like object 'vars'. The "$" character can be written
	litterally by saying "$$". Cases are written in braces, separated with
	commas, as in {foo,bar,quux}. Commas at top-level also count as choice
	separators, as if there was a pair of braces around the whole string.
	Returns a pair (cases,pos) where 'cases' is the list of expansions of the
	string and 'pos' is the position of the first unbalanced "}" or the end of
	the string.
	"""
	pos = 0   # current position
	start = 0   # starting point of the current chunk
	cases = []   # possible expansions from previous cases
	current = ['']   # possible values for the current case, up to 'start'

	while pos < len(string):

		# Cases

		if string[pos] == ',':
			suffix = string[start:pos]
			cases.extend([s + suffix for s in current])
			current = ['']
			start = pos = pos + 1

		elif string[pos] == '{':
			mid = string[start:pos]
			next, shift = expand_cases(string[pos + 1:], vars)
			current = [left + mid + right for left in current for right in next]
			start = pos = pos + shift + 2

		elif string[pos] == '}':
			suffix = string[start:pos]
			return cases + [s + suffix for s in current], pos

		# Variable expansion

		elif string[pos] == '$' and pos < len(string):
			if string[pos + 1] == '{':
				end = string.find('}', pos + 2)
				if end < 0:
					end = len(string)
				name = string[pos+2:end]
				suffix = string[start:pos]
				if name in vars:
					suffix += vars[name]
				current = [s + suffix for s in current]
				start = pos = end + 1
			elif string[pos + 1] == '$':
				suffix = string[start:pos+1]
				current = [s + suffix for s in current]
				start = pos = pos + 2
			else:
				m = re_variable.match(string, pos + 1)
				if m:
					name = m.group()
					suffix = string[start:pos]
					if name in vars:
						suffix += vars[name]
					current = [s + suffix for s in current]
					start = pos = m.end()
				else:
					pos += 1

		else:
			pos += 1

	suffix = string[start:]
	return cases + [s + suffix for s in current], pos

class Rule (Variables):
	"""
	This class represents a single rule, as described in rules.ini. It is
	essentially a dictionary, but also includes a compiled form of the regular
	expression for the target.
	"""
	def __init__ (self, context, dict):
		Variables.__init__(self, context, dict)
		self.cost = dict['cost']
		self.re_target = re.compile(dict['target'] + '$')

class Converter (object):
	"""
	This class represents a set of translation rules that may be used to
	produce input files. Objects contain a table of rewriting rules to deduce
	potential source names from the target's name, and each rule has a given
	cost that indicates how expensive the translation is.

	Each rule contains a module name. The module is searched for in the
	package rubber.converters and it is supposed to contain two functions:

	- check(source, target, context):
	    Returns True if conversion from 'source' to 'target' is possible (i.e.
	    the source file is suitable, all required tools are available, etc.).
		The 'context' object is a dictionary-like object that contains values
		from the rule and possibly additional user settings. If the function
		is absent, conversion is always assumed to be possible.

	- convert(source, target, context, set):
	    Produce a dependency node in the given 'set' to produce 'target' from
		'source', using settings from the 'context'.
	"""
	def __init__ (self, set):
		"""
		Initialize the converter, associated with a given dependency set, with
		an empty set of rules.
		"""
		self.set = set
		self.modules = {}
		self.rules = {}

	def read_ini (self, filename):
		"""
		Read a set of rules from a file. The file has the form of an INI file,
		each section describes a rule.
		"""
		cp = ConfigParser()
		try:
			cp.read(filename)
		except ParsingError:
			msg.error(_("parse error, ignoring this file"), file=filename)
			return
		for name in cp.sections():
			dict = { 'name': name }
			for key in cp.options(name):
				dict[key] = cp.get(name, key)
			try:
				dict['cost'] = cp.getint(name, 'cost')
			except NoOptionError:
				msg.warn(_("ignoring rule `%s' (no cost found)") % name,
						file=filename)
				continue
			except ValueError:
				msg.warn(_("ignoring rule `%s' (invalid cost)") % name,
						file=filename)
				continue
			if 'target' not in dict:
				msg.warn(_("ignoring rule `%s' (no target found)") % name,
						file=filename)
				continue
			if 'rule' not in dict:
				msg.warn(_("ignoring rule `%s' (no module found)") % name,
						file=filename)
			if not self.load_module(dict['rule']):
				msg.warn(_("ignoring rule `%s' (module `%s' not found)") %
						(name, dict['rule']), file=filename)
			self.rules[name] = Rule(None, dict)

	def load_module (self, name):
		"""
		Check if the module of the given name exists and load it. Returns True
		if the module was loaded and False otherwise.
		"""
		if name in self.modules:
			return self.modules[name] is not None
		try:
			answer = imp.find_module(name, rubber.converters.__path__)
		except ImportError:
			self.modules[name] = None
			return False
		self.modules[name] = imp.load_module(name, *answer)
		return True

	def may_produce (self, name):
		"""
		Return true if the given filename may be that of a file generated by
		this converter, i.e. if it matches one of the target regular
		expressions.
		"""
		for rule in self.rules.values():
			if rule.re_target.match(name):
				return True
		return False

	def best_rule (self, target, check=None, context=None):
		"""
		Search for an applicable rule for the given target with the least
		cost. The returned value is a dictionary that describes the best rule
		found, or None if no rule is applicable. The optional argument 'check'
		is a function that takes the rule parameters as arguments (as a
		dictionary that contains at least 'source' and 'target') and can
		return false if the rule is refused. The optional argument 'context'
		is a dictionary that contains additional parameters passed to the
		converters.
		"""
		candidates = []

		for rule in self.rules.values():
			match = rule.re_target.match(target)
			if not match:
				continue
			templates, _ = expand_cases(rule['source'], {})
			for template in templates:
				source = match.expand(template)
				if source == target:
					continue
				if not os.path.exists(source):
					continue
				candidates.append((rule['cost'], source, target, rule))

		candidates.sort()
		for cost, source, target, rule in candidates:
			instance = Variables(context, rule)
			instance['source'] = source
			instance['target'] = target
			if check is not None and not check(instance):
				continue
			module = self.modules[rule['rule']]
			if hasattr(module, 'check'):
				if not module.check(source, target, instance):
					continue
			return instance

		return None

	def apply (self, instance):
		"""
		Apply a rule with the variables given in the dictionary passed as
		argument (as returned from the 'best_rule' method), and return a
		dependency node for the result.
		"""
		module = self.modules[instance['rule']]
		return module.convert(
				instance['source'], instance['target'], instance, self.set)
