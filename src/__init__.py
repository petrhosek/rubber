# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2005
"""
LaTeX document building system for Rubber.

This module contains all the code in Rubber that actually does the job of
building a LaTeX document from start to finish.
"""

# Stop python 2.2 from calling "yield" statements syntax errors.
from __future__ import generators

import os, sys, posix
from os.path import *
import re
import string

# The function `_' is defined here to prepare for internationalization.
def _ (txt): return txt

from rubber.version import moddir

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
		if where is None or where == {}:
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
		path = normpath(join(self.path, name))
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

#----  Dependency nodes  ----{{{1

class Depend (object): #{{{2
	"""
	This is a base class to represent file dependencies. It provides the base
	functionality of date checking and recursive making, supposing the
	existence of a method `run()' in the object. This method is supposed to
	rebuild the files of this node, returning zero on success and something
	else on failure.
	"""
	def __init__ (self, env, prods=[], sources={}, loc={}):
		"""
		Initialize the object for a given set of output files and a given set
		of sources. The argument `prods' is a list of file names, and the
		argument `sources' is a dictionary that associates file names with
		dependency nodes. The optional argument `loc' is a dictionary that
		describes where in the sources this dependency was created.
		"""
		self.env = env
		self.prods = prods
		self.set_date()
		self.sources = sources
		self.making = 0
		self.failed_dep = None
		self.loc = loc

	def set_date (self):
		"""
		Define the date of the last build of this node as that of the most
		recent file among the products. If some product does not exist or
		there are ne products, the date is set to None.
		"""
		if self.prods == []:
			# This is a special case used in rubber.Environment
			self.date = None
		else:
			try:
				# We set the node's date to that of the most recently modified
				# product file, assuming all other files were up to date then
				# (though not necessarily modified).
				self.date = max(map(getmtime, self.prods))
			except OSError:
				# If some product file does not exist, set the last
				# modification date to None.
				self.date = None

	def should_make (self):
		"""
		Check the dependencies. Return true if this node has to be recompiled,
		i.e. if some dependency is modified. Nothing recursive is done here.
		"""
		if not self.date:
			return 1
		for src in self.sources.values():
			if src.date > self.date:
				return 1
		return 0

	def make (self, force=0):
		"""
		Make the destination file. This recursively makes all dependencies,
		then compiles the target if dependencies were modified. The semantics
		of the return value is the following:
		- 0 means that the process failed somewhere (in this node or in one of
		  its dependencies)
		- 1 means that nothing had to be done
		- 2 means that something was recompiled (therefore nodes that depend
		  on this one have to be remade)
		"""
		if self.making:
			print "FIXME: cyclic make"
			return 1
		self.making = 1

		# Make the sources

		self.failed_dep = None
		must_make = force
		for src in self.sources.values():
			ret = src.make()
			if ret == 0:
				self.making = 0
				self.failed_dep = src.failed_dep
				return 0
			if ret == 2:
				must_make = 1
		
		# Make this node if necessary

		if must_make or self.should_make():
			if force:
				ret = self.force_run()
			else:
				ret = self.run()
			if ret:
				self.making = 0
				self.failed_dep = self
				return 0

			# Here we must take the integer part of the value returned by
			# time.time() because the modification times for files, returned
			# by os.path.getmtime(), is an integer. Keeping the fractional
			# part could lead to errors in time comparison with the main log
			# file when the compilation of the document is shorter than one
			# second...

			self.date = int(time.time())
			self.making = 0
			return 2
		self.making = 0
		return 1

	def force_run (self):
		"""
		This method is called instead of 'run' when rebuilding this node was
		forced. By default it is equivalent to 'run'.
		"""
		return self.run()

	def failed (self):
		"""
		Return a reference to the node that caused the failure of the last
		call to "make". If there was no failure, return None.
		"""
		return self.failed_dep

	def get_errors (self):
		"""
		Report the errors that caused the failure of the last call to run.
		"""
		if None:
			yield None

	def clean (self):
		"""
		Remove the files produced by this rule and recursively clean all
		dependencies.
		"""
		for file in self.prods:
			if exists(file):
				msg.log(_("removing %s") % file)
				os.unlink(file)
		for src in self.sources.values():
			src.clean()
		self.date = None

	def leaves (self):
		"""
		Return a list of all source files that are required by this node and
		cannot be built, i.e. the leaves of the dependency tree.
		"""
		if self.sources == {}:
			return self.prods
		ret = []
		for dep in self.sources.values():
			ret.extend(dep.leaves())
		return ret

