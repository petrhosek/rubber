# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2006
"""
This is the main module of rubber. It includes code related to guessing of
conversion rules (the Converter class) and formatted message output (the
Message class and msg object). Environment is the main class containing all
information about a given building process.
"""

import os, os.path, sys, subprocess, thread
import re, string
from subprocess import Popen

# The function `_' is defined here to prepare for internationalization.
def _ (txt): return txt

from rubber.version import version, moddir
__version__ = version

#----  Message writers  ----{{{1

class Message (object):
	"""
	All messages in the program are output using the `msg' object in the
	main package. This class defines the interface for this object.
	"""
	def __init__ (self, level=1, write=None):
		"""
		Initialize the object with the specified verbosity level and an
		optional writing function. If no such function is specified, no
		message will be output until the 'write' field is changed.
		"""
		self.level = level
		self.write = write
		self.short = 0
		self.path = ""
		self.cwd = "./"
		self.pos = []

	def push_pos (self, pos):
		self.pos.append(pos)
	def pop_pos (self):
		del self.pos[-1]

	def __call__ (self, level, text):
		"""
		This is the low level printing function, it receives a line of text
		with an associated verbosity level, so that output can be filtered
		depending on command-line options.
		"""
		if self.write and level <= self.level:
			self.write(text, level=level)

	def display (self, kind, text, **info):
		"""
		Print an error or warning message. The argument 'kind' indicates the
		kind of message, among "error", "warning", "abort", the argument
		'text' is the main text of the message, the other arguments provide
		additional information, including the location of the error.
		"""
		if kind == "error":
			if text[0:13] == "LaTeX Error: ":
				text = text[13:]
			self(0, self.format_pos(info, text))
			if info.has_key("code") and info["code"] and not self.short:
				if info.has_key("macro"):
					del info["macro"]
				self(0, self.format_pos(info,
					_("leading text: ") + info["code"]))

		elif kind == "abort":
			if self.short:
				msg = _("compilation aborted ") + info["why"]
			else:
				msg = _("compilation aborted: %s %s") % (text, info["why"])
			self(0, self.format_pos(info, msg))

		elif kind == "warning":
			self(0, self.format_pos(info, text))

	def error (self, text, **info):
		self.display(kind="error", text=text, **info)
	def warn (self, what, **where):
		self(0, self.format_pos(where, what))
	def progress (self, what, **where):
		self(1, self.format_pos(where, what + "..."))
	def info (self, what, **where):
		self(2, self.format_pos(where, what))
	def log (self, what, **where):
		self(3, self.format_pos(where, what))
	def debug (self, what, **where):
		self(4, self.format_pos(where, what))

	def format_pos (self, where, text):
		"""
		Format the given text into a proper error message, with file and line
		information in the standard format. Position information is taken from
		the dictionary given as first argument.
		"""
		if len(self.pos) > 0:
			if where is None or not where.has_key("file"):
				where = self.pos[-1]
		elif where is None or where == {}:
			return text

		if where.has_key("file") and where["file"] is not None:
			pos = self.simplify(where["file"])
			if where.has_key("line") and where["line"]:
				pos = "%s:%d" % (pos, int(where["line"]))
				if where.has_key("last"):
					if where["last"] != where["line"]:
						pos = "%s-%d" % (pos, int(where["last"]))
			pos = pos + ": "
		else:
			pos = ""
		if where.has_key("macro"):
			text = "%s (in macro %s)" % (text, where["macro"])
		if where.has_key("page"):
			text = "%s (page %d)" % (text, int(where["page"]))
		if where.has_key("pkg"):
			text = "[%s] %s" % (where["pkg"], text)
		return pos + text

	def simplify (self, name):
		"""
		Simplify an path name by removing the current directory if the
		specified path is in a subdirectory.
		"""
		path = os.path.normpath(os.path.join(self.path, name))
		if path[:len(self.cwd)] == self.cwd:
			return path[len(self.cwd):]
		return path

	def display_all (self, generator):
		something = 0
		for msg in generator:
			self.display(**msg)
			something = 1
		return something

msg = Message()
from rubber.util import *


#----  Building environments  ----{{{1

import rubber.converters
import rubber.depend
from rubber.convert import Converter

re_kpse = re.compile("kpathsea: Running (?P<cmd>[^ ]*).* (?P<arg>[^ ]*)$")

