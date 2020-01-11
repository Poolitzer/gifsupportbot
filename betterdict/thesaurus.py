###
# Python Thesaurus - A different way to call a dictionary.
#
# Copyright (c) 2012-2019 Dave Cinege
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
###
from __future__ import print_function

__VERSION__ = (2, 9, 0, 20191110)

from sys import version_info, getrecursionlimit
__PYTHON_ORDERED__ = version_info[0:2] >= (3,6)	# cPython 3,6+ has ordered keys built in.
__MAXRECURSE = getrecursionlimit()

class Return (Exception):
	pass

class Keypath (list):
	"""Keypath: a list-like object representing a nested path of Thesaurus
	keys.
	
	__hash__() is defined to allow passing this mutable object as a
	Thesaurus key, however Keypath's should otherwise not be considered
	reliably hashable.
	"""
	__sep = '.'
	def __init__ (self, keypath=None):
		if isinstance(keypath, str):
			if keypath.startswith(self.__sep) or keypath.endswith(self.__sep) or self.__sep*2 in keypath or keypath == '':
				raise IndexError("'{0}' has empty keyname".format(keypath))
			super(Keypath, self).__init__(keypath.split(self.__sep))
		elif isinstance(keypath, list) or isinstance(keypath, tuple):
			super(Keypath, self).__init__(keypath)
		elif keypath is None:
			super(Keypath, self).__init__()
		else:
			raise TypeError(keypath)
	def __str__  (self):
		l = []
		for k in self:
			if '.' in k:
				l.append("['{0}']".format(k))
			else:
				l.append('.{0}'.format(k))
		s = ''.join(l)
		if s.startswith('.'):
			s = s[1:]
		return s
	def __hash__(self):
		return hash(tuple(self))
	def grow (self,end=0):
		for n in range(1,len(self)+1+end):
			yield self[:n]
	def shrink (self):
		for n in range(len(self),0,-1):
			yield self[:n]
	def walk (self, *args, **kw):
		"""
		def walk_callback(kp, key, depth, *args):
			raise Return(ret_value)
		return Keypath(keypath).walk(walk_callback)
		"""
		walk_list = enumerate(self) if not kw.pop('reverse', False) else enumerate_rev(self)
		for depth,key in walk_list:
			try:
				args[0](self[:depth], key, depth, *args[1:], **kw)
			except Return as r:
				return r

class Thesaurus (dict):
	def __getattr__ (self, name):
		if name.startswith('_'):
			if name.startswith('__') and name.endswith('__'):
				return dict.__getattr__(self, name)
			return self.__getitem__(alias_digit_key(name))
		return self.__getitem__(name)
	def __setattr__ (self, name, value):
		if name.startswith('_'):
			return self.__setitem__(alias_digit_key(name), value)
		return self.__setitem__(name, value)
	def __delattr__ (self, name):
		return self.__delitem__(name)
	def __contains__(self, key):
		return self.has_path(key)
	def __getitem__ (self, key):
		try:
			return dict.__getitem__(self, key)
		except:
			keypath = Keypath(key)
			if len(keypath) == 1:
				return dict.__getitem__(self, keypath[0])
		o = self
		for depth,key in enumerate(keypath):	# Walk keys recursively
			_checkrecurse(self, depth)
			try:
				o = o[key]			# Attempt key
			except:
				try:
					o = getattr(o, key)	# Attempt attr
				except:
					raise KeyError("'{key}' ({keypath} [depth={depth}])".format(**locals()))
		return o	# Will fall through to return self if len(keypath) == 0
	def __setitem__ (self, key, value):
		if not isinstance(key, str):
			raise KeyError(type(key))
		return dict.__setitem__(self, key, value)					
	def copy (self):
		t = self.__class__()
		t.overlay(self)
		return t
	def getitem (self, key):
		"""getitem with absolute key name and no recursion."""
		return dict.__getitem__(self, key)
	def has_key (self, key):
		"""has_key with absolute key name and no recursion."""
		return dict.__contains__(self, key)
	def has_path (self, keypath):
		"""has_key with recursion."""
		try:
			self.__getitem__(keypath)
			return True
		except KeyError:
			return False
	def set_path (self, keypath, value):
		"""set_path complete tree from keypath.split('.'))"""
		keypath = Keypath(keypath)
		o = self
		for _key in keypath[:-1]:
			if _key not in o:
				o.__setitem__(_key, self.__class__())
			elif not isinstance(o[_key], Thesaurus):
				raise KeyError('{0}: not a Thesaurus object'.format(_key))
			o = o[_key]
		return o.__setitem__(keypath[-1], value)
	def del_path (self, keypath):
		"""delete a path from end to start, walking backwards"""
		keypath = Keypath(keypath)
		if not self.has_path(keypath):
			raise KeyError(keypath)
		for kp in keypath.shrink():
			del self[kp[:-1]][kp[-1]]	# Accidently found it returns self on 0 len keypath. I claim Super Genius. 

	def filter (self, d):
		# TODO
		"""self.walk()
		if kp not in d:
			self.del_path(kp)
			# Can't do inplace
		"""
		pass
		
		
			
	# FIX ME: Rename screen to mask? Rename mesh to mask, and screen to mesh?		
	def merge (self, d=None):
		"""Recursively copy all items to self."""
		return self.overlay(d, overwrite=True)
	def mesh (self, d=None):
		"""Recursively copy items not existing in self."""
		return self.overlay(d, overwrite=False)
	def screen (self, d=None):	
		"""Recursively copy items only existing in self"""
		return self.overlay(d, overwrite=True, updateonly=True)

	# FIX ME, properly copy/deepcopy items	
	def overlay (self, d, overwrite=True, updateonly=False, withcopy=True):
		"""Recursively copy a mapping onto self according
		to parameters. dict subclasses will be converted
		to __class__()"""
		def recursedict(dst, src, depth=0):
			_checkrecurse(self, depth)
			for _key,_val in iter(src.items()):
				if not overwrite and _key in dst:
					continue
				if not isinstance(_val, dict):
					if updateonly and _key not in dst:
						continue
					dst.__setitem__(_key, _val)
				else:
					if _key not in dst:
						if updateonly:
							continue
						dst.__setitem__(_key, self.__class__())
					recursedict(dst[_key], _val, depth+1)
		recursedict(self, d)

