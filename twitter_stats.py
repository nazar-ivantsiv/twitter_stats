# -*- coding: utf-8 -*-
from __future__ import division

'''
Twitter statistics module.

Author:
Nazar Ivantsiv
'''

import os
import json
import time
import sys

from base64 import b64encode
from base64 import b64decode
from collections import Counter
from getpass import getpass

import oauth2

from auth_info import *
# File auth_info.py has to be in the same dir. Content:
#CONSUMER_KEY = <key>
#CONSUMER_SECRET = <secret>
#ACCESS_TOKEN = <token>
#ACCESS_TOKEN_SECRET = <token secret>

from exclude import EXCLUDE_SET
from languages import languages

WORK_DIR = os.getcwd()

# DECORATOR for Admin Tools
def only_for_admin(func):
    '''
    DECORATOR: Admin tools extender.
    Wrapper is used only to reach functions argument 'self'
    '''
    def wrapper(self, *args, **kwargs):
        if self.access == 'admin':
            return func(self, *args, **kwargs)
        else:
            return AttributeError
    return wrapper


class User(object):
    '''
    User's profile.
    It also applies DECORATOR user_stats to Stats on creation to change its 
    behavior according to users TOKEN (rights).
    '''

    def __init__(self, user, pwd):

        # Privat attributes
        self._token = self._gen_token(user, pwd)

        # Protected attributes
        self.__def_rights = ['admin', 'user']   # Default access options
        self.__access = self._get_access()      # Get current user access

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
    def user_name(self):
        return Stats._decrypt(self._token).split(':')[0]
    

    @property
    def __rights(self):
        '''
        Returns dict of token:user_rights ({'user_token':'admin'})
        '''
        try:
            with open('{}/user'.format(WORK_DIR), 'r') as f:
                encrypted_str = f.read()
            decrypted_str = Stats._decrypt(encrypted_str)    # Decodes string
            reconst_dict = json.loads(decrypted_str)     # Reconstructs original DICT

            if isinstance(reconst_dict, dict):
                return reconst_dict

        except IOError:
            print('No user file.\n')
            return ''

    def _get_access(self):
        if self._token in self.__rights:
            return self.__rights[self._token]

    @only_for_admin
    def set_user(self):
        self.show_users()

        user_name = raw_input('user name: ')
        user_pwd = getpass('user password: ')
        token = self._gen_token(user_name, user_pwd)
        access = self.choose(self.__def_rights)
        print('new user credentials: {}:{}'.format(token, access))

        rights_dict = self.__rights
        rights_dict.update({token:access})
        if len(rights_dict) > 0:
            with open('{}/user'.format(WORK_DIR), 'w+') as f:        
                data_to_write = json.dumps(rights_dict)
                f.write( Stats._encrypt(data_to_write) )

    @only_for_admin
    def del_user(self):
        name_lst, pwd_lst = self.show_users()
        rights_dict = self.__rights
        try:
            user_name = raw_input('user name: ')
            if user_name in name_lst:                
                user_token = self._gen_token( \
                    user_name, pwd_lst[ name_lst.index(user_name) ] )
                if user_token in rights_dict:
                    rights_dict.pop(user_token)            
                else:
                    raise KeyError
        except KeyError:
            print('no such user')
        else:
            print(self.__rights)
            with open('{}/user'.format(WORK_DIR), 'w+') as f:        
                data_to_write = json.dumps(rights_dict)
                f.write( Stats._encrypt(data_to_write) )           


    @only_for_admin
    def show_users(self):
        '''
        Prints username : password : access
        And returns names and passwords lists
        '''
        name_lst = []
        pwd_lst = []
        print('existing users:\n'
              'ACCESS : NAME : PASSWORD')
        for token, access in self.__rights.items():
            name = Stats._decrypt(token).split(':')[0]
            name_lst.append(name)
            pwd = Stats._decrypt(token).split(':')[1]
            pwd_lst.append(pwd)
            print('{} : {} : {}'.format(access, name, pwd))
        return name_lst, pwd_lst

    @staticmethod
    def _gen_token(user_name, user_pwd):
        return Stats._encrypt('{}:{}'.format(user_name, user_pwd))

    @staticmethod
    def choose(options_list):
        while True:
            for tup_item in enumerate(options_list):
                print('{}: {}'.format(*tup_item))
            try:
                print('choose from options above')
                answer = int(raw_input('    answer: '))
                if answer in range(len(options_list)):
                    return options_list[answer]
            except TypeError:
                continue

