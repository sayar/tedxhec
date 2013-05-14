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

    body = request.form.get('Body', None)
    sid = request.form.get('SmsSid', None)

    if len(body) < 30:
        print "Too Short Message"
        return str(twiml.Response())

    for word in re.split('\W+', body):
        if (not hunspell_en_CA.spell(word)) and (not hunspell_en_US.spell(word)):
            print "Misspelled word"
            return str(twiml.Response())

    if prof_filt.check(body):
        print "Profane Message"
        return str(twiml.Response())

    print "Good Message"

    # Persist to Mongodb
    db = mongo_client['tedxhec']
    collection = db['input_raw']

    collection.insert({
        '_id': request.form.get('SmsSid', None),
        'From': request.form.get('From', None),
        'FromZip': request.form.get('FromZip', None),
        'FromCity': request.form.get('FromCity', None),
        'FromState': request.form.get('FromState', None),
        'FromCountry': request.form.get('FromCountry', None),
        'To': request.form.get('To', None),
        'Body': body,
        'Created': datetime.datetime.now()
    })

    # Check to see if the body is not none or empty
    if body and isinstance(body, basestring) and body.strip() != '':
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