class DependLeaf (Depend): #{{{2
	"""
	This class specializes Depend for leaf nodes, i.e. source files with no
	dependencies.
	"""
	def __init__ (self, env, *dest, **args):
		"""
		Initialize the node. The arguments of this method are the file
		names, since one single node may contain several files.
		"""
		Depend.__init__(self, env, prods=list(dest), **args)

	def run (self):
		# FIXME
		if len(self.prods) == 1:
			msg.error(_("%r does not exist") % self.prods[0], **self.loc)
		else:
			msg.error(_("one of %r does not exist") % self.prods, **self.loc)
		return 1

	def clean (self):
		pass

class DependShell (Depend): #{{{2
	"""
	This class specializes Depend for generating files using shell commands.
	"""
	def __init__ (self, env, cmd, **args):
		Depend.__init__(self, env, **args)
		self.cmd = cmd

	def run (self):
		msg.progress(_("running %s") % self.cmd[0])
		if self.env.execute(self.cmd):
			msg.error(_("execution of %s failed") % self.cmd[0])
			return 1
		return 0


#----  Automatic file conversion  ----{{{1

class Converter (object):
	"""
	This class represents a set of translation rules that may be used to
	produce input files. Objects contain a table of rewriting rules to deduce
	potential source names from the target's name, and each rule has a given
	cost that indicates how expensive the translation is.

	Each rule is associated to a given plugin name. Plugins are expected to
	contain a method 'convert' that take as argument the source (an existing
	file), the target, and the environment, and that returns a dependency node
	or None if the rule is not applicable.
	"""
	def __init__ (self, plugins):
		"""
		Initialize the converter with an empty set of rules and the specified
		plugin manager.
		"""
		self.rules = {}
		self.plugins = plugins

	def read_ini (self, filename):
		"""
		Read a set of rules from a file. See the texinfo documentation for the
		expected format of this file.
		"""
		from ConfigParser import ConfigParser
		cp = ConfigParser()
		cp.read(filename)
		for name in cp.sections():
			rule = {}
			for key in cp.options(name):
				rule[key] = cp.get(name, key)
			rule["cost"] = cost = cp.getint(name, "cost")
			expr = re.compile(rule["target"] + "$")
			self.rules[name] = (expr, cost, rule)

	def add_rule (self, rule_name, **rule):
		"""
		Define a new conversion rule. The only arguments are keyword
		arguments, they have the same meaning as parameters in the
		initialization file.
		"""
		self.rules[rule_name] = (
			re.compile(rule["target"] + "$"), rule["cost"], rule)

	def may_produce (self, name):
		"""
		Return true if the given filename may be that of a file generated by
		this converter, i.e. if it matches one of the target regular
		expressions.
		"""
		for expr, _, _ in self.rules.values():
			if expr.match(name):
				return 1
		return 0

	def __call__ (self, name, env, check=None,
			suffixes=[""], prefixes=[""], **args):
		"""
		Search for an applicable rule for the given target with the least
		cost. The return value is a pair:
		- (None, None): no rule and no existing file was found
		- (None, d): no rule was found, d is a leaf node for an existing file
		- (c, d): a rule with cost w was found, the result node is d
		Optional arguments are:
		- check: a function that takes source and target as arguments can
			return false if the rule is refused
		- suffixes: a list of suffixes to be added after the name when
			searching
		- prefixes: similar
		Other keyword arguments are passed to the converters.
		"""
		conv = []
		existing = None

		for expr, cost, rule in self.rules.values():
			for target in [p + name + s for p in prefixes for s in suffixes]:
				if existing is None and exists(target):
					existing = target
				m = expr.match(target)
				if not m:
					continue
				templates, _ = expand_cases(rule["source"], {})
				for tmpl in templates:
					source = m.expand(tmpl)
					if source == target:
						continue
					if not exists(source):
						continue
					if check and not check(source, target):
						continue
					mod = rule["rule"]
					if not self.plugins.register(mod):
						continue
					conv.append((cost, source, target, rule))

		conv.sort()
		for (cost, source, target, rule) in conv:
			dict = rule.copy()
			for key, val in args.items():
				dict[key] = val
			dep = self.plugins[rule["rule"]].convert(source, target, env, dict)
			if dep:
				return (cost, dep)

		if existing:
			return (None, DependLeaf(env, existing))
		return (None, None)


