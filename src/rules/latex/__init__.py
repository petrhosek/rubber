# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2005
"""
LaTeX document building system for Rubber.

This module contains all the code in Rubber that actually does the job of
building a LaTeX document from start to finish.
"""

import os, sys, posix
from os.path import *
import re
import string

from rubber import _
from rubber import *
from rubber.version import moddir

#----  Module handler  ----{{{1

class Modules (Plugins):
	"""
	This class gathers all operations related to the management of modules.
	The modules are	searched for first in the current directory, then as
	scripts in the 'modules' directory in the program's data directort, then
	as a Python module in the package `rubber.latex'.
	"""
	def __init__ (self, env):
		Plugins.__init__(self, rubber.rules.latex.__path__)
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
		if self.has_key(name):
			msg.debug(_("module %s already registered") % name)
			return 2

		# First look for a script

		mod = None
		for path in "", join(moddir, "modules"):
			file = join(path, name + ".rub")
			if exists(file):
				mod = ScriptModule(self.env, file)
				msg.log(_("script module %s registered") % name)
				break

		# Then look for a Python module

		if not mod:
			if Plugins.register(self, name) == 0:
				msg.debug(_("no support found for %s") % name)
				return 0
			mod = self.modules[name].Module(self.env, dict)
			msg.log(_("built-in module %s registered") % name)

		# Run any delayed commands.

		if self.commands.has_key(name):
			for (cmd,args) in self.commands[name]:
				mod.command(cmd, args)
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

	def command (self, mod, cmd, args):
		"""
		Send a command to a particular module. If this module is not loaded,
		store the command so that it will be sent when the module is register.
		"""
		if self.objects.has_key(mod):
			self.objects[mod].command(cmd, args)
		else:
			if not self.commands.has_key(mod):
				self.commands[mod] = []
			self.commands[mod].append((cmd,args))


#----  Log parser  ----{{{1

re_loghead = re.compile("This is [0-9a-zA-Z-]*(TeX|Omega)")
re_rerun = re.compile("LaTeX Warning:.*Rerun")
re_file = re.compile("(\\((?P<file>[^ \n\t(){}]*)|\\))")
re_badbox = re.compile(r"(Ov|Und)erfull \\[hv]box ")
re_line = re.compile(r"l\.(?P<line>[0-9]+)( (?P<text>.*))?$")
re_cseq = re.compile(r".*(?P<seq>\\[^ ]*)$")
re_page = re.compile("\[(?P<num>[0-9]+)\]")
re_atline = re.compile(
"( detected| in paragraph)? at lines? (?P<line>[0-9]*)(--(?P<last>[0-9]*))?")
re_reference = re.compile("LaTeX Warning: Reference `(?P<ref>.*)' \
on page (?P<page>[0-9]*) undefined on input line (?P<line>[0-9]*)\\.$")
re_label = re.compile("LaTeX Warning: (?P<msg>Label .*)$")
re_warning = re.compile(
"(LaTeX|Package)( (?P<pkg>.*))? Warning: (?P<msg>.*)$")
re_online = re.compile("(; reported)? on input line (?P<line>[0-9]*)")

