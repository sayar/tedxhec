# author: Rami Sayar

import os

TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', None)
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', None)

#NOTE: The mongodb will be deleted right before this repo goes publis so I don't care if you can see the password.
MONGODB_HOST = os.environ.get('MONGODB_HOST', 'mongodb://ted:ted@sawyer.mongohq.com/TEDxHEC')
MONGODB_PORT = os.environ.get('MONGODB_PORT', 10015)

#NOTE: This is also going down... sorry internet.
REDIS_HOST = os.environ.get('REDIS_HOST', 'ec2-107-22-63-170.compute-1.amazonaws.com')
REDIS_PORT = os.environ.get('REDIS_PORT', 6379)
