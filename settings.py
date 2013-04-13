# author: Rami Sayar

import os

TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', None)
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', None)
MONGODB_HOST = os.environ.get('MONGODB_HOST', 'localhost')
MONGODB_PORT = os.environ.get('MONGODB_PORT', 27017)
ZMQ_ADDRESS = os.environ.get('ZMQ_ADDRESS', 'tcp://127.0.0.1:5555')
