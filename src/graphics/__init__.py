# This file is covered by the GPL as part of Rubber.
# (c) Emmanuel Beffara, 2002
"""
Graphics file converters.

Each module in this package describes the operation of a particular external
utility that can be used to convert graphics files between formats. This root
module contains a table that contains the name of the module to be used in
each case.

TODO: this file must know about installed modules, it lacks the flexibility of
the main module system.
"""

# The object `conv' is a dictionary, it associates patterns to
# sub-dictionnaries. Each sub-dictionary associates patterns to modules names.
# The patterns describe the suffixes for which the specified modules are to be
# used.

conv = {
"(.*)\\.pdf$" : {
	"\\1.fig" : "fig2dev",
	"\\1.eps" : "epstopdf" },
"(.*)\\.[0-9]+$" : {
	"\\1.mp" : "mpost" },
"(.*)\\.eps$" : {
	"\\1.fig" : "fig2dev",
	"\\1.jpeg" : "jpeg2ps",
	"\\1.jpg" : "jpeg2ps" },
"(.*)\\.png$" : {
	"\\1.fig" : "fig2dev" },
"(.*\\.e?ps)\\.bb$" : {
	"\\1.gz" : "eps_gz" }
}

import re
from os.path import *
from rubber.util import *

plugins = Plugins()
convert = Converter(conv, plugins, "rubber.graphics")

def dep_file (base, suffixes, prefixes, env):
	"""
	Search the given path list (prefix list, more precisely) for a file with
	the given basename and one of the given suffixes. If some transformation
	can be applied from an existing file, then a dependency tree is returned
	for this tranformation. If no transformation is found but an appropriate
	file is found, a dependency node for this file (as a leaf) is returned. If
	all fails, return None.
	"""
	targets = []
	for p in prefixes:
		for s in suffixes:
			targets.append(p + base + s)

	for target in targets:
		dep = convert(target, env)
		if dep:
			return dep

	for file in targets:
		if exists(file):
			return DependLeaf([file])
	return None
