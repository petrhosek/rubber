# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002
"""
This module contains material to extract information from compilation results.
"""

import re
from rubber import *

def _ (txt): return txt

re_hvbox = re.compile("(Ov|Und)erfull \\\\[hv]box ")

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
		last_file = None
		something = 0
		for line in self.lines:
			line = line.rstrip()
			if re_hvbox.match(line):
				if pos[-1] != last_file:
					last_file = pos[-1]
					self.msg(0, _("in file %s:") % last_file)
				self.msg(0, line)
				something = 1
			else:
				self.update_file(line, pos)
		return something
