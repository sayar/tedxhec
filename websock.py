#! /usr/bin/env python

import argparse
import gevent
import json
import sys

from gevent.pywsgi import WSGIServer
from geventwebsocket.handler import WebSocketHandler

MESSAGES = [
    { 'text': "The fox jumped over the dog.", 'pos': 0 },
    { 'text': "quick", 'pos': 1 },
    { 'text': "lazy", 'pos': 6 },
    { 'text': "brown", 'pos': 2 }
]

def serve(env, respond):
    ws = env.get('wsgi.websocket')

    if ws is None:
        respond("400 Bad Request", [])
        return ["Unexpected HTTP connection to WebSocket server"]

    for msg in MESSAGES:
        if ws.socket is None:
            break

        ws.send(json.dumps(msg))
        gevent.sleep(1)

def main():
    parser = argparse.ArgumentParser(description='WebSocket Server')
    parser.add_argument('-P', '--port', action='store', default=8080, dest='port', type=int)
    parser.add_argument('-H', '--host', action='store', default='', dest='host', type=str)

    args = parser.parse_args()

    ws_server = WSGIServer((args.host, args.port), serve, handler_class=WebSocketHandler)
    ws_server.serve_forever()

if __name__ == '__main__':
    sys.exit(main())
