# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002
"""
This module contains material to extract information from compilation results.
"""

import re
import string
from rubber import _
from rubber import *

re_page = re.compile("\[(?P<num>[0-9]+)\]")
re_hvbox = re.compile("(Ov|Und)erfull \\\\[hv]box ")
re_reference = re.compile("LaTeX Warning: (?P<msg>Reference .*)")

class LogInfo (LogCheck):
	"""
	This class extends the class LogCheck from the main module, providing
	methods to extract various kinds of information.
	"""
	def show_boxes (self):
		"""
		Display all messages related so underfull and overfull boxes. Return 0
		if there is nothing to display.
		"""
		pos = []
		page = 1
		something = 0
		for line in self.lines:
			line = line.rstrip()
			if re_hvbox.match(line):
				self.msg.info({"file":pos[-1], "page":page}, line)
				something = 1
			else:
				self.update_file(line, pos)
				page = self.update_page(line, page)
		return something

	def show_references (self):
		"""
		Display all undefined references.
		"""
		something = 0
		for line in self.lines:
			m = re_reference.match(line)
			if m:
				self.msg(0, m.group("msg"))
				something = 1
		return something

	def show_warnings (self):
		"""
		Display all warnings. This function is pathetically dumb, as it simply
		shows all lines in the log that contain the substring 'Warning'.
		"""
		pos = []
		page = 1
		something = 0
		for line in self.lines:
			if line.find("Warning") != -1:
				self.msg.info(
					{"file":pos[-1], "page":page},
					string.rstrip(line))
				something = 1
			else:
				self.update_file(line, pos)
				page = self.update_page(line, page)
		return something

	def update_page (self, line, before):
		"""
		Parse the given line and return the number of the page that is being
		built after that line, assuming the current page before the line was
		`before'.
		"""
		ms = re_page.findall(line)
		if ms == []:
			return before
		return int(ms[-1]) + 1
