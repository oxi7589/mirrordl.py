# v.2022-02-04b
# requires-interpreter: CPython3.5+
# requires-lib: requests
# example-use: python3 ./vcmirrordl.py "https://vc.5ur3kg.gq/Betm"

try:
	import requests
except ImportError:
	print('Dependencies not met. Please run:')
	print('pip3 install requests')
	raise

from os import _exit as os_return
from os import mkdir
from sys import argv
from time import sleep
from urllib.parse import urljoin, urlparse, unquote, quote
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

def sanitize_local_fn(path):
	illegals = '/\\:*?"<>|'
	for i in illegals:
		path = path.replace(i, '_')
	return path

def dl_file(url, local_dir, local_fn, session):
	local_dir = sanitize_local_path(local_dir)
	force_directories(local_dir)
	fails = 0
	file_name = sanitize_local_fn(local_fn)
	try:
		with open(local_dir + '/' + file_name, 'rb') as _:
			print('Skipped: {}'.format(file_name))
			return
	except FileNotFoundError:
		pass
	print('Downloading {}'.format(file_name))
	while fails < 5:
		sleep(2**fails - 1) # [0, 1, 3, 7, 15]
		r = session.get(url, stream=True)
		if r.ok:
			with open(local_dir + '/' + file_name, 'wb') as f:
				for chunk in r.iter_content(chunk_size=8192):
					f.write(chunk)
			return
		else:
			print('Error: HTTP status code {} for {} [{}]' \
				.format(r.status_code, url, fails + 1))
			fails += 1
	raise Exception("Can't download {}".format(url))

def get_api_json(url, session):
	fails = 0
	while fails < 5:
		sleep(2**fails - 1) # [0, 1, 3, 7, 15]
		r = session.get(url)
		if r.ok:
			j = r.json()
			if not 'folder' in j:
				raise Exception("Not a folder")
			return j
		else:
			print('Error: HTTP status code {} for {} [{}]' \
				.format(r.status_code, url, fails + 1))
			if r.status_code == 404:
				raise Exception("Resource not found (404)")
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

def proc_url(path, params, session):
	print('Processing /{}'.format(path))
	base_netloc = params['base_netloc']
	api_url = base_netloc + '/api?path=/' + quote(path)
	j_fld = get_api_json(api_url, session)['folder']
	if not 'value' in j_fld:
		return
	j_fldval = j_fld['value']
	# list of (name, download_url) tuples
	files_links = ((z['name'], \
					z['@microsoft.graph.downloadUrl']) \
				   for z in j_fldval if 'file' in z)
	# list of subfolder names
	folders_links = (z['name'] \
					 for z in j_fldval if 'folder' in z)
	files_args = []
	dirs_args = []
	for name, down_url in files_links:
		full_rp = '/'.join([path, name])
		if matches_conditions(params, full_rp):
			# url, local_dir, local_fn, session
			files_args.append((down_url, path, name, session))
	for name in folders_links:
		full_rp = '/'.join([path, name])
		if matches_conditions(params, full_rp):
			dirs_args.append((full_rp, params, session))
	for fa in files_args:
		dl_file(*fa)
	for da in dirs_args:
		proc_url(*da)

def parse_args(args):
	if not args:
		print('usage: python3 /path/to/this.py "https://mirror.url/Artist"')
		os_return(-1)
	# known_args = {'parameter' : arguments count (0 or 1)}
	known_args = {'regex' : 1, 'condition': 1, 'allow-unknown-source': 0}
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
	if not '//vc.5ur3kg.gq' in url:
		if not 'allow-unknown-source' in params:
			print('This tool expects URLs to be from vc.5ur3kg.gq')
			print('Note: use --allow-unknown-source parameter to continue anyway,')
			print('      if you know what you are doing')
			os_return(-1)
	s = requests.Session()
	s.headers.update({
		'User-Agent' : 'Mozilla/5.0 mirrordl/0.0',
		'Accept' : 'application/json, */*',
		'Accept-Language' : 'en-us'
	})
	upr = urlparse(url)
	params['base_netloc'] = upr.scheme + '://' + upr.netloc
	try:
		proc_url(unquote(upr.path.strip('/')), params, s)
	except Exception as e:
		print('Aborted. {}'.format(e))

if __name__ == '__main__':
	main()