class Environment:
	"""
	This class contains all state information related to the building process
	for a whole document, the dependency graph and conversion rules.
	"""
	def __init__ (self, cwd=None):
		"""
		Initialize the environment. The optional argument is the path to the
		reference directory for compilation, by default it is the current
		working directory.
		"""
		self.kpse_msg = {
			"mktextfm" : _("making font metrics for \\g<arg>"),
			"mktexmf" : _("making font \\g<arg>"),
			"mktexpk" : _("making bitmap for font \\g<arg>")
			}

		if cwd is None: cwd = os.getcwd()
		self.vars = Variables(items = { 'cwd': cwd, '_environment': self })
		self.path = [cwd]
		self.conv_prefs = {}
		self.depends = rubber.depend.Set()
		self.converter = Converter(self.depends)
		self.converter.read_ini(os.path.join(moddir, 'rules.ini'))
		
		self.main = None
		self.final = None

	def find_file (self, name, suffix=None):
		"""
		Look for a source file with the given name, and return either the
		complete path to the actual file or None if the file is not found.
		The optional argument is a suffix that may be added to the name.
		"""
		for path in self.path:
			test = os.path.join(path, name)
			if suffix and os.path.exists(test + suffix) and os.path.isfile(test + suffix):
				return test + suffix
			elif os.path.exists(test) and os.path.isfile(test):
				return test
		return None

	def set_source (self, name, jobname=None):
		"""
		Create a main dependency node from the given file name. If this name
		has an extension that is known of a preprocessor, this preprocessor is
		used, otherwise the name is that of a LaTeX source.
		"""
		src = None
		i = name.rfind(".")
		if i >= 0:
			ext = name[i+1:]
			if ext in ["w", "lhs"]:
				path = self.find_file(name)
				if not path:
					msg.error(_("cannot find %s") % name)
					return 1
				src = path[:-len(ext)] + "tex"
				if ext == "w":
					from rubber.converters.cweb import CWebDep
					self.src_node = CWebDep(self, src, path)
				elif ext == "lhs":
					from rubber.converters.lhs2TeX import LHSDep
					self.src_node = LHSDep(self, src, path)

		if src is None:
			path = self.find_file(name, ".tex")
			if not path:
				msg.error(_("cannot find %s") % name)
				return 1
			src = path
			self.src_node = None

		from rubber.converters.latex import LaTeXDep
		self.main = LaTeXDep(self)
		if os.path.exists(src):
			if self.main.set_source(src, jobname):
				return 1
		self.final = self.main
		return 0

	def make_source (self):
		"""
		Produce the source from its dependency rules, if needed.
		Returns 0 on success and 1 on failure.
		"""
		if self.src_node and self.main.sources == []:
			if self.src_node.make() == rubber.depend.ERROR:
				return 1
			src = self.src_node.products[0]
			self.main.set_source(src)
		return 0

	def conv_set (self, file, vars):
		"""
		Define preferences for the generation of a given file. The argument
		'file' is the name of the target and the argument 'vars' is a
		dictionary that contains imposed values for some variables.
		"""
		self.conv_prefs[file] = vars

	def convert (self, target, prefixes=[""], suffixes=[""], check=None, context=None):
		"""
		Use conversion rules to make a dependency tree for a given target
		file, and return the final node, or None if the file does not exist
		and cannot be built. The optional arguments 'prefixes' and 'suffixes'
		are lists of strings that can be added at the beginning and the end of
		the name when searching for the file. Prefixes are tried in order, and
		for each prefix, suffixes are tried in order; the first file from this
		order that exists or can be made is kept. The optional arguments
		'check' and 'context' have the same meaning as in
		'Converter.best_rule'.
		"""
		# Try all suffixes and prefixes until something is found.

		last = None
		for t in [p + target + s for s in suffixes for p in prefixes]:

			# Define a check function, according to preferences.

			if self.conv_prefs.has_key(t):
				prefs = self.conv_prefs[t]
				def do_check (vars, prefs=prefs):
					if prefs is not None:
						for key, val in prefs.items():
							if not (vars.has_key(key) and vars[key] == val):
								return 0
					return 1
			else:
				prefs = None
				do_check = check

			# Find the best applicable rule.

			ans = self.converter.best_rule(t, check=do_check, context=context)
			if ans is not None:
				if last is None or ans["cost"] < last["cost"]:
					last = ans

			# Check if the target exists.

			if prefs is None and os.path.exists(t):
				if last is not None and last["cost"] <= 0:
					break
				msg.log(_("`%s' is `%s', no rule applied") % (target, t))
				return rubber.depend.Leaf(self.depends, t)

		if last is None:
			return None
		msg.log(_("`%s' is `%s', made from `%s' by rule `%s'") %
				(target, last["target"], last["source"], last["name"]))
		return self.converter.apply(last)

	def may_produce (self, name):
		"""
		Return true if the given filename may be that of a file generated by
		any of the converters.
		"""
		return self.converter.may_produce(name)

	#--  Executing external programs  {{{2

	def execute (self, prog, env={}, pwd=None, out=None, kpse=0):
		"""
		Silently execute an external program. The `prog' argument is the list
		of arguments for the program, `prog[0]' is the program name. The `env'
		argument is a dictionary with definitions that should be added to the
		environment when running the program. The standard output is passed
		line by line to the `out' function (or discarded by default). In the
		optional argument `kpse' is true, the error output is parsed and
		messages from Kpathsea are processed (to indicate e.g. font
		compilation), otherwise the error output is kept untouched.
		"""
		msg.log(_("executing: %s") % string.join(prog))
		if pwd:
			msg.log(_("  in directory %s") % pwd)
		if env != {}:
			msg.log(_("  with environment: %r") % env)

		progname = prog_available(prog[0])
		if not progname:
			msg.error(_("%s not found") % prog[0])
			return 1

		penv = os.environ.copy()
		for (key,val) in env.items():
			penv[key] = val

		if kpse:
			stderr = subprocess.PIPE
		else:
			stderr = None

		process = Popen(prog,
			executable = progname,
			env = penv,
			cwd = pwd,
			stdout = subprocess.PIPE,
			stderr = stderr)

		if kpse:
			def parse_kpse ():
				for line in process.stderr.readlines():
					line = line.rstrip()
					match = re_kpse.match(line)
					if not match:
						continue
					cmd = match.group("cmd")
					if self.kpse_msg.has_key(cmd):
						msg.progress(match.expand(self.kpse_msg[cmd]))
					else:
						msg.progress(_("kpathsea running %s") % cmd)
			thread.start_new_thread(parse_kpse, ())

		if out is not None:
			for line in process.stdout.readlines():
				out(line)
		else:
			process.stdout.readlines()

		ret = process.wait()
		msg.log(_("process %d (%s) returned %d") % (process.pid, prog[0],ret))
		return ret
