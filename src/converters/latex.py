# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2006
"""
LaTeX document building system for Rubber.

This module contains all the code in Rubber that actually does the job of
building a LaTeX document from start to finish.
"""

import os, os.path, sys
import re
import string

from rubber import _
from rubber import *
from rubber.depend import Node
from rubber.version import moddir
import rubber.latex_modules

from rubber.tex import Parser, EOF, OPEN, SPACE, END_LINE

#----  Module handler  ----{{{1

class Modules:
	"""
	This class gathers all operations related to the management of modules.
	The modules are	searched for first in the current directory, then as
	scripts in the 'modules' directory in the program's data directort, then
	as a Python module in the package `rubber.latex'.
	"""
	def __init__ (self, env):
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
		Attempt to register a module with the specified name. If the module is
		already loaded, do nothing. If it is found and not yet loaded, then
		load it, initialise it (using the context passed as optional argument)
		and run any delayed commands for it.
		"""
		if self.has_key(name):
			msg.debug(_("module %s already registered") % name)
			return 2

		# First look for a script

		mod = None
		for path in "", os.path.join(moddir, "modules"):
			file = os.path.join(path, name + ".rub")
			if os.path.exists(file):
				mod = ScriptModule(self.env, file)
				msg.log(_("script module %s registered") % name)
				break

		# Then look for a Python module

		if not mod:
			try:
				file, path, descr = imp.find_module(name,
						rubber.latex_modules.__path__)
				pymodule = imp.load_module(name, file, path, descr)
				file.close()
				mod = PyModule(self.env, pymodule, dict)
				msg.log(_("built-in module %s registered") % name)
			except ImportError:
				msg.debug(_("no support found for %s") % name)
				return 0

		# Run any delayed commands.

		if self.commands.has_key(name):
			for (cmd, args, vars) in self.commands[name]:
				msg.push_pos(vars)
				try:
					# put the variables as they were when the directive was
					# found
					saved_vars = self.env.vars
					self.env.vars = vars
					try:
						# call the command
						mod.command(cmd, args)
					finally:
						# restore the variables to their current state
						self.env.vars = saved_vars
				except AttributeError:
					msg.warn(_("unknown directive '%s.%s'") % (name, cmd))
				except TypeError:
					msg.warn(_("wrong syntax for '%s.%s'") % (name, cmd))
				msg.pop_pos()
			del self.commands[name]

		self.objects[name] = mod
		return 1

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
			self.commands[mod].append((cmd, args, self.env.vars))


#----  Log parser  ----{{{1

re_loghead = re.compile("This is [0-9a-zA-Z-]*(TeX|Omega)")
re_rerun = re.compile("LaTeX Warning:.*Rerun")
re_file = re.compile("(\\((?P<file>[^ \n\t(){}]*)|\\))")
re_badbox = re.compile(r"(Ov|Und)erfull \\[hv]box ")
re_line = re.compile(r"(l\.(?P<line>[0-9]+)( (?P<code>.*))?$|<\*>)")
re_cseq = re.compile(r".*(?P<seq>(\\|\.\.\.)[^ ]*) ?$")
re_macro = re.compile(r"^(?P<macro>\\.*) ->")
re_page = re.compile("\[(?P<num>[0-9]+)\]")
re_atline = re.compile(
"( detected| in paragraph)? at lines? (?P<line>[0-9]*)(--(?P<last>[0-9]*))?")
re_reference = re.compile("LaTeX Warning: Reference `(?P<ref>.*)' \
on page (?P<page>[0-9]*) undefined on input line (?P<line>[0-9]*)\\.$")
re_label = re.compile("LaTeX Warning: (?P<text>Label .*)$")
re_warning = re.compile(
"(LaTeX|Package)( (?P<pkg>.*))? Warning: (?P<text>.*)$")
re_online = re.compile("(; reported)? on input line (?P<line>[0-9]*)")
re_ignored = re.compile("; all text was ignored after line (?P<line>[0-9]*).$")

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

	def continued (self, line):
		"""
		Check if a line in the log is continued on the next line. This is
		needed because TeX breaks messages at 79 characters per line. We make
		this into a method because the test is slightly different in Metapost.
		"""
		return len(line) == 79

	def parse (self, errors=0, boxes=0, refs=0, warnings=0):
		"""
		Parse the log file for relevant information. The named arguments are
		booleans that indicate which information should be extracted:
		- errors: all errors
		- boxes: bad boxes
		- refs: warnings about references
		- warnings: all other warnings
		The function returns a generator. Each generated item is a dictionary
		that contains (some of) the following entries:
		- kind: the kind of information ("error", "box", "ref", "warning")
		- text: the text of the error or warning
		- code: the piece of code that caused an error
		- file, line, last, pkg: as used by Message.format_pos.
		"""
		if not self.lines:
			return
		last_file = None
		pos = [last_file]
		page = 1
		parsing = 0    # 1 if we are parsing an error's text
		skipping = 0   # 1 if we are skipping text until an empty line
		something = 0  # 1 if some error was found
		prefix = None  # the prefix for warning messages from packages
		accu = ""      # accumulated text from the previous line
		macro = None   # the macro in which the error occurs
		cseqs = {}     # undefined control sequences so far
		for line in self.lines:
			line = line[:-1]  # remove the line feed

			# TeX breaks messages at 79 characters, just to make parsing
			# trickier...

			if not parsing and self.continued(line):
				accu += line
				continue
			line = accu + line
			accu = ""

			# Text that should be skipped (from bad box messages)

			if prefix is None and line == "":
				skipping = 0
				continue

			if skipping:
				continue

			# Errors (including aborted compilation)

			if parsing:
				if error == "Undefined control sequence.":
					# This is a special case in order to report which control
					# sequence is undefined.
					m = re_cseq.match(line)
					if m:
						seq = m.group("seq")
						if cseqs.has_key(seq):
							error = None
						else:
							cseqs[seq] = None
							error = "Undefined control sequence %s." % m.group("seq")
				m = re_macro.match(line)
				if m:
					macro = m.group("macro")
				m = re_line.match(line)
				if m:
					parsing = 0
					skipping = 1
					pdfTeX = string.find(line, "pdfTeX warning") != -1
					if error is not None and ((pdfTeX and warnings) or (errors and not pdfTeX)):
						if pdfTeX:
							d = {
								"kind": "warning",
								"pkg": "pdfTeX",
								"text": error[error.find(":")+2:]
							}
						else:
							d =	{
								"kind": "error",
								"text": error
							}
						d.update( m.groupdict() )
						m = re_ignored.search(error)
						if m:
							d["file"] = last_file
							if d.has_key("code"):
								del d["code"]
							d.update( m.groupdict() )
						elif pos[-1] is None:
							d["file"] = last_file
						else:
							d["file"] = pos[-1]
						if macro is not None:
							d["macro"] = macro
							macro = None
						yield d
				elif line[0] == "!":
					error = line[2:]
				elif line[0:3] == "***":
					parsing = 0
					skipping = 1
					if errors:
						yield	{
							"kind": "abort",
							"text": error,
							"why" : line[4:],
							"file": last_file
							}
				elif line[0:15] == "Type X to quit ":
					parsing = 0
					skipping = 0
					if errors:
						yield	{
							"kind": "error",
							"text": error,
							"file": pos[-1]
							}
				continue

			if len(line) > 0 and line[0] == "!":
				error = line[2:]
				parsing = 1
				continue

			if line == "Runaway argument?":
				error = line
				parsing = 1
				continue

			# Long warnings

			if prefix is not None:
				if line[:len(prefix)] == prefix:
					text.append(string.strip(line[len(prefix):]))
				else:
					text = " ".join(text)
					m = re_online.search(text)
					if m:
						info["line"] = m.group("line")
						text = text[:m.start()] + text[m.end():]
					if warnings:
						info["text"] = text
						d = { "kind": "warning" }
						d.update( info )
						yield d
					prefix = None
				continue

			# Undefined references

			m = re_reference.match(line)
			if m:
				if refs:
					d =	{
						"kind": "warning",
						"text": _("Reference `%s' undefined.") % m.group("ref"),
						"file": pos[-1]
						}
					d.update( m.groupdict() )
					yield d
				continue

			m = re_label.match(line)
			if m:
				if refs:
					d =	{
						"kind": "warning",
						"file": pos[-1]
						}
					d.update( m.groupdict() )
					yield d
				continue

			# Other warnings

			if line.find("Warning") != -1:
				m = re_warning.match(line)
				if m:
					info = m.groupdict()
					info["file"] = pos[-1]
					info["page"] = page
					if info["pkg"] is None:
						del info["pkg"]
						prefix = ""
					else:
						prefix = ("(%s)" % info["pkg"])
					prefix = prefix.ljust(m.start("text"))
					text = [info["text"]]
				continue

			# Bad box messages

			m = re_badbox.match(line)
			if m:
				if boxes:
					mpos = { "file": pos[-1], "page": page }
					m = re_atline.search(line)
					if m:
						md = m.groupdict()
						for key in "line", "last":
							if md[key]: mpos[key] = md[key]
						line = line[:m.start()]
					d =	{
						"kind": "warning",
						"text": line
						}
					d.update( mpos )
					yield d
				skipping = 1
				continue

			# If there is no message, track source names and page numbers.

			last_file = self.update_file(line, pos, last_file)
			page = self.update_page(line, page)

	def get_errors (self):
		return self.parse(errors=1)
	def get_boxes (self):
		return self.parse(boxes=1)
	def get_references (self):
		return self.parse(refs=1)
	def get_warnings (self):
		return self.parse(warnings=1)

	def update_file (self, line, stack, last):
		"""
		Parse the given line of log file for file openings and closings and
		update the list `stack'. Newly opened files are at the end, therefore
		stack[1] is the main source while stack[-1] is the current one. The
		first element, stack[0], contains the value None for errors that may
		happen outside the source. Return the last file from which text was
		read (the new stack top, or the one before the last closing
		parenthesis).
		"""
		m = re_file.search(line)
		while m:
			if line[m.start()] == '(':
				last = m.group("file")
				stack.append(last)
			else:
				last = stack[-1]
				del stack[-1]
			line = line[m.end():]
			m = re_file.search(line)
		return last

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

re_command = re.compile("%[% ]*rubber: *(?P<cmd>[^ ]*) *(?P<arg>.*).*")

class SourceParser (Parser):
	"""
	Extends the general-purpose TeX parser to handle Rubber directives in the
	comment lines.
	"""
	def __init__ (self, file, dep):
		Parser.__init__(self, file)
		self.latex_dep = dep

	def read_line (self):
		while Parser.read_line(self):
			match = re_command.match(self.line.strip())
			if match is None:
				return True

			vars = dict(self.latex_dep.vars.items())
			vars['line'] = self.pos_line
			args = parse_line(match.group("arg"), vars)

			self.latex_dep.command(match.group("cmd"), args, vars)
		return False

	def skip_until (self, expr):
		regexp = re.compile(expr)
		while Parser.read_line(self):
			match = regexp.match(self.line)
			if match is None:
				continue
			self.line = self.line[match.end():]
			self.pos_char += match.end()
			return

class EndDocument:
	""" This is the exception raised when \\end{document} is found. """
	pass

class EndInput:
	""" This is the exception raised when \\endinput is found. """
	pass

class LaTeXDep (Node):
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
		Node.__init__(self, env.depends)
		self.env = env

		self.log = LogCheck()
		self.modules = Modules(self)

		self.vars = Variables(env.vars, {
			"program": "latex",
			"engine": "TeX",
			"paper": "",
			"arguments": [],
			"src-specials": "",
			"source": None,
			"target": None,
			"path": None,
			"base": None,
			"ext": None,
			"job": None,
			"graphics_suffixes" : [] })
		self.vars_stack = []

		self.cmdline = ["\\nonstopmode", "\\input{%s}"]

		# the initial hooks:

		self.comment_mark = "%"

		self.hooks = {
			"begin": ("a", self.h_begin),
			"end": ("a", self.h_end),
			"pdfoutput": ("", self.h_pdfoutput),
			"input" : ("", self.h_input),
			"include" : ("a", self.h_include),
			"includeonly": ("a", self.h_includeonly),
			"usepackage" : ("oa", self.h_usepackage),
			"RequirePackage" : ("oa", self.h_usepackage),
			"documentclass" : ("oa", self.h_documentclass),
			"LoadClass" : ("oa", self.h_documentclass),
			"LoadClassWithOptions" : ("a", self.h_documentclass),
			"tableofcontents" : ("", self.h_tableofcontents),
			"listoffigures" : ("", self.h_listoffigures),
			"listoftables" : ("", self.h_listoftables),
			"bibliography" : ("a", self.h_bibliography),
			"bibliographystyle" : ("a", self.h_bibliographystyle),
			"endinput" : ("", self.h_endinput)
		}
		self.begin_hooks = {
			"verbatim": self.h_begin_verbatim,
			"verbatim*": lambda loc: self.h_begin_verbatim(loc, env="verbatim\\*")
		}
		self.end_hooks = {
			"document": self.h_end_document
		}
		self.hooks_changed = True

		self.include_only = {}

		# description of the building process:

		self.aux_md5 = {}
		self.aux_old = {}
		self.watched_files = {}
		self.onchange_md5 = {}
		self.onchange_cmd = {}
		self.removed_files = []
		self.not_included = []  # dependencies that don't trigger latex

		# state of the builder:

		self.processed_sources = {}

		self.must_compile = 0
		self.something_done = 0
		self.failed_module = None

	def set_source (self, path, jobname=None):
		"""
		Specify the main source for the document. The exact path and file name
		are determined, and the source building process is updated if needed,
		according the the source file's extension. The optional argument
		'jobname' can be used to specify the job name to something else that
		the base of the file name.
		"""
		name = self.env.find_file(path, ".tex")
		if not name:
			msg.error(_("cannot find %s") % name)
			return 1
		self.reset_sources()
		self.vars['source'] = name
		(src_path, name) = os.path.split(name)
		self.vars['path'] = src_path
		(job, self.vars['ext']) = os.path.splitext(name)
		if jobname is None:
			self.set_job = 0
		else:
			self.set_job = 1
			job = jobname
		self.vars['job'] = job
		if src_path == "":
			src_path = "."
			self.vars['base'] = job
		else:
			self.env.path.append(src_path)
			self.vars['base'] = os.path.join(src_path, job)

		source = self.source()
		prefix = os.path.join(self.vars["cwd"], "")
		if source[:len(prefix)] == prefix:
			comp_name = source[len(prefix):]
		else:
			comp_name = source
		if comp_name.find('"') >= 0:
			msg.error(_("The filename contains \", latex cannot handle this."))
			return 1
		for c in " \n\t()":
			if source.find(c) >= 0:
				msg.warn(_("Source path uses special characters, error tracking might get confused."))
				break

		self.vars['target'] = self.target = os.path.join(prefix, job)
		self.reset_products([self.target + ".dvi"])

		return 0

	def includeonly (self, files):
		"""
		Use partial compilation, by appending a call to \\inlcudeonly on the
		command line on compilation.
		"""
		if self.vars["engine"] == "VTeX":
			msg.error(_("I don't know how to do partial compilation on VTeX."))
			return
		if self.cmdline[-2][:13] == "\\includeonly{":
			self.cmdline[-2] = "\\includeonly{" + ",".join(files) + "}"
		else:
			self.cmdline.insert(-1, "\\includeonly{" + ",".join(files) + "}")
		for f in files:
			self.include_only[f] = None

	def source (self):
		"""
		Return the main source's complete filename.
		"""
		return self.vars['source']

	def abspath (self, name, ref=None):
		"""
		Return the absolute path of a given filename. Relative paths are
		considered relative to the file currently processed, the optional
		argument "ref" can be used to override the reference file name.
		"""
		path = self.vars["cwd"]
		if ref is None and self.vars.has_key("file"):
			ref = self.vars["file"]
		if ref is not None:
			path = os.path.join(path, os.path.dirname(ref))
		return os.path.abspath(os.path.join(path, os.path.expanduser(name)))

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
		msg.log(_("dependencies: %r") % self.sources)

	def parse_file (self, file):
		"""
		Process a LaTeX source. The file must be open, it is read to the end
		calling the handlers for the macro calls. This recursively processes
		the included sources.
		"""
		parser = SourceParser(file, self)
		parser.set_hooks(self.hooks.keys())
		self.hooks_changed = False
		while True:
			if self.hooks_changed:
				parser.set_hooks(self.hooks.keys())
				self.hooks_changed = False
			token = parser.next_hook()
			if token.cat == EOF:
				break
			format, function = self.hooks[token.val]
			args = []
			for arg in format:
				if arg == 'a':
					args.append(parser.get_argument_text())
				elif arg == 'o':
					args.append(parser.get_latex_optional_text())
			self.parser = parser
			self.vars['line'] = parser.pos_line
			function(self.vars, *args)

	def process (self, path):
		"""
		This method is called when an included file is processed. The argument
		must be a valid file name.
		"""
		if self.processed_sources.has_key(path):
			msg.debug(_("%s already parsed") % path)
			return
		self.processed_sources[path] = None
		if path not in self.sources:
			self.add_source(path)

		try:
			saved_vars = self.vars
			try:
				msg.log(_("parsing %s") % path)
				self.vars = Variables(saved_vars,
					{ "file": path, "line": None })
				file = open(path)
				try:
					self.parse_file(file)
				finally:
					file.close()

			finally:
				self.vars = saved_vars
				msg.debug(_("end of %s") % path)

		except EndInput:
			pass

	def input_file (self, name, loc={}):
		"""
		Treat the given name as a source file to be read. If this source can
		be the result of some conversion, then the conversion is performed,
		otherwise the source is parsed. The returned value is a couple
		(name,dep) where `name' is the actual LaTeX source and `dep' is
		its dependency node. The return value is (None,None) if the source
		could neither be read nor built.
		"""
		if name.find("\\") >= 0 or name.find("#") >= 0:
			return None, None

		for path in self.env.path:
			pname = os.path.join(path, name)
			dep = self.env.convert(pname, suffixes=[".tex",""], context=self.vars)
			if dep:
				file = dep.products[0]
			else:
				file = self.env.find_file(name, ".tex")
				if not file:
					continue
				dep = None
			self.add_source(file)

			if dep is None or dep.is_leaf():
				self.process(file)

			if dep is None:
				return file, self.set[file]
			else:
				return file, dep

		return None, None

	#--  Directives  {{{2

	def command (self, cmd, args, pos=None):
		"""
		Execute the rubber command 'cmd' with arguments 'args'. This is called
		when a command is found in the source file or in a configuration file.
		A command name of the form 'foo.bar' is considered to be a command
		'bar' for module 'foo'. The argument 'pos' describes the position
		(file and line) where the command occurs.
		"""
		if pos is None:
			pos = self.vars
		# Calls to this method are actually translated into calls to "do_*"
		# methods, except for calls to module directives.
		lst = string.split(cmd, ".", 1)
		#try:
		if len(lst) > 1:
			self.modules.command(lst[0], lst[1], args)
		elif not hasattr(self, "do_" + cmd):
			msg.warn(_("unknown directive '%s'") % cmd, **pos)
		else:
			getattr(self, "do_" + cmd)(*args)
		#except TypeError:
		#	msg.warn(_("wrong syntax for '%s'") % cmd, **pos)

	def do_alias (self, name, val):
		if self.hooks.has_key(val):
			self.hooks[name] = self.hooks[val]
			self.hooks_changed = True

	def do_clean (self, *args):
		for file in args:
			self.removed_files.append(self.abspath(file))

	def do_depend (self, *args):
		for arg in args:
			file = self.env.find_file(arg)
			if file:
				self.add_source(file)
			else:
				msg.warn(_("dependency '%s' not found") % arg, **self.vars)

	def do_make (self, file, *args):
		file = self.abspath(file)
		vars = { "target": file }
		while len(args) > 1:
			if args[0] == "from":
				vars["source"] = self.abspath(args[1])
			elif args[0] == "with":
				vars["name"] = args[1]
			else:
				break
			args = args[2:]
		if len(args) != 0:
			msg.error(_("invalid syntax for 'make'"), **self.vars)
			return
		self.env.conv_set(file, vars)

	def do_module (self, mod, opt=None):
		dict = { 'arg': mod, 'opt': opt }
		self.modules.register(mod, dict)

	def do_onchange (self, file, cmd):
		file = self.abspath(file)
		self.onchange_cmd[file] = cmd
		if os.path.exists(file):
			self.onchange_md5[file] = md5_file(file)
		else:
			self.onchange_md5[file] = None

	def do_paper (self, arg):
		self.vars["paper"] = arg

	def do_path (self, name):
		self.env.path.append(self.abspath(name))

	def do_read (self, name):
		path = self.abspath(name)
		self.push_vars(file=path, line=None)
		try:
			file = open(path)
			lineno = 0
			for line in file.readlines():
				lineno += 1
				line = line.strip()
				if line == "" or line[0] == "%":
					continue
				self.vars["line"] = lineno
				lst = parse_line(line, self.vars)
				self.command(lst[0], lst[1:])
			file.close()
		except IOError:
			msg.warn(_("cannot read option file %s") % name, **self.vars)
		self.pop_vars()

	def do_rules (self, file):
		name = self.env.find_file(file)
		if name is None:
			msg.warn(_("cannot read rule file %s") % file, **self.vars)
		else:
			self.env.converter.read_ini(name)

	def do_set (self, name, *val):
		if name in self.vars:
			self.vars[name] = val[0]
		elif len(val) != 1:
			raise TypeError()
		else:
			self.vars[name] = val[0]

	def do_watch (self, *args):
		for arg in args:
			self.watch_file(self.abspath(arg))


	#--  Macro handling  {{{2

	def hook_macro (self, name, format, fun):
		self.hooks[name] = (format, fun)
		self.hooks_changed = True

	def hook_begin (self, name, fun):
		self.begin_hooks[name] = fun

	def hook_end (self, name, fun):
		self.end_hooks[name] = fun

	# Now the macro handlers:

	def h_begin (self, loc, env):
		if self.begin_hooks.has_key(env):
			self.begin_hooks[env](loc)

	def h_end (self, loc, env):
		if self.end_hooks.has_key(env):
			self.end_hooks[env](loc)

	def h_pdfoutput (self, loc):
		"""
		Called when \\pdfoutput is found. Tries to guess if it is a definition
		that asks for the output to be in PDF or DVI.
		"""
		parser = self.parser
		token = parser.get_token()
		if token.raw == '=':
			token2 = parser.get_token()
			if token2.raw == '0':
				mode = 0
			elif token2.raw == '1':
				mode = 1
			else:
				parser.put_token(token2)
				return
		elif token.raw == '0':
			mode = 0
		elif token.raw == '1':
			mode = 1
		else:
			parser.put_token(token)
			return

		if mode == 0:
			if 'pdftex' in self.modules:
				self.modules['pdftex'].pymodule.mode_dvi()
			else:
				self.modules.register('pdftex', {'opt': 'dvi'})
		else:
			if 'pdftex' in self.modules:
				self.modules['pdftex'].pymodule.mode_pdf()
			else:
				self.modules.register('pdftex')

	def h_input (self, loc):
		"""
		Called when an \\input macro is found. This calls the `process' method
		if the included file is found.
		"""
		token = self.parser.get_token()
		if token.cat == OPEN:
			file = self.parser.get_group_text()
		else:
			file = ""
			while token.cat not in (EOF, SPACE, END_LINE):
				file += token.raw
				token = self.parser.get_token()
		self.input_file(file, loc)

	def h_include (self, loc, filename):
		"""
		Called when an \\include macro is found. This includes files into the
		source in a way very similar to \\input, except that LaTeX also
		creates .aux files for them, so we have to notice this.
		"""
		if self.include_only and not self.include_only.has_key(filename):
			return
		file, _ = self.input_file(filename, loc)
		if file:
			aux = filename + ".aux"
			self.removed_files.append(aux)
			self.aux_old[aux] = None
			if os.path.exists(aux):
				self.aux_md5[aux] = md5_file(aux)
			else:
				self.aux_md5[aux] = None

	def h_includeonly (self, loc, files):
		"""
		Called when the macro \\includeonly is found, indicates the
		comma-separated list of files that should be included, so that the
		othe \\include are ignored.
		"""
		self.include_only = {}
		for name in files.split(","):
			name = name.strip()
			if name != "":
				self.include_only[name] = None

	def h_documentclass (self, loc, opt, name):
		"""
		Called when the macro \\documentclass is found. It almost has the same
		effect as `usepackage': if the source's directory contains the class
		file, in which case this file is treated as an input, otherwise a
		module is searched for to support the class.
		"""
		file = self.env.find_file(name + ".cls")
		if file:
			self.process(file)
		else:
			dict = Variables(self.vars, { 'opt': opt })
			self.modules.register(name, dict)

	def h_usepackage (self, loc, opt, names):
		"""
		Called when a \\usepackage macro is found. If there is a package in the
		directory of the source file, then it is treated as an include file
		unless there is a supporting module in the current directory,
		otherwise it is treated as a package.
		"""
		for name in string.split(names, ","):
			name = name.strip()
			file = self.env.find_file(name + ".sty")
			if file and not os.path.exists(name + ".py"):
				self.process(file)
			else:
				dict = Variables(self.vars, { 'opt': opt })
				self.modules.register(name, dict)

	def h_tableofcontents (self, loc):
		self.watch_file(self.target + ".toc")
	def h_listoffigures (self, loc):
		self.watch_file(self.target + ".lof")
	def h_listoftables (self, loc):
		self.watch_file(self.target + ".lot")

	def h_bibliography (self, loc, names):
		"""
		Called when the macro \\bibliography is found. This method actually
		registers the module bibtex (if not already done) and registers the
		databases.
		"""
		self.modules.register("bibtex", dict)
		# This registers the actual hooks, so that subsequent occurrences of
		# \bibliography and \bibliographystyle will be caught by the module.
		# However, the first time, we have to call the hooks from here. The
		# line below assumes that the new hook has the same syntax.
		self.hooks['bibliography'][1](loc, names)

	def h_bibliographystyle (self, loc, name):
		"""
		Called when \\bibliographystyle is found. This registers the module
		bibtex (if not already done) and calls the method set_style() of the
		module.
		"""
		self.modules.register("bibtex", dict)
		# The same remark as in 'h_bibliography' applies here.
		self.hooks['bibliographystyle'][1](loc, name)

	def h_begin_verbatim (self, dict, env="verbatim"):
		"""
		Called when \\begin{verbatim} is found. This disables all macro
		handling and comment parsing until the end of the environment. The
		optional argument 'end' specifies the end marker, by default it is
		"\\end{verbatim}".
		"""
		self.parser.skip_until(r"[ \t]*\\end\{%s\}.*" % env)

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
		Run one LaTeX compilation on the source. Return true on success or
		false if errors occured.
		"""
		msg.progress(_("compiling %s") % msg.simplify(self.source()))

		file = self.source()

		prefix = os.path.join(self.vars["cwd"], "")
		if file[:len(prefix)] == prefix:
			file = file[len(prefix):]
		if file.find(" ") >= 0:
			file = '"%s"' % file

		cmd = [self.vars["program"]]

		if self.set_job:
			if self.vars["engine"] == "VTeX":
				msg.error(_("I don't know how set the job name with %s.")
					% self.vars["engine"])
			else:
				cmd.append("-jobname=" + self.vars["job"])

		specials = self.vars["src-specials"]
		if specials != "":
			if self.vars["engine"] == "VTeX":
				msg.warn(_("I don't know how to make source specials with %s.")
					% self.vars["engine"])
				self.vars["src-specials"] = ""
			elif specials == "yes":
				cmd.append("-src-specials")
			else:
				cmd.append("-src-specials=" + specials)

		cmd += self.vars["arguments"]

		cmd += [x.replace("%s",file) for x in self.cmdline]

		# Remove the CWD from elements inthe path, to avoid potential problems
		# with special characters if there are any (except that ':' in paths
		# is not handled).

		prefix = self.env.vars["cwd"]
		prefix_ = os.path.join(prefix, "")
		paths = []
		for p in self.env.path:
			if p == prefix:
				paths.append(".")
			elif p[:len(prefix_)] == prefix_:
				paths.append("." + p[len(prefix):])
			else:
				paths.append(p)
		inputs = string.join(paths, ":")

		if inputs == "":
			env = {}
		else:
			inputs = inputs + ":" + os.getenv("TEXINPUTS", "")
			env = {"TEXINPUTS": inputs}

		self.env.execute(cmd, env, kpse=1)
		self.something_done = 1

		if self.log.read(self.target + ".log"):
			msg.error(_("Could not run %s.") % cmd[0])
			return False
		if self.log.errors():
			return False
		if not os.access(self.products[0], os.F_OK):
			msg.error(_("Output file `%s' was not produced.") %
				msg.simplify(self.products[0]))
			return False
		for aux, md5 in self.aux_md5.items():
			self.aux_old[aux] = md5
			self.aux_md5[aux] = md5_file(aux)
		return True

	def pre_compile (self, force):
		"""
		Prepare the source for compilation using package-specific functions.
		This function must return False on failure. This function sets
		`must_compile' to True if we already know that a compilation is
		needed, because it may avoid some unnecessary preprocessing (e.g.
		BibTeXing).
		"""
		aux = self.target + ".aux"
		if os.path.exists(aux):
			self.aux_md5[aux] = md5_file(aux)
		else:
			self.aux_md5[aux] = None
		self.aux_old[aux] = None

		self.log.read(self.target + ".log")

		self.must_compile = force
		self.must_compile = self.compile_needed()

		msg.log(_("building additional files..."))

		for mod in self.modules.objects.values():
			if not mod.pre_compile():
				self.failed_module = mod
				return False
		return True

	def post_compile (self):
		"""
		Run the package-specific operations that are to be performed after
		each compilation of the main source. Returns true on success or false
		on failure.
		"""
		msg.log(_("running post-compilation scripts..."))

		for file, md5 in self.onchange_md5.items():
			if not os.path.exists(file):
				continue
			new = md5_file(file)
			if md5 != new:
				msg.progress(_("running %s") % self.onchange_cmd[file])
				self.env.execute(["sh", "-c", self.onchange_cmd[file]])
			self.onchange_md5[file] = new

		for mod in self.modules.objects.values():
			if not mod.post_compile():
				self.failed_module = mod
				return False
		return True

	def clean (self, all=0):
		"""
		Remove all files that are produced by compilation.
		"""
		self.remove_suffixes([".log", ".aux", ".toc", ".lof", ".lot"])

		for file in self.products + self.removed_files:
			if os.path.exists(file):
				msg.log(_("removing %s") % file)
				os.unlink(file)

		msg.log(_("cleaning additional files..."))

		for dep in self.source_nodes():
			dep.clean()

		for mod in self.modules.objects.values():
			mod.clean()

	#--  Building routine  {{{2

	def force_run (self):
		return self.run(True)

	def run (self, force=False):
		"""
		Run the building process until the last compilation, or stop on error.
		This method supposes that the inputs were parsed to register packages
		and that the LaTeX source is ready. If the second (optional) argument
		is true, then at least one compilation is done. As specified by the
		class depend.Node, the method returns True on success and False on
		failure.
		"""
		if not self.pre_compile(force):
			return False

		# If an error occurs after this point, it will be while LaTeXing.
		self.failed_dep = self
		self.failed_module = None

		if force or self.compile_needed():
			self.must_compile = False
			if not self.compile():
				return False
			if not self.post_compile():
				return False
			while self.recompile_needed():
				self.must_compile = False
				if not self.compile():
					return False
				if not self.post_compile():
					return False

		# Finally there was no error.
		self.failed_dep = None

		if self.something_done:
			self.date = int(time.time())
		return True

	def compile_needed (self):
		"""
		Returns true if a first compilation is needed. This method supposes
		that no compilation was done (by the script) yet.
		"""
		if self.must_compile:
			return 1
		msg.log(_("checking if compiling is necessary..."))
		if not os.path.exists(self.products[0]):
			msg.debug(_("the output file doesn't exist"))
			return 1
		if not os.path.exists(self.target + ".log"):
			msg.debug(_("the log file does not exist"))
			return 1
		if os.path.getmtime(self.products[0]) < os.path.getmtime(self.source()):
			msg.debug(_("the source is younger than the output file"))
			return 1
		if self.log.read(self.target + ".log"):
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
		if self.deps_modified(os.path.getmtime(self.products[0])):
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
		for name in self.sources:
			if name in self.not_included:
				continue
			node = self.set[name]
			if node.date > date:
				return True
		return False

	#--  Utility methods  {{{2

	def get_errors (self):
		if self.failed_module is None:
			return self.log.get_errors()
		else:
			return self.failed_module.get_errors()

	def watch_file (self, file):
		"""
		Register the given file (typically "jobname.toc" or such) to be
		watched. When the file changes during a compilation, it means that
		another compilation has to be done.
		"""
		if os.path.exists(file):
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
			if os.path.exists(file):
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
			file = self.target + suffix
			if os.path.exists(file):
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
		document correctly. The method must return true on success.
		"""
		return True

	def post_compile (self):
		"""
		This method is called after each LaTeX compilation. It is supposed to
		process the compilation results and possibly request a new
		compilation. The method must return true on success.
		"""
		return True

	def clean (self):
		"""
		This method is called when cleaning the compiled files. It is supposed
		to remove all the files that this modules generates.
		"""

	def command (self, cmd, args):
		"""
		This is called when a directive for the module is found in the source.
		The method can raise 'AttributeError' when the directive does not
		exist and 'TypeError' if the syntax is wrong. By default, when called
		with argument "foo" it calls the method "do_foo" if it exists, and
		fails otherwise.
		"""
		getattr(self, "do_" + cmd)(*args)

	def get_errors (self):
		"""
		This is called if something has failed during an operation performed
		by this module. The method returns a generator with items of the same
		form as in LaTeXDep.get_errors.
		"""
		if None:
			yield None

class ScriptModule (Module):
	"""
	This class represents modules that are defined as Rubber scripts.
	"""
	def __init__ (self, env, filename):
		vars = Variables(env.vars, {
			'file': filename,
			'line': None })
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

class PyModule (Module):
	def __init__ (self, document, pymodule, context):
		self.pymodule = pymodule
		if hasattr(pymodule, 'setup'):
			pymodule.setup(document, context)

	def pre_compile (self):
		if hasattr(self.pymodule, 'pre_compile'):
			return self.pymodule.pre_compile()
		return True

	def post_compile (self):
		if hasattr(self.pymodule, 'post_compile'):
			return self.pymodule.post_compile()
		return True

	def clean (self):
		if hasattr(self.pymodule, 'clean'):
			self.pymodule.clean()

	def command (self, cmd, args):
		if hasattr(self.pymodule, 'command'):
			self.pymodule.command(cmd, args)
		else:
			getattr(self.pymodule, "do_" + cmd)(*args)

	def get_errors (self):
		if hasattr(self.pymodule, 'get_errors'):
			return self.pymodule.get_errors()
		return []
