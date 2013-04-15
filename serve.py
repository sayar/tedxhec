#!/usr/bin/env python

import argparse
import gevent
import redis
import settings
import sys

from gevent import monkey
monkey.patch_all()
from pymongo import MongoClient

from flask import Flask, request, Response, render_template

from socketio import socketio_manage
from socketio.namespace import BaseNamespace
from socketio.mixins import BroadcastMixin
from socketio.server import SocketIOServer

flask_app = Flask(__name__)
mongo_client = MongoClient(settings.MONGODB_HOST, int(settings.MONGODB_PORT))
redis_client = redis.client.StrictRedis(settings.REDIS_HOST, int(settings.REDIS_PORT))


class SMSNamespace(BaseNamespace, BroadcastMixin):
    def initialize(self):
        def receive_sms():
            sub = redis_client.pubsub()
            sub.subscribe('queue')

            while True:
                for sms in sub.listen():
                    data = sms['data']

                    if isinstance(data, basestring):
                        msg = {'text': data, 'pos': -1}
                        self.emit('sms', msg)

                gevent.sleep(0)

        self.spawn(receive_sms)

    def recv_connect(self):
        db = mongo_client['tedxhec']
        smses = db['input']

        for sms in smses.find().sort('Created'):
            msg = {'text': sms['Body'], 'pos': -1}
            self.emit('sms', msg)


@flask_app.route('/')
def index():
    return render_template('index.html')

@flask_app.route('/clear')
def clear():
    db = mongo_client['tedxhec']
    smses = db['input']
    smses.remove(None)
    return Response()


@flask_app.route('/socket.io/<path:remaining>')
def socketio(remaining):
    try:
        socketio_manage(request.environ, {'/sms': SMSNamespace}, request)
    except Exception, e:
        print e

    return Response()


def main():
    parser = argparse.ArgumentParser(description='SMS Output Service')
    parser.add_argument('-P', '--port', action='store', default=8080, dest='port', type=int)
    parser.add_argument('-H', '--host', action='store', default='', dest='host', type=str)

    args = parser.parse_args()

    SocketIOServer((args.host, args.port), flask_app, transports=["websocket", "xhr-polling"], policy_server=False,
                   resource="socket.io").serve_forever()

if __name__ == '__main__':
    sys.exit(main())
