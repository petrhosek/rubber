# This file is covered by the GPL as part of Rubber.
# (c) Emmanuel Beffara, 2002--2005
"""
Conversion of XFig graphics into various formats.
"""

from rubber import _, msg
from rubber import *

import string, re

class Dep (Depend):
	"""
	This class represents dependency nodes from XFig files to standard
	graphics formats (i.e. not combined ps/latex).
	"""
	def __init__ (self, env, target, source):
		leaf = DependLeaf(env, source)
		Depend.__init__(self, env, [target], {source: leaf})
		self.env = env
		self.source = source

		# Here we assume the target has an extension of a standard form, i.e.
		# its requested type can be deduced from the part of its name after
		# the last dot. We also assume that this extension is the name of the
		# appropriate language (it works fine in the cases where the module is
		# used, that is for eps, pdf and png).

		lang = target[string.rfind(target, ".")+1:]
		self.lang = string.upper(lang)
		
		self.cmd = ["fig2dev", "-L", lang, source, target]

	def run (self):
		msg.progress(_("converting %s to %s") % (self.source, self.lang))
		if self.env.execute(self.cmd):
			msg.error(_("converstion of %s to %s failed")
					% (self.source, self.lang))
			return 1
		return 0

re_pstname = re.compile("(?P<base>.*)\\.(?P<type>eps|pstex|pdf|pdftex)_t")
pst_lang = {
	"eps": ("pstex", "EPS"), "pstex": ("pstex", "EPS"),
	"pdf": ("pdftex", "PDF"), "pdftex": ("pdftex", "PDF")
}

class PSTDep (Depend):
	"""
	This class represents dependency nodes for combined EPS/LaTeX figures from
	XFig. They produce both a LaTeX source that contains an \\includegraphics
	and an EPS file.
	"""
	def __init__ (self, env, tex, fig, vars, module=None, loc={}):
		"""
		The arguments of the constructor are, respectively, the figure's
		source, the LaTeX source produced, the EPS figure produced, the name
		to use for it (probably the same one), and the environment.
		"""
		leaf = DependLeaf(env, fig, loc=loc)
		self.env = env

		m = re_pstname.match(tex)
		base = m.group("base")
		type = m.group("type")
		eps = base + "." + type
		if module is not None and "." + type in module.suffixes:
			epsname = base
		else:
			epsname = eps
		lang, self.langname = pst_lang[type]

		Depend.__init__(self, env, prods=[tex, eps], sources={fig: leaf}, loc=loc)
		self.fig = fig
		self.cmd_t = ["fig2dev", "-L", lang + "_t", "-p",
			os.path.basename(epsname), fig, tex ]
		self.cmd_p = ["fig2dev", "-L", lang, fig, eps ]

	def run (self):
		msg.progress(_("converting %s into %s/LaTeX") %
				(self.fig, self.langname))
		if self.env.execute(self.cmd_t): return 1
		return self.env.execute(self.cmd_p)

def check (vars, env):
	if not prog_available("fig2dev"):
		return None
	target = vars["target"]
	i = target.rfind(".")
	if i > 0 and target[i+1:] in ["eps_t", "pstex_t", "pdf_t", "pdftex_t"]:
		vars["mode"] = "pstex"
	else:
		vars["mode"] = "normal"
	return vars

def convert (vars, env):
	if vars["mode"] == "pstex":
		return PSTDep(env, vars["target"], vars["source"], vars)
	else:
		return Dep(env, vars["target"], vars["source"])