# DECORATOR for Stats class
def user_stats(cls, access):
    '''
    Decorator for users version of Stats

    '''
    # User can NOT save stats
    NOT_USER_ATTRS = {'refresh', 'save'}
    # Guest can do almost nothing, only view =)
    NOT_GUEST_ATTRS = {'refresh', '_decrypt', '_encrypt', 'get', 'save'}

    
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
    Tweets statistics routines

    word - word for query
    time - period to get as much tweets as it can.
    tweet_language - language of tweets
    '''

    def __init__(self, word, time_interval=30, tweet_language='en'):
        self.word = word

        self.tweets_count = 0
        # Create Twitter API client instance
        self.client = self.set_client()

        self.time_interval = time_interval
        self.lang = tweet_language
        self._stats = { 'uniques': Counter(), 'letters_per_word': Counter(),
                        'origin': Counter(), 'global_retweets':0, 
                        'global_length':0, 'global_words_count':1, 
                        'global_sentences':0, 'unique_30_most':[] }

    @property
    def sentence(self):
        '''
        Generates human readable sentence of 30 words (generalization of tweets)
        '''
        return ' '.join(self._stats['unique_30_most'])

    @property
    def uniques(self):
        '''
        Property to make class interface user friendly
        '''
        return self._stats['uniques']

    @property
    def letters_per_word(self):
        '''
        Property to make class interface user friendly
        '''
        return self._stats['letters_per_word']

    @property
    def origin(self):
        '''
        Where are tweets from (time zone)
        '''
        return self._stats['origin']

    def get(self):
        '''
        Load tweets from file if it exists or runs get NEW stats otherwise. 
        DIDN'T SAVE THE RESULTS! (self.save() - required)
        '''
        path = '{}/stats/{}.data'.format(WORK_DIR, self.word) 
        if not os.path.isfile(path):    # Check if FILE exist
            self._gen_stats(self._get_tweets())
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
        print_dicts - enables printing of large dictionaries
        '''
        print('Statistics by word: {}'.format(self.word.upper()) )
        get_key = lambda x: x[1]    # Second element of tuple as sort key

        for key ,value in sorted(self._stats.items()):
            if isinstance(value, dict):
                if print_dicts:
                    print(u'\n[{key}]:\n'.format(key=key))

                    for key2, value2 in sorted(value.items(), \
                                               reverse=True, key=get_key):
                        if value2 > 1:
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
            decrypted_str = Stats._decrypt(encrypted_str)    # Decodes string
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
            data_to_write = json.dumps(self._stats)
            f.write( Stats._encrypt(data_to_write) )
    
    def _gen_stats(self, tweet_gen):
        '''
        Generate stats from the GENERATOR by query

        tweet_gen - generator or iterable of tweets 
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
        if self.tweets_count == 1:
            stats['avg_sentences'] = 1
        stats['avg_words_per_sentence'] = stats['avg_words_count'] /\
            stats['avg_sentences']

        get_key = lambda x: stats['uniques'][x]
        stats['unique_30_most'] = sorted(stats['uniques'].keys(), reverse=True, \
                key=get_key)[0:30]
        print('stats generated in {:.5f} seconds\n'.format(time.time() - start_time))

    def _get_tweets(self):
        '''
        Get tweets from Twitter REST API
        '''
        # Create query
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

        # Get as much tweets as possible during the time_interval
        start_time = time.time()
        tweet_id = set()
        self.tweets_count = 0

        while (time.time() - start_time) <= self.time_interval:

            resp, content = self.client.request(query)

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
    def set_client(key=CONSUMER_KEY, secret=CONSUMER_SECRET, \
                   acc_key=ACCESS_TOKEN, acc_secret=ACCESS_TOKEN_SECRET):
        '''
        Creates Twitter API Client as self.client
        '''
        consumer = oauth2.Consumer(key=key, secret=secret)
        token = oauth2.Token(key=acc_key, secret=acc_secret)

        return oauth2.Client(consumer, token)

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
        '''
        Advenced sleep func, with status printed.
        '''
        left = 1
        while left <= interval:
            time.sleep(1)
            sys.stdout.write('\rpause: {} seconds left...'.format(interval-left))
            sys.stdout.flush()
            left += 1
        print('\n')