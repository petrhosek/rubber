# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2006
"""
This is an experimental module that provides colored output using VT100 escape
codes. It works by replacing the writing method in the standard Message class
(doing this was the reason why such a class was used, actually).

A serious use of colors would require more than assigning one color to each
verbosity level. Some fontification of the messages would be nice, maybe by
including control sequences in the strings, that the message writer would
translate in an appropriate way.
"""

import rubber

color = [
	"\x1B[31;1m", # level 0: red, boldface
	"",           # level 1: normal
	"\x1B[34m",   # level 2: blue
	"\x1B[35m",   # level 3: magenta
	"\x1B[36m" ]  # level 4: cyan

class Module (rubber.rules.latex.Module):
	def __init__ (self, doc, dict):
		rubber.msg.write = self.write

	def write (self, text, level=0):
		if level <= rubber.msg.level:
			print "%s%s\x1B[0m" % (color[level], text)
