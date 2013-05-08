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


class SMSNamespace(BaseNamespace):
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

class AdminNamespace(BaseNamespace, BroadcastMixin):
    removed_smses = []
    def initialize(self):
        def receive_sms_admin():
            sub = redis_client.pubsub()
            sub.subscribe('admin_queue')
            while True:
                for sms in sub.listen():
                    data = sms['data']
                    if isinstance(data, basestring):
                        data = data.split("\t", 1)
                        msg = {'text': data[0], 'sid': data[1], 'pos': -1}
                        self.emit('admin', msg)
                        #gevent.spawn_later(5, self.send_sms_to_client, data[0], data[1])
                gevent.sleep(0)
        self.spawn(receive_sms_admin)

    def on_approve_sms(self, message):
        print message
        #move the database entry to the input collection
        db = mongo_client['tedxhec']
        db_entry = db['input_raw'].find_and_modify(query={'_id': message["id"]}, remove=True)
        print db_entry
        db['input'].insert(db_entry)

        #publish the text for the story page
        redis_client.publish('queue', message["text"])

        #signal all admin pages to remove this sms from the page
        #self.emit('admin_remove', {'sid': message["id"]})
        self.broadcast_event_not_me('admin_remove', {'sid': message["id"]})


    def recv_connect(self):
        #find all the entries in the database collection input_raw
        db = mongo_client['tedxhec']
        smses = db['input_raw']

        for sms in smses.find().sort('Created'):
            msg = {'text': sms['Body'], 'sid': sms['_id'], 'pos': -1}
            self.emit('admin', msg)

    def on_remove_sms(self, message):
        print message
        #put the id into the list of ids we manually removed
        self.removed_smses.append(message["id"])

        #transfer the database entry to the input_removed collection
        db = mongo_client['tedxhec']
        db_entry = db['input_raw'].find_and_modify(query={'_id': message["id"]}, remove=True)
        db['input_removed'].insert(db_entry)

        #signal all the other admin pages to remove this element
        #self.emit('admin_remove', {'sid': message['id']})
        self.broadcast_event_not_me('admin_remove', {'sid': message["id"]})


@flask_app.route('/')
def index():
    return render_template('index.html')

@flask_app.route('/admin')
def admin():
    return render_template('admin.html')

@flask_app.route('/clear')
def clear():
    db = mongo_client['tedxhec']
    db['input'].remove(None)
    db['input_raw'].remove(None)
    db['input_removed'].remove(None)

    return Response()


@flask_app.route('/socket.io/<path:remaining>')
def socketio(remaining):
    try:
        print remaining
        socketio_manage(request.environ, {'/sms': SMSNamespace, '/admin': AdminNamespace}, request)
    except Exception, e:
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
