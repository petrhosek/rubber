# This file is covered by the GPL as part of Rubber.
# (c) Emmanuel Beffara, 2002
"""
Metapost support for Rubber.

The module parses input files for dependencies and does some checkings on
Metapost's log files after the process. Is it enough?
"""

import re

from rubber.util import *

re_input = re.compile("input +(?P<file>[^ ]+)")
# This is very restrictive, and so is the parsing routine. FIXME?

class Dep (Depend):
	"""
	This class represents dependency nodes for MetaPost figures. The __init__
	method simply creates one node for the figures and one leaf node for all
	sources.
	"""
	def __init__ (self, target, source, env):
		sources = []
		self.include(source, sources)
		env.msg(2, "%s is made from %r" % (target, sources))
		self.leaf = DependLeaf(sources)
		Depend.__init__(self, [target], {source: self.leaf})
		self.env = env
		self.base = source[:-3]
		self.cmd = ["mpost", "--interaction=batchmode", self.base]
		if env.src_path != "":
			cmd = [
				"env", "MPINPUTS=:%s:%s" %
				(self.env.src_path, os.getenv("MPINPUTS", ""))] + cmd

	def include (self, source, list):
		"""
		This function tries to find a specified MetaPost source (currently all
		in the same directory), appends its actual name to the list, and
		parses it to find recursively included files.
		"""
		if exists(source + ".mp"):
			file = source + ".mp"
		elif exists(source):
			file = source
		else:
			return
		list.append(file)
		fd = open(file)
		for line in fd.readlines():
			m = re_input.search(line)
			if m:
				self.include(m.group("file"), list)
		fd.close()

	def run (self):
		self.env.msg(0, "running Metapost on %s.mp..." % self.base)
		self.env.execute(self.cmd)

		# This creates a log file that has the same aspect as TeX logs.

		log = open(self.base + ".log")
		# The semantics of `error' is:
		# 0: no error occured,
		# 1: there has been an error,
		# 2: there has been an error, we are showing it.
		error = 0
		line = log.readline()
		while line != "":
			if error == 2:
				self.msg(0, line.rstrip())
				if line[0:2] == "l." or line[0:3] == "***":
					error = 1
			elif line[0] == "!":
				if not error:
					self.msg(0, _("There were errors in Metapost code:"))
				self.msg(0, line.rstrip())
				error = 2
			line = log.readline()
		log.close()
		return error

# The `files' dictionary associates dependency nodes to MetaPost sources. It
# is used to detect when several figures from the same source are included. It
# uses a global variable, and this is authentically BAD. Therefore it deserves
# a big fat huge FIXME. Graphics modules should proably be encapsuled in
# classes the same way as standard Rubber modules, that would help for this
# problem.

files = {}

def convert (source, target, env):
	if files.has_key(source):
		files[source].prods.append(target)
	else:
		files[source] = Dep(target, source, env)
	return files[source]
