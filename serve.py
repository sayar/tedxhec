#!/usr/bin/env python

import argparse
import gevent
import redis
import settings
import sys
import datetime

from random import choice

from gevent import monkey
from gevent.queue import Queue, Empty

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

unapproved_queue = Queue()
approved_queue = Queue()
story_queue = Queue()

story_mode = "Everything"


def queue_from_redis():
    """
    Take all messages and put them into the unapproved queue.
    """
    sub = redis_client.pubsub()
    sub.subscribe('admin_queue')
    while True:
        for sms in sub.listen():
            data = sms['data']
            if isinstance(data, basestring):
                data = data.split("\t", 1)
                msg = {'text': data[0], 'sid': data[1]}
                unapproved_queue.put_nowait(msg)
        gevent.sleep(0)


class AdminNamespace(BaseNamespace):
    waiting_for_approval = None

    def recv_connect(self):
        def emit_unapproved_message():
            while True:
                if self.waiting_for_approval:
                    item = unapproved_queue.get(True)
                    self.waiting_for_approval = item
                    self.emit('admin', item)

                gevent.sleep(0)
        gevent.spawn(emit_unapproved_message)

        def emit_story_mode():
            while True:
                self.emit("print_mode", {'mode': story_mode})
                gevent.sleep(2)
        gevent.spawn(emit_story_mode)

    def on_approve_sms(self, message):
        db = mongo_client['tedxhec']
        entry = db['input_raw'].find_one(self.waiting_for_approval['sid'])
        db['input_approved'].insert(entry)

        approved_queue.put_nowait(self.waiting_for_approval)
        self.waiting_for_approval = None

    def on_unapprove_sms(self, message):
        db = mongo_client['tedxhec']
        entry = db['input_raw'].find_one(self.waiting_for_approval['sid'])
        db['input_unapproved'].insert(entry)

        approved_queue.put_nowait(self.waiting_for_approval)
        self.waiting_for_approval = None

    def recv_disconnect(self):
        if self.waiting_for_approval:
            unapproved_queue.put_nowait(self.waiting_for_approval)

    def on_change_mode(self, message):
        if globals()['story_mode'] == "Everything":
            globals()['story_mode'] = "Rounds"
        else:
            globals()['story_mode'] = "Everything"


def story_control():
    switchedModes = False
    smses_round = []
    db = mongo_client['tedxhec']
    start_time = datetime.datetime.now()

    while True:
        if story_mode == "Everything":
            switchedModes = False
            try:
                sms = approved_queue.get_nowait()
                entry = db['input_raw'].find_one(sms['sid'])
                db['story'].insert(entry)

                story_queue.put({'text': sms['text'], 'type': 'publish'})
            except Empty:
                pass
        else:
            #if this is the first time after switching modes, mark the time
            if not switchedModes:
                switchedModes = True
                start_time = datetime.datetime.now()
            try:
                sms = approved_queue.get_nowait()
                story_queue.put({'text': sms['text'], 'type': 'potential'})
                smses_round.append(sms)
            except Empty:
                pass

            #if 30 seconds have passed, choose an sms from the list and push it to the story
            if (datetime.datetime.now() - start_time).seconds > 30:
                start_time = datetime.datetime.now()
                if len(smses_round) == 0:
                    continue
                chosenSms = choice(smses_round)

                entry = db['input_raw'].find_one(chosenSms['sid'])
                db['story'].insert(entry)

                story_queue.put({'text': chosenSms['text'], 'type': 'publish'})
                smses_round = []

        gevent.sleep(0)


class SMSNamespace(BaseNamespace, BroadcastMixin):
    def initialize(self):
        def receive_sms():
            while True:
                sms = story_queue.get()
                if sms['type'] == 'publish':
                    msg = {'text': sms['text'], 'pos': -1}
                    self.emit('sms', msg)
                else:
                    msg = {'text': sms['text']}
                    self.emit('potential', msg)
                gevent.sleep(0)

        self.spawn(receive_sms)


    def recv_connect(self):
        db = mongo_client['tedxhec']
        smses = db['story']

        for sms in smses.find().sort('Created'):
            msg = {'text': sms['Body'], 'pos': -1}
            self.emit('sms', msg)

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
    #TODO: UPDATE...
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


def main():
    parser = argparse.ArgumentParser(description='SMS Output Service')
    parser.add_argument('-P', '--port', action='store', default=8080, dest='port', type=int)
    parser.add_argument('-H', '--host', action='store', default='', dest='host', type=str)

    args = parser.parse_args()

    for i in range(3):
        gevent.spawn(queue_from_redis)
    gevent.spawn(story_control)

    SocketIOServer((args.host, args.port), flask_app, resource="socket.io").serve_forever()


if __name__ == '__main__':
    sys.exit(main())
