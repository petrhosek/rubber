# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002
"""
LaTeX document building system for Rubber.

This module contains all the code in Rubber that actually does the job of
building a LaTeX document from start to finish.
"""

import imp
import os
from os.path import *
import re
import string
import sys

def _ (txt): return txt

#---------------------------------------

class Config:
	"""
	This class contains all configuration parameters. This includes search
	paths, the verbosity level, the name of the compiler and options for it.
	"""
	def __init__ (self):
		"""
		Initialize the configuration with default settings.
		"""
		self.path = [""]
		self.verb_level = 0
		self.latex = "latex"
		self.latex_opts = ["--interaction=batchmode"]
		self.tex = "TeX"

	def find_input (self, name):
		"""
		Look for a source file with the given name, and return either the
		complete path to the actual file or None if the file is not found.
		"""
		for path in self.path:
			test = join(path, name)
			if exists(test):
				return test
			elif exists(test + ".tex"):
				return test + ".tex"
		return None

	def compile_cmd (self, file):
		"""
		Return the list of arguments for the command that should be used to
		compile the specified file.
		"""
		return [self.latex] + self.latex_opts + [file]

#---------------------------------------

class Message:
	"""
	All messages should be output using this class. It manages verbosity level
	and possible redirection. One can imagine using a derived class to
	redirect messages to a GUI widget, or any other funky stuff.
	"""
	def __init__ (self, env):
		self.conf = env.config

	def __call__ (self, level, text):
		"""
		Output a text with the specified verbosity level. If this level is
		larger than the current output level, no message is produced.
		"""
		if level <= self.conf.verb_level:
			print text

#---------------------------------------

class Parser:
	"""
	Objects from this class read text lines from a file and parse them to
	extract LaTeX macro calls. When such a macro is found, a handler is
	searched for in the `hooks' dictionary. Handlers are called with two
	arguments, the processor object and the dictionary for the regular
	expression.
	"""
	def __init__ (self, env):
		"""
		Initialize the object, compiling the regular expressions and
		initializing the hook dictionary.
		"""
		self.env = env
		self.conf = env.config
		self.msg = env.message
		self.comment = re.compile("(?P<line>[^%]*)(%.*)?")
		self.input_seq = re.compile("\\\\input +(?P<arg>[^{} \n\\\\]+)")

		self.hooks = {
			"input" : self.input, "include" : self.input,
			"usepackage" : self.usepackage, "RequirePackage" : self.usepackage,
			"documentclass" : self.documentclass,
			"bibliography" : self.bibliography
		}
		self.update_seq()

	def update_seq (self):
		"""
		Update the regular expression used to match macro calls using the keys
		in the `hook' dictionary.
		"""
		self.seq = re.compile("\\\\(?P<name>%s)( *(\\[(?P<opt>[^\\]]*)\\])?{(?P<arg>[^\\\\{}]*)}|[^A-Za-z])" % string.join(self.hooks.keys(), "|"))

	def do_process (self, file):
		"""
		Process a LaTeX source. The file must be open, it is read to the end
		calling the handlers for the macro calls. This recursively processes
		the included sources.
		"""
		lines = file.readlines()
		for line in lines:
			line = self.comment.match(line).group(1)
			match = self.seq.search(line)
			while match:
				dict = match.groupdict()
				name = dict["name"]
				
				# The case of \input is handled specifically, because of the
				# TeX syntax with no braces

				if name == "input" and not dict["arg"]:
					match2 = self.input_seq.search(line)
					if match2:
						match = match2
						dict = match.groupdict()

				self.hooks[name](dict)
				line = line[match.end():]
				match = self.seq.search(line)

	def process (self, path):
		"""
		This method is called when an included file is processed. The argument
		must be a valid file name.
		"""
		self.msg(2, "parsing " + path)
		file = open(path)
		self.env.process.depends.append(path)
		self.do_process(file)
		file.close()
		self.msg(3, "end of " + path)

	# Module interface:

	def add_hook (self, name, fun):
		"""
		Register a given function to be called (with no arguments) when a
		given macro is found.
		"""
		self.hooks[name] = fun
		self.update_seq()

	# Now the macro handlers:

	def input (self, dict):
		"""
		Called when an \\input or an \\include is found. This calls the
		`process' method if the included file is found.
		"""
		if dict["arg"]:
			file = self.conf.find_input(dict["arg"])
			if file:
				self.process(file)

	def documentclass (self, dict):
		"""
		Called when the macro \\documentclass is found. It almost has the same
		effect as `usepackage': if the source's directory contains the class
		file, in which case this file is treated as an input, otherwise a
		module is searched for to support the class.
		"""
		if not dict["arg"]: return
		for name in string.split(dict["arg"], ","):
			file = self.conf.find_input (name + ".cls")
			if file:
				self.process(file)
			else:
				self.env.modules.register(name, dict)

	def usepackage (self, dict):
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
				self.env.modules.register(name, dict)

	def bibliography (self, dict):
		"""
		Called when the macro \\bibliography is found. This method actually
		registers the package bibtex.
		"""
		self.env.modules.register("bibtex", dict)

