# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2005
"""
Support for the `graphicx' package in Rubber.

This package is essentially the same as `graphics', so we derive this module
form the module for `graphics'. We do this as an import, so it requires that
`graphics' is installed as a package module (which it is in standard).
"""

import rubber.rules.latex.graphics

class Module (rubber.rules.latex.graphics.Module):
	pass
