#!/usr/bin/env python3
import http.client
import urllib.parse
import json
import difflib
import re
import time
import datetime

with open('access_token', 'r') as f:
	ACCESS_TOKEN = f.read().strip()

with open('target_id', 'r') as f:
	TARGET_ID = f.read().strip()

with open('target_url', 'r') as f:
	TARGET_URL = f.read().strip()

assert len(ACCESS_TOKEN)
assert len(TARGET_ID)
assert len(TARGET_URL)

try:
	with open('latest_contents', 'r') as f:
		LATEST_CONTENTS = f.read()
except FileNotFoundError:
	LATEST_CONTENTS = ''

try:
	with open('access_token_expires', 'r') as f:
		EXPIRES = int(f.read()) # as UNIX timestamp
except	FileNotFoundError:
	EXPIRES = 0

def fetch_url(url):
	pr = urllib.parse.urlparse(url)
	c = {'': http.client.HTTPConnection, 'http': http.client.HTTPConnection, 'https': http.client.HTTPSConnection}.get(pr.scheme.lower(), None)(pr.netloc)
	c.request('GET', pr.path, pr.query)
	return c.getresponse().read().decode()

def publish(access_token, target_id, message='', link=''):
	c = http.client.HTTPSConnection('graph.facebook.com')
	c.request('POST', '/v2.5/{}/feed'.format(target_id), urllib.parse.urlencode({'access_token': access_token, 'message': message, 'link': link}))
	return c.getresponse().read().decode()

sanitize = lambda x: re.sub(r'(\s)+', r'\1', re.sub(r'<[^>]+>', '\n', x)).strip()

if 0 < EXPIRES - time.time() < 86400*3: # 3 days
	message = 'Your access token (which expires at {}) has to be updated.'.format(datetime.datetime.fromtimestamp(EXPIRES))
	print(message)
	publish(ACCESS_TOKEN, TARGET_ID, message, 'https://developers.facebook.com/tools/accesstoken/')

new_contents = fetch_url(TARGET_URL)

try:
	if len(LATEST_CONTENTS):
		# differ
		diff = list(difflib.unified_diff(sanitize(LATEST_CONTENTS), sanitize(new_contents)))[2:]
		pdiff = ''.join(map(lambda x:x[1:], filter(lambda x:x.startswith('+'),diff))).strip()
		mdiff = ''.join(map(lambda x:x[1:], filter(lambda x:x.startswith('-'),diff))).strip()

		if len(pdiff) or len(mdiff):
			summary = 'added:\n{}\n\ndeleted:\n{}\n'.format(pdiff, mdiff)
			print(summary)

			# publish
			publish(ACCESS_TOKEN, TARGET_ID, summary, TARGET_URL)
except:
	import traceback
	traceback.print_exc()
finally:
	with open('latest_contents', 'w') as f:
		f.write(new_contents)
