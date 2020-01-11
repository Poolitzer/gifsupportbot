###
# Python Thesaurus Config
#
# Copyright (c) 2019 Dave Cinege
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

__VERSION__ = (2, 9, 0, 20191113)

import os
import sys
import re
import shlex

from string import Template

from thesaurus import thes, thesext

class cfg_types (object):
	class __EXAMPLE (object):
		def set (self, key, val, curval):
			"""value assignment call.
			return value is passed to __setitem__()"""
			return val
		def parse (self, key, val):
			"""str value as parsed from cfg format.
			return value is passed to __setitem__()"""
			return val
		def dump (self, key, val):
			"""return value is converted to str() and
			written to cfg format"""
			return val
	class static (object):
		"""Return current value for setitem except
		when *first* read from cfg"""
		def set (self, key, val, curval):
			return curval
	class int (object):
		def parse (self, key, val):
			return int(val)
	class static_int (static, int):
		pass

	class str_list (object):
		def parse (self, key, val):
			return shlex.split(val)
		def dump (self, key, val):
			if len(val) == 0:
				return ''
			s = ''
			for i in val:
				s += '"%s" ' % (i.replace('"','\\"'))
			return s[:-1]
	class str_to_bool (object):
		""""Support 3 values: True, False, None"""
		def set (self, key, val, curval):
			if val in (True, False, None):
				return val
			raise ValueError(s)
		def parse (self, key, val):
			s = val.lower()
			if s in ('true', 'yes', 'on', '1'):
				return True
			if s in ('false', 'no', 'off', '0'):
				return False
			if s in ('none', ''):
				return None
			raise ValueError(s)
		def dump (self, key, val):
			if val == None:
				return 'None'
			return bool(val)
	class ipv4 (object):
		def set (self, key, val, curval):
			return self.parse(key, val)
		def parse (self, key, val):
			l = val.split('.')
			if len(l) != 4:
				raise ValueError(val)
			for i in l:
				try:
					i = int(i)
				except:
					raise ValueError(val)
				if i < 0 or i > 255:
					raise ValueError(val)
			return val

