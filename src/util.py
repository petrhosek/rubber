# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002
"""
This module contains utility functions used by the main system and by the
modules for various tasks.
"""

import md5
import os.path
import imp

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
					pname = os.path.join(pname, p)
				file, path, descr = imp.find_module(os.path.join(pname, name));
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
