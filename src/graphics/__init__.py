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
	"\\1.eps" : "epstopdf" },
"(.*)\\.[0-9]+$" : {
	"\\1.mp" : "mpost" }
}

import re
from os.path import *
from rubber.util import *

cconv = {}
for k in conv.keys():
	cconv[re.compile(k)] = conv[k]

plugins = Plugins()

def dep_file (base, suffixes, path, env):
	"""
	Search the given path list for a file with the given basename and one of
	the given suffixes. If some transformation can be applied from an existing
	file, then a dependency tree is returned for this tranformation. If no
	transformation is found but an appropriate file is found, a dependency
	node for this file (as a leaf) is returned. If all fails, return None.
	"""
	targets = []
	for p in path:
		for s in suffixes:
			targets.append(join(p, base + s))

	for target in targets:
		for dest in cconv.keys():
			m = dest.match(target)
			if m:
				rules = cconv[dest]
				for src in rules.keys():
					source = m.expand(src)
					if exists(source):
						mod = rules[src]
						if not plugins.load_module(mod, "rubber.graphics"):
							continue
						dep = plugins[mod].convert(source, target, env)
						if dep:
							return dep

	for file in targets:
		if exists(file):
			return DependLeaf([file])
	return None
