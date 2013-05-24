import string
import random
import requests

class Transaction(object):
    def __init__(self):
        pass

    def run(self):
      r = requests.post("http://ec2-23-20-181-107.compute-1.amazonaws.com:5000/input", data={
            'From': "+1%s" % ''.join(random.choice(string.digits) for x in range(10)),
            'FromZip': "000000",
            'FromCity': "Montreal",
            'FromState': "QC",
            'FromCountry': "CA",
            'Body': "HELLO WORLD, THIS PIECE OF SOFTWARE IS AWESOME. MECHANIZE ROCKS.",
            'SmsSid': ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(10))
        })


if __name__ == '__main__':
    trans = Transaction()
    trans.run()
    print trans.custom_timers
