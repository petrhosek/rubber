# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2008
"""
Support for nomenclatures with package 'nomencl'.

This module simply wraps the functionality of the 'index' module with default
values for the 'nomencl' package.
"""

import rubber
from rubber.rules.latex.index import Index

class Module (Index, rubber.rules.latex.Module):
	def __init__ (self, doc, dict):
		Index.__init__(self, doc, "nlo", "nls", "ilg")
		self.do_style("nomencl.ist")
