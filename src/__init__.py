# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2004
"""
LaTeX document building system for Rubber.

This module contains all the code in Rubber that actually does the job of
building a LaTeX document from start to finish.
"""

import os, sys, posix
from os.path import *
import re
import string

# The function `_' is defined here to prepare for internationalization.
def _ (txt): return txt

from rubber.util import *
import rubber.modules

#---------------------------------------

class Config (object):
	"""
	This class contains all configuration parameters. This includes search
	paths, the name of the compiler and options for it, and paper size
	options.
	"""
	def __init__ (self):
		"""
		Initialize the configuration with default settings.
		"""
		self.path = [""]
		self.latex = "latex"
		self.cmdline = ["\\nonstopmode\\input{%s}"]
		self.tex = "TeX"
		self.loghead = re.compile("This is [0-9a-zA-Z-]*(TeX|Omega)")
		self.paper = []

	def find_input (self, name):
		"""
		Look for a source file with the given name, and return either the
		complete path to the actual file or None if the file is not found.
		"""
		for path in self.path:
			test = join(path, name)
			if exists(test + ".tex") and isfile(test + ".tex"):
				return test + ".tex"
			elif exists(test) and isfile(test):
				return test
		return None

	def compile_cmd (self, file):
		"""
		Return the the command that should be used to compile the specified
		file, in the form of a pair. The first member is the list of
		command-line arguments, and the second one is a dictionary of
		environment variables to define.
		"""
		cmd = [self.latex] + map(lambda x: x.replace("%s",file), self.cmdline)
		inputs = string.join(self.path, ":")
		if inputs == "":
			return (cmd, {})
		else:
			inputs = inputs + ":" + os.getenv("TEXINPUTS", "")
			return (cmd, {"TEXINPUTS": inputs})

#---------------------------------------

class Modules (Plugins):
	"""
	This class gathers all operations related to the management of modules.
	The modules are	searched for first in the current directory, then in the
	package `rubber.modules'.
	"""
	def __init__ (self, env):
		Plugins.__init__(self, rubber.modules.__path__)
		self.env = env
		self.objects = {}
		self.commands = {}

	def __getitem__ (self, name):
		"""
		Return the module object of the given name.
		"""
		return self.objects[name]

	def has_key (self, name):
		"""
		Check if a given module is loaded.
		"""
		return self.objects.has_key(name)

	def register (self, name, dict={}):
		"""
		Attempt to register a package with the specified name. If a module is
		found, create an object from the module's class called `Module',
		passing it the environment and `dict' as arguments, and execute all
		delayed commands for this module. The dictionary describes the
		command that caused the registration.
		"""
		r = Plugins.register(self, name)
		if r == 0:
			self.env.msg(3, _("no support found for %s") % name)
			return 0
		elif r == 2:
			self.env.msg(3, _("module %s already registered") % name)
			return 2
		mod = self.modules[name].Module(self.env, dict)
		self.env.msg(2, _("module %s registered") % name)

		if self.commands.has_key(name):
			for (cmd,arg) in self.commands[name]:
				mod.command(cmd, arg)
			del self.commands[name]

		self.objects[name] = mod
		return 1

	def clear (self):
		"""
		Unregister all modules.
		"""
		Plugins.clear(self)
		self.objects = {}
		self.commands = {}

	def command (self, mod, cmd, arg):
		"""
		Send a command to a particular module. If this module is not loaded,
		store the command so that it will be sent when the module is register.
		"""
		if self.objects.has_key(mod):
			self.objects[mod].command(cmd, arg)
		else:
			if not self.commands.has_key(mod):
				self.commands[mod] = []
			self.commands[mod].append((cmd,arg))

#---------------------------------------

re_rerun = re.compile("LaTeX Warning:.*Rerun")
re_file = re.compile("(\\((?P<file>[^ \n\t(){}]*)|\\))")
re_badbox = re.compile(r"(Ov|Und)erfull \\[hv]box ")
re_line = re.compile(r"l\.(?P<line>[0-9]+)( (?P<text>.*))?$")

