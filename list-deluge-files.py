#!/usr/bin/python
"""list-incomplete-deluge-files

Lists incomplete files from the specified torrent. Uses Deluge's web
UI to get the list.
"""
from __future__ import print_function

import argparse
import gzip
import json
import urllib2

from cookielib import CookieJar
from StringIO import StringIO

def shellquote(s):
    return "'" + s.replace("'", "'\\''") + "'"

def unzipped(response):
    s = response.read()
    if response.info().get('Content-Encoding') == 'gzip':
        buf = StringIO(s)
        f = gzip.GzipFile(fileobj=buf)
        return f.read()
    else:
        return s

def post(opener, url, data):
    r = json.loads(unzipped(opener.open(url, json.dumps(data))))
    assert r['error'] is None, 'API error: {0}'.format(r)
    return r

def counter(_cache={'count': 0}):
    _cache['count'] = _cache['count'] + 1
    return _cache['count']

def authenticate(opener, url, password):
    login_data = {"method":"auth.login","params":[password],"id":counter()}    
    response = post(opener, url, login_data)
    assert response['result'], 'Authentication failure'

def list_files(url, password, torrent, type_):
    cj = CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))

    authenticate(opener, url, password)

    ui_data = {"method":"web.update_ui","params":[["name","save_path"],{}],"id":counter()}
    response = post(opener, url, ui_data)
    torrents = response['result']['torrents']

    matches = [torrent_id for torrent_id, details in torrents.items() if details['name'] == torrent]
    assert len(matches) > 0, "Couldn't find torrent"
    assert len(matches) == 1, "Found too many matching torrents"
    
    get_torrent_req = {"method":"web.get_torrent_files",
                       "params":[matches[0]],
                       "id":counter()}
    response = post(opener, url, get_torrent_req)
    
    def recurse(tree):
        for key, item in tree['contents'].items():
            if item['type'] == 'file':
                if not type_ or \
                   (type_ == 'incomplete' and item['progress'] < 1.0) or \
                   (type_ == 'complete' and item['progress'] == 1.0):
                    print(shellquote(item['path'].encode('utf-8')))
            elif item['type'] == 'dir':
                recurse(item)

    recurse(response['result'])

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--URL', default='http://localhost:8112/json')
    parser.add_argument('--password', default='')
    parser.add_argument('--type', default=None, help='either "complete" or "incomplete"')
    parser.add_argument('--torrent')
    args = parser.parse_args()
    list_files(url=args.URL, password=args.password,
               torrent=args.torrent, type_=args.type)

if __name__ == '__main__':
    main()
