"""
		jfrog2pypi: Jfrog Artifactory python modules loader

A simple yet useful module that was originally developed to be able to
parse any generic jfrog artifactory repositories and secondly, to provide
the version-control mechanism over all contained packages. It implements
a really easy-to-use class to find and load any module from a remote
repository. PyPI repositories are also supported, but yet way less optimised.

Author: SkymeFactor

Python version support: 3.6+
"""
import sys, os
import importlib
import re
import logging
from os import listdir
from subprocess import Popen
import requests
from urllib.parse import urljoin
from threading import Thread, Lock
from distutils.version import LooseVersion
from bs4 import BeautifulSoup
from artifactory import ArtifactoryPath

__version__ = "0.1.1"

class ArtifactoryParser:
	"""
	The class that implements searching, downloading and versioning
	of packages in a remote Artifactory repository. Supports
	the following types of artifacts: .py, .whl. It is also capable
	at parsing original PyPI repositories when html parser is used,
	really don't recommend to do it though, due to it's slowness :)
	"""
	def __init__(self, max_nesting_level = 8, max_threads_num = 16):
		# Define limiters
		self.max_nesting_level = max_nesting_level
		self.max_threads_num = max_threads_num
		# Pre-compile most used regexp
		self.re_find_folder = re.compile(r'.*/$')
		self.re_find_backs = re.compile(r'^(../.*|/*|\?.*|#.*)$')
		self.re_find_version = re.compile(r'(.+?)([>=<_-]{1,2})((\d+)\.?(\d+)\.?(\d+)?)(?:.*(\..*))?')
		
		self.lock = Lock()
		self.module = ''
		self.login = ''
		self.password = ''
		self.opener = None
	
	
	def get_module(self, req_module, url, tags=[], login='', password='', searcher='dohq'):
		"""
		This huge method checks whether your package is already insatlled and
			initiates remote reposytory parsing otherwise. After that it validates
			the results, downloads and imports your package.
		
		:param req_module (str): exact name of the required module, it also may
			contain a few version checks in standart python requirements format
		:param url (str): repository address where the module will be searched for
		:param tags (list): to avoid collision you can pass this attribute,
			whether it is a folder name or platform tags, anything will be useful
		:param login (str): repository login
		:param password (str): repository password
		:param searcher (str): defaul searcher to be used (supports 'dohq'(default) and 'html')
		:return loaded module
		"""
		#===============================================================
		# Some setting up actions
		#===============================================================
		# Check for empty module name
		if not req_module:
			logging.error('Module name is missing')
			return
		# Check for empty urls
		if not url:
			logging.error('Empty url is not acceptable')
			return
		# Make sure that our link ends with trailing slash
		if not url.endswith('/'):
			url += '/'
		# Define the searcher
		if searcher == 'html':
			self.searcher = _html_search(Base=self)
		elif searcher == 'dohq':
			self.searcher = _dohq_search(Base=self)
		else:
			logging.warn(f'Unknown searcher {searcher}, setting to dohq by default')
			self.searcher = _dohq_search(Base=self)
		# Extract info from 'req_module'
		match = [x for x in re.split('([>=<]+)', req_module) if x]
		if match[0]:
			self.module = match[0]
		else:
			logging.error('Module name parsing error')
			return
		
		self.conditions = []
		self.target_versions = []
		
		for i in range(1, len(match), 2):
			self.conditions.append(match[i])
			if len(match) > i+1:
				self.target_versions.append(match[i+1])
		
		# Check if requested module is not installed on the system
		is_not_installed = importlib.util.find_spec(self.module) is None
		
		#===============================================================
		# In case module is not installed, scan PWD
		#===============================================================
		if is_not_installed:
			# Check if a file with module's name exists in PWD
			valid_packages = self.__check_for_requested_packages(
				{ i: f for i, f in enumerate(listdir('.')) if f.endswith('.py')}
			)
			
			if valid_packages:
				package_name = valid_packages[-1][1]
				package_version = valid_packages[-1][2]
				is_not_installed = False
			
			#===============================================================
			# In case if file wiht given module name doesn't exist
			#===============================================================
			if is_not_installed:
				# Receive packages list
				packages = {}
				packages = self.searcher.search(url, login=login, password=password)
				if not packages:
					logging.error('No packages found, check if URL and credentials are valid')
					return
				
				#===============================================================
				# Getting the exact module name and version
				#===============================================================
				# Iterate through the packages
				valid_packages = self.__check_for_requested_packages(packages)
				
				# Collision check if there are any
				if len(valid_packages) > 1:
					logging.warn('More then one package satisfies your requirements')
					if tags:
						valid_packages = [pkg for pkg in valid_packages if all(tag in pkg[0] for tag in tags)]
					else:
						logging.error("We couldn't resolve the collision, please, provide some tags")
				
				# Get package's name and link for last valid match
				if valid_packages:
					package_url = valid_packages[-1][0]
					package_name = valid_packages[-1][1]
					package_version = valid_packages[-1][2]
				else:
					logging.error('Required package is not found')
					return
				
				#===============================================================
				# Installation process
				#===============================================================
				# Retrieve the package file (whether .py or .whl)
				try:
					response = requests.get(package_url, auth=(login, password))
					if response.status_code == 200:
						with open(package_name, 'wb') as out:
							out.write(response.content)
						response.close()
					else:
						logging.error(f'Server response code: {response.status_code}')
						response.close()
						return None
				except Exception:
					logging.error('Unable to download package')
					return None

				# Install and load pip packages if any
				if package_name.endswith('.whl'):
					pipe = Popen([sys.executable, '-m', 'pip', 'install', package_name])
					out = pipe.communicate()
					if pipe.returncode == 0:
						try:
							new_module = importlib.import_module(self.module)
							return new_module
						except Exception:
							logging.error('Installed module cannot be loaded')
							return None
					else:
						logging.error("Module installation didn't succeed")
						return
			#===============================================================
			# Load module from specs
			#===============================================================
			spec = importlib.util.spec_from_file_location(self.module, package_name)
			new_module = importlib.util.module_from_spec(spec)
			sys.modules[new_module] = new_module
			new_module.__version__ = package_version
			spec.loader.exec_module(new_module)
		else:
			try:
				new_module = importlib.import_module(self.module)
			except Exception:
				logging.error('Failed to load existing module')
				return None
		
		return new_module
	
	
	def __check_for_requested_packages(self, packages):
		"""
		This method separates module names from module versions and returns only
			those modules that are matching user requirements
		:param packages (dict): must satisfy the model {'module link': 'module name')}
		:return list of packages formatted like [('link', 'name', 'version')]
		"""
		valid_packages = []
		
		for (key, value) in packages.items():
			# If package is found, get it's link and name
			if self.module in value:
				# Extract package version
				match = self.re_find_version.match(value).groups()
				version = '0'
				if match[2]:
					version = match[2]
				
				__satisfy = True
				# Check if we satisfy all given requirements
				for __cond, __vers in zip(self.conditions, self.target_versions):
					if not eval(
						f'v1{__cond}v2',
						{'__builtins__': {},'v1': LooseVersion(version), 'v2': LooseVersion(__vers)},
						{}
					):
						__satisfy = False

				if __satisfy:
					valid_packages.append((key, value, version))
					
		return valid_packages
	
	
	def search_packages_dohq(self, url, dictionary={}, **kwargs):
		"""
		This method parses the remote artifactory repository structure
			and chooses those files that are having the extension .py or .whl.
			Uses dohq-artifactory API.
		:param url (str): remote artifactory repository address
		:param dictionary (dict): dict where will be passed the result
		:**kwargs may contain 'login', 'password'
		:return dict formatted like {'module link', 'module name'}
		"""
		if 'login' in kwargs and 'password' in kwargs:
			path = ArtifactoryPath(url, auth=(kwargs['login'], kwargs['password']))
		else:
			path = ArtifactoryPath(url, auth=(self.login, self.password))
		
		for p in path.glob('**/*.*'):
			link = str(p)
			if link.endswith('.py') or link.endswith('.whl'):
				dictionary.update({link: link.split('/')[-1]})
		
		return dictionary
	
	
	def __parse_html_from_string(self, url):
		"""
		Parses the html of given link with BeautifulSoup, in case of
			exceptions returns empty BS.
		:param url (str): link to be parsed
		:return BeautifulSoup of downloaded html page
		"""
		# Request the page and wrap it with BeautifulSoup
		response = requests.get(url, auth=(self.login, self.password))
		if response.status_code == 200:
			page = str(response.content)
		else:
			logging.error(f'HTTP request error: status code {response.status_code}')
			page = ''
		response.close()
		content = BeautifulSoup(page, 'html.parser')

	
		return content
	
	
	def search_packages_html(self, url, dictionary={}, **kwargs):
		"""
		Similarly to previous method, this one parses remote artifactory
			repository structure and chooses those files that are having the
			extension .py or .whl. Uses html parser, multi-threading and regexp
		:param url (str): remote artifactory repository address
		:param dictionary (dict): dict where will be passed the result
		:**kwargs may contain 'login' (str), 'password' (str)
		:return dict formatted like {'module link', 'module name'}
		"""
		#===============================================================
		# Retrieving the information from kwargs
		#===============================================================
		# Update nesting level if given
		if 'nesting_level' in kwargs:
			kwargs['nesting_level'] += 1
		else:
		# If nesting level is not defined, define it
			kwargs.update({'nesting_level': 0})
		
		# Retrieve login and password from kwargs if any were given
		if 'login' in kwargs and 'password' in kwargs:
			self.login = kwargs['login']
			self.password = kwargs['password']
			del kwargs['login']
			del kwargs['password']
		
		soup = self.__parse_html_from_string(url)
		
		#===============================================================
		# Walking through all the links on the page
		#===============================================================
		
		# Define array of scan-threads
		threads = []
		
		for link in soup.find_all('a', href=True):
			if not self.re_find_backs.match(link['href']):
				# Next line is debug only<<<----------------------------
				#print(link.text)#, link['href'])
				# Check if this is a folder link
				if self.re_find_folder.match(link['href']):
				#===============================================================
				# In case if link is a folder
				#===============================================================
					# Make sure that nesting level is lesser then max
					if kwargs['nesting_level'] < self.max_nesting_level:
						# If link is absolute, do not concat it with url
						if link['href'].startswith('http'):
							threads.append(Thread(
									target=self.search_packages_html,
									args=[link['href'], dictionary],
									kwargs=kwargs
							))
						else:
							threads.append(Thread(
									target=self.search_packages_html,
									args=[urljoin(url, link['href']), dictionary],
									kwargs=kwargs
							))
						# Make sure we didn't exceed max number of threads
						if len(threads) > self.max_threads_num:
							[t.start() for t in threads]
							[t.join() for t in threads]
							threads = []
				
				#===============================================================
				# In case if link is a file
				#===============================================================
				else:
					# Make sure that we are only searching for .py and .whl files
					if link.text.endswith('.py') or link.text.endswith('.whl'):
						# If link is absolute, do not concat it with url
						self.lock.acquire()
						if link['href'].startswith('http://') or link['href'].startswith('https://'):
							dictionary.update({link['href'] : link.text})
						else:
							dictionary.update({urljoin(url, link['href']) : link.text})
						self.lock.release()
		
		#===============================================================
		# Process finishing
		#===============================================================

		# Await till all sub-directories scans are finished
		[t.start() for t in threads]
		[t.join() for t in threads]
		
		return dictionary


class _dohq_search():
	"""
	Supporting class that standartizes the call to dohq search of a Base class
	:param Base (ArtifactoryParser): object that has search_package_dohq method
	"""
	def __init__(self, Base):
		self.Base = Base
	
	def search(self, url, dictionary={}, **kwargs):
		return self.Base.search_packages_dohq(url, dictionary, **kwargs)

class _html_search():
	"""
	Supporting class that standartizes the call to html search of a Base class
	:param Base (ArtifactoryParser): object that has search_package_html method
	"""
	def __init__(self, Base):
		self.Base = Base
	
	def search(self, url, dictionary={}, **kwargs):
		return self.Base.search_packages_html(url, dictionary, **kwargs)



