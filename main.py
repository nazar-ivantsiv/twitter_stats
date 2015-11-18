#!bin/python
# -*- coding: utf-8 -*-
from __future__ import division

'''
Twitter statistics
'''
import os
import json
import time
import sys

from ast import literal_eval
from base64 import b64encode
from base64 import b64decode
from collections import Counter
from sys import stdout
#from string import lowercase
#from string import uppercase

import oauth2

from auth_info import *
# File auth_info.py has to be in the same dir. Content:
#CONSUMER_KEY = <key>
#CONSUMER_SECRET = <secret>
#ACCESS_TOKEN = <token>
#ACCESS_TOKEN_SECRET = <token secret>
from exclude import EXCLUDE_SET

WORK_DIR = os.getcwd()

# Implement User as abstract class???
class User(object):
    '''
    User profile
    It also applies DECORATOR user_stats to Stats to change it behavior according
    to users TOKEN (rights).
    '''
    def __init__(self, user, pwd):

        self.user = user
        # Protected attribures
        self.__pwd = pwd
        # First run:
        #self.__set_user('^7muhIt2RoR5SVBB', 'admin')
        self.__access = self._get_access()

    def __call__(self, word):
        '''
        Applies DECORATOR to Stats (according to access rights).
        returns UserStats object
        '''
        UserStats = user_stats(Stats, self.__access)
        return UserStats(word)

    @property
    def access(self):
        return self.__access
    

    @property
    def __rights(self):
        try:
            with open('{}/user'.format(WORK_DIR), 'r') as f:
                encrypted_str = f.read()
            decrypted_str = Stats._decrypt(encrypted_str)    # Decodes string
            #print('>>>>'+decrypted_str)
            reconst_dict = json.loads(decrypted_str)     # Reconstructs original DICT

            if isinstance(reconst_dict, dict):
                return reconst_dict

        except IOError:
            print('No user file.\n')

    def admin(func, on=False):
        if on:
            return func
        else:
            return AttributeError

    @admin    # passing User instance to decorator
    def set_user(self, token, access):
        rights_dict = self.__rights
        rights_dict.update({token:access})
        if len(rights_dict) > 0:
            with open('{}/user'.format(WORK_DIR), 'w+') as f:        
                data_to_write = unicode(json.dumps(rights_dict))
                f.write( Stats._encrypt(data_to_write) )

    @admin
    def show_users(self):
        print(self.__rights)

    def _gen_token(self):
        return Stats._encrypt('{}:{}'.format(self.user, self.__pwd))

    def _get_access(self):
        token = self._gen_token()
        if token in self.__rights:
            return self.__rights[token]

# DECORATOR for Stats class
def user_stats(cls, access):
    '''
    Decorator for users version of Stats

    '''
    NOT_USER_ATTRS = {'refresh','_gen_stats','_get_tweets', '_decrypt'}
    NOT_GUEST_ATTRS = {'refresh', '_gen_stats','_get_tweets', '_decrypt', 
                        '_encrypt', 'get', 'load', 'save'}
    #print(access)

    
    class UserStats(cls):

        def __init__(self, *args, **kwargs):

            def error():
                raise AttributeError

            if access == 'admin':
                super(UserStats, self).__init__(*args, **kwargs)
                self.authorised = True


            elif access == 'user':
                super(UserStats, self).__init__(args[0])
                # Delete methods/attrs that are not for USER interface
                for attr in NOT_USER_ATTRS:
                    setattr(self, attr, error)
                self.authorised = True

            else:   # guest user or None user
                super(UserStats, self).__init__(args[0])
                # Delete methods/attrs that are not for USER interface
                for attr in NOT_GUEST_ATTRS:
                    setattr(self, attr, error)
                self.authorised = False

    return UserStats


