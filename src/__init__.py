# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002
"""
LaTeX document building system for Rubber.

This module contains all the code in Rubber that actually does the job of
building a LaTeX document from start to finish.
"""

import os
from os.path import *
import re
import string
import sys

from rubber.util import *

def _ (txt): return txt

#---------------------------------------

class Config:
	"""
	This class contains all configuration parameters. This includes search
	paths, the name of the compiler and options for it.
	"""
	def __init__ (self):
		"""
		Initialize the configuration with default settings.
		"""
		self.path = [""]
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
			if exists(test + ".tex") and isfile(test + ".tex"):
				return test + ".tex"
			elif exists(test) and isfile(test):
				return test
		return None

	def compile_cmd (self, file):
		"""
		Return the list of arguments for the command that should be used to
		compile the specified file.
		"""
		cmd = [self.latex] + self.latex_opts + [file]
		inputs = string.join(self.path, ":")
		if inputs != "":
			inputs = inputs + ":" + os.getenv("TEXINPUTS", "")
			cmd = ["env", "TEXINPUTS=" + inputs] + cmd
		return cmd

#---------------------------------------

class Message:
	"""
	All messages in the program are output using the `message' object in the
	main class. This class provides a simple version that writes text on the
	standard output. It manages verbosity level and possible redirection. One
	can imagine using a derived class to redirect messages to a GUI widget, or
	any other funky stuff.
	"""
	def __init__ (self, level=0):
		"""
		Initialize the object with the specified verbosity threshold.
		"""
		self.level = level
		self.write = self.do_write

	def do_write (self, level, text):
		"""
		Output a text with the specified verbosity level. If this level is
		larger than the current output level, no message is produced.
		"""
		if level <= self.level:
			print text

	def __call__ (self, level, text):
		"""
		This method calls the actual writing function. This extra indirection
		allows redefining the output method while the program is running,
		while allowing objects to store references to the Message object.
		"""
		self.write(level, text)

#---------------------------------------

class Modules (Plugins):
	"""
	This class gathers all operations related to the management of modules.
	The modules are	searched for first in the current directory, then in the
	package `rubber.modules'.
	"""
	def __init__ (self, env):
		Plugins.__init__(self)
		self.env = env
		self.objects = {}

	def __getitem__ (self, name):
		"""
		Return the module object of the given name.
		"""
		return self.objects[name]

	def register (self, name, dict={}):
		"""
		Attempt to register a package with the specified name. If a module is
		found, create an object from the module's class called `Module',
		passing it the environment and `dict' as arguments. This dictionary
		describes the command that caused the registration.
		"""
		r = self.load_module(name, "rubber.modules")
		if r == 0:
			self.env.msg(3, _("no support found for %s") % name)
			return 1
		elif r == 2:
			self.env.msg(3, _("module %s already registered") % name)
			return 1
		mod = self.modules[name].Module(self.env, dict)
		self.env.msg(2, _("module %s registered") % name)
		self.objects[name] = mod
		return 0

#---------------------------------------

re_rerun = re.compile("LaTeX Warning:.*Rerun")
re_file = re.compile("(\((?P<file>[^ ()]*)|\))")

class LogCheck:
	"""
	This class performs all the extraction of information from the log file.
	For efficiency, the instances contain the whole file as a list of strings
	so that it can be read several times with no disk access.
	"""
	def __init__ (self, env):
		self.env = env
		self.msg = env.msg

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
		if line.find("This is " + self.env.conf.tex) == -1:
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
			if re_rerun.match(line):
				return 1
		return 0

	# information extraction:

	def update_file (self, line, stack):
		"""
		Parse the given line of log file for file openings and closings and
		update the list `stack'. Newly opened files are at the end, therefore
		stack[0] is the main source while stack[-1] is the current one.
		"""
		m = re_file.search(line)
		if not m:
			return
		while m:
			file = m.group("file")
			if file:
				stack.append(file)
			else:
				del stack[-1]
			line = line[m.end():]
			m = re_file.search(line)
		return

	def show_errors (self):
		"""
		Display all errors that occured during compilation. Return 0 if there
		was no error.
		"""
		pos = ["(no file)"]
		last_file = None
		showing = 0
		something = 0
		for line in self.lines:
			line = line.rstrip()
			if line == "":
				continue
			if showing:
				self.msg(0, line)
				if line[0:2] == "l." or line[0:3] == "***":
					showing = 0
				else:
					self.update_file(line, pos)
			else:
				if line[0] == "!":
					if pos[-1] != last_file:
						last_file = pos[-1]
						self.msg(0, _("in file %s:") % last_file)
					self.msg(0, line)
					showing = 1
					something = 1
				else:
					self.update_file(line, pos)
		return something

