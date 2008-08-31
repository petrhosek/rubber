"""
This module contains code for handling dependency graphs.
"""

import os, time
from subprocess import Popen
from rubber import msg, _

class Set (dict):
	"""
	Represents a set of dependency nodes. Nodes can be accessed by absolute
	path name using the dictionary interface.
	"""
	pass

# constants for the return value of Node.make:

ERROR = 0
UNCHANGED = 1
CHANGED = 2

class Node (object):
	"""
	This is the base class to represent dependency nodes. It provides the base
	functionality of date checking and recursive making, supposing the
	existence of a method `run()' in the object.
	"""
	def __init__ (self, set, products=[], sources=[]):
		"""
		Initialize the object for a given set of output files and a given set
		of sources. The argument `products' is the list of names for files
		produced by this node, and the argument `sources' is the list of names
		for the dependencies. The node registers itself in the dependency set,
		and if a given depedency is not known in the set, a leaf node is made
		for it.
		"""
		self.set = set
		self.products = []
		self.sources = []
		self.making = False
		self.failed_dep = None
		for name in products:
			self.add_product(name)
		for name in sources:
			self.add_source(name)
		self.set_date()

	def set_date (self):
		"""
		Define the date of the last build of this node as that of the most
		recent file among the products. If some product does not exist or
		there are no products, the date is set to None.
		"""
		if self.products == []:
			self.date = None
		else:
			try:
				# We set the node's date to that of the most recently modified
				# product file, assuming all other files were up to date then
				# (though not necessarily modified).
				self.date = max(map(os.path.getmtime, self.products))
			except OSError:
				# If some product file does not exist, set the last
				# modification date to None.
				self.date = None

	def reset_sources (self, names=[]):
		"""
		Redefine the set of produced files for this node.
		"""
		self.sources = []
		for name in names:
			self.add_source(name)

	def add_source (self, name):
		"""
		Register a new source for this node. If the source is unknown, a leaf
		node is made for it.
		"""
		if not self.set.has_key(name):
			self.set[name] = Leaf(self.set, name)
		if name not in self.sources:
			self.sources.append(name)

	def remove_source (self, name):
		"""
		Remove a source for this node.
		"""
		self.sources.remove(name)

	def reset_products (self, names=[]):
		"""
		Redefine the set of produced files for this node.
		"""
		for name in self.products:
			del self.set[name]
		self.products = []
		for name in names:
			self.add_product(name)

	def add_product (self, name):
		"""
		Register a new product for this node.
		"""
		self.set[name] = self
		if name not in self.products:
			self.products.append(name)

	def source_nodes (self):
		"""
		Return the list of nodes for the sources of this node.
		"""
		return [self.set[name] for name in self.sources]

	def is_leaf (self):
		"""
		Returns True if this node is a leaf node.
		"""
		return self.sources == []

	def should_make (self):
		"""
		Check the dependencies. Return true if this node has to be recompiled,
		i.e. if some dependency is modified. Nothing recursive is done here.
		"""
		if not self.date:
			return True
		for source in self.source_nodes():
			if source.date > self.date:
				return True
		return False

	def make (self, force=False):
		"""
		Make the destination file. This recursively makes all dependencies,
		then compiles the target if dependencies were modified. The return
		value is one of the following:
		- ERROR means that the process failed somewhere (in this node or in
		  one of its dependencies)
		- UNCHANGED means that nothing had to be done
		- CHANGED means that something was recompiled (therefore nodes that
		  depend on this one have to be remade)
		If the optional argument 'force' is true, then the method 'run' is
		called unless an error occurred in dependencies, and in this case
		UNCHANGED cannot be returned.
		"""
		if self.making:
			print "FIXME: cyclic make"
			return UNCHANGED
		self.making = True

		# Make the sources

		self.failed_dep = None
		must_make = force
		for source in self.source_nodes():
			ret = source.make()
			if ret == ERROR:
				self.making = False
				self.failed_dep = source.failed_dep
				return ERROR
			elif ret == CHANGED:
				must_make = True

		# Make this node if necessary

		if must_make or self.should_make():
			if force:
				ok = self.force_run()
			else:
				ok = self.run()
			if not ok:
				self.making = False
				self.failed_dep = self
				return ERROR

			# Here we must take the integer part of the value returned by
			# time.time() because the modification times for files, returned
			# by os.path.getmtime(), is an integer. Keeping the fractional
			# part could lead to errors in time comparison when a compilation
			# is shorter than one second...

			self.date = int(time.time())
			self.making = False
			return CHANGED

		self.making = False
		return UNCHANGED

	def run (self):
		"""
		This method is called when a node has to be (re)built. It is supposed
		to rebuild the files of this node, returning true on success and false
		on failure. It must be redefined by derived classes.
		"""
		return False

	def force_run (self):
		"""
		This method is called instead of 'run' when rebuilding this node was
		forced. By default it is equivalent to 'run'.
		"""
		return self.run()

	def failed (self):
		"""
		Return a reference to the node that caused the failure of the last
		call to 'make'. If there was no failure, return None.
		"""
		return self.failed_dep

	def get_errors (self):
		"""
		Report the errors that caused the failure of the last call to run, as
		an iterable object.
		"""
		return []

	def clean (self):
		"""
		Remove the files produced by this rule and recursively clean all
		dependencies.
		"""
		for file in self.products:
			if os.path.exists(file):
				msg.log(_("removing %s") % file)
				os.unlink(file)
		for source in self.source_nodes():
			source.clean()
		self.date = None

	def leaves (self):
		"""
		Return a list of all source files that are required by this node and
		cannot be built, i.e. the leaves of the dependency tree.
		"""
		if self.sources == []:
			return self.products
		ret = []
		for source in self.source_nodes():
			ret.extend(source.leaves())
		return ret

class Leaf (Node):
	"""
	This class specializes Node for leaf nodes, i.e. source files with no
	dependencies.
	"""
	def __init__ (self, set, name):
		"""
		Initialize the node. The argument of this method are the dependency
		set and the file name.
		"""
		Node.__init__(self, set, products=[name])

	def run (self):
		if self.date is not None:
			return True
		# FIXME
		msg.error(_("%r does not exist") % self.products[0])
		return False

	def clean (self):
		pass

class Shell (Node):
	"""
	This class specializes Node for generating files using shell commands.
	"""
	def __init__ (self, set, command, products, sources):
		Node.__init__(self, set, products, sources)
		self.command = command

	def run (self):
		msg.progress(_("running: %s") % ' '.join(self.command))
		process = Popen(self.command)
		if process.wait() != 0:
			msg.error(_("execution of %s failed") % self.command[0])
			return False
		return True
