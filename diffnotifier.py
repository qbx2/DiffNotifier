#!/usr/bin/env python3
import http.client
import urllib.parse
import json
import difflib
import re
import time
import datetime
import json

def read_file_with_default(filename, default=''):
	try:
		with open(filename, 'r') as f:
			return f.read()
	except FileNotFoundError:
		return default

USER_ACCESS_TOKEN = read_file_with_default('user_access_token').strip()
APP_ACCESS_TOKEN = read_file_with_default('app_access_token').strip()
EXPIRES = int(read_file_with_default('user_access_token_expires', 0)) # UNIX timestamp
TARGET_ID = read_file_with_default('target_id').strip()
TARGET_URL = read_file_with_default('target_url').strip()
LATEST_CONTENTS = read_file_with_default('latest_contents', '')
GRAPH_API_HOST = 'graph.facebook.com'
API_VERSION = 'v2.5'

def fetch_url(url):
	if not len(url):
		return

	pr = urllib.parse.urlparse(url)
	c = {'': http.client.HTTPConnection, 'http': http.client.HTTPConnection, 'https': http.client.HTTPSConnection}.get(pr.scheme.lower(), None)(pr.netloc)
	c.request('GET', pr.path, pr.query)
	return c.getresponse().read().decode()

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

sanitize = lambda x: re.sub(r'(\s){2,}', r'\n', re.sub(r'<[^>]+>', r'\n', x)).strip()

if 0 < EXPIRES - time.time() < 86400*3: # 3 days
	message = 'Your access token (which expires at {}) has to be updated.'.format(datetime.datetime.fromtimestamp(EXPIRES))
	print(message)
	notify(APP_ACCESS_TOKEN, read(USER_ACCESS_TOKEN)['id'], message, '?redirect_uri={}'.format(urllib.parse.quote('https://developers.facebook.com/tools/accesstoken/')))

new_contents = fetch_url(TARGET_URL)

if not len(LATEST_CONTENTS):
	with open('latest_contents', 'w') as f:
		f.write(new_contents)
	exit()

# differ
diff = list(difflib.unified_diff(sanitize(LATEST_CONTENTS), sanitize(new_contents)))[2:]
pdiff = ''.join(map(lambda x:x[1:], filter(lambda x:x.startswith('+'),diff))).strip()
mdiff = ''.join(map(lambda x:x[1:], filter(lambda x:x.startswith('-'),diff))).strip()

if len(pdiff) or len(mdiff):
	summary = 'added:\n{}\n\ndeleted:\n{}\n'.format(pdiff, mdiff)
	print(summary)

	# publish & notify
	message = 'New diff has been notified to : {}'.format(read(USER_ACCESS_TOKEN, TARGET_ID)['name'])
	ret = publish(USER_ACCESS_TOKEN, TARGET_ID, summary, TARGET_URL)
	try:		
		notify(APP_ACCESS_TOKEN, read(USER_ACCESS_TOKEN)['id'], message, '?redirect_uri={}'.format(urllib.parse.quote('https://www.facebook.com/{}'.format(ret['id']))))
	finally:
		with open('latest_contents', 'w') as f:
			f.write(new_contents)
