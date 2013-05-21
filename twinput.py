#! /usr/bin/env python
# author: Rami Sayar

import re
import sys
import argparse
import datetime
import settings
from profanity_filter import Filter
from gevent import monkey
from gevent.wsgi import WSGIServer
# Monkey patch first for MongoClient
monkey.patch_all()

import hunspell
import redis
from flask import Flask, request
from twilio import twiml
from pymongo import MongoClient

flask_app = Flask(__name__)
mongo_client = MongoClient(settings.MONGODB_HOST, int(settings.MONGODB_PORT))
redis_client = redis.client.StrictRedis(settings.REDIS_HOST, int(settings.REDIS_PORT))
hunspell_en_CA = hunspell.HunSpell('/usr/share/hunspell/en_CA.dic', '/usr/share/hunspell/en_CA.aff')
hunspell_en_US = hunspell.HunSpell('/usr/share/hunspell/en_US.dic', '/usr/share/hunspell/en_US.aff')
prof_filt = Filter()

@flask_app.route('/input', methods=['POST'])
def sms():
    """
    Handle SMS received from Twilio, Persist to Mongodb
    """
    if flask_app.debug:
        import pprint
        pprint.pprint(request.form)

    db = mongo_client['tedxhec']

    # Persist phone numbers for after the presentation thank you message.
    collection = db['participants']
    # Save instead of insert as people are expected to participate more than once.
    collection.save({
        '_id': request.form.get('From', None),
        'FromZip': request.form.get('FromZip', None),
        'FromCity': request.form.get('FromCity', None),
        'FromState': request.form.get('FromState', None),
        'FromCountry': request.form.get('FromCountry', None),
    })

    body = request.form.get('Body', None)
    sid = request.form.get('SmsSid', None)

    # Kill none and empty messages.
    if not body or not isinstance(body, basestring) or body.strip() == '':
        return str(twiml.Response())

    # We don't want message with anything less than a phrase to pop up on the screen.
    if len(body) < 30:
        if flask_app.debug:
            print "Too Short Message: %s" % body
        return str(twiml.Response())

    # Check for spelling mistakes.
    for word in re.split('\W+', body):
        if (not hunspell_en_CA.spell(word)) and (not hunspell_en_US.spell(word)):
            if flask_app.debug:
                print "Misspelled Words in Message: %s" % body
            return str(twiml.Response())

    # Check for profanity
    if prof_filt.check(body):
        if flask_app.debug:
            print "Profane Message: %s" % body
        return str(twiml.Response())

    # Persist to Mongodb
    collection = db['input_raw']
    collection.insert({
        '_id': request.form.get('SmsSid', None),
        'Body': body,
        'Created': datetime.datetime.now()
    })

    # Publish to the admin queue
    redis_client.publish('admin_queue', body + "\t" + sid)

    # Return an empty response to Twilio.
    return str(twiml.Response())


def main():
    """
    Main Method for SMS Input Service.
    """
    parser = argparse.ArgumentParser(description='SMS Input Service')
    parser.add_argument('-d', '--debug', action='store_true', default=False, dest='debug')
    parser.add_argument('-P', '--port', action='store', default=5000, dest='port', type=int)
    parser.add_argument('-H', '--host', action='store', default='', dest='host', type=str)

    args = parser.parse_args()

    if args.debug:
        print "Running in Debug Mode"
        flask_app.debug = True

    http_server = WSGIServer((args.host, args.port), flask_app)
    http_server.serve_forever()


if __name__ == '__main__':
    sys.exit(main())