class configparser (object):
	def __init__(self, *args, **kwargs):
		self._thes_type = thesext
		self._value_lstrip = True
		self._value_rstrip_comment = True
		self._value_rstrip = True
		for k,v in kwargs.items():
			setattr(self, '_'+k, v)
	def split_key (self, key):
		lex = shlex.shlex(key, posix=True)
		lex.whitespace_split = True
		lex.whitespace = '.'
		return list(lex)
	def read(self, filename=None, t=None):
		if t == None: t = self._thes_type()
		t = self._thes_type()
		with open(filename, 'r') as fp:
			return self.readfp(fp, t)
	def readfp (self, fp=None, t=None):
		if t == None: t = self._thes_type()
		return self.parse(t, fp.read())
	def parse (self, t=None, s='', func_map={}):
		"""Original trimmed text is returned, sustain for input back to parse"""
		def full_key (root_key, key):
			if root_key != '':
				return root_key+'.'+key
			return key
		if t == None: t = self._thes_type()

		comment_mline_double_pat = r'(\A|\n)""".*?"""(\Z|\n)'
		comment_mline_single_pat = r"(\A|\n)'''.*?'''(\Z|\n)"
		comment_line_pat = r'(\A|\n)#.*'
		empty_head_pat = r'\A\n+?'
		empty_tail_pat = r'\n+?\Z'
		empty_line_pat = r'\n\n+'
		keyval_line_pat = r'\n([^ \t].*?)\n'

		s = re.sub('\r\n', '\n', s)		# DOS conversion
		s = re.sub('\r', '\n', s)		# MAC conversion

		# Python 2.6 doesn't accept flags= on methods, so compile all
		s = re.compile(comment_mline_double_pat, flags=re.UNICODE|re.DOTALL).sub('', s)
		s = re.compile(comment_mline_single_pat, flags=re.UNICODE|re.DOTALL).sub('', s)
		s = re.compile(comment_line_pat, flags=re.UNICODE).sub('', s)
		s = re.compile(empty_head_pat, flags=re.UNICODE|re.DOTALL).sub('', s)
		s = re.compile(empty_tail_pat, flags=re.UNICODE|re.DOTALL).sub('', s)
		s = re.compile(empty_line_pat, flags=re.UNICODE|re.DOTALL).sub('\n', s)

		# I know this is a bad idea to touch data, but just soooo easy for now
		evil_mline_sep = '__%%mline_sep%0A%%__'
		s = re.compile('\n[ \t]', flags=re.UNICODE|re.DOTALL).sub(evil_mline_sep, s)
		re_mline_sep = re.compile(evil_mline_sep, flags=re.UNICODE|re.DOTALL)

		re_sep = re.compile('[=:]+?', flags=re.UNICODE)

		#print(lines)
		root_key = ''
		for line in s.split('\n'):
			if line.strip() == '':
				continue
			
			#print('A:',line,':E')

			# FIX ME suport empty root sections without []
			if line.startswith('[') and line.rstrip().endswith(']'):
				root_key = line.rstrip()[1:-1].strip()		# '[]' section resets root_key
				root_keypath = self.split_key(root_key)
				if root_key != '' and root_keypath not in t:
					t.set_path(root_keypath, self._thes_type())	# FIX me use parent class
				continue

			key,value = re_sep.split(line, 1)
			value = re_mline_sep.sub('\n', value)

			if self._value_rstrip_comment:
				if '\n' not in value:
					value = value.rsplit('#')[0]
			if self._value_rstrip:
				value = value.rstrip()
			if self._value_lstrip:
				value = value.lstrip()

			if '(' not in key:
				key = full_key(root_key, key.strip())
				funcname = None
			else:
				key,funcvar = key.strip().split('(')
				key = full_key(root_key, key.strip())
				funcname = funcvar[:-1].strip()


			keypath = self.split_key(key)
			if len(keypath) > 1 and keypath[:-1] not in t:
				t.set_path(keypath, self._thes_type())
			o = t[keypath[:-1]]
			key = keypath[-1]
			
			if funcname and funcname in func_map:
				if hasattr(func_map[funcname], 'parse'):
					o._ThesConf__parse_map[key] = func_map[funcname]().parse
			if key in o._ThesConf__parse_map:
				value = o._ThesConf__parse_map[key](key, value)
			o[key] = value

			if funcname and funcname in func_map:
				if hasattr(func_map[funcname], 'set'):
					o._ThesConf__set_map[key] = func_map[funcname]().set
				if hasattr(func_map[funcname], 'dump'):
					o._ThesConf__dump_map[key] = func_map[funcname]().dump

		return t
	def write (self, fp=None, t=None):
		if t == None: t = self._thes_type()
		return self.dump(t, fp.read())
		
	def dump(self, t, sections=0, empty_sect=True):
		def recursedict(d, sections, empty_sect, key_tree=[], depth=0, s='', r=''):
			for k,v in iter(d.items()):
				if hasattr(v, 'keys'):
					if '.' in k:
						key_tree.append("'"+k+"'")
					else:	
						key_tree.append(k)
					r = recursedict(v, sections, empty_sect, key_tree, depth+1)
					if sections and depth < sections:
						if r  or empty_sect:
							if s != '': s += '\n'	# Not at top of output
							s += '[%s]\n' % (key_treepath(key_tree))
					elif not r and empty_sect:
						s += '%s\n' % (key_treepath(key_tree))
					s += r
					key_tree.pop(-1)
				else:
					if sections and depth == 0 and r:		# More root level values after recursing
						s += '\n[]\n'; r = ''			# Reset section so not absorbed by previous

					if k in d._ThesConf__dump_map:
						v = d._ThesConf__dump_map[k](k, v)
						
					if '\n' in str(v):
						v = ':\n\t%s\n' % (v.replace('\n','\n\t'))
					else:
						v = ' = %s\n' % (str(v))
					if not sections:
						s += key_treepath(key_tree, k) + v
					else:
						s += key_treepath(key_tree[sections:], k) + v
			return s
		return recursedict(t, sections, empty_sect)

class ThesConf (object):
	def __init__(self, *args, **kwargs):
		self.__set_map = dict()
		self.__parse_map = dict()
		self.__dump_map = dict()

	def read (self, filename, *args, **kwargs):
		with open(filename, 'r') as f:
			return self.parse(f.read(), *args, **kwargs)
	def parse (self, data, *args, **kwargs):
		func_map=mapper(cfg_types())
		return configparser(thes_type=self.__class__).parse(self, data, func_map=func_map)
	def write (self, fp, *args, **kwargs):
		fp.write(self.dump(*args, **kwargs))
	def dump (self, sections=0, empty_sect=True):
		return configparser(thes_type=self.__class__).dump(self, sections, empty_sect)