class ThesaurusOrdered (Thesaurus):
	def __init__(self, *args, **kwargs):
		Thesaurus.__init__(self)
		self.__keyorder = list()
		if len(args) == 1:			# WARNING: mappings will not come in ordered!
			self.update(args[0])
		if len(kwargs) > 0:
			self.update(kwargs)
	def __setattr__ (self, name, value):
		if name.startswith('_'):
			if name.startswith('_ThesaurusOrdered__'):
				return object.__setattr__(self, name, value)
			name = alias_digit_key(name)
		if name not in self.__keyorder:
			self.__keyorder.append(name)
		return Thesaurus.__setitem__(self, name, value)
	def __setitem__ (self, key, value):
		if not isinstance(key, str):
			raise KeyError(type(key))
		if key not in self.__keyorder:
			self.__keyorder.append(key)
		return Thesaurus.__setitem__(self, key, value)
	def __delitem__ (self, key):
		if key in self.__keyorder:
			self.__keyorder.remove(key)
		return Thesaurus.__delitem__(self, key)
	def keys (self):
		return list( self.__keyorder )
	def values (self):
		return list( self[key] for key in self.__keyorder )
	def items (self):
		return list( (key, self[key]) for key in self.__keyorder )
	def clear (self):
		for key in self.__keyorder:
			del self[key]
		del self.__keyorder[:]
	def __iter__ (self):
		return self.iterkeys()
	def iterkeys (self):
		for key in self.__keyorder:
			yield key
	def itervalues (self):
		for key in self.__keyorder:
			yield self[key]
	def iteritems (self):
		for key in self.__keyorder:
			yield key, self[key]

	def pop (self, key, default=None):
		if key in self.__keyorder:
			self.__keyorder.remove(key)
		return Thesaurus.pop(self, key, default)
	def popitem (self):
		if len(self.__keyorder) == 0:
			raise KeyError('popitem(): thesaurus is empty')
		key = self.__keyorder.pop(-1)
		value = self[key]
		del self[key]
		return key, value
	def setdefault (self, key, default=None):
		if key not in self.__keyorder:
			self.__keyorder.append(key)
		return Thesaurus.setdefault(self, key, default)
	def update(self, *args, **kwargs):
		d = args[0]
		if isinstance(d, dict):
			items = iter(d.items())
		else:
			items = d
		for k,v in items:
			if k not in self.__keyorder:
				self.__keyorder.append(k)
			self[k] = v


