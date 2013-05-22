#! /usr/bin/env python
import string
import random
import requests

if __name__ == '__main__':
    r = requests.post("http://localhost:5000/input", data={
          'From': "+1%s" % ''.join(random.choice(string.digits) for x in range(10)),
          'FromZip': "000000",
          'FromCity': "Montreal",
          'FromState': "QC",
          'FromCountry': "CA",
          'Body': "HELLO WORLD, THIS PIECE OF SOFTWARE IS AWESOME. MECHANIZE ROCKS.",
          'SmsSid': ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(10))
    })