#----  Building environments  ----{{{1

import rubber.rules

re_kpse = re.compile("kpathsea: Running (?P<cmd>[^ ]*).* (?P<arg>[^ ]*)$")

class Environment:
	"""
	This class contains all state information related to the building process
	for a whole document, the dependency graph and conversion rules.
	"""
	def __init__ (self):
		"""
		Initialize the environment.
		"""
		self.kpse_msg = {
			"mktextfm" : _("making font metrics for \\g<arg>"),
			"mktexmf" : _("making font \\g<arg>"),
			"mktexpk" : _("making bitmap for font \\g<arg>")
			}

		self.vars = { "cwd": os.getcwd() }
		self.path = [""]
		self.plugins = Plugins(rubber.rules.__path__)
		self.pkg_rules = Converter(self.plugins)
		self.user_rules = Converter(self.plugins)
		
		self.main = None
		self.final = None

	def find_file (self, name, suffix=None):
		"""
		Look for a source file with the given name, and return either the
		complete path to the actual file or None if the file is not found.
		The optional argument is a suffix that may be added to the name.
		"""
		for path in self.path:
			test = join(path, name)
			if suffix and exists(test + suffix) and isfile(test + suffix):
				return test + suffix
			elif exists(test) and isfile(test):
				return test
		return None

	def set_source (self, name):
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
					return 1
				src = path[:-len(ext)] + "tex"
				if ext == "w":
					from rubber.rules.cweb import CWebDep
					self.src_node = CWebDep(self, src, path)
				elif ext == "lhs":
					from rubber.rules.lhs2TeX import LHSDep
					self.src_node = LHSDep(self, src, path)

		if src is None:
			path = self.find_file(name, ".tex")
			if not path:
				return 1
			src = path
			self.src_node = None

		import rubber.rules.latex
		self.main = rubber.rules.latex.LaTeXDep(self)
		if exists(src):
			self.main.set_source(src)
			if self.src_node:
				self.main.sources[src] = self.src_node
		self.final = self.main
		return 0

	def make_source (self):
		"""
		Produce the source from its dependency rules, if needed.
		Returns 0 on success and 1 on failure.
		"""
		if self.src_node and self.main.sources == {}:
			if not self.src_node.make():
				return 1
			src = self.src_node.prods[0]
			self.main.set_source(src)
			self.main.sources[src] = self.src_node
		return 0

	def convert (self, target, **args):
		"""
		Use conversion rules to make a dependency tree for a given target
		file, and return the final node, or None if the file does not exist
		and cannot be built. The optional arguments 'prefixes' and 'suffixes'
		are lists of strings that can be added at the beginning and the end of
		the name when searching for the file. Other keyword arguments are
		passed to the converters.
		"""
		dep = None
		for conv in self.user_rules, self.pkg_rules, rubber.rules.std_rules:
			(w, d) = conv(target, self, **args)
			if w is not None:
				return d
			elif dep is None:
				dep = d
		return dep

	def may_produce (self, name):
		"""
		Return true if the given filename may be that of a file generated by
		any of the converters.
		"""
		for conv in self.user_rules, self.pkg_rules, rubber.rules.std_rules:
			if conv.may_produce(name):
				return 1
		return 0

	#--  Executing external programs  {{{2

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
		msg.log(_("executing: %s") % string.join(prog))
		if pwd:
			msg.log(_("  in directory %s") % pwd)
		if env != {}:
			msg.log(_("  with environment: %r") % env)

		# We first look for the program to run so we can fail properly if the
		# executable is not found.

		progname = prog_available(prog[0])
		if not progname:
			msg.error(_("%s not found") % prog[0])
			return 1

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
			os.execve(progname, prog, penv)

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
				cmd = m.group("cmd")
				if self.kpse_msg.has_key(cmd):
					msg.progress(m.expand(self.kpse_msg[cmd]))
				else:
					msg.progress(_("kpathsea running %s") % cmd)

		# After the executed program is finished (which we now be seeing that
		# its error stream was closed), we wait for it and return its exit
		# code.

		(p, ret) = os.waitpid(pid, 0)
		os.waitpid(pid2, 0)
		f_err.close()
		msg.log(_("process %d (%s) returned %d") % (pid, prog[0], ret))

		return ret