#---------------------------------------

class LogCheck:
	"""
	This class performs all the extraction of information from the log file.
	For efficiency, the instances contain the whole file as a list of strings
	so that it can be read several times with no disk access.
	"""
	def __init__ (self, env):
		self.env = env
		self.msg = env.message
		self.re_rerun = re.compile("LaTeX Warning:.*Rerun")

	def read (self, name):
		"""
		Read the specified log file, checking that it was produced by the
		right compiler. Returns true if the log file is invalid.
		"""
		file = open(name)
		line = file.readline()
		if not line:
			file.close()
			return 1
		if line.find("This is " + self.env.config.tex) == -1:
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
				return 1
		return 0

	def run_needed (self):
		"""
		Returns true if LaTeX indicated that another compilation is needed.
		"""
		for line in self.lines:
			if self.re_rerun.match(line):
				return 1
		return 0

	# information extraction:

	def show_errors (self):
		"""
		Display all errors that occured during compilation.
		"""
		showing = 0
		for line in self.lines:
			line = line.rstrip()
			if line == "":
				continue
			if showing:
				self.msg(0, line)
				if line[0:2] == "l." or line[0:3] == "***":
					showing = 0
			else:
				if line[0] == "!":
					self.msg(0, line)
					showing = 1

#---------------------------------------