class LogCheck (object):
	"""
	This class performs all the extraction of information from the log file.
	For efficiency, the instances contain the whole file as a list of strings
	so that it can be read several times with no disk access.
	"""
	def __init__ (self, env):
		self.env = env
		self.msg = env.msg
		self.lines = None

	def read (self, name):
		"""
		Read the specified log file, checking that it was produced by the
		right compiler. Returns true if the log file is invalid or does not
		exist.
		"""
		self.lines = None
		try:
			file = open(name)
		except IOError:
			return 2
		line = file.readline()
		if not line:
			file.close()
			return 1
		if not self.env.conf.loghead.match(line):
			file.close()
			return 1
		self.lines = file.readlines()
		file.close()
		return 0

	# checkings:

	def errors (self):
		"""
		Returns true if there was an error during the compilation.
		"""
		for line in self.lines:
			if line[0] == "!":
				# We check for the substring "pdfTeX warning" because pdfTeX
				# sometimes issues warnings (like undefined references) in the
				# form of errors...

				if string.find(line, "pdfTeX warning") == -1:
					return 1
		return 0

	def run_needed (self):
		"""
		Returns true if LaTeX indicated that another compilation is needed.
		"""
		for line in self.lines:
			if re_rerun.match(line):
				return 1
		return 0

	# information extraction:

	def update_file (self, line, stack):
		"""
		Parse the given line of log file for file openings and closings and
		update the list `stack'. Newly opened files are at the end, therefore
		stack[1] is the main source while stack[-1] is the current one. The
		first element, stack[0], contains the string \"(no file)\" for errors
		that may happen outside the source.
		"""
		m = re_file.search(line)
		if not m:
			return
		while m:
			if line[m.start()] == '(':
				stack.append(m.group("file"))
			else:
				del stack[-1]
			line = line[m.end():]
			m = re_file.search(line)

	def show_errors (self):
		"""
		Display all errors that occured during compilation. Return 0 if there
		was no error. If not log file was produced (that can happen if LaTeX
		could not be run), report nothing and return 1.
		"""
		if not self.lines:
			return 1
		pos = ["(no file)"]
		last_file = None
		parsing = 0    # 1 if we are parsing an error's text
		skipping = 0   # 1 if we are skipping text until an empty line
		something = 0  # 1 if some error was found
		for line in self.lines:
			line = line.rstrip()
			if line == "":
				skipping = 0
			elif skipping:
				pass
			elif parsing:
				m = re_line.match(line)
				if m:
					parsing = 0
					skipping = 1
					self.msg.error(pos[-1], int(m.group("line")),
						error, m.group("text"))
				elif line[0:3] == "***":
					parsing = 0
					skipping = 1
					self.msg.abort(error, line[4:])
			elif line[0] == "!":
				error = line[2:]
				parsing = 1
				something = 1
			else:
				# Here there is no error to show, so we use the text of the
				# line to track the source file name. However, there might be
				# confusing text in the log file, in particular when there is
				# an overfull/underfull box message (the text following this
				# is extracted from the source, and the extract may contain
				# unbalanced parentheses). Therefore we take care of this
				# specifically.

				m = re_badbox.match(line)
				if m:
					skipping = 1
				else:
					self.update_file(line, pos)

		return something

#---------------------------------------

re_comment = re.compile(r"(?P<line>([^\\%]|\\%|\\)*)(%.*)?")
re_command = re.compile("[% ]*(rubber: *(?P<cmd>[^ ]*) *(?P<arg>.*))?.*")
re_input = re.compile("\\\\input +(?P<arg>[^{} \n\\\\]+)")
re_kpse = re.compile("kpathsea: Running (?P<cmd>[^ ]*).* (?P<arg>[^ ]*)$")

class EndDocument:
	""" This is the exception raised when \\end{document} is found. """
	pass

class EndInput:
	""" This is the exception raised when \\endinput is found. """
	pass

