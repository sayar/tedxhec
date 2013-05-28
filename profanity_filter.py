"""
Uses a line separated file listing bad words as it's source
to check if a user submitted something inappropriate

f = Filter(clean_word='unicorn')
word = f.clean('Annoyingwhores and fudge packers')
print word
>>Annoyingunicorns and unicorns
f.check('whore')
>>True
"""
import re


class Filter(object):
    """
    Replaces a bad word in a string with something more PG friendly

    Also checks to see if a string contains words that are profane
        
    """
    def __init__(self, clean_word='****'):
        self.bad_words = set(line.strip('\n') for line in open('bad_words.txt'))
        self.clean_word = clean_word
        
    def clean(self, string):
        exp = '(%s)' % '|'.join(self.bad_words)
        r = re.compile(exp, re.IGNORECASE)
        return r.sub(self.clean_word, string)

    def check(self, string):
        exp = '\\b(%s)\\b' % '|'.join(self.bad_words)
        if re.search(exp, string.lower()):
            return True
        else:
            return False