#---------------------------------------

re_comment = re.compile("(?P<line>[^%]*)(%.*)?")
re_input = re.compile("\\\\input +(?P<arg>[^{} \n\\\\]+)")
re_kpse = re.compile("kpathsea: Running (?P<cmd>[^ ]*).* (?P<arg>[^ ]*)$")

class Environment:
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
	"""
	Objects from this class read text lines from a file and parse them to
	extract LaTeX macro calls. When such a macro is found, a handler is
	searched for in the `hooks' dictionary. Handlers are called with two
	arguments, the processor object and the dictionary for the regular
	expression.
	"""
	def __init__ (self, message):
		"""
		Initialize the environment. This prepares the processing steps for the
		given file (all steps are initialized empty) and sets the regular
		expressions and the hook dictionary.
		"""
		self.msg = message
		self.msg(2, _("initializing Rubber..."))

		self.conf = Config()
		self.log = LogCheck(self)
		self.modules = Modules(self)

		# (a priori) static dictionaries:

		self.source_exts = { ".w" : "cweb" }

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
		self.msg(1, _("initializing..."))
		self.modules.clear()
		self.initialize()

	def initialize (self):
		"""
		This is the method that actually does the initialization. It is also
		used when restarting the process.
		"""
		# the initial hooks:

		self.hooks = {
			"input" : self.h_input,
			"include" : self.h_input,
			"usepackage" : self.h_usepackage,
			"RequirePackage" : self.h_usepackage,
			"documentclass" : self.h_documentclass,
			"tableofcontents" : self.h_tableofcontents,
			"listoffigures" : self.h_listoffigures,
			"listoftables" : self.h_listoftables,
			"bibliography" : self.h_bibliography,
			"bibliographystyle" : self.h_bibliographystyle
		}
		self.update_seq()

		# description of the building process:

		self.source_building = None
		self.ext_building = []
		self.compile_process = []
		self.output_processing = None

		self.watched_files = {}

		self.cleaning_process = []

		# state of the builder:

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
		self.process(self.source())
		self.msg(2, _("dependencies: %r") % self.depends.keys())

	def do_process (self, file):
		"""
		Process a LaTeX source. The file must be open, it is read to the end
		calling the handlers for the macro calls. This recursively processes
		the included sources.
		"""
		lines = file.readlines()
		for line in lines:
			line = re_comment.match(line).group(1)
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
		self.depends[path] = DependLeaf([path])
		self.do_process(file)
		file.close()
		self.msg(3, "end of " + path)

	def update_seq (self):
		"""
		Update the regular expression used to match macro calls using the keys
		in the `hook' dictionary. We don't match all control sequences for
		obvious efficiency reasons.
		"""
		self.seq = re.compile("\\\\(?P<name>%s)\*?( *(\\[(?P<opt>[^\\]]*)\\])?{(?P<arg>[^\\\\{}]*)}|[^A-Za-z])" % string.join(self.hooks.keys(), "|"))

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
		Called when an \\input or an \\include is found. This calls the
		`process' method if the included file is found.
		"""
		if dict["arg"]:
			file = self.conf.find_input(dict["arg"])
			if file:
				self.process(file)

	def h_documentclass (self, dict):
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
				self.modules.register(name, dict)

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
		self.watch_file(".toc")
	def h_listoffigures (self, dict):
		self.watch_file(".lof")
	def h_listoftables (self, dict):
		self.watch_file(".lot")

	def h_bibliography (self, dict):
		"""
		Called when the macro \\bibliography is found. This method actually
		registers the module bibtex (if not already done) and registers the
		databases.
		"""
		self.modules.register("bibtex", dict)
		for db in dict["arg"].split(","):
			self.modules["bibtex"].add_db(db)

	def h_bibliographystyle (self, dict):
		"""
		Called when \\bibliographystyle is found. This registers the module
		bibtex (if not already done) and calls the method set_style() of the
		module.
		"""
		self.modules.register("bibtex", dict)
		self.modules["bibtex"].set_style(dict["arg"])

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
		self.depends = {}
		(self.src_path, name) = split(name)
		if self.src_path != "":
			self.conf.path.append(self.src_path)
		(self.src_base, self.src_ext) = splitext(name)
		self.src_pbase = join(self.src_path, self.src_base)

		self.out_ext = ".dvi"

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
		Run one LaTeX compilation on the source. If errors occured, display
		them and return true, otherwise return false.
		"""
		self.msg(0, _("compiling %s...") % self.source())
		self.execute(self.conf.compile_cmd(self.source()))
		self.log.read(self.src_base + ".log")
		if self.log.errors():
			self.msg(-1, _("There were errors."))
			self.log.show_errors()
			return 1
		return 0

	def pre_compile (self):
		"""
		Prepare the source for compilation using package-specific functions.
		This function must return true on failure. This function sets
		`must_compile' to 1 if we already know that a compilation is needed,
		because it may avoid some unnecessary preprocessing (e.g. BibTeXing).
		"""
		self.must_compile = 0
		self.must_compile = self.compile_needed()
		if self.ext_building != []:
			self.msg(1, _("building additional files..."))
			for dep in self.depends.values():
				if dep.make() == 0:
					return 1
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
		if not exists(self.src_base + self.out_ext):
			self.msg(3, _("the output file doesn't exist"))
			return 1
		if not exists(self.src_base + ".log"):
			self.msg(3, _("the log file does not exist"))
			return 1
		if getmtime(self.src_base + ".log") < getmtime(self.source()):
			self.msg(3, _("the source is younger than the log file"))
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
			return 1
		self.msg(3, _("no new compilation is needed"))
		return 0

	def deps_modified (self, date):
		"""
		Returns true if any of the dependencies is younger than the specified
		date.
		"""
		for dep in self.depends.values():
			if dep.date > date:
				return 1
		return 0

	###  utility methods

	def watch_file (self, suffix):
		"""
		Register the file with the given suffix (typically .toc or such) to be
		watched. When the file changes during a compilation, it means that
		another compilation has to be done.
		"""
		if exists(self.src_base + suffix):
			self.watched_files[suffix] = md5_file(self.src_base + suffix)
		else:
			self.watched_files[suffix] = None

	def update_watches (self):
		"""
		Update the MD5 sums of all files watched, and return the suffix of one
		of the files that changed, or None of they didn't change.
		"""
		changed = None
		for suffix in self.watched_files.keys():
			if exists(self.src_base + suffix):
				new = md5_file(self.src_base + suffix)
				if self.watched_files[suffix] != new:
					changed = suffix
				self.watched_files[suffix] = new
		return changed

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
			line = line.rstrip()
			m = re_kpse.match(line)
			if m:
				self.msg(1, line)
				cmd = m.group("cmd")
				if self.kpse_msg.has_key(cmd):
					self.msg(0, m.expand(self.kpse_msg[cmd]))
				else:
					self.msg(0, _("kpathsea running %s...") % cmd)
		self.something_done = 1

	def remove_suffixes (self, list):
		"""
		Remove all files derived from the main source with one of the
		specified suffixes.
		"""
		for suffix in list:
			file = self.src_base + suffix
			if exists(file):
				self.msg(3, _("removing %s") % file)
				os.unlink(file)
