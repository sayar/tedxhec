#! /usr/bin/env python
# author: Rami Sayar

import sys
import argparse
import datetime
import settings
from gevent import monkey
from gevent.wsgi import WSGIServer
# Monkey patch first for MongoClient
monkey.patch_all()

from flask import Flask, request
from twilio import twiml
from pymongo import MongoClient

flask_app = Flask(__name__)
mongo_client = MongoClient(settings.MONGODB_HOST, int(settings.MONGODB_PORT))


@flask_app.route('/input', methods=['POST'])
def sms():
    """
    Handle SMS received from Twilio, Persist to Mongodb
    """
    if flask_app.debug:
        import pprint
        pprint.pprint(request.form)

    # Persist to Mongodb
    db = mongo_client['tedxhec']
    collection = db['input']
    collection.insert({
        '_id': request.form.get('SmsSid', None),
        'From': request.form.get('From', None),
        'FromZip': request.form.get('FromZip', None),
        'FromCity': request.form.get('FromCity', None),
        'FromState': request.form.get('FromState', None),
        'FromCountry': request.form.get('FromCountry', None),
        'To': request.form.get('To', None),
        'Body': request.form.get('Body', None),
        'Created': datetime.datetime.now()
    })

    # Check to see if the body is not none or empty
    body = request.form.get('Body', None),
    if body and isinstance(body, basestring) and body.strip() != '':
        if 'queue' not in db.collection_names():
            db.create_collection(
                'queue',
                capped=True,
                size=2 ** 20,
                max=100,
                autoIndexId=False)

        queue = db['queue']
        queue.insert({
            'Body': body
        })

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
