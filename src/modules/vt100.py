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
		self.conf = env.config
		if self.conf.verb_level <= 0:
			# if no extra verbosity is required, there is no need to write
			# everything in boldface
			self.shift = 1
		else:
			self.shift = 1
		env.message.write = self.write

	def write (self, level, text):
		if level <= self.conf.verb_level:
			print "%s%s\x1B[0m" % (color[level+self.shift], text)