class LogCheck (object):
	"""
	This class performs all the extraction of information from the log file.
	For efficiency, the instances contain the whole file as a list of strings
	so that it can be read several times with no disk access.
	"""
	#-- Initialization {{{2

	def __init__ (self):
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
		if not re_loghead.match(line):
			file.close()
			return 1
		self.lines = file.readlines()
		file.close()
		return 0

	#-- Process information {{{2

	def errors (self):
		"""
		Returns true if there was an error during the compilation.
		"""
		skipping = 0
		for line in self.lines:
			if line.strip() == "":
				skipping = 0
				continue
			if skipping:
				continue
			m = re_badbox.match(line)
			if m:
				skipping = 1
				continue
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

	#-- Information extraction {{{2

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
				if error == "Undefined control sequence.":
					# This is a special case in order to report which control
					# sequence is undefined.
					m = re_cseq.match(line)
					if m:
						error = "Undefined control sequence %s." % m.group("seq")
				m = re_line.match(line)
				if m:
					parsing = 0
					skipping = 1
					msg.error(error, code=m.group("text"),
						file=pos[-1], line=m.group("line"))
				elif line[0:3] == "***":
					parsing = 0
					skipping = 1
					msg.abort(error, line[4:])
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

	def show_boxes (self):
		"""
		Display all messages related so underfull and overfull boxes. Return 0
		if there is nothing to display.
		"""
		pos = ["(no file)"]
		page = 1
		something = 0
		skip = 0
		for line in self.lines:
			line = line.rstrip()
			if skip:
				if line == "": skip = 0
			elif re_badbox.match(line):
				mpos = { "file": pos[-1], "page": page }
				m = re_atline.search(line)
				if m:
					md = m.groupdict()
					for key in "line", "last":
						if md[key]: mpos[key] = md[key]
					line = line[:m.start()]
				msg.warn(line, **mpos)
				something = 1
				skip = 1
			else:
				self.update_file(line, pos)
				page = self.update_page(line, page)
		return something

	def show_references (self):
		"""
		Display all undefined or multiply defined references.
		"""
		pos = ["(no file)"]
		something = 0
		for line in self.lines:
			m = re_reference.match(line)
			if m:
				msg.warn(_("Reference `%s' undefined.") % m.group("ref"),
					file=pos[-1], **m.groupdict())
				something = 1
				continue
			m = re_label.match(line)
			if m:
				msg.warn(m.group("msg"), file=pos[-1])
			else:
				self.update_file(line, pos)
		return something

	def show_warnings (self):
		"""
		Display all warnings. This function parses LaTeX style warnings
		(possibly on several lines) and extracts the location in the sources,
		as well as the responsible package if there is one.
		"""
		pos = ["(no file)"]
		page = 1
		something = 0
		skip = 0
		prefix = None
		for line in self.lines:
			if skip:
				if line == "": skip = 0
			elif prefix is not None:
				if line[:len(prefix)] == prefix:
					text.append(string.strip(line[len(prefix):]))
				else:
					text = " ".join(text)
					m = re_online.search(text)
					if m:
						dict["line"] = m.group("line")
						text = text[:m.start()] + text[m.end():]
					msg.warn(text, **dict)
					prefix = None
					something = 1
			elif re_badbox.match(line):
				skip = 1
			elif line.find("Warning") != -1:
				m = re_warning.match(line)
				if m:
					dict = m.groupdict()
					dict["file"] = pos[-1]
					dict["page"] = page
					if dict["pkg"] is not None:
						prefix = ("(%s)" % dict["pkg"])
					else:
						prefix = ""
					prefix = prefix.ljust(m.start("msg"))
					text = [dict["msg"]]
			else:
				self.update_file(line, pos)
				page = self.update_page(line, page)
		return something

	def update_page (self, line, before):
		"""
		Parse the given line and return the number of the page that is being
		built after that line, assuming the current page before the line was
		`before'.
		"""
		ms = re_page.findall(line)
		if ms == []:
			return before
		return int(ms[-1]) + 1

#----  Parsing and compiling  ----{{{1

re_comment = re.compile(r"(?P<line>([^\\%]|\\%|\\)*)(%.*)?")
re_command = re.compile("[% ]*(rubber: *(?P<cmd>[^ ]*) *(?P<arg>.*))?.*")
re_input = re.compile("\\\\input +(?P<arg>[^{} \n\\\\]+)")

class EndDocument:
	""" This is the exception raised when \\end{document} is found. """
	pass

class EndInput:
	""" This is the exception raised when \\endinput is found. """
	pass