class ThesaurusCfg (thesext, ThesConf):
	"""A configuration file format utilizing the Thesaurus
	data type supporting nested sections and parse, dump,
	and assignment callbacks functions."""
	def __init__(self, *args, **kwargs):
		thesext.__init__(self, *args, **kwargs)
		ThesConf.__init__(self)
	def __setattr__ (self, name, value):
		if name.startswith('_ThesConf__'):
			return object.__setattr__(self, name, value)
		if '_ThesConf__set_map' in self.__dict__ and name in self._ThesConf__set_map:
			value = self._ThesConf__set_map[name](name, value, self[name])
		return thesext.__setattr__(self, name, value)
	def __setitem__ (self, key, value):
		if '_ThesConf__set_map' in self.__dict__ and key in self._ThesConf__set_map:
			value = self._ThesConf__set_map[key](key, value, self[key])
		return thesext.__setitem__(self, key, value)


class mapper (dict):
	"""map from multiple objects:
	'%(a)s %(b)s' % mapper(locals(), dict0, class1 ...)"""
	def __init__  (self, *args):
		self.__mappings = args
	def __hasattr__ (self, name):
		return self.__contains__(name)
	def __getattr__ (self, name):
		return self.__getitem__(name)
	def __contains__(self, key):
		try:
			self.__getitem__(key)
			return True
		except:
			return False
	def __getitem__ (self, key):
		for d in self.__mappings:
			try:
				return d[key]
			except: pass
			try:
				return getattr(d, key)
			except: pass
		raise KeyError('can not map: {0}'.format(key))


def kwmapper (*args):
	""" '{keyname}'.format(**kwmapper(locals(), dict0, class1 ... ))
	NOTE: this can not recurse into object attributes like mapper
	because it's copying to a single dict. :-( With that said
	''.format(kwmapper()) is much faster then % (printf) or string.Template
	using mapper().
	"""
	kw = dict()
	for d in args:
		if isinstance(d, dict):
			kw.update(d)
		elif hasattr(d, '__dict__'):
			for k in d.__dict__:
				if k.startswith('_'):
					continue
				kw[k] = getattr(d, k)
		else:
			raise TypeError('can not map: {0}'.format(type(d)))
	return kw


"""
Wrapper functions for .format(), % (printf), and string.Template that use the
last argument as the input string and all preceding arguments with kwmapper
or mapper(). Use it like this for very clean syntax with large block strings:
	s = fmt(locals(), dict0, class1, thes2, '''
	/sbin/iptables -t nat -F {chain}
	/sbin/iptables -t nat -D {parent.chain} -j {chain}
	/sbin/iptables -t nat -X {chain}
	/sbin/iptables -t nat -N {chain}
	''')
"""	
def fmt (*args):
	return args[-1].format(**kwmapper(*(args[:-1])))
def prtf (*args):
	return args[-1] % mapper(*(args[:-1]))

class template (Template):
	"""add '.' and recognize digits so we can
	recurse with Thesaurus. Must use ${} to recurse."""
	idpattern = r'[_a-z0-9][._a-z0-9]*' 	# orig r'[_a-z][_a-z0-9]*'
	delimiter = '$'
def tmpl (*args):
	return template(args[-1]).substitute(mapper(*(args[:-1])))
def tmpl_safe (*args):
	return template(args[-1]).safe_substitute(mapper(*(args[:-1])))

# tl;dr:  use fmt() for speed unless you have f-string available (py 3.6+)
# t = thes() ; t.set_path('a.b.c.table', '9999'); table = '123'
# test_str = '''\n/sbin/iptables -t {table} -N {a.b.c.table}\n/sbin/iptables -t {table} -A\n'''
# 100000 Iteration performance test	cPython 3.6		cPython2.7	cPython2.6
# tmpl(locals(), t, test_str)		1.0474729537963867	1.19237399101	1.44343900681
# prtf(locals(), t, test_str)		0.5701203346252441	0.709426879883	0.879161119461
# fmt(locals(), t, test_str)		0.4930698871612549	0.479194879532	0.610402822495
# fstr(test_str)
# test_str.format(**locals(), **t)	0.396730899810791	N/A		N/A
# f''' (f-string)			0.2974255084991455	N/A		N/A


