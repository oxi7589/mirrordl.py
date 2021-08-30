# v.2021-08-30
# requires-interpreter: CPython3.5+
# requires-lib: beautifulsoup4, requests
# example-use: python3 ./mirrordl.py "https://5ur3kg.gq/?dir=public/Betm/15007%20%E5%AE%BFX%E8%99%8E"

try:
	import requests
	from bs4 import BeautifulSoup
except ImportError:
	print('Dependencies not met. Please run:')
	print('pip3 install requests beautifulsoup4')
	raise

from os import _exit as os_return
from os import mkdir
from sys import argv
from time import sleep
from urllib.parse import urljoin, urlparse, unquote
import re

def mkdir_if_not_exists(d):
	try:
		mkdir(d)
	except:
		pass

def force_directories(path):
	pp = [x for x in path.split('/') if x]
	parents = ''
	for p in pp:
		mkdir_if_not_exists(parents + p)
		parents += p + '/'

def sanitize_local_path(path):
	illegals = '\\:*?"<>|'
	for i in illegals:
		path = path.replace(i, '_')
	return path

def dl_file(url, local_dir, session):
	local_dir = sanitize_local_path(local_dir)
	force_directories(local_dir)
	fails = 0
	file_name = unquote(url.split('/')[-1])
	try:
		with open(local_dir + file_name, 'rb') as _:
			print('Skipped: {}'.format(file_name))
			return
	except FileNotFoundError:
		pass
	print('Downloading {}'.format(file_name))
	while fails < 5:
		sleep(2**fails - 1) # [0, 1, 3, 7, 15]
		r = session.get(url, stream=True)
		if r.ok:
			with open(local_dir + file_name, 'wb') as f:
				for chunk in r.iter_content(chunk_size=8192):
					f.write(chunk)
			return
		else:
			print('Error: HTTP status code {} for {} [{}]' \
				.format(r.status_code, url, fails + 1))
			fails += 1
	raise Exception("Can't download {}".format(url))

def get_bs4_html(url, session):
	fails = 0
	while fails < 5:
		sleep(2**fails - 1) # [0, 1, 3, 7, 15]
		r = session.get(url)
		if r.ok:
			r.encoding = 'utf-8'
			return BeautifulSoup(r.text, features="html.parser")
		else:
			print('Error: HTTP status code {} for {} [{}]' \
				.format(r.status_code, url, fails + 1))
			fails += 1
	raise Exception("Can't get {}".format(url))

def matches_conditions(params, url):
	if not 'regex' in params.keys():
		return True
	if not 'regexc' in params.keys():
		params['regexc'] = re.compile(params['regex'])
	regex_c = params['regexc']
	match = regex_c.search(url)
	if not 'condition' in params.keys():
		return bool(match)
	return bool(eval(params['condition']))

def proc_url(url, params, session):
	print('Getting {}'.format(url))
	base_netloc = params['base_netloc']
	child_urls = []
	bs = get_bs4_html(url, session)
	header_links = (x['href'] for x in bs.header.find_all('a') \
		if '?dir=' in x.get('href'))
	self_href = list(header_links)[-1] + '/' # used to prevent going up to '..'
	local_path = unquote(self_href.split('?dir=')[1])
	bs.header.decompose()
	bs.footer.decompose()
	files_links = (x['href'] for x in bs.find_all('a') \
		if x.get('href') and not '?dir' in x['href'])
	folders_links = (x['href'] for x in bs.find_all('a') \
		if x.get('href') \
		and x['href'].startswith(self_href))
	files_args = []
	dirs_args = []
	for u in files_links:
		if matches_conditions(params, u):
			full_url = urljoin(base_netloc, u)
			files_args.append((full_url, local_path, session))
	for u in folders_links:
		if matches_conditions(params, u):
			full_url = urljoin(base_netloc, u)
			dirs_args.append((full_url, params, session))
	del bs # free up the precious memory used by the HTML parser
	for fa in files_args:
		dl_file(*fa)
	for da in dirs_args:
		proc_url(*da)

def parse_args(args):
	if not args:
		print('usage: python3 /path/to/this.py "https://mirror.url/?dir=artist"')
		os_return(-1)
	# known_args = {'parameter' : arguments count (0 or 1)}
	known_args = {'regex' : 1, 'condition': 1}
	parsed_args = {}
	expect = None
	url = ''
	for arg in args:
		if arg.startswith('--'):
			if expect is not None:
				print('Missing argument for {}'.format(expect))
				os_return(-1)
			arg = arg[2:]
			if not arg in known_args.keys():
				print('Unknown parameter: {}'.format(arg))
				os_return(-1)
			else:
				subargs = known_args[arg]
				if subargs == 1:
					expect = arg
				else:
					parsed_args[expect] = True
		elif expect:
			parsed_args[expect] = arg
			expect = None
		else:
			parsed_args['url'] = arg
	if expect is not None:
		print('Missing argument for {}'.format(expect))
		os_return(-1)
	if not 'url' in parsed_args.keys():
		print('URL is required')
		os_return(-1)
	return parsed_args

def main():
	params = parse_args(argv[1:])
	url = params['url']
	if not '//' in url:
		print('{} does not look like an URL. Is it missing https://?'.format(url))
		os_return(-1)
	if '//mirror.5ur3kg.gq' in url:
		print('This tool expects URLs to be from 5ur3kg.gq, not mirror.5ur3kg.gq')
		os_return(-1)
	if '//adf.rocks' in url:
		print('This tool expects URLs to be from 5ur3kg.gq, not adf.rocks')
		os_return(-1)
	if not '?dir=' in url:
		print('Could not find a "?dir=" part. Is this a directory?')
		os_return(-1)
	s = requests.Session()
	s.headers.update({
		'User-Agent' : 'Mozilla/5.0 (mirrordl/0.0)',
		'Accept' : 'text/html, */*',
		'Accept-Language' : 'en-us'
	})
	params['base_netloc'] = 'https://' + urlparse(url).netloc
	proc_url(url, params, s)

if __name__ == '__main__':
	main()
