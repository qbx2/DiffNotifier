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
import os

sys.path.append('DiffNotifier-Django')

# django
import django

if __name__ == '__main__':
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "DiffNotifier.settings")
    django.setup()

from DiffNotifier import settings
from settings.models import *

USER_ACCESS_TOKEN = settings.USER_ACCESS_TOKEN
APP_ACCESS_TOKEN = settings.APP_ACCESS_TOKEN
EXPIRES = settings.EXPIRES # UNIX timestamp

FCM_KEY = settings.FCM_KEY

GRAPH_API_HOST = 'graph.facebook.com'
API_VERSION = 'v2.6'

FCM_API_HOST = 'fcm.googleapis.com'

def fetch_url(r, encoding='utf-8'):
	if len(r.url) == 0:
		return

	pr = urllib.parse.urlparse(r.url)
	c = {'': http.client.HTTPConnection, 'http': http.client.HTTPConnection, 'https': http.client.HTTPSConnection}.get(pr.scheme.lower(), None)(pr.netloc)
	c.request('GET', pr.path + '?' + pr.query, headers=r.headers_dict())
	r = c.getresponse()
	return (r.status, r.read())

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

def fcm_send(key, fcm_type, obj, to):
    if not key:
        return

    if fcm_type == 'noti':
        noti = obj
        data = {'type': fcm_type, 'target_id': noti.target.id, 'url': noti.target.request.url, 'contents': re.sub(r'\s+', ' ', noti.contents)}
        payload = json.dumps({'data': data, 'to': to})
    elif fcm_type == 'comment':
        comment = obj
        data = {'type': fcm_type, 'target_id': comment.noti.target.id, 'body': '{}: {}'.format(comment.owner, comment.comment), 'url': comment.noti.target.request.url, 'noti_id': comment.noti.id}
        payload = json.dumps({'data': data, 'to': to})

    print('fcm_send({})'.format(data))

    c = http.client.HTTPSConnection(FCM_API_HOST)
    c.request('POST', '/fcm/send', payload, {'Authorization': 'key=' + key, 'Content-Type': 'application/json'})
    ret = json.loads(c.getresponse().read().decode())	
    return ret

def sanitize(s, regex_filter_list=[]):
	for regex_filter in regex_filter_list:
		s = re.sub(regex_filter, r'\n', s, flags=re.S)
	return re.sub(r'(\s){2,}', r'\n', re.sub(r'\xa0+', ' ', html.unescape(re.sub(r'<[^>]+>', r'\n', s)))).strip()

def update_request(r):
    print('Fetching url: {}'.format(r.url))

    try:
        status_code, new_contents = fetch_url(r)

        if status_code == 200:
            with open(r.filename(), 'wb') as f:
                f.write(new_contents)

            r.updated_timestamp = time.time()
            r.save()

            return new_contents
    except Exception as e:
        print(repr(e), 'while updating', r)
        traceback.print_exc()
        return None

def update_target(t, old_contents, new_contents):
    noti_targets = t.noti_targets.all()

    if len(noti_targets) == 0:
        return

    encoding_candidates = [t.encoding, 'utf-8', 'cp949']

    while True:
        try:
            encoding = encoding_candidates.pop()
            tentative_old_contents = old_contents.decode(encoding)
            tentative_new_contents = new_contents.decode(encoding)
            old_contents = tentative_old_contents
            new_contents = tentative_new_contents
            break
        except UnicodeDecodeError:
            pass
        except IndexError:
            print('Couldn\'t decode', t)
            return False

    regex_filter_list = t.filters_set()

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
        print(str(summary))

        if not len(t.noti_targets.all()):
            return

        noti = Noti.objects.create(contents=summary, target=t)
        summary += '\n\nNoti Id: {}'.format(noti.id)

        for noti_target in noti_targets:
            target_id = noti_target.facebook_id
            fcm_token = noti_target.fcm_token

            if target_id:
                # publish & notify
                ret = publish(USER_ACCESS_TOKEN, target_id, summary, t.request.url)

                message = 'New diff has been notified to : {}'.format(read(USER_ACCESS_TOKEN, target_id)['name'])
                notify(APP_ACCESS_TOKEN, read(USER_ACCESS_TOKEN)['id'], message, '?redirect_uri={}'.format(urllib.parse.quote('https://www.facebook.com/{}'.format(ret['id']))))
            
            if fcm_token:
                ret = fcm_send(FCM_KEY, 'noti', noti, fcm_token)

def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
            print(read(USER_ACCESS_TOKEN))
            print(notify(APP_ACCESS_TOKEN, read(USER_ACCESS_TOKEN)['id'], 'notify_test'))
            print(publish(USER_ACCESS_TOKEN, 'me', 'publish_test'))
            exit()

    if 0 < EXPIRES - time.time() < 86400*3: # 3 days
        message = 'Your access token (which expires at {}) has to be updated.'.format(datetime.datetime.fromtimestamp(EXPIRES))
        print(message)
        notify(APP_ACCESS_TOKEN, read(USER_ACCESS_TOKEN)['id'], message, '?redirect_uri={}'.format(urllib.parse.quote('https://developers.facebook.com/tools/accesstoken/')))

    rs = Request.objects.all()

    for r in rs:
        if len(r.target_set.exclude(noti_targets=None)):
            try:
                with open(r.filename(), 'rb') as f:
                    old_contents = f.read()
            except:
                old_contents = b''

            new_contents = update_request(r)

            if (not old_contents) or new_contents is None:
                continue
            
            for t in r.target_set.all():
                update_target(t, old_contents, new_contents)

if __name__ == '__main__':
    main()