class ThesaurusExtension (object):
	"""Extra methods for Thesaurus that argulably don't belong in the base
	data type.
	"""
	def get_keys (self, value):
		"""recursively search for 'value' in tree and reply with
		keypaths with this value or empty list.
		"""
		return self._search_tree(None,value,0)
	def get_values (self, key):
		"""recursively search for 'key' in tree and reply with
		values of this key or empty list.
		"""
		return self._search_tree(key,None,1)
	def get_items (self, key):
		"""recursively search for 'key' in tree and reply with
		(keypath, value) found or empty list.
		"""
		return self._search_tree(key,None,2)
	def get_in (self, value, val_type=False):
		"""recursively search for 'value' in values in tree and reply
		with keypaths found or empty list. Optionally only compare
		values of X type to prevent false positives. (IE: Finding a
		substr in a key name)
		"""
		return self._search_tree(None,value,5,val_type)
	def find_key (self, key):
		"""recursively search for 'key' in tree and reply with
		keypaths containing this key or empty list. 'key' is not
		returned in keypaths.
		"""
		return self._search_tree(key,None,3)
	def find_item (self, key, value):
		"""recursively search for item (d[key] == value') in tree
		and reply with keypaths found or empty list. 'key' is not
		returned in keypaths.
		"""
		return self._search_tree(key,value,4)				
	def _search_tree (self, key=None, value=None, search=0, val_type=False):
		key_tree = list()
		def recursedict(d, key, value, search, val_type, key_tree, _key_tree=[], depth=0):
			_checkrecurse(self, depth)
			for _key,_val in iter(d.items()):
				if   search == 0 and _val == value:
					key_tree.append(key_treepath(_key_tree, _key))
				elif search == 1 and _key == key:
					key_tree.append(_val)
				elif search == 2 and _key == key:
					key_tree.append((key_treepath(_key_tree, _key), _val))
				elif search == 3 and _key == key:
					key_tree.append(key_treepath(_key_tree))
				elif search == 4 and _key == key and _val == value:
					key_tree.append(key_treepath(_key_tree))
				elif search == 5:
					if val_type and val_type != type(_val):
						pass
					else:
						try:
							if value in _val:
								key_tree.append(key_treepath(_key_tree, _key))
						except:	pass
				if isinstance(_val, dict):
					recursedict(_val, key, value, search, val_type, key_tree, _key_tree+[_key], depth+1)
		recursedict(self, key, value, search, val_type, key_tree)
		return key_tree
	def print_tree (self, tostr=False):
		def recursedict(d, keypath, depth=0, s=''):
			_checkrecurse(self, depth)
			for _key,_val in iter(d.items()):
				if not isinstance(_val, dict):
					s += '[{depth}] {0} = {_val}\n'.format(Keypath(keypath+[_key]), **locals())
				else:	
					keypath.append(_key)
					s += '[{depth}] {keypath}:  {0}\n'.format(type(_val), **locals())
					s += recursedict(_val, keypath, depth+1)
					del keypath[-1]
			return s
		s = recursedict(self, Keypath())
		s = '{0} {{\n{1}}}'.format(type(self), s)
		if tostr:
			return s
		print(s)

### Define the prefered import names. Default to use ordered keys.
if __PYTHON_ORDERED__:
	thes = Thesaurus
else:	
	thes = ThesaurusOrdered
###

class ThesaurusExtended (ThesaurusExtension, thes):
	def __getitem__ (self, key):
		"""Support int index and slicing."""
		if isinstance (key, int) or isinstance (key, slice):
			return list(self.values())[key]
		return thes.__getitem__(self, key)

thesext = ThesaurusExtended


def key_treepath (key_tree, *keys):
	return Keypath(key_tree+list(keys))

def alias_digit_key (name):
	"""Attribute alias for keynames starting with a digit: t._0ab == t['0ab'].
	We check name.startswith('_') above.
	"""
	return name[1:] if name[1:2].isdigit() else name

def enumerate_rev (arg):
	"""Generator to enumerate in reverse"""
	return ( (n,arg[n]) for n in range(len(arg)-1,-1,-1) )

def _checkrecurse (self, depth):
	if depth >= __MAXRECURSE:
		raise RuntimeError('maximum recursion depth exceeded while calling a {0} object'.format(self.__class__.__name__))

if __name__ == '__main__':
	import timeit
	#t = thes()

	#kp = Keypath('a.b.c')
	#kp += ('c','d')
	#kp += 'e'
	#kp += 'f.g.h'

	
	#print(kp)
	#print(repr(kp))
	#kp.walk(print)
	#kp.walk(print, reverse=True)
	"""
	def do (kp, k, depth, t):
		if depth == 1:
			raise Return(thes())
		print('do',k)
		t[k] = depth
		t = t[k]
	print(str(kp.walk(do, t)))
	"""
	#print(t.__class__.__name__)

	#t.set_path('a.b.c.d', 'ddd')
	#print(t)

	#ti = timeit.Timer("thes().set_path('a.b.c.d', 'ddd')", globals=locals())
	#print(ti.timeit(number=100000))


	"""
	te = thesext()
	te.a = 1
	te.b = 2
	te.c = 3
	print(te[1])
	print(te[-1])
	print(te.a)
	print('a.b.c' in te)
	"""
	t = thesext()
	t.set_path('a.b.c.d', 'ddd')
	
	kp = Keypath('a.b.c')
	kp += ('this.host.com',)
	print('kp:',repr(kp))
	t.set_path(kp, 'abyss')
	
	#t[kp] = 'abyss'
	t.print_tree()
	print(t[kp])

	print(t.get_keys('abyss'))

	print(t.get_values('c'))

	print(t.get_items('d'))

	print(t.a.b.c[1])

	#print(t['a.b.c.d'])
	#print(repr(t.a.b.c))

	# This works
	# del t['a.b.c']['d']
	# del t.a.b.c.d

	# This will not work
	# del t['a.b.c.d'] 	
	
	#t.a.b.del_path('c.d')

	"""
	del t.a.b[('c',)]['d']
	tp = tuple()
	kp = Keypath(tp)
	del t.a.b[kp]['c']
	#del t.a.b.c.d
	print(repr(t))
	"""
	
	import timeit
	print(timeit.timeit(
		"t['a.b.c.d']",
		setup="from __main__ import thes; t = thes(); t.set_path('a.b.c.d.e.f.g.h.i.j', 'ddd')",
		number=100000),
	)
