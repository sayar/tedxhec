#!/usr/bin/env python

import argparse
import gevent
import settings
import sys

from gevent import monkey
monkey.patch_all()
from gevent_zeromq import zmq
from pymongo import MongoClient

from flask import Flask, request, Response, render_template

from socketio import socketio_manage
from socketio.namespace import BaseNamespace
from socketio.server import SocketIOServer

flask_app = Flask(__name__)
mongo_client = MongoClient(settings.MONGODB_HOST, int(settings.MONGODB_PORT))


class SMSNamespace(BaseNamespace):
    def initialize(self):
        def receive_sms():
            context = zmq.Context()

            socket = context.socket(zmq.SUB)
            socket.connect(settings.ZMQ_ADDRESS)
            socket.setsockopt(zmq.SUBSCRIBE, '')

            while True:
                sms = socket.recv()
                msg = {'text': sms, 'pos': -1}
                self.emit('sms', msg)

        self.spawn(receive_sms)

    def recv_connect(self):
        def send_smses():
            db = mongo_client['tedxhec']
            smses = db['input']

            for sms in smses.find().sort('Created'):
                msg = {'text': sms['Body'], 'pos': -1}
                self.emit('sms', msg)
                gevent.sleep(1)

        self.spawn(send_smses)


@flask_app.route('/')
def index():
    return render_template('index.html')


@flask_app.route('/socket.io/<path:remaining>')
def socketio(remaining):
    try:
        socketio_manage(request.environ, {'/sms': SMSNamespace}, request)
    except Exception, e:
        print remaining
        print e

    return Response()


def main():
    parser = argparse.ArgumentParser(description='SMS Output Service')
    parser.add_argument('-P', '--port', action='store', default=8080, dest='port', type=int)
    parser.add_argument('-H', '--host', action='store', default='', dest='host', type=str)

    args = parser.parse_args()

    SocketIOServer((args.host, args.port), flask_app, resource="socket.io").serve_forever()

if __name__ == '__main__':
    sys.exit(main())
