# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2006
"""
This is the command line interface for Rubber.
"""

import sys
import os.path
import string
from getopt import *

from rubber import _, msg
from rubber import *
from rubber.version import *
from rubber.depend import ERROR, CHANGED, UNCHANGED
from rubber.util import parse_line

class Main (object):
	def __init__ (self):
		self.max_errors = 10
		self.include_only = None
		self.path = []
		self.compress = None
		msg.write = self.stderr_write

	def stderr_write (self, text, level=0):
		sys.stderr.write(text + "\n")

	def short_help (self):
		"""
		Display a short description of the command line.
		"""
		msg(0, _("""\
usage: rubber [options] sources...
For more information, try `rubber --help'."""))

	def help (self):
		"""
		Display the description of all the options and exit.
		"""
		print _("""\
This is Rubber version %s.
usage: rubber [options] sources...
available options:
  -b, --bzip2              compress the final document with bzip2
      --cache              use the (experimental) caching mechanism
      --clean              remove produced files instead of compiling
  -c, --command=CMD        run the directive CMD before parsing (see man page)
  -e, --epilogue=CMD       run the directive CMD after parsing
  -f, --force              force at least one compilation
  -z, --gzip               compress the final document
  -h, --help               display this help
      --inplace            compile the documents from their source directory
      --into=DIR           go to directory DIR before compiling
      --jobname=NAME       set the job name for the first target
  -l, --landscape          change paper orientation (if relevant)
  -n, --maxerr=NUM         display at most NUM errors (default: 10)
  -m, --module=MOD[:OPTS]  use module MOD (with options OPTS)
      --only=SOURCES       only include the specified SOURCES
  -o, --post=MOD[:OPTS]    postprocess with module MOD (with options OPTS)
  -d, --pdf                produce a pdf (synonym for -m pdftex or -o ps2pdf)
  -p, --ps                 process through dvips (synonym for -o dvips)
  -q, --quiet              suppress messages
  -r, --read=FILE          read additional directives from FILE
  -S, --src-specials       enable insertion of source specials
  -s, --short              display errors in a compact form
  -I, --texpath=DIR        add DIR to the search path for LaTeX
  -v, --verbose            increase verbosity
      --version            print version information and exit
  -W, --warn=TYPE          report warnings of the given TYPE (see man page)\
""") % version

	def parse_opts (self, cmdline, short="", long=[]):
		try:
			opts, args = getopt(
				cmdline, "I:bc:de:fhklm:n:o:pqr:SsvW:z" + short,
				["bzip2", "cache", "clean", "command=", "epilogue=", "force", "gzip",
				 "help", "inplace", "into=", "jobname=", "keep", "landcape", "maxerr=",
				 "module=", "only=", "post=", "pdf", "ps", "quiet", "read=",
				 "src-sepcials", "short", "texpath=", "verbose", "version", "warn="] + long)
		except GetoptError, e:
			print e
			sys.exit(1)

		extra = []
		using_dvips = 0

		for (opt,arg) in opts:
			if opt in ("-b", "--bzip2"):
				if self.compress is not None and self.compress != "bzip2":
					msg.warn(_("warning: ignoring option %s") % opt)
				else:
					self.compress = "bzip2"
			elif opt == "--cache":
				print 'warning: cache is currently disabled'
			elif opt == "--clean":
				self.clean = 1
			elif opt in ("-c", "--command"):
				self.prologue.append(arg)
			elif opt in ("-e", "--epilogue"):
				self.epilogue.append(arg)
			elif opt in ("-f", "--force"):
				self.force = 1
			elif opt in ("-z", "--gzip"):
				if self.compress is not None and self.compress != "gz":
					msg.warn(_("warning: ignoring option %s") % opt)
				else:
					self.compress = "gzip"
			elif opt in ("-h", "--help"):
				self.help()
				sys.exit(0)
			elif opt == "--inplace":
				self.place = None
			elif opt == "--into":
				self.place = arg
			elif opt == "--jobname":
				self.jobname = arg
			elif opt in ("-k", "--keep"):
				self.clean = 0
			elif opt in ("-l", "--landscape"):
				self.prologue.append("paper landscape")
			elif opt in ("-n", "--maxerr"):
				self.max_errors = int(arg)
			elif opt in ("-m", "--module"):
				self.prologue.append("module " +
					string.replace(arg, ":", " ", 1))
			elif opt == "--only":
				self.include_only = arg.split(",")
			elif opt in ("-o", "--post"):
				self.epilogue.append("module " +
					string.replace(arg, ":", " ", 1))
			elif opt in ("-d", "--pdf"):
				if using_dvips:
					self.epilogue.append("module ps2pdf")
				else:
					self.prologue.append("module pdftex")
			elif opt in ("-p", "--ps"):
				self.epilogue.append("module dvips")
				using_dvips = 1
			elif opt in ("-q", "--quiet"):
				msg.level = msg.level - 1
			elif opt in ("-r" ,"--read"):
				self.prologue.append("read " + arg)
			elif opt in ("-S", "--src-specials"):
				self.prologue.append("set src-specials yes")
			elif opt in ("-s", "--short"):
				msg.short = 1
			elif opt in ("-I", "--texpath"):
				self.path.append(arg)
			elif opt in ("-v", "--verbose"):
				msg.level = msg.level + 1
			elif opt == "--version":
				print "Rubber version: " + version
				print "module path: " + moddir
				sys.exit(0)
			elif opt in ("-W", "--warn"):
				self.warn = 1
				if arg == "all":
					self.warn_boxes = 1
					self.warn_misc = 1
					self.warn_refs = 1
				if arg == "boxes":
					self.warn_boxes = 1
				elif arg == "misc":
					self.warn_misc = 1
				elif arg == "refs":
					self.warn_refs = 1

			elif arg == "":
				extra.append(opt)
			else:
				extra.extend([arg, opt])

		return extra + args

	def main (self, cmdline):
		"""
		Run Rubber for the specified command line. This processes each
		specified source in order (for making or cleaning). If an error
		happens while making one of the documents, the whole process stops.
		The method returns the program's exit code.
		"""
		self.jobname = None
		self.prologue = []
		self.epilogue = []
		self.clean = 0
		self.force = 0

		self.warn = 0
		self.warn_boxes = 0
		self.warn_misc = 0
		self.warn_refs = 0

		self.place = "."

		args = self.parse_opts(cmdline)

		initial_dir = os.getcwd()
		msg.cwd = os.path.join(initial_dir, "")

		if self.place != "." and self.place is not None:
			msg.path = self.place
			self.place = os.path.abspath(self.place)

		msg.log(_("This is Rubber version %s.") % version)

		for srcname in args:
			src = os.path.abspath(os.path.join(initial_dir, srcname))

			# Go to the appropriate directory

			if self.place != ".":
				if self.place is None:
					msg.path = os.path.dirname(src)
					os.chdir(os.path.dirname(src))
					src = os.path.basename(src)
				else:
					os.chdir(self.place)

			# Check the source and prepare it for processing
	
			env = Environment()

			if env.set_source(src, jobname=self.jobname):
				return 1
			self.jobname = None

			if self.include_only is not None:
				env.main.includeonly(self.include_only)

			if self.clean:
				if env.main.products == []:
					msg.warn(_("there is no LaTeX source for %s") % srcname)
					continue
			else:
				env.make_source()

			saved_vars = env.main.vars
			env.main.vars = Variables(saved_vars, { "cwd": initial_dir })
			for dir in self.path:
				env.main.do_path(dir)
			for cmd in self.prologue:
				cmd = parse_line(cmd, env.main.vars)
				env.main.command(cmd[0], cmd[1:], {'file': 'command line'})
			env.main.vars = saved_vars

			env.main.parse()

			saved_vars = env.main.vars
			env.main.vars = Variables(saved_vars, { "cwd": initial_dir })
			for cmd in self.epilogue:
				cmd = parse_line(cmd, env.main.vars)
				env.main.command(cmd[0], cmd[1:], {'file': 'command line'})
			env.main.vars = saved_vars

			if self.compress is not None:
				last_node = env.final
				filename = last_node.products[0]
				if self.compress == 'gzip':
					from rubber.converters.gz import GzipDep
					env.final = GzipDep(env.depends,
							filename + '.gz', filename)
				elif self.compress == 'bzip2':
					from rubber.converters.bzip2 import Bzip2Dep
					env.final = Bzip2Dep(env.depends,
							filename + '.bz2', filename)

			# Compile the document

			if self.clean:
				env.final.clean()
				continue

			if self.force:
				ret = env.main.make(True)
				if ret != ERROR and env.final is not env.main:
					ret = env.final.make()
				else:
					# This is a hack for the call to get_errors() below
					# to work when compiling failed when using -f.
					env.final.failed_dep = env.main.failed_dep
			else:
				ret = env.final.make(self.force)

			if ret == ERROR:
				msg.info(_("There were errors compiling %s.") % srcname)
				number = self.max_errors
				for err in env.final.failed().get_errors():
					if number == 0:
						msg.info(_("More errors."))
						break
					msg.display(**err)
					number -= 1
				return 1

			if ret == UNCHANGED:
				msg(1, _("nothing to be done for %s") % srcname)

			if self.warn:
				log = env.main.log
				if log.read(env.main.target + ".log"):
					msg.error(_("cannot read the log file"))
					return 1
				msg.display_all(log.parse(boxes=self.warn_boxes,
					refs=self.warn_refs, warnings=self.warn_misc))

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
			msg(0, _("*** interrupted"))
			return 2
