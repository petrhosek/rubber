# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002
"""
This module contains utility functions and classes used by the main system and
by the modules for various tasks.
"""

import md5
import os
from os.path import *
import imp
import time
import re, string

#-- MD5 computation

def md5_file (fname):
	"""
	Compute the MD5 sum of a given file.
	"""
	m = md5.new()
	file = open(fname)
	for line in file.readlines():
		m.update(line)
	file.close()
	return m.digest()


#-- Keyval parsing

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


#-- Plugin management

class Plugins:
	"""
	This class gathers operations related to the management of external Python
	modules. Modules are requested through the `load_module' method, and
	they are searched for first in the current directory, then in the
	(possibly) specified Python package (using Python's path).
	"""
	def __init__ (self):
		self.modules = {}

	def __getitem__ (self, name):
		"""
		Return the module object of the given name.
		"""
		return self.modules[name]

	def load_module (self, name, package=None):
		"""
		Attempt to register a module with the specified name. If an
		appropriate module is found, load it and store it in the object's
		dictionary. Return 0 if no module was found, 1 if a module was found
		and loaded, and 2 if the module was found but already loaded.
		"""
		if self.modules.has_key(name):
			return 2
		try:
			file, path, descr = imp.find_module(name, [""])
		except ImportError:
			if not package:
				return 0
			try:
				pname = ""
				for p in package.split("."):
					pname = join(pname, p)
				file, path, descr = imp.find_module(join(pname, name));
			except ImportError:
				return 0
		module = imp.load_module(name, file, path, descr)
		file.close()
		self.modules[name] = module
		return 1

	def clear(self):
		"""
		Empty the module table, unregistering every module registered. No
		modules are unloaded, however, but this has no other effect than
		speeding the registration if the modules are loaded again.
		"""
		self.modules.clear()


#-- Dependency nodes

class Depend:
	"""
	This is a base class to represent file dependencies. It provides the base
	functionality of date checking and recursive making, supposing the
	existence of a method `run()' in the object. This method is supposed to
	rebuild the files of this node, returning zero on success and something
	else on failure.
	"""
	def __init__ (self, prods, sources):
		"""
		Initialize the object for a given set of output files and a given set
		of sources. The argument `prods' is a list of file names, and the
		argument `sources' is a dictionary that associates file names with
		dependency nodes.
		"""
		self.prods = prods
		try:
			# We set the node's date to that of the most recently modified
			# product file, assuming all other files were up to date then
			# (though not necessarily modified).
			self.date = max(map(getmtime, prods))
		except OSError:
			# If some product file does not exist, set the last modification
			# date to None.
			self.date = None
		self.sources = sources

	def should_make (self):
		"""
		Check the dependencies. Return true if this node has to be recompiled,
		i.e. if some dependency is modified. Nothing recursive is done here.
		"""
		if not self.date:
			return 1
		for src in self.sources.values():
			if src.date > self.date:
				return 1
		return 0

	def make (self):
		"""
		Make the destination file. This recursively makes all dependencies,
		then compiles the target if dependencies were modified. The semantics
		of the return value is the following:
		- 0 means that the process failed somewhere (in this node or in one of
		  its dependencies)
		- 1 means that nothing had to be done
		- 2 means that something was recompiled (therefore nodes that depend
		  on this one have to be remade)
		"""
		must_make = 0
		for src in self.sources.values():
			ret = src.make()
			if ret == 0:
				return 0
			if ret == 2:
				must_make = 1
		if must_make or self.should_make():
			if self.run():
				return 0

			# Here we must take the integer part of the value returned by
			# time.time() because the modification times for files, returned
			# by os.path.getmtime(), is an integer. Keeping the fractional
			# part could lead to errors in time comparison with the main log
			# file when the compilation of the document is shorter than one
			# second...

			self.date = int(time.time())
			return 2
		return 1

	def clean (self):
		"""
		Remove the files produced by this rule and recursively clean all
		dependencies.
		"""
		for file in self.prods:
			if exists(file):
				os.unlink(file)
		for src in self.sources.values():
			src.clean()

class DependLeaf (Depend):
	"""
	This class specializes Depend for leaf nodes, i.e. source files with no
	dependencies.
	"""
	def __init__ (self, dest):
		"""
		Initialize the node. The argument of this method is a *list* of file
	names, since one single node may contain several files.
		"""
		Depend.__init__(self, dest, {})
	def run (self):
		# FIXME
		if len(self.prods) == 1:
			print "%r does not exit" % self.prods[0]
		else:
			print "one of %r does not exit" % self.prods
		return 1
	def clean (self):
		pass
