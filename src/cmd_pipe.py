# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2003--2004
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
		"""
		Create the object used for message output.
		"""
		self.msg = rubber.cmdline.Message(level=-1)

	def help (self):
		"""
		Display the description of all the options and exit.
		"""
		self.msg (0, _("""\
This is Rubber version %s.
usage: rubber-pipe [options]
available options:
  -c, --command=CMD        run the directive CMD before parsing (see man page)
  -e, --epilogue=CMD       run the directive CMD after parsing
  -z, --gzip               compress the final document
  -h, --help               display this help
  -k, --keep               keep the temporary files after compiling
  -l, --landscape          change paper orientation (if relevant)
  -m, --module=MOD[:OPTS]  use module MOD (with options OPTS)
  -o, --post=MOD[:OPTS]    postprocess with module MOD (with options OPTS)
  -d, --pdf                compile with pdftex (synonym for -m pdftex)
  -p, --ps                 process through dvips (synonym for -m dvips)
  -q, --quiet              suppress messages
  -r, --read=FILE          read additional directives from FILE
  -s, --short              display errors in a compact form
  -I, --texpath=DIR        add DIR to the search path for LaTeX
  -v, --verbose            increase verbosity
      --version            print version information and exit\
""") % version)

	def parse_opts (self, cmdline):
		args = rubber.cmdline.Main.parse_opts(self, cmdline)
		if len(args) > 0:
			self.msg(0, _("warning: the following options were ignored: %s")
				% string.join(args, " "))
				
	def main (self, cmdline):
		"""
		Run Rubber as a pipe for the specified command line. This dumps the
		standard input into a temporary file, compiles it, dumps the result on
		standard output, and then removes the files if requested. If an error
		happens while building the document, the process stops.  The method
		returns the program's exit code.
		"""
		self.prologue = []
		self.epilogue = []
		self.clean = 1
		self.parse_opts(cmdline)
		self.msg(2, _("This is Rubber version %s.") % version)

		# Put the standard input in a file

		src = make_name() + ".tex"
		try:
			srcfile = open(src, 'w')
		except IOError:
			self.msg(0, _("cannot create temporary files"))
			return 1

		self.msg(1, _("saving the input in %s...") % src)
		dump_file(sys.stdin, srcfile)
		srcfile.close()

		# Make the document

		env = Environment(self.msg)

		if env.set_source(src):
			sys.exit(1)

		for cmd in self.prologue:
			cmd = string.split(cmd, maxsplit = 1)
			if len(cmd) == 1:
				cmd.append("")
			env.command(cmd[0], cmd[1], {'file': 'command line'})

		env.make_source()
		env.parse()

		for cmd in self.epilogue:
			cmd = string.split(cmd, maxsplit = 1)
			if len(cmd) == 1:
				cmd.append("")
			env.command(cmd[0], cmd[1], {'file': 'command line'})

		ret = env.final.make()

		if ret == 0:
			if not self.msg.short:
				self.msg(1, _("There were errors."))
			env.final.failed().show_errors()
			return 1

		# Dump the results on standard output

		output = open(env.final.prods[0])
		dump_file(output, sys.stdout)

		# Clean the intermediate files

		if self.clean:
			env.clean(1)
			os.unlink(src)
		return 0

	def __call__ (self, cmdline):
		try:
			return self.main(cmdline)
		except KeyboardInterrupt:
			self.msg(0, _("*** interrupted"))
			return 2
