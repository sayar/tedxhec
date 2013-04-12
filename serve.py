#!/usr/bin/env python

import argparse
import gevent
import settings
import sys

from gevent import monkey; monkey.patch_all()
from pymongo import MongoClient
from socketio import socketio_manage
from socketio.namespace import BaseNamespace
from socketio.server import SocketIOServer

mongo_client = MongoClient(settings.MONGODB_HOST, int(settings.MONGODB_PORT))

class SMSNamespace(BaseNamespace):
    def recv_connect(self):
        def send_smses():
            db = mongo_client['tedxhec']
            input = db['input']

            for sms in input.find().sort('Created'):
                msg = {'text': sms['Body'], 'pos': -1}
                self.emit('sms', msg)
                gevent.sleep(1)

        self.spawn(send_smses)

class Server():
    def __call__(self, environ, start_response):
        path = environ['PATH_INFO'].strip('/') or 'index.html'

        if path.startswith('static') or path == 'index.html':
            try:
                body = open(path).read()

            except Exception:
                return not_found(start_response)

            if path.endswith('.css'):
                content_type = 'text/css'

            elif path.endswith('.js'):
                content_type = 'text/javascript'

            else: content_type = 'text/html'

            start_response('200 OK', [('Content-Type', content_type)])
            return [body]

        elif path.startswith('socket.io'):
            socketio_manage(environ, {'/sms': SMSNamespace})

        else: return not_found(start_response)

def not_found(start_response):
    start_response('404 Not Found', [])
    return ['<h1>Not Found</h1>']

def main():
    parser = argparse.ArgumentParser(description='WebSocket Server')
    parser.add_argument('-P', '--port', action='store', default=8080, dest='port', type=int)
    parser.add_argument('-H', '--host', action='store', default='', dest='host', type=str)

    args = parser.parse_args()

    SocketIOServer((args.host, args.port), Server()).serve_forever()

if __name__ == '__main__':
    sys.exit(main())
