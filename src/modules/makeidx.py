# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002
"""
Makeindex support for Rubber.

This module (associated to the package makeidx) handles the processing of the
document's index using makeindex. It stores an MD5 sum of the .idx file
between two runs, in order to detect modifications.
"""

import os
import md5

def _ (txt): return txt

class Module:
	def __init__ (self, env, dict):
		"""
		Initialize the module, checking if there is already an index.
		"""
		self.env = env
		self.msg = env.message
		env.process.compile_process.append(self.make)
		env.process.cleaning_process.append(self.clean)

		if os.path.exists(self.env.process.src_pbase + ".idx"):
			self.md5 = self.md5sum()
		else:
			self.md5 = None

	def make (self):
		"""
		Run makeindex if needed.
		"""
		if not os.path.exists(self.env.process.src_pbase + ".idx"):
			self.msg(2, _("strange, there is no index file"))
			return 0
		if not self.run_needed():
			return 0
		self.msg(0, "making index...")
		self.env.process.execute(["makeindex", self.env.process.src_pbase])
		self.env.process.must_compile = 1

	def run_needed (self):
		"""
		Check if makeindex has to be run. This is the case either if the .ind
		file does not exist or if the .idx file has changed.
		"""
		if not os.path.exists(self.env.process.src_pbase + ".ind"):
			self.md5 = self.md5sum()
			return 1
		if not self.md5:
			self.md5 = self.md5sum()
			self.msg(2, _("the index file is new"))
			return 1
		new = self.md5sum()
		if self.md5 == new:
			self.msg(2, _("the index did not change"))
			return 0
		self.md5 = new
		self.msg(2, _("the index has changed"))
		return 1

	def md5sum (self):
		"""
		Compute the MD5 sum of the .idx file.
		"""
		m = md5.new()
		file = open(self.env.process.src_pbase + ".idx")
		for line in file.readlines():
			m.update(line)
		file.close()
		return m.digest()

	def clean (self):
		"""
		Remove all generated files related to the document's index.
		"""
		self.env.process.remove_suffixes([".idx", ".ind", ".ilg"])
