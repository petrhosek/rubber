# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002
"""
This is an experimental module that provides colored output using VT100 escape
codes. It works by replacing the writing method in the standard Message class
(doing this was the reason why such a class was used, actually).

A serious use of colors would require more than assigning one color to each
verbosity level. Some fontification of the messages would be nice, maybe by
including control sequences in the strings, that the message writer would
translate in an appropriate way.
"""

color = [
	"\x1B[31;1m", # level -1: red, boldface
	"",           # level  0: normal
	"\x1B[36m",   # level  1: cyan
	"\x1B[34m",   # level  2: blue
	"\x1B[35m" ]  # level  3: magenta

class Module:
	def __init__ (self, env, dict):
		self.msg = env.msg
		self.msg.write = self.write

	def write (self, level, text):
		if level <= self.msg.level:
			print "%s%s\x1B[0m" % (color[level + 1], text)
