# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002
"""
pfdLaTeX support for Rubber.
"""

class Module:
	def __init__ (self, env, dict):
		env.config.latex = "pdflatex"
		env.config.tex = "pdfTeX"
		env.process.out_ext = ".pdf"