class Process:
	"""
	This class represents de building process for the document. It handles the
	execution of all required programs. The steps are the following:
	  1. building of the LaTeX source (e.g. when using WEB)
	  2. preparation of external dependencies (e.g. compilation of figures)
	  3. cyclic LaTeX compilation until a stable output, including:
	     a. actual compilation (with a parametrable executable)
	     b. possible processing of compilation results (e.g. running BibTeX)
	  4. processing of the final output (e.g. dvips)
	The class also handles the cleaning mechanism.
	"""
	def __init__ (self, env):
		"""
		Initialize the processing steps for the given file. All steps are
		initialized empty.
		"""
		self.env = env
		self.msg = env.message
		self.log = env.logcheck

		# description of the building process:

		self.source_building = None
		self.ext_building = []
		self.compile_process = []
		self.output_processing = None

		self.cleaning_process = []

		# state of the builder:

		self.must_compile = 0
		self.something_done = 0

		# additional data:

		self.re_kpse = re.compile("kpathsea: Running (?P<cmd>[^ ]*) +(?P<arg>.*)")
		self.kpse_msg = {
			"mktextfm" : _("making font metrics for %s..."),
			"mktexmf" : _("making font %s...") }

	###  preparation things

	def set_source (self, path):
		"""
		Specify the main source for the document. The exact path and file name
		are determined, and the source building process is updated if needed,
		according the the source file's extension.
		"""
		env = self.env
		name = env.config.find_input(path)
		if not name:
			self.msg(0, _("cannot find %s") % path)
			return 1
		self.depends = []
		(self.src_path, name) = split(name)
		(self.src_base, self.src_ext) = splitext(name)
		self.src_pbase = join(self.src_path, self.src_base)

		self.out_ext = ".dvi"

		if env.source_exts.has_key(self.src_ext):
			env.modules.register(env.source_exts[self.src_ext])

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
		Run one LaTeX compilation on the source. If errors occured, display
		them and return true, otherwise return false.
		"""
		self.msg(0, _("compiling %s...") % self.source())
		self.execute(self.env.config.compile_cmd(self.source()))
		self.log.read(self.src_pbase + ".log")
		if self.log.errors():
			self.msg(0, _("There were errors."))
			self.log.show_errors()
			return 1
		return 0

	def pre_compile (self):
		"""
		Prepare the source for compilation using package-specific functions.
		This function must return true on failure.
		"""
		if self.ext_building != []:
			self.msg(1, _("building additional files..."))
			for proc in self.ext_building:
				if proc(): return 1
		return 0
		

	def post_compile (self):
		"""
		Run the package-specific operations that are to be performed after
		each compilation of the main source. Returns true on failure.
		"""
		if self.compile_process != []:
			self.msg(2, _("running post-compilation scripts..."))
			for proc in self.compile_process:
				if proc(): return 1
		return 0

	def post_process (self):
		"""
		Run all operations needed to post-process the result of compilation.
		"""
		if self.output_processing:
			self.msg(2, _("post-processing..."))
			return self.output_processing()
		return 0

	def clean (self):
		"""
		Remove all files that are produced by comiplation.
		"""
		self.remove_suffixes([
			".log", ".aux", ".toc", ".lof", ".lot", self.out_ext])
		if self.cleaning_process != []:
			self.msg(2, _("cleaning additional files..."))
			for proc in self.cleaning_process:
				proc()

	###  complete process

	def make (self):
		"""
		Run the building process until the end, or stop on error. This method
		supposes that the inputs were parsed to register packages and that the
		LaTeX source is ready.
		"""
		if self.pre_compile(): return 1
		if self.compile_needed():
			self.must_compile = 0
			if self.compile(): return 1
			if self.post_compile(): return 1
			while self.recompile_needed():
				self.must_compile = 0
				if self.compile(): return 1
				if self.post_compile(): return 1		
		if self.post_process(): return 1
		if not self.something_done:
			self.msg(0, _("nothing to be done for %s") % self.source())

	def compile_needed (self):
		"""
		Returns true if a first compilation is needed. This method supposes
		that no compilatin was done (by the script) yet.
		"""
		if self.must_compile:
			return 1
		self.msg(3, _("checking if compiling is necessary..."))
		if not exists(self.src_pbase + self.out_ext):
			self.msg(3, _("the output file doesn't exist"))
			return 1
		if not exists(self.src_pbase + ".log"):
			self.msg(3, _("the log file does not exist"))
			return 1
		if getmtime(self.src_pbase + ".log") < getmtime(self.source()):
			self.msg(3, _("the source is younger than the log file"))
			return 1
		if self.log.read(self.src_pbase + ".log"):
			self.msg(3, _("the log file is not produced by %s") % self.env.config.tex)
			return 1
		return self.recompile_needed()

	def recompile_needed (self):
		"""
		Returns true if another compilation is needed. This method is used
		when a compilation has already been done.
		"""
		if self.must_compile:
			return 1
		if self.log.errors():
			self.msg(3, _("last compilation failed"))
			return 1
		if self.deps_modified(getmtime(self.src_pbase + ".log")):
			self.msg(3, _("dependencies were modified"))
			return 1
		if self.log.run_needed():
			self.msg(3, _("LaTeX asks to run again"))
			return 1
		self.msg(3, _("no new compilation is needed"))
		return 0

	def deps_modified (self, date):
		"""
		Returns true if any of the dependencies is younger than the specified
		date.
		"""
		for file in self.depends:
			if exists(file):
				if getmtime(file) > date:
					return 1
			else:
				self.msg(2, _("dependency %s does not exist") % file)
		return 0

	###  utility methods

	def execute (self, prog):
		"""
		Silently execute an external program. The `prog' argument is the list
		of arguments for the program, `prog[0]' is the program name. The
		output is dicarded, but messages from Kpathsea are processed (to
		indicate e.g. font compilation).
		"""
		cmd = string.join(prog, " ")
		self.msg(1, _("executing: %s") % cmd)
		f_in, f_out, f_err = os.popen3(cmd)
		while 1:
			line = f_err.readline()
			if line == "": break
			m = self.re_kpse.match(line)
			if m:
				cmd = m.group("cmd")
				if self.kpse_msg.has_key(cmd):
					self.msg(0, self.kpse_msg[cmd] % m.group("arg"))
				else:
					self.msg(0, _("kapthsea running %s...") % cmd)
		self.something_done = 1

	def remove_suffixes (self, list):
		"""
		Remove all files derived from the main source with one of the
		specified suffixes.
		"""
		for suffix in list:
			file = self.src_pbase + suffix
			if exists(file):
				self.msg(3, _("removing %s") % file)
				os.unlink(file)

#---------------------------------------

class Modules:
	"""
	This class gathers all operations related to the management of external
	modules. Package supports are loaded through the `register' method, and
	mosules are searched for first in the current directory, then in the
	package `rubber.modules' (using Python's path).
	"""
	def __init__ (self, env):
		self.env = env
		self.modules = {}

	def register (self, name, dict={}):
		"""
		Attempt to register a package with the specified name. If a module is
		found to support the package, create an object from the module's class
		called `Module', passing it the environment and `dict' as arguments.
		This dictionary describes the command that caused the registration.
		"""
		if self.modules.has_key(name):
			self.env.message(2, _("module %s already registered") % name)
			return 1
		try:
			file, path, descr = imp.find_module(name, [""])
		except ImportError:
			try:
				file, path, descr = imp.find_module(
					join("rubber", "modules", name));
			except ImportError:
				self.env.message(2, _("no support found for %s") % name)
				return 1
		module = imp.load_module(name, file, path, descr)
		file.close()
		mod = module.Module(self.env, dict)
		self.env.message(2, _("module %s registered") % name)
		self.modules[name] = mod
		return 0

	def clear(self):
		"""
		Empty the module table, unregistering every module registered. No
		modules are unloaded, however, but this has no other effect than
		speeding the registration of the modules again.
		"""
		self.modules.clear()


#---------------------------------------

class Environment:
	"""
	This class contains the whole processing environment.
	"""
	def __init__ (self):
		"""
		Initialize the environment by creating an object of each required
		class.
		"""
		self.config = Config()
		self.message = Message(self)
		self.message(3, _("initializing Rubber..."))
		self.parser = Parser(self)
		self.logcheck = LogCheck(self)
		self.process = Process(self)
		self.modules = Modules(self)
		self.source_exts = { ".w" : "cweb" }
		self.message(3, _("ready"))

	def restart (self):
		"""
		Restart the system by unregistering all modules.
		"""
		self.message(1, _("initializing..."))
		self.modules.clear()
		self.parser.__init__(self)
		self.process.__init__(self)

	def prepare (self, name):
		"""
		Initialize the process for the given document and make the LaTeX
		source if needed.
		"""
		self.message(1, _("preparing compilation of %s...") % name)
		if self.process.set_source(name): return 1
		return self.process.make_source()

	def parse (self):
		"""
		Parse the source for packages and supported macros.
		"""
		self.parser.process(self.process.source())
		self.message(2, _("dependencies: %r") % self.process.depends)

	def make (self):
		"""
		Make the document initialized using `prepare'.
		"""
		self.process.make()

	def clean (self):
		"""
		Clean all files produced by the (prepared) document's compilation.
		"""
		self.process.clean()
