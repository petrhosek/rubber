# This file is covered by the GPL as part of Rubber.
# (c) Emmanuel Beffara, 2002--2004
"""
Graphics file converters.

Each module in this package describes the operation of a particular external
utility that can be used to convert graphics files between formats. This root
module contains a table that contains the name of the module to be used in
each case.

TODO: this file must know about installed modules, it lacks the flexibility of
the main module system.
"""

import re
from os.path import *
from rubber.util import *

# The object `conv' is a dictionary, it associates patterns to
# sub-dictionnaries. Each sub-dictionary associates patterns to modules names.
# The patterns describe the suffixes for which the specified modules are to be
# used.

conv = {
"(.*)\\.pdf$" : {
	"\\1.fig" : ["fig2dev"],
	"\\1.eps" : ["epstopdf"] },
"(.*)\\.[0-9]+$" : {
	"\\1.mp" : ["mpost"] },
"(.*)\\.eps$" : {
	"\\1.fig" : ["fig2dev"],
	"\\1.jpeg" : ["jpeg2ps"],
	"\\1.jpg" : ["jpeg2ps"] },
"(.*)\\.png$" : {
	"\\1.fig" : ["fig2dev"] },
"(.*\\.e?ps)\\.bb$" : {
	"\\1.gz" : ["eps_gz"] }
}

# The module 'convert' (for the conversion program shipped with ImageMagick)
# provides a lot of formats, we let it include the rules in the table.

from rubber.graphics.convert import update_rules
update_rules(conv)

plugins = Plugins(__path__)
convert = Converter(conv, plugins)

def dep_file (base, suffixes, prefixes, env, loc={}):
	"""
	Search the given path list (prefix list, more precisely) for a file with
	the given basename and one of the given suffixes. If some transformation
	can be applied from an existing file that may not be generated,
	then a dependency tree is returned for this tranformation. If no
	transformation is found but an appropriate file is found, a dependency
	node for this file (as a leaf) is returned. If all fails, return None.
	"""
	targets = []
	for p in prefixes:
		for s in suffixes:
			target = p + base + s
			dep = convert(target, env)
			if dep:
				dep.loc = loc
				return dep
			if exists(target):
				return DependLeaf([target], env.msg, loc)
	return None