class LaTeXDep (Depend):
	"""
	This class represents dependency nodes for LaTeX compilation. It handles
	the cyclic LaTeX compilation until a stable output, including actual
	compilation (with a parametrable executable) and possible processing of
	compilation results (e.g. running BibTeX).

	Before building (or cleaning) the document, the method `parse' must be
	called to load and configure all required modules. Text lines are read
	from the files and parsed to extract LaTeX macro calls. When such a macro
	is found, a handler is searched for in the `hooks' dictionary. Handlers
	are called with one argument: the dictionary for the regular expression
	that matches the macro call.
	"""

	#--  Initialization  {{{2

	def __init__ (self, env):
		"""
		Initialize the environment. This prepares the processing steps for the
		given file (all steps are initialized empty) and sets the regular
		expressions and the hook dictionary.
		"""
		Depend.__init__(self, env)

		self.log = LogCheck()
		self.modules = Modules(self)

		self.vars = {
			"program": "latex",
			"engine": "TeX",
			"paper": "" }
		self.cmdline = ["\\nonstopmode\\input{%s}"]

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

		# description of the building process:

		self.aux_md5 = {}
		self.aux_old = {}
		self.watched_files = {}
		self.onchange_md5 = {}
		self.onchange_cmd = {}
		self.removed_files = []

		# state of the builder:

		self.processed_sources = {}

		self.must_compile = 0
		self.something_done = 0
		self.failed_module = None

	def set_source (self, path):
		"""
		Specify the main source for the document. The exact path and file name
		are determined, and the source building process is updated if needed,
		according the the source file's extension.
		"""
		name = self.env.find_file(path, ".tex")
		if not name:
			return 1
		self.sources = {}
		(self.src_path, name) = split(name)
		(self.src_base, self.src_ext) = splitext(name)
		if self.src_path == "":
			self.src_path = "."
			self.src_pbase = self.src_base
		else:
			self.env.path.append(self.src_path)
			self.src_pbase = join(self.src_path, self.src_base)

		self.prods = [self.src_base + ".dvi"]

		self.vars['job'] = self.src_base
		self.vars['base'] = self.src_pbase
		return 0

	def source (self):
		"""
		Return the main source's complete filename.
		"""
		return self.src_pbase + self.src_ext

	#--  LaTeX source parsing  {{{2

	def parse (self):
		"""
		Parse the source for packages and supported macros.
		"""
		try:
			self.process(self.source())
		except EndDocument:
			pass
		self.set_date()
		msg.log(_("dependencies: %r") % self.sources.keys())

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
		vars = self.vars
		vars['file'] = path

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
					vars['line'] = lineno
					args = parse_line(m.group("arg"), vars)
					self.command(m.group("cmd"), args, vars)
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

	def process (self, path, loc={}):
		"""
		This method is called when an included file is processed. The argument
		must be a valid file name.
		"""
		if self.processed_sources.has_key(path):
			msg.debug(_("%s already parsed") % path)
			return
		self.processed_sources[path] = None
		msg.log(_("parsing %s") % path)
		file = open(path)
		if not self.sources.has_key(path):
			self.sources[path] = DependLeaf(self.env, path, loc=loc)
		try:
			try:
				self.do_process(file, path)
			finally:
				file.close()
				msg.debug(_("end of %s") % path)
		except EndInput:
			pass

	def input_file (self, name, loc={}):
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

		for path in self.env.path:
			pname = join(path, name)
			dep = self.env.convert(pname, suffixes=[".tex",""], doc=self)
			if dep:
				dep.loc = loc
				file = dep.prods[0]
				self.sources[file] = dep
			else:
				file = self.env.find_file(name, ".tex")
				if not file:
					continue
				dep = None

			if dep is None or isinstance(dep, DependLeaf):
				self.process(file, loc)

			if dep is None:
				return file, self.sources[file]
			else:
				return file, dep

		return None, None

	#--  Directives  {{{2

	def command (self, cmd, args, pos={}):
		"""
		Execute the rubber command 'cmd' with arguments 'args'. This is called
		when a command is found in the source file or in a configuration file.
		A command name of the form 'foo.bar' is considered to be a command
		'bar' for module 'foo'. The argument 'pos' describes the position
		(file and line) where the command occurs.
		"""
		# Calls to this method are actually translated into calls to "do_*"
		# methods, except for calls to module directives.
		lst = string.split(cmd, ".", 1)
		if len(lst) > 1:
			self.modules.command(lst[0], lst[1], args)
		else:
			if hasattr(self, "do_" + cmd):
				try:
					getattr(self, "do_" + cmd)(*args)
				except:
					msg.warn(_("wrong syntax for '%s'") % cmd, **pos)
			else:
				msg.warn(_("unknown directive '%s'") % cmd, **pos)

	def do_clean (self, *args):
		self.removed_files.extend(args)

	def do_depend (self, *args):
		for arg in args:
			file = self.env.find_file(arg)
			if file:
				self.sources[file] = DependLeaf(self.env, file)
			else:
				msg.warn(_("dependency '%s' not found") % arg, **pos)

	def do_latex (self, arg):
		self.vars["program"] = arg

	def do_module (self, mod, opt=None):
		dict = { 'arg': mod, 'opt': opt }
		self.modules.register(mod, dict)

	def do_onchange (self, file, cmd):
		self.onchange_cmd[file] = cmd
		if exists(file):
			self.onchange_md5[file] = md5_file(file)
		else:
			self.onchange_md5[file] = None

	def do_paper (self, arg):
		self.vars["paper"] = arg

	def do_alias (self,name,val):
	    if self.hooks.has_key(val):
		self.hooks[name] = self.hooks[val]
		self.update_seq()
	    
	def do_path (self, name):
		self.env.path.append(expanduser(name))

	def do_read (self, name):
		try:
			file = open(name)
			for line in file.readlines():
				line = line.strip()
				if line == "" or line[0] == "%":
					continue
				lst = parse_line(line, pos)
				self.command(lst[0], lst[1:])
			file.close()
		except IOError:
			msg.warn(_("cannot read option file %s") % name) #, **pos)

	def do_watch (self, *args):
		for arg in args:
			self.watch_file(arg)


	#--  Macro handling  {{{2

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
			self.input_file(dict["arg"], dict)

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
		file, _ = self.input_file(dict["arg"], dict)
		if file:
			if file[-4:] == ".tex":
				file = file[:-4]
			aux = basename(file) + ".aux"
			self.removed_files.append(aux)
			self.aux_old[aux] = None
			if exists(aux):
				self.aux_md5[aux] = md5_file(aux)
			else:
				self.aux_md5[aux] = None

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
		file = self.env.find_file(dict["arg"] + ".cls")
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
			file = self.env.find_file(name + ".sty")
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

	#--  Compilation steps  {{{2

	def compile (self):
		"""
		Run one LaTeX compilation on the source. Return true if errors
		occured, and false if compilaiton succeeded.
		"""
		msg.progress(_("compiling %s") % self.source())
		
		file = self.source()
		cmd = [self.vars["program"]]
		cmd += map(lambda x: x.replace("%s",file), self.cmdline)
		inputs = string.join(self.env.path, ":")
		if inputs == "":
			env = {}
		else:
			inputs = inputs + ":" + os.getenv("TEXINPUTS", "")
			env = {"TEXINPUTS": inputs}
		
		self.env.execute(cmd, env)
		if self.log.read(self.src_base + ".log"):
			msg.error(_("Could not run %s.") % cmd[0])
			return 1
		if self.log.errors():
			return 1
		for aux, md5 in self.aux_md5.items():
			self.aux_old[aux] = md5
			self.aux_md5[aux] = md5_file(aux)
		return 0

	def pre_compile (self):
		"""
		Prepare the source for compilation using package-specific functions.
		This function must return true on failure. This function sets
		`must_compile' to 1 if we already know that a compilation is needed,
		because it may avoid some unnecessary preprocessing (e.g. BibTeXing).
		"""
		aux = self.src_base + ".aux"
		if os.path.exists(aux):
			self.aux_md5[aux] = md5_file(aux)
		else:
			self.aux_md5[aux] = None
		self.aux_old[aux] = None

		self.log.read(self.src_base + ".log")

		self.must_compile = 0
		self.must_compile = self.compile_needed()

		msg.log(_("building additional files..."))

		for mod in self.modules.objects.values():
			if mod.pre_compile():
				self.failed_module = mod
				return 1
		return 0
		

	def post_compile (self):
		"""
		Run the package-specific operations that are to be performed after
		each compilation of the main source. Returns true on failure.
		"""
		msg.log(_("running post-compilation scripts..."))

		for file, md5 in self.onchange_md5.items():
			if not exists(file):
				continue
			new = md5_file(file)
			if md5 != new:
				msg.progress(_("running %s") % self.onchange_cmd[file])
				self.env.execute(["sh", "-c", self.onchange_cmd[file]])
			self.onchange_md5[file] = new

		for mod in self.modules.objects.values():
			if mod.post_compile():
				self.failed_module = mod
				return 1
		return 0

	def clean (self, all=0):
		"""
		Remove all files that are produced by compilation.
		"""
		self.remove_suffixes([".log", ".aux", ".toc", ".lof", ".lot"])

		for file in self.prods + self.removed_files:
			if exists(file):
				msg.log(_("removing %s") % file)
				os.unlink(file)

		msg.log(_("cleaning additional files..."))

		for dep in self.sources.values():
			dep.clean()

		for mod in self.modules.objects.values():
			mod.clean()

	#--  Building routine  {{{2

	def force_run (self):
		return self.run(1)

	def run (self, force=0):
		"""
		Run the building process until the last compilation, or stop on error.
		This method supposes that the inputs were parsed to register packages
		and that the LaTeX source is ready. If the second (optional) argument
		is true, then at least one compilation is done. As specified by the
		class Depend, the method returns 0 on failure, 1 if nothing was done
		and 2 if something was done without failure.
		"""
		if self.pre_compile():
			return 1

		# If an error occurs after this point, it will be while LaTeXing.
		self.failed_dep = self
		self.failed_module = None

		if force or self.compile_needed():
			self.must_compile = 0
			if self.compile(): return 1
			if self.post_compile(): return 1
			while self.recompile_needed():
				self.must_compile = 0
				if self.compile(): return 1
				if self.post_compile(): return 1

		# Finally there was no error.
		self.failed_dep = None

		if self.something_done:
			self.date = int(time.time())
			return 1
		return 0

	def compile_needed (self):
		"""
		Returns true if a first compilation is needed. This method supposes
		that no compilation was done (by the script) yet.
		"""
		if self.must_compile:
			return 1
		msg.log(_("checking if compiling is necessary..."))
		if not exists(self.prods[0]):
			msg.debug(_("the output file doesn't exist"))
			return 1
		if not exists(self.src_base + ".log"):
			msg.debug(_("the log file does not exist"))
			return 1
		if getmtime(self.prods[0]) < getmtime(self.source()):
			msg.debug(_("the source is younger than the output file"))
			return 1
		if self.log.read(self.src_base + ".log"):
			msg.debug(_("the log file is not produced by TeX"))
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
			msg.debug(_("last compilation failed"))
			self.update_watches()
			return 1
		if self.deps_modified(getmtime(self.src_base + ".log")):
			msg.debug(_("dependencies were modified"))
			self.update_watches()
			return 1
		suffix = self.update_watches()
		if suffix:
			msg.debug(_("the %s file has changed") % suffix)
			return 1
		if self.log.run_needed():
			msg.debug(_("LaTeX asks to run again"))
			aux_changed = 0
			for aux, md5 in self.aux_md5.items():
				if md5 is not None and md5 != self.aux_old[aux]:
					aux_changed = 1
					break
			if not aux_changed:
				msg.debug(_("but the aux files are unchanged"))
				return 0
			return 1
		msg.debug(_("no new compilation is needed"))
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

	#--  Utility methods  {{{2

	def show_errors (self):
		if self.failed_module is None:
			self.log.show_errors()
		else:
			self.failed_module.show_errors()

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
				msg.log(_("removing %s") % file)
				os.unlink(file)