class Environment (Depend):
	"""
	This class represents the building process for the document. It handles
	the execution of all required programs. The steps are the following:
	  1. building of the LaTeX source (e.g. when using CWEB)
	  2. preparation of external dependencies (e.g. compilation of figures)
	  3. cyclic LaTeX compilation until a stable output, including:
	     a. actual compilation (with a parametrable executable)
	     b. possible processing of compilation results (e.g. running BibTeX)
	  4. processing of the final output (e.g. dvips)
	The class also handles the cleaning mechanism.

	Before building (or cleaning) the document, the method `parse' must be
	called to load and configure all required modules. Text lines are read
	from the files and parsed to extract LaTeX macro calls. When such a macro
	is found, a handler is searched for in the `hooks' dictionary. Handlers
	are called with one argument: the dictionary for the regular expression
	that matches the macro call.
	"""
	def __init__ (self, message):
		"""
		Initialize the environment. This prepares the processing steps for the
		given file (all steps are initialized empty) and sets the regular
		expressions and the hook dictionary.
		"""
		Depend.__init__(self, [], {}, message)
		self.msg(2, _("initializing Rubber..."))

		self.log = LogCheck(self)
		self.modules = Modules(self)

		# (a priori) static dictionaries:

		self.source_exts = {
			".w" : "cweb",
			".lhs" : "lhs2TeX" }

		self.kpse_msg = {
			"mktextfm" : _("making font metrics for \\g<arg>..."),
			"mktexmf" : _("making font \\g<arg>..."),
			"mktexpk" : _("making bitmap for font \\g<arg>...")
			}

		self.initialize()

	def restart (self):
		"""
		Reinitialize the environment, in order to process a new document. This
		resets the process and the hook dictionary and unloads modules.
		"""
		self.msg(1, _("reinitializing..."))
		self.modules.clear()
		self.initialize()

	def initialize (self):
		"""
		This is the method that actually does the initialization. It is also
		used when restarting the process.
		"""
		self.conf = Config()

		# the initial hooks:

		self.hooks = {
			"input" : self.h_input,
			"include" : self.h_include,
			"includeonly": self.h_includeonly,
			"usepackage" : self.h_usepackage,
			"RequirePackage" : self.h_usepackage,
			"documentclass" : self.h_documentclass,
			"tableofcontents" : self.h_tableofcontents,
			"listoffigures" : self.h_listoffigures,
			"listoftables" : self.h_listoftables,
			"bibliography" : self.h_bibliography,
			"bibliographystyle" : self.h_bibliographystyle,
			"endinput" : self.h_endinput,
			"end{document}" : self.h_end_document
		}
		self.update_seq()

		self.include_only = {}

		self.convert = Converter({}, self.modules)

		# description of the building process:

		self.source_building = None
		self.final = self
		self.watched_files = {}
		self.onchange_md5 = {}
		self.onchange_cmd = {}
		self.removed_files = []

		# state of the builder:

		self.processed_sources = {}

		self.must_compile = 0
		self.something_done = 0

		self.msg(3, _("ready"))

	#
	# The following methods are related to LaTeX source parsing.
	#

	def parse (self):
		"""
		Parse the source for packages and supported macros.
		"""
		try:
			self.process(self.source())
		except EndDocument:
			pass
		self.set_date()
		self.msg(2, _("dependencies: %r") % self.sources.keys())

	def do_process (self, file, path, dump=None):
		"""
		Process a LaTeX source. The file must be open, it is read to the end
		calling the handlers for the macro calls. This recursively processes
		the included sources.

		If the optional argument 'dump' is not None, then it is considered as
		a stream on which all text not matched as a macro is written.
		"""
		lines = file.readlines()
		lineno = 0

		# If a line ends with braces open, we read on until we get a correctly
		# braced text. We also stop accumulating on paragraph breaks, the way
		# non-\long macros do in TeX.

		brace_level = 0
		accu = ""

		for line in lines:
			lineno = lineno + 1

			# Lines that start with a comment are the ones where directives
			# may be found.

			if line[0] == "%":
				m = re_command.match(string.rstrip(line))
				if m.group("cmd"):
					self.command(m.group("cmd"), m.group("arg"),
						{ 'file' : path, 'line' : lineno } )
				continue

			# Otherwise we accumulate lines (with comments stripped) until
			# bracing is correct.

			line = re_comment.match(line).group("line")
			if accu != "" and accu[-1] != '\n':
				line = string.lstrip(line)
			brace_level = brace_level + count_braces(line)

			if brace_level <= 0 or string.strip(line) == "":
				brace_level = 0
				line = accu + line
				accu = ""
			else:
				accu = accu + line
				continue

			# Then we check for supported macros in the text.

			match = self.seq.search(line)
			while match:
				dict = match.groupdict()
				name = dict["name"]
				
				# The case of \input is handled specifically, because of the
				# TeX syntax with no braces

				if name == "input" and not dict["arg"]:
					match2 = re_input.search(line)
					if match2:
						match = match2
						dict = match.groupdict()

				if dump: dump.write(line[:match.start()])
				dict["match"] = line[match.start():match.end()]
				dict["line"] = line[match.end():]
				dict["pos"] = { 'file': path, 'line': lineno }
				dict["dump"] = dump
				self.hooks[name](dict)
				line = dict["line"]
				match = self.seq.search(line)

			if dump: dump.write(line)

	def command (self, cmd, arg, pos={}):
		"""
		Execute the rubber command 'cmd' with argument 'arg'. This is called
		when a command is found in the source file or in a configuration file.
		A command name of the form 'foo.bar' is considered to be a command
		'bar' for module 'foo'. The argument 'pos' describes the position
		(file and line) where the command occurs.
		"""
		if cmd == "clean":
			self.removed_files.append(arg)

		elif cmd == "depend":
			file = self.conf.find_input(arg)
			if file:
				self.sources[file] = DependLeaf([file], self.msg)
			else:
				self.msg.info(pos, _("dependency '%s' not found") % arg)

		elif cmd == "latex":
			self.conf.latex = arg

		elif cmd == "module":
			args = string.split(arg, maxsplit=1)
			if len(args) == 0:
				self.msg.info(pos, _("argument required for command 'module'"))
			else:
				dict = { 'arg': args[0], 'opt': None }
				if len(args) > 1:
					dict['opt'] = args[1]
				self.modules.register(args[0], dict)

		elif cmd == "onchange":
			args = string.split(arg, maxsplit=1)
			if len(args) < 2:
				self.msg.info(pos, _("two arguments required for command 'onchange'"))
			else:
				file = args[0]
				self.onchange_cmd[file] = args[1]
				if exists(file):
					self.onchange_md5[file] = md5_file(file)
				else:
					self.onchange_md5[file] = None

		elif cmd == "paper":
			self.conf.paper.extend(string.split(arg))

		elif cmd == "path":
			self.conf.path.append(expanduser(arg))

		elif cmd == "read":
			try:
				file = open(arg)
				for line in file.readlines():
					line = line.strip()
					if line == "" or line[0] == "%":
						continue
					lst = string.split(line, maxsplit = 1)
					if len(lst) == 1:
						lst.append("")
					self.command(lst[0], lst[1])
				file.close()
			except IOError:
				self.msg.info(pos, _("cannot read option file %s") % arg)

		elif cmd == "watch":
			self.watch_file(arg)

		else:
			lst = string.split(cmd, ".", 1)
			if len(lst) > 1:
				self.modules.command(lst[0], lst[1], arg)
			else:
				self.msg.info(pos, _("unknown directive '%s'") % cmd)

	def process (self, path):
		"""
		This method is called when an included file is processed. The argument
		must be a valid file name.
		"""
		if self.processed_sources.has_key(path):
			self.msg(3, _("%s already parsed") % path)
			return
		self.processed_sources[path] = None
		self.msg(2, _("parsing %s") % path)
		file = open(path)
		if not self.sources.has_key(path):
			self.sources[path] = DependLeaf([path], self.msg)
		try:
			try:
				self.do_process(file, path)
			finally:
				file.close()
				self.msg(3, _("end of %s") % path)
		except EndInput:
			pass

	def input_file (self, name):
		"""
		Treat the given name as a source file to be read. If this source can
		be the result of some conversion, then the conversion is performed,
		otherwise the source is parsed. The returned value is a couple
		(name,dep) where `name' is the actual LaTeX source and `dep' is
		its dependency node. The return value is (None,None) is the source
		could neither be read nor built.
		"""
		if name.find("\\") >= 0 or name.find("#") >= 0:
			return None, None

		for path in self.conf.path:
			pname = join(path, name)
			dep = self.convert(pname, self)
			if dep:
				self.sources[pname] = dep
				return pname, dep
			dep = self.convert(pname + ".tex", self)
			if dep:
				self.sources[pname] = dep
				return pname + ".tex", dep

		file = self.conf.find_input(name)
		if file:
			self.process(file)
			return file, self.sources[file]
		else:
			return None, None

	def update_seq (self):
		"""
		Update the regular expression used to match macro calls using the keys
		in the `hook' dictionary. We don't match all control sequences for
		obvious efficiency reasons.
		"""
		self.seq = re.compile("\
\\\\(?P<name>%s)\*?\
 *(\\[(?P<opt>[^\\]]*)\\])?\
 *({(?P<arg>[^{}]*)}|(?=[^A-Za-z]))"
 			% string.join(self.hooks.keys(), "|"))

	# Module interface:

	def add_hook (self, name, fun):
		"""
		Register a given function to be called (with no arguments) when a
		given macro is found.
		"""
		self.hooks[name] = fun
		self.update_seq()

	# Now the macro handlers:

	def h_input (self, dict):
		"""
		Called when an \\input macro is found. This calls the `process' method
		if the included file is found.
		"""
		if dict["arg"]:
			self.input_file(dict["arg"])

	def h_include (self, dict):
		"""
		Called when an \\include macro is found. This includes files into the
		source in a way very similar to \\input, except that LaTeX also
		creates .aux files for them, so we have to notice this.
		"""
		if not dict["arg"]:
			return
		if self.include_only and not self.include_only.has_key(dict["arg"]):
			return
		file, _ = self.input_file(dict["arg"])
		if file:
			if file[-4:] == ".tex":
				file = file[:-4]
			self.removed_files.append(basename(file) + ".aux")

	def h_includeonly (self, dict):
		"""
		Called when the macro \\includeonly is found, indicates the
		comma-separated list of files that should be included, so that the
		othe \\include are ignored.
		"""
		if not dict["arg"]:
			return
		self.include_only = {}
		for name in dict["arg"].split(","):
			self.include_only[name] = None

	def h_documentclass (self, dict):
		"""
		Called when the macro \\documentclass is found. It almost has the same
		effect as `usepackage': if the source's directory contains the class
		file, in which case this file is treated as an input, otherwise a
		module is searched for to support the class.
		"""
		if not dict["arg"]: return
		file = self.conf.find_input(dict["arg"] + ".cls")
		if file:
			self.process(file)
		else:
			self.modules.register(dict["arg"], dict)

	def h_usepackage (self, dict):
		"""
		Called when a \\usepackage macro is found. If there is a package in the
		directory of the source file, then it is treated as an include file
		unless there is a supporting module in the current directory,
		otherwise it is treated as a package.
		"""
		if not dict["arg"]: return
		for name in string.split(dict["arg"], ","):
			file = self.conf.find_input(name + ".sty")
			if file and not exists(name + ".py"):
				self.process(file)
			else:
				self.modules.register(name, dict)

	def h_tableofcontents (self, dict):
		self.watch_file(self.src_base + ".toc")
	def h_listoffigures (self, dict):
		self.watch_file(self.src_base + ".lof")
	def h_listoftables (self, dict):
		self.watch_file(self.src_base + ".lot")

	def h_bibliography (self, dict):
		"""
		Called when the macro \\bibliography is found. This method actually
		registers the module bibtex (if not already done) and registers the
		databases.
		"""
		if dict["arg"]:
			self.modules.register("bibtex", dict)
			for db in dict["arg"].split(","):
				self.modules["bibtex"].add_db(db)

	def h_bibliographystyle (self, dict):
		"""
		Called when \\bibliographystyle is found. This registers the module
		bibtex (if not already done) and calls the method set_style() of the
		module.
		"""
		if dict["arg"]:
			self.modules.register("bibtex", dict)
			self.modules["bibtex"].set_style(dict["arg"])

	def h_endinput (self, dict):
		"""
		Called when \\endinput is found. This stops the processing of the
		current input file, thus ignoring any code that appears afterwards.
		"""
		raise EndInput

	def h_end_document (self, dict):
		"""
		Called when \\end{document} is found. This stops the processing of any
		input file, thus ignoring any code that appears afterwards.
		"""
		raise EndDocument

	#
	# The following macros are related to the building process.
	#

	###  preparation things

	def set_source (self, path):
		"""
		Specify the main source for the document. The exact path and file name
		are determined, and the source building process is updated if needed,
		according the the source file's extension.
		"""
		name = self.conf.find_input(path)
		if not name:
			self.msg(0, _("cannot find %s") % path)
			return 1
		self.sources = {}
		(self.src_path, name) = split(name)
		(self.src_base, self.src_ext) = splitext(name)
		if self.src_path == "":
			self.src_path = "."
			self.src_pbase = self.src_base
		else:
			self.conf.path.append(self.src_path)
			self.src_pbase = join(self.src_path, self.src_base)

		self.prods = [self.src_base + ".dvi"]

		if self.source_exts.has_key(self.src_ext):
			self.modules.register(self.source_exts[self.src_ext])

		return 0

	def source (self):
		"""
		Return the main source's complete filename.
		"""
		return self.src_pbase + self.src_ext

	###  building steps

	def make_source (self):
		"""
		Run the source building steps, ensuring that the source file (as
		returned by the `source' method) exists and is up to date.
		"""
		if self.source_building:
			self.msg(1, _("building the source..."))
			return self.source_building()
		return 0

	def compile (self):
		"""
		Run one LaTeX compilation on the source. Return true if errors
		occured, and false if compilaiton succeeded.
		"""
		self.msg(0, _("compiling %s...") % self.source())
		(cmd, env) = self.conf.compile_cmd(self.source())
		self.execute(cmd, env)
		if self.log.read(self.src_base + ".log"):
			self.msg(0, _("Could not run %s.") % cmd[0])
			return 1
		if self.log.errors():
			return 1
		self.aux_md5_old = self.aux_md5
		self.aux_md5 = md5_file(self.src_base + ".aux")
		return 0

	def pre_compile (self):
		"""
		Prepare the source for compilation using package-specific functions.
		This function must return true on failure. This function sets
		`must_compile' to 1 if we already know that a compilation is needed,
		because it may avoid some unnecessary preprocessing (e.g. BibTeXing).
		"""
		if os.path.exists(self.src_base + ".aux"):
			self.aux_md5 = md5_file(self.src_base + ".aux")
		else:
			self.aux_md5 = None
		self.aux_md5_old = None

		self.log.read(self.src_base + ".log")

		self.must_compile = 0
		self.must_compile = self.compile_needed()

		self.msg(2, _("building additional files..."))

		for dep in self.sources.values():
			if dep.make() == 0:
				self.failed_dep = dep.failed_dep
				return 1

		for mod in self.modules.objects.values():
			if mod.pre_compile():
				return 1
		return 0
		

	def post_compile (self):
		"""
		Run the package-specific operations that are to be performed after
		each compilation of the main source. Returns true on failure.
		"""
		self.msg(2, _("running post-compilation scripts..."))

		for file, md5 in self.onchange_md5.items():
			if not exists(file):
				continue
			new = md5_file(file)
			if md5 != new:
				self.msg(0, _("running %s...") % self.onchange_cmd[file])
				self.execute(["sh", "-c", self.onchange_cmd[file]])
			self.onchange_md5[file] = new

		for mod in self.modules.objects.values():
			if mod.post_compile():
				return 1
		return 0

	def post_process (self):
		"""
		Run all operations needed to post-process the result of compilation.
		"""
		if self.final != self:
			self.msg(2, _("post-processing..."))
			return self.final.make()
		return 0

	def clean (self, all=0):
		"""
		Remove all files that are produced by comiplation.
		"""
		self.remove_suffixes([".log", ".aux", ".toc", ".lof", ".lot"])

		for file in self.prods + self.removed_files:
			if exists(file):
				self.msg(1, _("removing %s") % file)
				os.unlink(file)

		self.msg(2, _("cleaning additional files..."))

		for dep in self.sources.values():
			dep.clean()

		if all:
			for mod in self.modules.objects.values():
				mod.clean()

	###  complete process

	def make (self, force=0):
		"""
		Run the building process until the last compilation, or stop on error.
		This method supposes that the inputs were parsed to register packages
		and that the LaTeX source is ready. If the second (optional) argument
		is true, then at least one compilation is done. As specified by the
		class Depend, the method returns 0 on failure, 1 if nothing was done
		and 2 if something was done without failure.
		"""
		if self.pre_compile(): return 0

		# If an error occurs after this point, it will be while LaTeXing.
		self.failed_dep = self

		if force or self.compile_needed():
			self.must_compile = 0
			if self.compile(): return 0
			if self.post_compile(): return 0
			while self.recompile_needed():
				self.must_compile = 0
				if self.compile(): return 0
				if self.post_compile(): return 0

		# Finally there was no error.
		self.failed_dep = None

		if self.something_done:
			self.date = int(time.time())
			return 2
		return 1

	def compile_needed (self):
		"""
		Returns true if a first compilation is needed. This method supposes
		that no compilation was done (by the script) yet.
		"""
		if self.must_compile:
			return 1
		self.msg(3, _("checking if compiling is necessary..."))
		if not exists(self.prods[0]):
			self.msg(3, _("the output file doesn't exist"))
			return 1
		if not exists(self.src_base + ".log"):
			self.msg(3, _("the log file does not exist"))
			return 1
		if getmtime(self.prods[0]) < getmtime(self.source()):
			self.msg(3, _("the source is younger than the output file"))
			return 1
		if self.log.read(self.src_base + ".log"):
			self.msg(3, _("the log file is not produced by %s") % self.conf.tex)
			return 1
		return self.recompile_needed()

	def recompile_needed (self):
		"""
		Returns true if another compilation is needed. This method is used
		when a compilation has already been done.
		"""
		if self.must_compile:
			self.update_watches()
			return 1
		if self.log.errors():
			self.msg(3, _("last compilation failed"))
			self.update_watches()
			return 1
		if self.deps_modified(getmtime(self.src_base + ".log")):
			self.msg(3, _("dependencies were modified"))
			self.update_watches()
			return 1
		suffix = self.update_watches()
		if suffix:
			self.msg(3, _("the %s file has changed") % suffix)
			return 1
		if self.log.run_needed():
			self.msg(3, _("LaTeX asks to run again"))
			if self.aux_md5 and self.aux_md5 == self.aux_md5_old:
				self.msg(3, _("but the aux file is unchanged"))
				return 0
			return 1
		self.msg(3, _("no new compilation is needed"))
		return 0

	def deps_modified (self, date):
		"""
		Returns true if any of the dependencies is younger than the specified
		date.
		"""
		for dep in self.sources.values():
			if dep.date > date:
				return 1
		return 0

	def show_errors (self):
		self.log.show_errors()

	###  utility methods

	def watch_file (self, file):
		"""
		Register the given file (typically "jobname.toc" or such) to be
		watched. When the file changes during a compilation, it means that
		another compilation has to be done.
		"""
		if exists(file):
			self.watched_files[file] = md5_file(file)
		else:
			self.watched_files[file] = None

	def update_watches (self):
		"""
		Update the MD5 sums of all files watched, and return the name of one
		of the files that changed, or None of they didn't change.
		"""
		changed = None
		for file in self.watched_files.keys():
			if exists(file):
				new = md5_file(file)
				if self.watched_files[file] != new:
					changed = file
				self.watched_files[file] = new
		return changed

	def remove_suffixes (self, list):
		"""
		Remove all files derived from the main source with one of the
		specified suffixes.
		"""
		for suffix in list:
			file = self.src_base + suffix
			if exists(file):
				self.msg(1, _("removing %s") % file)
				os.unlink(file)

	###  program execution

	def execute (self, prog, env={}, pwd=None, out=None):
		"""
		Silently execute an external program. The `prog' argument is the list
		of arguments for the program, `prog[0]' is the program name. The `env'
		argument is a dictionary with definitions that should be added to the
		environment when running the program. The standard output is passed
		line by line to the `out' function (or discarded by default). The
		error output is parsed and messages from Kpathsea are processed (to
		indicate e.g. font compilation).
		"""
		self.msg(1, _("executing: %s") % string.join(prog))
		if pwd:
			self.msg(2, _("  in directory %s") % pwd)
		if env != {}:
			self.msg(2, _("  with environment: %r") % env)

		penv = posix.environ.copy()
		for (key,val) in env.items():
			penv[key] = val

		# Python provides the os.popen* functions for what we want to do, but
		# it has two crucial limitations: it only allows the execution of
		# shell commands, which is problematic because of shell expansion for
		# instance, and it doesn't provide a way to get the program's return
		# code, except using UNIX-only methods in the Popen[34] classes. So we
		# decide to drop non-UNIX compatibility by doing the fork/exec stuff
		# ourselves.

		(f_out_r, f_out_w) = os.pipe()
		(f_err_r, f_err_w) = os.pipe()
		pid = os.fork()

		# The forked process simply closes the appropriate pipes and execvp's
		# the specified program in the appropriate directory.

		if pid == 0:
			os.close(f_out_r)
			os.close(f_err_r)
			os.dup2(f_out_w, sys.__stdout__.fileno())
			os.dup2(f_err_w, sys.__stderr__.fileno())
			if pwd:
				os.chdir(pwd)
			os.execvpe(prog[0], prog, penv)

		# The main process reads whatever is sent to the error stream and
		# parses it for Kpathsea messages.

		os.close(f_out_w)
		os.close(f_err_w)
		f_out = os.fdopen(f_out_r)
		f_err = os.fdopen(f_err_r)

		# If the external program writes a lot of data on both its standard
		# output and standard error streams, we might fall into a deadlock,
		# waiting for input on one while the program fills the other's
		# buffer. To solve this, we add a thread to read on the program's
		# standard output. The thread simply discards this output unless the
		# optional argument is used.
		#
		# In fact, we fork a new process instead of using a thread, because it
		# is more robust (Vim-Python hangs when using a thread).

		pid2 = os.fork()
		if pid2 == 0:
			if out:
				while 1:
					line = f_out.readline()
					if line == "": break
					out(line)
			else:
				while f_out.readline() != "": pass
			f_out.close()
			os._exit(0)
		else:
			f_out.close()

		# At this point, all we have to do is read lines from the error stream
		# and parse them for relevant messages.

		while 1:
			line = f_err.readline()
			if line == "": break
			line = line.rstrip()
			m = re_kpse.match(line)
			if m:
				self.msg(1, line)
				cmd = m.group("cmd")
				if self.kpse_msg.has_key(cmd):
					self.msg(0, m.expand(self.kpse_msg[cmd]))
				else:
					self.msg(0, _("kpathsea running %s...") % cmd)

		# After the executed program is finished (which we now be seeing that
		# its error stream was closed), we wait for it and return its exit
		# code.

		(p, ret) = os.waitpid(pid, 0)
		os.waitpid(pid2, 0)
		f_err.close()
		self.msg(3, _("process %d (%s) returned %d") % (pid, prog[0], ret))

		self.something_done = 1
		return ret

