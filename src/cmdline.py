# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2004
"""
This is the command line interface for Rubber.
"""

import sys
import os.path
import string
from getopt import *

from rubber import _
from rubber import *
from rubber.version import *

class Message (Message):
	"""
	This class defines a message writer that outputs the messages according to
	GNU conventions. It manages verbosity level and possible redirection.
	"""
	def __init__ (self, level=0, short=0):
		"""
		Initialize the object with the specified verbosity threshold. The
		other argument is a boolean that indicates whether error messages
		should be short or normal.
		"""
		self.level = level
		self.short = short
		self.write = self.do_write

	def do_write (self, level, text):
		if level <= self.level:
			print text

	def __call__ (self, level, text):
		self.write(level, text)

	def error (self, file, line, text, code):
		file = simplify_path(file)

		if line:
			prefix = "%s:%d: " % (file, line)
		else:
			prefix = file + ": "

		if text[0:13] == "LaTeX Error: ":
			text = text[13:]

		self.write(-1, prefix + text)
		if code and not self.short:
			self.write(-1, prefix + _("leading text: ") + code)

	def abort (self, what, why):
		if self.short:
			self.write(0, _("compilation aborted ") + why)
		else:
			self.write(0, _("compilation aborted: %s %s") % (what, why))

	def info (self, where, what):
		if where.has_key("file"):
			text = simplify_path(where["file"])
			if where.has_key("line"):
				text = "%s:%d" % (text, where["line"])
				if where.has_key("last"):
					if where["last"] != where["line"]:
						text = "%s-%d" % (text, where["last"])
		else:
			text = _("(nowhere)")
		text = "%s: %s" % (text, what)
		if where.has_key("page"):
			text = "%s (page %d)" % (text, where["page"])
		self.write(0, text)

class Main (object):
	def __init__ (self):
		"""
		Create the object used for message output.
		"""
		self.msg = Message()

	def short_help (self):
		"""
		Display a short description of the command line.
		"""
		self.msg (0, _("""\
usage: rubber [options] sources...
For more information, try `rubber --help'."""))

	def help (self):
		"""
		Display the description of all the options and exit.
		"""
		self.msg (0, _("""\
This is Rubber version %s.
usage: rubber [options] sources...
available options:
      --clean              remove produced files instead of compiling
  -c, --command=CMD        run the directive CMD before parsing (see man page)
  -e, --epilogue=CMD       run the directive CMD after parsing
  -f, --force              force at least one compilation
  -z, --gzip               compress the final document
  -h, --help               display this help
  -l, --landscape          change paper orientation (if relevant)
  -m, --module=MOD[:OPTS]  use module MOD (with options OPTS)
  -o, --post=MOD[:OPTS]    postprocess with module MOD (with options OPTS)
  -d, --pdf                compile with pdftex (synonym for -m pdftex)
  -p, --ps                 process through dvips (synonym for -o dvips)
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
				cmdline, "I:c:de:fhklm:o:pqr:svz",
				["clean", "command=", "epilogue=", "force", "gzip", "help",
				 "keep", "landcape", "module=", "post=", "pdf", "ps", "quiet",
				 "read=", "short", "texpath=", "verbose", "version"])
		except GetoptError, e:
			print e
			sys.exit(1)

		for (opt,arg) in opts:
			if opt == "--clean":
				self.clean = 1
			elif opt in ("-c", "--command"):
				self.prologue.append(arg)
			elif opt in ("-e", "--epilogue"):
				self.epilogue.append(arg)
			elif opt in ("-f", "--force"):
				self.force = 1
			elif opt in ("-z", "--gzip"):
				self.epilogue.append("module gz")
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
			elif opt in ("-o", "--post"):
				self.epilogue.append("module " +
					string.replace(arg, ":", " ", 1))
			elif opt in ("-d", "--pdf"):
				self.prologue.append("module pdftex")
			elif opt in ("-p", "--ps"):
				self.epilogue.append("module dvips")
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
				print "Rubber version: " + version
				print "module path: " + moddir
				sys.exit(0)

		return args

	def main (self, cmdline):
		"""
		Run Rubber for the specified command line. This processes each
		specified source in order (for making or cleaning). If an error
		happens while making one of the documents, the whole process stops.
		The method returns the program's exit code.
		"""
		self.prologue = []
		self.epilogue = []
		self.clean = 0
		self.force = 0
		args = self.parse_opts(cmdline)
		self.msg(2, _("This is Rubber version %s.") % version)

		for src in args:
			env = Environment(self.msg)

			# Check the source and prepare it for processing
	
			if env.set_source(src):
				sys.exit(1)

			for cmd in self.prologue:
				cmd = string.split(cmd, maxsplit = 1)
				if len(cmd) == 1:
					cmd.append("")
				env.command(cmd[0], cmd[1], {'file': 'command line'})

			if self.clean:
				if not os.path.exists(env.source()):
					self.msg(1, _("there is no LaTeX source"))
					continue

			env.make_source()
			env.parse()

			for cmd in self.epilogue:
				cmd = string.split(cmd, maxsplit = 1)
				if len(cmd) == 1:
					cmd.append("")
				env.command(cmd[0], cmd[1], {'file': 'command line'})

			# Compile the document

			if self.clean:
				env.parse()
				env.clean(1)
			else:
				if self.force:
					ret = env.make(1)
					if ret != 0:
						ret = env.final.make()
				else:
					ret = env.final.make(self.force)

				if ret == 1:
					self.msg(0, _("nothing to be done for %s") % env.source())
				elif ret == 0:
					if not self.msg.short:
						self.msg(-1, _("There were errors compiling %s.")
							% env.source())
					env.log.show_errors()
					return 1

		return 0

	def __call__ (self, cmdline):
		"""
		This method is a wrapper around the main method, showing a short help
		message when the command line is empty, and catching the keyboard
		interruption signal.
		"""
		if cmdline == []:
			self.short_help()
			return 1
		try:
			return self.main(cmdline)
		except KeyboardInterrupt:
			self.msg(0, _("*** interrupted"))
			return 2