def fstr (s):
	"""The poor mans' f-string for CPython2.6 -> 3.8+"""
	return s.format(**sys._getframe(1).f_locals)
	
def readlineclean (s, nostrip=False, isfile=False, nocomments=True):
	"""
	Iterate lines from str or filename, skips blanks and comments.
	"""
	if isfile:
		f = open(s)
		lines = f.readlines
	else:
		lines = s.splitlines
		
	for line in lines():
		if line.strip() == '' or line.strip().startswith('#'):
			continue
		if nocomments:
			line,_,_ = line.partition('#')
		if nostrip:
			yield line
		else:
			yield line.strip()
	try:
		f.close()
	except: pass
	
def key_treepath (key_tree, *keys):
	"""''.join keeps playing with my emotions"""
	return '.'.join(key_tree+list(keys))

#Define prefered import name
thescfg = ThesaurusCfg

if __name__ == '__main__':
	#cp = configparser()
	#cp.read(sys.argv[1])
	#cp.write(None,0)
	#cp.t.print_tree()


	#t = thescfg()
	#t.read('thesaurus_config.testcfg')
	#t.read('fw.admin.cfg')
	#t.print_tree()

	a = 'Hello'
	print(fstr('{a}! I am {__name__}'))
	print(fstr('{a}! I am {__name__}. sys is {sys.__name__}'))

	import time
	t = thes()
	t.set_path('a.b.c.table', '9999')
	table = '123'

	test_str = '''\n/sbin/iptables -t {table} -N {t.a.b.c.table}\n/sbin/iptables -t {table} -A\n'''
	print(fstr(test_str))
	sys.exit(0)

	test_str = '''\n/sbin/iptables -t %(table)s -N %(a.b.c.table)s\n/sbin/iptables -t %(table)s -A\n'''
	b = time.time()
	for i in range(100000):
		prtf(locals(), t, test_str)
	print(time.time() - b)

	test_str = '''\n/sbin/iptables -t {table} -N {a.b.c.table}\n/sbin/iptables -t {table} -A\n'''
	b = time.time()
	for i in range(100000):
		fmt(locals(), t, test_str)
	print(time.time() - b)
	
	test_str = '''\n/sbin/iptables -t {table} -N {t.a.b.c.table}\n/sbin/iptables -t {table} -A\n'''
	b = time.time()
	for i in range(100000):
		fstr(test_str)
	print(time.time() - b)

	
	#t.print_tree()
	#print(t.dump(sections=2))
	#keypaths = t.search_key('ip')
	#print('keypaths:', keypaths)
	#for keypath in keypaths:
	#	print(t[keypath].ip)



	#print(t.myvarname)
	#print('xyz',t.xyz,type(t.xyz))
	#print('mybool',t.mybool,type(t.mybool))

	#print('abc = 123',t.abc,type(t.abc))
	#t.abc = 2000
	#print('abc = 2000',t.abc,type(t.abc))
	#t['abc'] = 4000
	#print('abc = 4000',t.abc,type(t.abc))
	#t['new'] = 1
	#print(dir( mapper(cfg_types())))


	#t.print_tree()
	#t.dump(sections=0)
	#print(t.dump(sections=0))

	"""
	print(t.find_key('table'))
	print(t.find_item('table', '130'))
	print(t.get_keys('130'))
	print(t.get_values('table'))
	print(t.get_items('table'))
	
	print(t.get_in('192.'))
	"""
	"""
	t = thescfg()
	t.set_path('a.b.c.d', 'a value')
	#t.print_tree()
	#t.del_path('a.b.c.d')

	t.a.b.dt = dict()
	t.a.b.dt['d1a'] = 1
	t.a.b.dt['d1b'] = thescfg()

	t.a.b.dt['d1b'].z = 3
	
	#t.print_tree()

	t1 = thescfg()
	t1.merge(t)
	#t1.print_tree()

	#print(isinstance(t1, dict))
	
	#Template.delimiter = r'%'
	#print('delim',Template.delimiter)

	"""
	



	#for line in readlineclean('thesaurus_config.testcfg', isfile=True):
	#	print(line)
