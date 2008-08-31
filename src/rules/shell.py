# This file is covered by the GPL as part of Rubber.
# (c) Emmanuel Beffara, 2005
"""
Generic shell conversion rule.

The action of this rule is defined by variables specified in the rule file:
- "command" is the command line, it is split the same way as directives,
   other variables are substituted,
- "source" is the input file name,
- "target" is the output file name.
"""

from rubber.util import parse_line, prog_available
from rubber.depend import Shell

def check (source, target, context):
	line = parse_line(context['command'], context)
	return prog_available(line[0])

def convert (source, target, context, set):
	return Shell(set,
		parse_line(context['command'], context),
		[target], [source])
