from rubber import _, msg


def setup(doc, context):
    doc.vars['program'] = 'xelatex'
    doc.vars['engine'] = 'XeLaTeX'

    if doc.env.final != doc and doc.products[0][-4:] != '.pdf':
        msg.error(_("there is already a post-processor registered"))
        return

    doc.reset_products([doc.target + '.pdf'])