class Stats(object):
    '''
    name = word from query
    time = period to get as much tweets as it can.
    _get_tweets - method (generator) - authenticates to Twitter get tweets without
        duplicates.
    _gen_stats - calculate statistics METHODs
    statistic ATTRIBUTES
    encrypt()/decrypt() method
    save to file method
    read from file METHOD
    @decorator for class to give diff user rights (UserStats() - wrapper)
    '''

    def __init__(self, word, time_interval=30, tweet_language='en'):
        self.word = word

        self.tweets_count = 0

        self.time_interval = time_interval
        self.lang = tweet_language
        self._stats = {    'uniques': Counter(), 'letters_per_word': Counter(),
                        'origin': Counter(), 'global_retweets':0, 
                        'global_length':0, 'global_words_count':1, 
                        'global_sentences':0 }

    @property
    def uniques(self):
        return self._stats['uniques']

    @property
    def letters_per_word(self):
        return self._stats['letters_per_word']

    @property
    def origin(self):
        '''
        Where are tweets from (time zone)
        '''
        return self._stats['origin']

    def get(self):
        '''
        Load tweets from file if it exists or run .refresh() method otherwise
        '''
        path = '{}/stats/{}.data'.format(WORK_DIR, self.word) 
        if not os.path.isfile(path):    # Check if FILE exist
            self.refresh()
        else:
            self.load()

    def refresh(self):
        '''
        Get new Tweets and generate new stats for current word. 
        Saves this to file.
        '''
        self._gen_stats(self._get_tweets())
        self.save()

    def view(self, print_dicts=0):
        '''
        Prints statistics in legible way
        '''
        print('Statistics by word: {}'.format(self.word.upper()) )
        get_key = lambda x: x[1]    # Second element of tuple as sort key

        for key ,value in sorted(self._stats.items()):
            if isinstance(value, dict):
                if print_dicts:
                    print(u'\n[{key}]:\n'.format(key=key))

                    for key2, value2 in sorted(value.items(), reverse=True, key=get_key):
                        print(u'{key}: {value}'.format(key=key2, value=value2))
            elif isinstance(value, list):
                print(u'\n[{}]:\n\n'
                        '{}'.format(key, ' '.join(value)))
            else:
                if isinstance(value, float):
                    print(u'\n[{key}]: {value:.2f}'.format(key=key, value=value))
                else:
                    print(u'\n[{key}]: {value}'.format(key=key, value=value))

    def load(self):
        '''
        Loads data from file and decrypts it.
        '''
        try:
            with open('{}/stats/{}.data'.format(WORK_DIR, self.word), 'r') as f:
                encrypted_str = f.read()
            #print(encrypted_str)
            decrypted_str = Stats._decrypt(encrypted_str)    # Decodes string
            #print('>>>>'+decrypted_str)
            reconst_dict = json.loads(decrypted_str)     # Reconstructs original DICT

            if isinstance(reconst_dict, dict):
                self._stats.update(reconst_dict)

        except IOError:
            print('No such file.\nCreating new statistics.\n')
            self.refresh()


    def save(self):
        '''
        Encrypts data and saves it to file
        '''
        path = '{}/stats/'.format(WORK_DIR)
        if not os.path.exists(path):    # Create FOLDER if not exist
            os.makedirs(path)

        with open('{}{}.data'.format(path, self.word), 'w+') as f:
            data_to_write = unicode(json.dumps(self._stats))
            f.write( Stats._encrypt(data_to_write) )
        #    f.writelines( b64encode(str(self._stats)) )
    
    def _gen_stats(self, tweet_gen):
        '''
        Generate stats from the GENERATOR by query

            Length: 102 characters
            Length witout white-space: 85 characters
            Words: 18
            Sentences: 1
            Unique words: 17
            Unique words(%): 94%
            Length of shortest word: 2 characters
            Length of longest word: 9 characters
            Avg. word length: 4.72
            Avg. words per sentence: 18  
        '''
        BIAS = 20    # Max word len bias

        stats = self._stats

        for tweet in tweet_gen:

            words = self.extract_words( tweet[u'text'].lower() )
            # Unique words
            stats['uniques'].update( Counter(words) )
            # words count by length (letters per word)
            stats['letters_per_word'].update( Counter([len(word) for word in words]) )
            # time zones - origin of tweet
            stats['origin'].update( Counter({tweet[u'user'][u'time_zone']:1}) )
            # Global sum of all retweets
            stats['global_retweets'] += int(tweet[u'retweet_count'])
            # Global tweets length
            stats['global_length']    +=  len(tweet)    
            # Global words count
            stats['global_words_count'] += len(words)
            # Global sentences count
            stats['global_sentences'] += tweet[u'text'].count('.')

        start_time = time.time()
        # Avoiding DIVISION by ZERO
        if self.tweets_count <= 0:
            self.tweets_count = 1
        # Remove too big words
        stats['letters_per_word'] = \
            {k:v for k,v in stats['letters_per_word'].items() if k < BIAS}
        # avg retweets per tweet
        stats['avg_retweets'] = stats['global_retweets'] / self.tweets_count
        # avg length (chars per tweet)
        stats['avg_length'] = stats['global_length'] / self.tweets_count
        # avg words per tweet
        stats['avg_words_count'] = stats['global_words_count'] / self.tweets_count
        # avg sentences per tweet
        stats['avg_sentences'] = stats['global_sentences'] / self.tweets_count
        # unique words count
        stats['unique_words_count'] = len(stats['uniques'].keys())
        # unique words count % of all words
        stats['unique_words_count_per'] = \
            stats['unique_words_count'] / stats['global_words_count']
        #stats['avg_word_len'] = IMPLEMENT (like: 4.56 letters per word)

        stats['avg_words_per_sentence'] = stats['avg_words_count'] /\
            stats['avg_sentences']

        get_key = lambda x: stats['uniques'][x]
        stats['unique_30_most'] = sorted(stats['uniques'].keys(), reverse=True, \
                key=get_key)[0:30]
        print('stats generated in {:.5f} seconds\n'.format(time.time() - start_time))

    def _get_tweets(self):
        '''
        word - word to seek for 
        time - time interval
        '''
        # Create query
        HTTP_METHOD='GET'
        POST_BODY=''
        HTTP_HEADERS=None
        TWEETS_TO_GET = 100
        RESULT_TYPE = 'mixed' #'recent'
        IDLE = 6    #seconds (< 180 requests in 15 mins window)
        ERROR_CODES = { '400':'Bad Request',
                        '401':'Unauthorized',
                        '403':'Forbidden',
                        '410':'Gone',
                        '429':'Too Many Requests',
                        '504':'Gateway timeout'
                        }

        query = (
            'https://api.twitter.com/1.1/search/tweets.json?'
            'q={}&count={}&result_type={}&lang={}'
            ''.format(self.word, TWEETS_TO_GET, RESULT_TYPE, self.lang) 
            )

        consumer = oauth2.Consumer(key=CONSUMER_KEY, secret=CONSUMER_SECRET)
        token = oauth2.Token(key=ACCESS_TOKEN, secret=ACCESS_TOKEN_SECRET)

        client = oauth2.Client(consumer, token)

        # Get as much tweets as possible during the time_interval
        start_time = time.time()
        tweet_id = set()
        self.tweets_count = 0

        while (time.time() - start_time) <= self.time_interval:
            resp, content = client.request( \
                query, method=HTTP_METHOD, body=POST_BODY,    headers=HTTP_HEADERS )

            print( '{}:\nserver answer: {}'.format( \
                time.ctime().split(' ')[3], resp['status']) )
            print('{} sec. remaining.'.format(round( \
                self.time_interval-(time.time() - start_time), 2)) )

            response = json.loads(content)

            if resp['status'] == '200':
                if 'statuses' in response.keys():
                    for tweet in response['statuses']:
                        if not tweet['id'] in tweet_id:    # Excludes DUPLICATES
                            tweet_id.add(tweet['id'])
                            yield tweet
                            self.tweets_count += 1
                    print('{} unique tweets downloaded.'.format(self.tweets_count))
                    self._idle(IDLE)
                elif (resp['status'] == '429')and(self.time_interval > 910):
                    self._idle(900)    # 15 minutes
            else :
                print('Twitte API Error: [{code}]:{descr}'.format( \
                    code=resp['status'], descr=ERROR_CODES[resp['status']]))
                break

    @staticmethod
    def _encrypt(s, code=5):
        '''
        Encrypts s string with base64 alg + Caesar cipher.
        '''
        def c_encode(c, code):
            # Ceasar encode for single CHR
            return chr( (((ord(c)-48) + code) % 75) + 48)

        result = b64encode(s)
 
        return ''.join([c_encode(c, code) for c in result])

    @staticmethod
    def _decrypt(s, code=5):
        '''
        Decryption. Opposite to Encryption :)
        '''
        def c_decode(c, code):
            # Ceasar decode for single CHR
            return chr( (((ord(c)-48) - code) % 75) + 48)

        result = ''.join([c_decode(c, code) for c in s])

        return b64decode(result)

    @staticmethod
    def extract_words(s):
        '''
        Split string by white_space and Strips all the punctuation marks.
        TODO:
        Use word Stemming to generalize stats (requires external module).
        '''
        #EXCLUDE_SET - imported from exclude.py
        EXCLUDE_CHR = '1234567890!%^&*$()_+=-[]{}|,:;\'\"?'
        # Excludes CHR's, 'http' from 
        result = filter( lambda x: not x.count('http'),\
            map( lambda x: x.strip(EXCLUDE_CHR), s.split(' ') ))

        return [word for word in result if not word in EXCLUDE_SET]

    @staticmethod
    def _idle(interval=10):
        left = 1
        while left <= interval:
            time.sleep(1)
            stdout.write('\rpause: {} seconds left...'.format(interval-left))
            stdout.flush()
            left += 1
        print('\n')