#----  Base classes for modules  ----{{{1

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
		document correctly. The method must return true on failure.
		"""
		return 0

	def post_compile (self):
		"""
		This method is called after each LaTeX compilation. It is supposed to
		process the compilation results and possibly request a new
		compilation. The method must return true on failure.
		"""
		return 0

	def clean (self):
		"""
		This method is called when cleaning the compiled files. It is supposed
		to remove all the files that this modules generates.
		"""

	def command (self, cmd, args):
		"""
		This is called when a directive for the module is found in the source.
		By default, when called with argument "foo" it calls the method
		"do_foo" if it exists, and fails otherwise.
		"""
		if hasattr(self, "do_" + cmd):
			try:
				getattr(self, "do_" + cmd)(*args)
			except TypeError:
				msg.warn(_("wrong syntax for %s") % cmd)

	def show_errors (self):
		"""
		This is called if something has failed during an operation performed
		by this module.
		"""

class ScriptModule (Module):
	"""
	This class represents modules that are defined as Rubber scripts.
	"""
	def __init__ (self, env, filename):
		vars = env.vars.copy()
		vars['file'] = filename
		lineno = 0
		file = open(filename)
		for line in file.readlines():
			line = line.strip()
			lineno = lineno + 1
			if line == "" or line[0] == "%":
				continue
			vars['line'] = lineno
			lst = parse_line(line, vars)
			env.command(lst[0], lst[1:], vars)
		file.close()
