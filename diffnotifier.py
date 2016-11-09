#!/usr/bin/env python3
import traceback
import http.client
import urllib.parse
import json
import difflib
import re
import time
import datetime
import json
import pickle
import gzip
import html
import sys

def read_file_with_default(filename, default=''):
	try:
		with open(filename, 'r') as f:
			return f.read()
	except FileNotFoundError:
		return default

USER_ACCESS_TOKEN = read_file_with_default('user_access_token.txt').strip()
APP_ACCESS_TOKEN = read_file_with_default('app_access_token.txt').strip()
EXPIRES = int(read_file_with_default('user_access_token_expires.txt', 0)) # UNIX timestamp
TARGET_LIST = json.loads(read_file_with_default('target_list.json', '[]').strip()) # [[target_id, target_url], ...]
LATEST_CONTENTS_LIST_FILENAME = 'latest_contents_list.pkl.gz'

try:
	with gzip.open(LATEST_CONTENTS_LIST_FILENAME, 'rb') as f:
		LATEST_CONTENTS_LIST = pickle.load(f) # {target_url: latest_contents}
except (FileNotFoundError, EOFError):
	LATEST_CONTENTS_LIST = {}

GRAPH_API_HOST = 'graph.facebook.com'
API_VERSION = 'v2.6'

def fetch_url(url, encoding='utf-8'):
	if len(url) == 0:
		return

	pr = urllib.parse.urlparse(url)
	c = {'': http.client.HTTPConnection, 'http': http.client.HTTPConnection, 'https': http.client.HTTPSConnection}.get(pr.scheme.lower(), None)(pr.netloc)
	c.request('GET', pr.path + '?' + pr.query)
	r = c.getresponse()
	return (r.status, r.read().decode(encoding))

def publish(access_token, target_id, message='', link=''):
	if not access_token or not target_id:
		return

	c = http.client.HTTPSConnection(GRAPH_API_HOST)
	c.request('POST', '/{}/{}/feed'.format(API_VERSION, target_id), urllib.parse.urlencode({'access_token': access_token, 'message': message, 'link': link}))
	ret = json.loads(c.getresponse().read().decode())	
	if 'error' in ret:
		raise Exception(ret)
	return ret

def notify(access_token, user_id, template, href=''):
	if not access_token or not user_id or not template:
		return

	c = http.client.HTTPSConnection(GRAPH_API_HOST)
	c.request('POST', '/{}/{}/notifications'.format(API_VERSION, user_id), urllib.parse.urlencode({'access_token': access_token, 'template': template, 'href': href}))
	ret = json.loads(c.getresponse().read().decode())	
	if 'error' in ret:
		raise Exception(ret)
	return ret

def read(access_token, identifier='me', fields=''):
	if not access_token:
		return

	c = http.client.HTTPSConnection(GRAPH_API_HOST)
	c.request('GET', '/{}/{}'.format(API_VERSION, identifier) + '?' + urllib.parse.urlencode({'access_token': access_token, 'fields': fields}))
	ret = json.loads(c.getresponse().read().decode())	
	if 'error' in ret:
		raise Exception(ret)
	return ret

def sanitize(s, regex_filter_list=[]):
	for regex_filter in regex_filter_list:
		s = re.sub(regex_filter, r'\n', s, flags=re.S)
	return re.sub(r'(\s){2,}', r'\n', re.sub(r'\xa0+', ' ', html.unescape(re.sub(r'<[^>]+>', r'\n', s)))).strip()

if len(sys.argv) > 1 and sys.argv[1] == 'test':
        print(read(USER_ACCESS_TOKEN))
        print(notify(APP_ACCESS_TOKEN, read(USER_ACCESS_TOKEN)['id'], 'notify_test'))
        print(publish(USER_ACCESS_TOKEN, 'me', 'publish_test'))
        exit()

if 0 < EXPIRES - time.time() < 86400*3: # 3 days
	message = 'Your access token (which expires at {}) has to be updated.'.format(datetime.datetime.fromtimestamp(EXPIRES))
	print(message)
	notify(APP_ACCESS_TOKEN, read(USER_ACCESS_TOKEN)['id'], message, '?redirect_uri={}'.format(urllib.parse.quote('https://developers.facebook.com/tools/accesstoken/')))

for target_id, target_url, *optional_params in TARGET_LIST:
	if len(optional_params):
		encoding = optional_params[0]
	else:
		encoding = 'utf-8'

	try:
		print(target_url)
		status_code, new_contents = fetch_url(target_url, encoding)
	except Exception as e:
		print(e, 'while fetching url from', target_url)
		continue

	if status_code != 200:
		continue

	old_contents = LATEST_CONTENTS_LIST.get(target_url, '')
	LATEST_CONTENTS_LIST[target_url] = new_contents

	with gzip.open(LATEST_CONTENTS_LIST_FILENAME, 'wb') as f:
		pickle.dump(LATEST_CONTENTS_LIST, f, protocol=pickle.HIGHEST_PROTOCOL)

	regex_filter_list = optional_params[1:]

	# differ
	diff = list(difflib.unified_diff(sanitize(old_contents, regex_filter_list), sanitize(new_contents, regex_filter_list)))[2:]
	pdiff = ''.join(map(lambda x:x[1:], filter(lambda x:x.startswith('+'),diff))).strip()
	mdiff = ''.join(map(lambda x:x[1:], filter(lambda x:x.startswith('-'),diff))).strip()

	summary = []

	if len(pdiff):
		summary.append('Added:\n{}\n'.format(pdiff))

	if len(mdiff):
		summary.append('Deleted:\n{}\n'.format(mdiff))

	if len(summary):
		summary = '\n'.join(summary)
		print(str(time.time()) + '\n\n' + summary)

		# publish & notify
		ret = publish(USER_ACCESS_TOKEN, target_id, summary, target_url)
		message = 'New diff has been notified to : {}'.format(read(USER_ACCESS_TOKEN, target_id)['name'])
		notify(APP_ACCESS_TOKEN, read(USER_ACCESS_TOKEN)['id'], message, '?redirect_uri={}'.format(urllib.parse.quote('https://www.facebook.com/{}'.format(ret['id']))))
