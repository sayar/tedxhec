#!/usr/bin/env python
# author: Rami Sayar, Alex Carruthers, Kelley Mitchell

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

unapproved_queue = []
approved_queue = []
story_queue = []

story_mode = "Everything"
CHOICE_TIME_SPAN = 20


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
                unapproved_queue.append(msg)

        gevent.sleep(0)


class AdminNamespace(BaseNamespace):
    waiting_for_approval = None

    def recv_connect(self):
        def emit_unapproved_message():
            while True:
                if not self.waiting_for_approval:
                    if len(unapproved_queue) > 0:
                        item = unapproved_queue.pop(0)
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

        copy = self.waiting_for_approval
        self.waiting_for_approval = None  # let other gevent threads work properly.
        approved_queue.append(copy)

    def on_remove_sms(self, message):
        db = mongo_client['tedxhec']
        entry = db['input_raw'].find_one(self.waiting_for_approval['sid'])
        db['input_unapproved'].insert(entry)

        self.waiting_for_approval = None  # let other gevent threads work properly.

    def recv_disconnect(self):
        if self.waiting_for_approval:
            unapproved_queue.append(self.waiting_for_approval)

    def on_change_mode(self, message):
        if globals()['story_mode'] == "Everything":
            globals()['story_mode'] = "Rounds"
        else:
            globals()['story_mode'] = "Everything"

    def on_clear(self, message):
        db = mongo_client['tedxhec']
        db['input_raw'].remove(None)
        db['input_approved'].remove(None)
        db['input_unapproved'].remove(None)
        db['story'].remove(None)
        redis_client.flushall()

        # Not sure if this is the correct way of doing this... there is no clear method.
        del unapproved_queue[:]
        del approved_queue[:]
        del story_queue[:]


def story_control():
    switchedModes = False
    smses_round = []
    db = mongo_client['tedxhec']
    start_time = datetime.datetime.now()

    while True:
        if story_mode == "Everything":
            switchedModes = False
            if len(approved_queue) > 0:
                sms = approved_queue.pop(0)
                entry = db['input_raw'].find_one(sms['sid'])
                db['story'].insert(entry)

                story_queue.append({'text': sms['text'], 'type': 'publish'})
        else:
            #if this is the first time after switching modes, mark the time
            if not switchedModes:
                switchedModes = True
                start_time = datetime.datetime.now()
            if len(approved_queue) > 0:
                sms = approved_queue.pop(0)
                story_queue.append({'text': sms['text'], 'type': 'potential'})
                smses_round.append(sms)

            #if 30 seconds have passed, choose an sms from the list and push it to the story
            if (datetime.datetime.now() - start_time).seconds > CHOICE_TIME_SPAN:
                start_time = datetime.datetime.now()
                if len(smses_round) == 0:
                    continue
                chosenSms = choice(smses_round)

                entry = db['input_raw'].find_one(chosenSms['sid'])
                db['story'].insert(entry)

                story_queue.append({'text': chosenSms['text'], 'type': 'publish'})
                smses_round = []

        gevent.sleep(0)


class SMSNamespace(BaseNamespace, BroadcastMixin):
    def initialize(self):
        def receive_sms():
            while True:
                if len(story_queue) > 0:
                    sms = story_queue.pop(0)
                    if sms['type'] == 'publish':
                        msg = {'text': sms['text'], 'pos': -1}
                        self.broadcast_event('sms', msg)
                    else:
                        msg = {'text': sms['text']}
                        self.broadcast_event('potential', msg)
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


@flask_app.route('/socket.io/<path:remaining>')
def socketio(remaining):
    try:
        socketio_manage(request.environ, {'/sms': SMSNamespace, '/admin': AdminNamespace}, request)
    except Exception, e:
        print e
        print remaining
    return Response()


def main():
    parser = argparse.ArgumentParser(description='SMS Output Service')
    parser.add_argument('-P', '--port', action='store', default=8080, dest='port', type=int)
    parser.add_argument('-H', '--host', action='store', default='', dest='host', type=str)

    args = parser.parse_args()

    gevent.spawn(queue_from_redis)
    gevent.spawn(story_control)

    SocketIOServer((args.host, args.port), flask_app, resource="socket.io").serve_forever()


if __name__ == '__main__':
    sys.exit(main())
