# This file is covered by the GPL as part of Rubber.
# (c) Emmanuel Beffara, 2005
"""
Generic shell conversion rule.

The action of this rule is defined by variables specified in the rule file:
- "command" is the command line, it is split the same way as directives,
    others variables are substituted,
- "message" is the progress message, it is treated the same way as "command",
    a default message is produced when it is undefined,
- "source" is the input file name,
- "target" is the output file name.
"""

from rubber import _, msg
from rubber import *
from rubber.util import parse_line

class Dep (Depend):
	def __init__ (self, env, target, source, vars):
		leaf = DependLeaf(env, source)
		Depend.__init__(self, env, prods=[target], sources={source: leaf})
		self.env = env
		vars["source"] = source
		vars["target"] = target
		self.vars = vars

	def run (self):
		cmd = parse_line(self.vars["command"], self.vars)
		if self.vars.has_key("message"):
			msg.progress(" ".join(parse_line(self.vars["message"], self.vars)))
		else:
			msg.progress(_("running %s") % " ".join(cmd))
		if self.env.execute(cmd):
			msg.error(_("'%s' failed") % cmd[0])
			return 1
		return 0

def convert (source, target, env, vars):
	check = vars["command"].split()[0]
	if not prog_available(check):
		return None
	return Dep(env, target, source, vars)
