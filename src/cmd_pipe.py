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

class MessageErr (rubber.cmdline.Message):
	"""
	This class modifies the standard Message class to make it write messages
	on standard error instead of standard output.
	"""
	def do_write (self, level, text):
		if level <= self.level:
			sys.stderr.write(text + "\n")

class Main (rubber.cmdline.Main):
	def __init__ (self):
		"""
		Create the object used for message output.
		"""
		self.msg = MessageErr(level=-1)

	def help (self):
		"""
		Display the description of all the options and exit.
		"""
		self.msg (-1, _("""\
This is Rubber version %s.
usage: rubber-pipe [options]
available options:
  -c, --command=CMD        run the directive CMD before parsing (see man page)
  -e, --epilogue=CMD       run the directive CMD after parsing
  -h, --help               display this help
  -k, --keep               keep the temporary files after compiling
  -l, --landscape          change paper orientation (if relevant)
  -m, --module=MOD[:OPTS]  use module MOD (with options OPTS)
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
		try:
			opts, args = getopt(
				cmdline, "I:c:de:fhklm:pqr:svz",
				["command=", "epilogue=", "gzip", "help", "keep", "landcape",
				 "module=", "pdf", "ps", "quiet", "read=", "short",
				 "texpath=", "verbose", "version"])
		except GetoptError, e:
			print e
			sys.exit(1)

		for (opt,arg) in opts:
			if opt in ("-c", "--command"):
				self.prologue.append(arg)
			elif opt in ("-e", "--epilogue"):
				self.epilogue.append(arg)
			elif opt in ("-h", "--help"):
				self.help()
				sys.exit(0)
			elif opt in ("-k", "--keep"):
				self.clean = 0
			elif opt in ("-l", "--landscape"):
				self.prologue.append("paper landscape")
			elif opt in ("-m", "--module"):
				self.prologue.append("module " +
					string.replace(arg, ":", " ", 1))
			elif opt in ("-d", "--pdf"):
				self.prologue.append("module pdftex")
			elif opt in ("-p", "--ps"):
				self.prologue.append("module dvips")
			elif opt in ("-q", "--quiet"):
				self.msg.level = -1
			elif opt in ("-r" ,"--read"):
				self.prologue.append("read " + arg)
			elif opt in ("-s", "--short"):
				self.msg.short = 1
			elif opt in ("-I", "--texpath"):
				self.prologue.append("path " + arg)
			elif opt in ("-v", "--verbose"):
				self.msg.level = self.msg.level + 1
			elif opt == "--version":
				print version
				sys.exit(0)

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
				self.msg(-1, _("There were errors."))
			env.log.show_errors()
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
