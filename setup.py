#!/usr/bin/python
import os
from setuptools import setup
import git_version as gv

setup(
        name = "rubber",
        version = gv.get_git_version(),
        description = "an automated system for building LaTeX documents",
        long_description = """\
This is a building system for LaTeX documents. It is based on a routine that
runs just as many compilations as necessary. The module system provides a
great flexibility that virtually allows support for any package with no user
intervention, as well as pre- and post-processing of the document. The
standard modules currently provide support for bibtex, dvips, dvipdfm, pdftex,
makeindex. A good number of standard packages are supported, including
graphics/graphicx (with automatic conversion between various formats and
Metapost compilation).\
""",
        author = "Emmanuel Beffara",
        author_email = "manu@beffara.org",
        url = "http://rubber.sourceforge.net/",
        license = "GPL",
        packages = ["rubber", "rubber.converters", "rubber.latex_modules"],
        package_data = { 'rubber': ['data/modules/*.rub',
                                    'data/rules.ini',
                                    'data/_rubber', # Do we need this?
                                    os.path.basename(gv.__version_file)
                                   ]
                       },
        entry_points = { 'console_scripts': ['rubber = rubber.cmdline:script_entry_point',
                                             'rubber-info = rubber.cmd_info:script_entry_point',
                                             'rubber-pipe = rubber.cmd_pipe:script_entry_point',
                                            ]
                       }
        # FIXME: Find a clean way to install documentation via setuptools
        #data_files =
        #[(moddir + "/modules", glob.glob("data/modules/*.rub")),
        # (moddir, ["data/rules.ini"]),
        # (mandir + "/man1",
        #        ["doc/man-en/rubber.1", "doc/man-en/rubber-info.1", "doc/man-en/rubber-pipe.1"]),
        # (mandir + "/fr/man1",
        #        ["doc/man-fr/rubber.1", "doc/man-fr/rubber-info.1", "doc/man-fr/rubber-pipe.1"]),
        # (infodir, ["doc/rubber.info"])]
    )
