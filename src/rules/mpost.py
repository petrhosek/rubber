# This file is covered by the GPL as part of Rubber.
# (c) Emmanuel Beffara, 2002--2005
"""
Metapost support for Rubber.

The module parses input files for dependencies and does some checkings on
Metapost's log files after the process. Is it enough?
"""

import os, os.path
import re

from rubber import _
from rubber import *
from rubber.rules.latex import LogCheck

re_input = re.compile("input\\s+(?P<file>[^\\s;]+)")
# This is very restrictive, and so is the parsing routine. FIXME?
re_mpext = re.compile("[0-9]+|mpx|log")

class MPLogCheck (LogCheck):
	"""
	This class adapats the LogCheck class from the main program to the case of
	MetaPost log files, which are very similar to TeX log files.
	"""
	def read (self, name):
		"""
		The read() method in LogCheck checks that the log is produced by TeX,
		here we check that it is produced by MetaPost.
		"""
		file = open(name)
		line = file.readline()
		if not line:
			file.close()
			return 1
		if line.find("This is MetaPost,") == -1:
			file.close()
			return 1
		self.lines = file.readlines()
		file.close()
		return 0


class Dep (Depend):
	"""
	This class represents dependency nodes for MetaPost figures. The __init__
	method simply creates one node for the figures and one leaf node for all
	sources.
	"""
	def __init__ (self, env, target, source):
		sources = []
		self.cmd_pwd = os.path.dirname(source)
		self.include(os.path.basename(source), sources)
		msg.log(_("%s is made from %r") % (target, sources))
		self.leaf = DependLeaf(env, *sources)
		Depend.__init__(self, env, prods=[target], sources={source: self.leaf})
		self.env = env
		self.base = source[:-3]
		self.cmd = ["mpost", "\\batchmode;input %s" %
			os.path.basename(self.base)]
		if env.path == [""]:
			self.penv = {}
		else:
			self.penv = { "MPINPUTS":
				"%s:%s" % (self.env.path, os.getenv("MPINPUTS", "")) }
		self.log = None

	def include (self, source, list):
		"""
		This function tries to find a specified MetaPost source (currently all
		in the same directory), appends its actual name to the list, and
		parses it to find recursively included files.
		"""
		file = os.path.normpath(os.path.join(self.cmd_pwd, source))
		if exists(file + ".mp"):
			file = file + ".mp"
		elif not exists(file):
			return
		list.append(file)
		fd = open(file)
		for line in fd.readlines():
			m = re_input.search(line)
			if m:
				self.include(m.group("file"), list)
		fd.close()

	def run (self):
		"""
		Run Metapost from the source file's directory, so that figures are put
		next to their source file.
		"""
		msg.progress(_("running Metapost on %s.mp") % self.base)
		if self.env.execute(self.cmd, self.penv, pwd=self.cmd_pwd) == 0:
			return 0

		# This creates a log file that has the same aspect as TeX logs.

		self.log = MPLogCheck(self.env)
		if self.log.read(self.base + ".log"):
			msg.error(_(
				"I can't read MetaPost's log file, this is wrong."))
			return 1
		return self.log.errors()

	def show_errors (self):
		"""
		Report the errors from the last compilation.
		"""
		msg.info(_("There were errors in Metapost code:"))
		self.log.show_errors()

	def clean (self):
		"""
		This method removes all the files that the Metapost compilation may
		have created. It is required because the compilation may produce more
		files than just the figures used by the document.
		"""
		base = self.base + "."
		ln = len(base)
		dir = os.path.dirname(base)
		if dir == "":
			list = os.listdir(".")
		else:
			list = os.listdir(dir)
		for f in list:
			file = os.path.join(dir, f)
			if file[:ln] == base:
				ext = file[ln:]
				m = re_mpext.match(ext)
				if m and ext[m.end():] == "":
					msg.log(_("removing %s") % file)
					os.unlink(file)

# The `files' dictionary associates dependency nodes to MetaPost sources. It
# is used to detect when several figures from the same source are included. It
# uses a global variable, and this is authentically BAD. Therefore it deserves
# a big fat huge FIXME. Graphics modules should proably be encapsuled in
# classes the same way as standard Rubber modules, that would help for this
# problem.

files = {}

def convert (source, target, env, **args):
	if not prog_available("mpost"):
		return None
	if files.has_key(source):
		dep = files[source]
		dep.prods.append(target)
	else:
		dep = Dep(env, target, source)
		files[source] = dep
	return dep
