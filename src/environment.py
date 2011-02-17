# This file is part of Rubber and thus covered by the GPL
# (c) Emmanuel Beffara, 2002--2006
"""
This module contains the code for formatted message output (the Message class)
and the class Environment, which contains all information about a given
building process.
"""

import os, os.path, sys, subprocess, thread
import re, string
from subprocess import Popen

from rubber.version import moddir
from rubber.util import _
from rubber.util import *
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

	def file_name (self, path):
		"""
		Return a path equivalent to the one passed as argument, but relative
		to the reference working directory.
		"""
		full_path = os.path.abspath(path)
		cwd = os.path.join(self.vars['cwd'], '')
		if full_path[:len(cwd)] == cwd:
			return full_path[len(cwd):]
		return full_path

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
