# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002
"""
Makeindex support for Rubber.

This module (associated to the package makeidx) handles the processing of the
document's index using makeindex. It stores an MD5 sum of the .idx file
between two runs, in order to detect modifications.

The following directives are provided to specify options for makeindex:

  order <ordering> =
    Modify the ordering to be used. The argument must be a space separated
    list of:
    - standard = use default ordering (no options, this is the default)
    - german = use German ordering (option "-g")
    - letter = use letter instead of word ordering (option "-l")

  path <directory> =
    Add the specified directory to the search path for styles.

  style <name> =
    Use the specified style file.
"""

import os

import rubber
from rubber import _
from rubber.util import *

class Module (rubber.Module):
	def __init__ (self, env, dict):
		"""
		Initialize the module, checking if there is already an index.
		"""
		self.env = env
		self.msg = env.msg
		self.pbase = env.src_base
		if os.path.exists(self.pbase + ".idx"):
			self.md5 = md5_file(self.pbase + ".idx")
		else:
			self.md5 = None

		self.path = [""]
		if env.src_path != "" and env.src_path != ".":
			self.path.append(env.src_path)
		self.style = None
		self.opts = []

	def command (self, cmd, arg):
		if cmd == "order":
			for opt in arg.split():
				if opt == "standard": self.opts = []
				elif opt == "german": self.opts.append("-g")
				elif opt == "letter": self.opts.append("-l")
				else: self.msg(1,
					_("unknown option '%s' for 'makeidx.order'") % opt)
		elif cmd == "path":
			self.path.append(os.path.expanduser(arg))
		elif cmd == "style":
			self.style = arg

	def post_compile (self):
		"""
		Run makeindex if needed, with appropriate options and environment.
		"""
		if not os.path.exists(self.pbase + ".idx"):
			self.msg(2, _("strange, there is no index file"))
			return 0
		if not self.run_needed():
			return 0

		self.msg(0, "making index...")
		cmd = ["makeindex"] + self.opts
		if self.style:
			cmd.extend(["-s", self.style])
		cmd.append(self.pbase)
		if self.path != [""]:
			env = { 'INDEXSTYLE':
				string.join(self.path + [os.getenv("INDEXSTYLE", "")], ":") }
		else:
			env = {}
		if self.env.execute(cmd, env):
			self.env.msg(0, _("the operation failed"))
			return 1

		self.env.must_compile = 1
		return 0

	def run_needed (self):
		"""
		Check if makeindex has to be run. This is the case either if the .ind
		file does not exist or if the .idx file has changed.
		"""
		if not os.path.exists(self.pbase + ".ind"):
			self.md5 = md5_file(self.pbase + ".idx")
			return 1
		if not self.md5:
			self.md5 = md5_file(self.pbase + ".idx")
			self.msg(2, _("the index file is new"))
			return 1
		new = md5_file(self.pbase + ".idx")
		if self.md5 == new:
			self.msg(2, _("the index did not change"))
			return 0
		self.md5 = new
		self.msg(2, _("the index has changed"))
		return 1

	def clean (self):
		"""
		Remove all generated files related to the document's index.
		"""
		self.env.remove_suffixes([".idx", ".ind", ".ilg"])
