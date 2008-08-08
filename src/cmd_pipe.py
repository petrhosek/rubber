# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2003--2006
"""
This is the command line pipe interface for Rubber.
"""

import sys
import os.path
import string
import re
from getopt import *

from rubber import _
from rubber import *
from rubber.version import *
from rubber.depend import ERROR, CHANGED, UNCHANGED
import rubber.cmdline

re_rubtmp = re.compile("rubtmp(?P<num>[0-9]+)\\.")

def make_name ():
	"""
	Return a base name suitable for a new compilation in the current
	directory. The name will have the form "rubtmp" plus a number, such
	that no file of this prefix exists.
	"""
	num = 0
	for file in os.listdir("."):
		m = re_rubtmp.match(file)
		if m:
			num = max(num, int(m.group("num")) + 1)
	return "rubtmp%d" % num

def dump_file (f_in, f_out):
	"""
	Dump the contents of a file object into another.
	"""
	for line in f_in.readlines():
		f_out.write(line)

class Main (rubber.cmdline.Main):
	def __init__ (self):
		rubber.cmdline.Main.__init__(self)
		msg.level = 0

	def help (self):
		"""
		Display the description of all the options and exit.
		"""
		print _("""\
This is Rubber version %s.
usage: rubber-pipe [options]
available options:
  -b, --bzip2              compress the final document with bzip2
  -c, --command=CMD        run the directive CMD before parsing (see man page)
  -e, --epilogue=CMD       run the directive CMD after parsing
  -z, --gzip               compress the final document
  -h, --help               display this help
      --into=DIR           go to directory DIR before compiling
  -k, --keep               keep the temporary files after compiling
  -l, --landscape          change paper orientation (if relevant)
  -n, --maxerr=NUM         display at most NUM errors (default: 10)
  -m, --module=MOD[:OPTS]  use module MOD (with options OPTS)
      --only=SOURCES       only include the specified SOURCES
  -o, --post=MOD[:OPTS]    postprocess with module MOD (with options OPTS)
  -d, --pdf                produce a pdf (synonym for -m pdftex or -o ps2pdf)
  -p, --ps                 process through dvips (synonym for -m dvips)
  -q, --quiet              suppress messages
  -r, --read=FILE          read additional directives from FILE
  -S, --src-specials       enable insertion of source specials
  -s, --short              display errors in a compact form
  -I, --texpath=DIR        add DIR to the search path for LaTeX
  -v, --verbose            increase verbosity
      --version            print version information and exit\
""") % version

	def parse_opts (self, cmdline):
		args = rubber.cmdline.Main.parse_opts(self, cmdline)
		if len(args) > 0:
			msg.warn(_("the following options were ignored: %s")
				% string.join(args, " "))
				
	def main (self, cmdline):
		"""
		Run Rubber as a pipe for the specified command line. This dumps the
		standard input into a temporary file, compiles it, dumps the result on
		standard output, and then removes the files if requested. If an error
		happens while building the document, the process stops. The method
		returns the program's exit code.
		"""
		self.prologue = []
		self.epilogue = []
		self.clean = 1
		self.place = "."
		self.path = []
		self.parse_opts(cmdline)
		msg.log(_("This is Rubber version %s.") % version)

		# Put the standard input in a file

		initial_dir = os.getcwd()

		if self.place is not None and self.place != ".":
			self.path.insert(0, initial_dir)
			os.chdir(self.place)

		src = make_name() + ".tex"
		try:
			srcfile = open(src, 'w')
		except IOError:
			msg.error(_("cannot create temporary files"))
			return 1

		msg.progress(_("saving the input in %s") % src)
		dump_file(sys.stdin, srcfile)
		srcfile.close()

		# Make the document

		env = Environment()
		env.vars["cwd"] = initial_dir

		if env.set_source(src):
			msg.error(_("cannot open the temporary %s") % src)
			return 1

		if self.include_only is not None:
			env.main.includeonly(self.include_only)

		env.make_source()

		for dir in self.path:
			env.main.do_path(dir)
		for cmd in self.prologue:
			cmd = parse_line(cmd, {})
			env.main.command(cmd[0], cmd[1:], {'file': 'command line'})

		env.main.parse()

		for cmd in self.epilogue:
			cmd = parse_line(cmd, {})
			env.main.command(cmd[0], cmd[1:], {'file': 'command line'})

		ret = env.final.make()

		if ret == ERROR:
			msg.info(_("There were errors."))
			number = self.max_errors
			for err in env.final.failed().get_errors():
				if number == 0:
					msg.info(_("More errors."))
					break
				msg.display(**err)
				number -= 1
			return 1


		# Dump the results on standard output

		output = open(env.final.products[0])
		dump_file(output, sys.stdout)

		# Clean the intermediate files

		if self.clean:
			env.final.clean()
			os.unlink(src)
		return 0

	def __call__ (self, cmdline):
		try:
			return self.main(cmdline)
		except KeyboardInterrupt:
			msg(0, _("*** interrupted"))
			return 2
