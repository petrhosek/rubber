# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2003
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

class MessageErr (Message):
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
		self.msg = MessageErr()

	def short_help (self):
		"""
		Display a short description of the command line.
		"""
		self.msg (0, _("""\
usage: rubber-pipe [options]
For more information, try `rubber-pipe --help'."""))

	def help (self):
		"""
		Display the description of all the options and exit.
		"""
		self.msg (0, _("""\
This is Rubber version %s.
usage: rubber-pipe [options]
available options:
  -c / --command <cmd> = run the specified command
                   (see man page section "Directives" for details)
  -h / --help    = display this help
  -k / --keep    = keep the temporary files after compiling
  -l / --landscape = change paper orientation (if relevant)
  -m / --module <mod>[:<options>] =
                   use a specific module (with the given options)
  -d / --pdf     = produce PDF output instead of DVI (synonym for -m pdftex)
  -p / --ps      = produce a PostScript document (synonym for -m dvips)
  -q / --quiet   = suppress messages
  -s / --short   = display errors in a compact form
  -r / --read <file> =
                   read additional directives from a file
  -v / --verbose = increase verbosity
       --version = print version information and exit\
""") % version)

	def parse_opts (self, cmdline):
		try:
			opts, args = getopt(
				cmdline, "c:dfhklm:pqr:sv",
				["command=", "help", "keep", "landcape", "module=",
				 "pdf", "ps", "quiet", "read=", "short", "verbose", "version"])
		except GetoptError, e:
			print e
			sys.exit(1)

		for (opt,arg) in opts:
			if opt in ("-c", "--command"):
				self.commands.append(arg)
			elif opt in ("-h", "--help"):
				self.help()
				sys.exit(0)
			elif opt in ("-k", "--keep"):
				self.clean = 0
			elif opt in ("-l", "--landscape"):
				self.commands.append("paper landscape")
			elif opt in ("-m", "--module"):
				self.commands.append("module " +
					string.replace(arg, ":", " ", 1))
			elif opt in ("-d", "--pdf"):
				self.commands.append("module pdftex")
			elif opt in ("-p", "--ps"):
				self.commands.append("module dvips")
			elif opt in ("-q", "--quiet"):
				self.msg.level = -1
			elif opt in ("-s", "--short"):
				self.msg.short = 1
			elif opt in ("-r" ,"--read"):
				self.commands.append("read " + arg)
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
		self.env = Environment(self.msg)
		env = self.env
		self.commands = []
		self.clean = 1
		self.parse_opts(cmdline)
		self.msg(2, _("This is Rubber version %s.") % version)
		first = 1

		src = make_name() + ".tex"
		try:
			srcfile = open(src, 'w')
		except IOError:
			self.msg(0, _("cannot create temporary files"))
			return 1

		self.msg(1, _("saving the input in %s...") % src)
		dump_file(sys.stdin, srcfile)
		srcfile.close()

		self.prepare(src)
		error = env.make()
		if error:
			self.msg(-1, _("There were errors."))
			if error == 1:
				env.log.show_errors()
			return error

		output = open(env.final_file)
		dump_file(output, sys.stdout)

		if self.clean:
			env.clean()
			os.unlink(src)
		return 0