print('### Twitter statistics ###\n')

### LOGIN ###
login = raw_input('login: ')
pwd = raw_input('password: ')

UserStats = User(login, pwd)
#UserStats = User('chip','12345')

# Initial instance
word = raw_input('keyword: ')
if word == '':
    stats = UserStats('test')
else:
    stats = UserStats(word)

if stats.authorised:
    print('\nWelcome, {}!'.format(UserStats.user))
else:
    print('\n### Limited access. ###\n' 
          'Logged in as \'guest\'.')
############

### USER INTERFACE ###
while True:
    command = raw_input('\n({}) >>> '.format(stats.word.upper()))

    if command == 'new':
        word = raw_input('  keyword: ')
        print('Keyword changed to {}:'.format(word))
        stats = UserStats(word)
        stats.get()
        continue
    elif command == 'time':
        time = raw_input('  time interval (sec): ')
        stats.time_interval = int(time)
        continue

    elif command == 'exit':
        sys.exit()

    else:
        if hasattr(stats, command):
            try:
                getattr(stats, command)()
            except AttributeError:
                print('no permission to use this command')
            except TypeError:   # Works in case if the attr is not CALLABLE
                try:
                    print(getattr(stats, command))
                except AttributeError:
                    print('no permission to use get this attribute')
        else:
            print('no such command')
####################

#print(getattr(UserStats, 'set_user'))
#stats.set_user(Stats._encrypt('user:pass'),'user')
#stats.get()
#stats.view()


#UserStats.show_users()
#token = Stats._encrypt('user:pass')
#UserStats.set_user(token,'user')
#UserStats.show_users()

#stats = Stats('paris', cur_user, 60)    # GOOD KEY-WORD 'news'

#stats = Stats('test', cur_user, 20)
#stats.refresh()

#stats2 = Stats('words', cur_user, 20)
#stats2.get()
#for item in stats.__dict__:
#    print(item)
#stats2.view(0)

#print(stats.uniques)
#print(stats.letters_per_word)
#print(stats.letters_per_word)

#stats.save()