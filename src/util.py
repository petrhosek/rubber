# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002
"""
This module contains utility functions used by the main system and by the
modules for various tasks.
"""

import md5

def md5_file (fname):
	"""
	Compute the MD5 sum of a given file.
	"""
	m = md5.new()
	file = open(fname)
	for line in file.readlines():
		m.update(line)
	file.close()
	return m.digest()