#---------------------------------------

class Message (object):
	"""
	All messages in the program are output using the `msg' object in the
	main class. This class defines the interface for this object.
	"""
	def __call__ (self, level, text):
		"""
		This method calls the actual writing function. This extra indirection
		allows redefining the output method while the program is running,
		while allowing objects to store references to the Message object.
		"""
		pass

	def error (self, file, line, text, code):
		"""
		This method is called when the parsing of the log file found an error.
		The arguments are, respectively, the name of the file and the line
		number where the error occurred, the description of the error, and the
		offending code (up to the error). The line number and the code may be
		None, the file name and the text are required.
		"""
		pass

	def abort (self, what, why):
		"""
		This method is called when the compilation was aborted, for instance
		due to lack of input. The arguments are the nature of the error and
		the cause of the interruption.
		"""
		pass

	def info (self, where, what):
		"""
		This method is called when reporting information and warnings. The
		first argument is a dictionary that describes the position the
		information concerns (it may contain entries 'file', 'page' and
		'line'). The second argument is the information message.
		"""
		pass

#---------------------------------------

class Module (object):
	"""
	This is the base class for modules. Each module should define a class
	named 'Module' that derives from this one. The default implementation
	provides all required methods with no effects.
	"""
	def __init__ (self, env, dict):
		"""
		The constructor receives two arguments: 'env' is the compiling
		environment, 'dict' is a dictionary that describes the command that
		caused the module to load.
		"""

	def pre_compile (self):
		"""
		This method is called before the first LaTeX compilation. It is
		supposed to build any file that LaTeX would require to compile the
		document correctly.
		"""

	def post_compile (self):
		"""
		This method is called after each LaTeX compilation. It is supposed to
		process the compilation results and possibly request a new
		compilation.
		"""

	def clean (self):
		"""
		This method is called when cleaning the compiled files. It is supposed
		to remove all the files that this modules generates.
		"""

	def command (self, cmd, arg):
		"""
		This is called when a directive for the module is found in the source.
		"""
