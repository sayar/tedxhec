#!/usr/bin/env python

import argparse
import gevent
import redis
import settings
import sys
import datetime

from random import choice

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

story_mode = "Everything"
init = False

class SMSNamespace(BaseNamespace):
    def initialize(self):

        def receive_sms():
            sub = redis_client.pubsub()
            sub.subscribe('story')
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
        smses = db['story']

        for sms in smses.find().sort('Created'):
            msg = {'text': sms['Body'], 'pos': -1}
            self.emit('sms', msg)

class AdminNamespace(BaseNamespace, BroadcastMixin):
    removed_smses = []
    def initialize(self):
        def receive_sms_admin():
            sub = redis_client.pubsub()
            sub.subscribe('admin_queue')
            self.emit('print_mode', {'mode': story_mode})
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

    def recv_connect(self):
        #find all the entries in the database collection input_raw
        db = mongo_client['tedxhec']
        smses = db['input_raw']

        for sms in smses.find().sort('Created'):
            msg = {'text': sms['Body'], 'sid': sms['_id'], 'pos': -1}
            self.emit('admin', msg)

    def on_approve_sms(self, message):
        #move the database entry to the input collection
        db = mongo_client['tedxhec']
        db_entry = db['input_raw'].find_and_modify(query={'_id': message["id"]}, remove=True)
        db['input'].insert(db_entry)

        #publish the text for the story controller
        globals()['smses'].append(message["text"] + '\t' + message["id"])

        #signal all admin pages to remove this sms from the page
        self.broadcast_event_not_me('admin_remove', {'sid': message["id"]})

    def on_change_mode(self, message):
        if globals()['story_mode'] == "Everything":
            globals()['story_mode'] = "Rounds"
        else:
            globals()['story_mode'] = "Everything"
        self.broadcast_event('print_mode', {'mode': story_mode})
            
    def on_remove_sms(self, message):
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
        socketio_manage(request.environ, {'/sms': SMSNamespace, '/admin': AdminNamespace}, request)
    except Exception, e:
        print e

    return Response()

smses = []

def storyControl():
    sub = redis_client.pubsub()
    sub.subscribe('queue')
    switchedModes = False
    db = mongo_client['tedxhec']


    while True:
        if story_mode == "Everything":
            switchedModes = False
            #pull the smses out of the list and publish them to the page
            for sms in smses:
                smsSplit = sms.split("\t", 1)
                redis_client.publish('story', smsSplit[0])
                smses.remove(sms)
                db_entry = db['input'].find_and_modify(query={'_id': smsSplit[1]}, remove=True)
                db['story'].insert(db_entry)
        else:
            #if this is the first time after switching modes, mark the time
            if not switchedModes:
                switchedModes = True
                start_time = datetime.datetime.now()

            #if 30 seconds have passed, choose an sms from the list and push it to the story
            if (datetime.datetime.now() - start_time).seconds > 30:
                start_time = datetime.datetime.now()
                if len(smses) == 0:
                    continue
                chosenSms = choice(smses)
                chosenSms = chosenSms.split("\t", 1)
                redis_client.publish('story', chosenSms[0])
                db_entry = db['input'].find_and_modify(query={'_id': chosenSms[1]}, remove=True)
                db['story'].insert(db_entry)
                smses[:] = []


        gevent.sleep(0)

def main():
    parser = argparse.ArgumentParser(description='SMS Output Service')
    parser.add_argument('-P', '--port', action='store', default=8080, dest='port', type=int)
    parser.add_argument('-H', '--host', action='store', default='', dest='host', type=str)

    args = parser.parse_args()

    gevent.spawn(storyControl)

    SocketIOServer((args.host, args.port), flask_app, resource="socket.io").serve_forever()

if __name__ == '__main__':
    sys.exit(main())
