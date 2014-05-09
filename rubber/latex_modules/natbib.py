# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2003
"""
Natbib support for Rubber

This package handles the behaviour specific to natbib, i.e. the fact that an
extra compilation may be needed when using this package.
"""

import re
re_rerun = re.compile("\(natbib\).*Rerun ")

def setup (document, context):
	global doc
	doc = document

def post_compile ():
	for line in doc.log.lines:
		if re_rerun.match(line):
			doc.must_compile = True
			return True
	return True
