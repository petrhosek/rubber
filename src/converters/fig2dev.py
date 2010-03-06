# This file is covered by the GPL as part of Rubber.
# (c) Emmanuel Beffara, 2002--2006
"""
Conversion of XFig graphics into various formats.
"""

from rubber.util import prog_available
from rubber.depend import Shell

def check (source, target, context):
	return prog_available('fig2dev')

def convert (source, target, context, set):
	if target[-2:] != '_t':

		# Here we assume the target has an extension of a standard form, i.e.
		# its requested type can be deduced from the part of its name after
		# the last dot. We also assume that this extension is the name of the
		# appropriate language (it works fine in the cases where the module is
		# used, that is for eps, pdf and png).

		language = target[target.rfind('.')+1:]
		return Shell(set,
			['fig2dev', '-L', language, source, target],
			[target], [source])

	else:

		# Here we assume that the target has the form BASE.EXT_t, where EXT is
		# eps, pdf, pstex or pdftex. In this case we call fig2dev in such a
		# way that BASE.EXT_t refers to graphics file BASE and not BASE.EXT.
		# This way, the source will compile independently of the engine.

		the_dot = target.rfind('.')
		base_name = target[:the_dot]
		extension = target[the_dot+1:]
		image_reference = base_name[base_name.rfind('/')+1:]

		if 'graphics_suffixes' in context:
			if '.pdf' in context['graphics_suffixes']:
				language = 'pdftex'
				image_file = base_name + '.pdf'
			else:
				language = 'pstex'
				image_file = base_name + '.eps'
		elif extension in ('pdftex_t', 'pdf_t'):
			language = 'pdftex'
			image_file = base_name + '.pdf'
		else:
			language = 'pstex'
			image_file = base_name + '.eps'

		Shell(set,
			['fig2dev', '-L', language, source, image_file],
			[image_file], [source])
		return Shell(set,
			['fig2dev', '-L', language + '_t',
				'-p', image_reference, source, target],
			[target], [source, image_file])
