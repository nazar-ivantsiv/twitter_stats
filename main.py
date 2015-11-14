#! /usr/bin/env python
# -*- coding: utf-8 -*-

'''
Twitter statistics


'''
import os
import json
import time

from ast import literal_eval
from base64 import b64encode
from base64 import b64decode
from collections import Counter

import oauth2

from auth_info import *
# File auth_info.py has to be in the same dir. Content:
#CONSUMER_KEY = <key>
#CONSUMER_SECRET = <secret>
#ACCESS_TOKEN = <token>
#ACCESS_TOKEN_SECRET = <token secret>

from test_ import T_list

WORK_DIR = os.getcwd()

ACCESS_RIGHTS = {'user', 'admin'}

TWEET_KEYS = {u'text', u'retweet_count',}
TWEET_USER_KEYS = {u'followers_count', u'friends_count', u'lang', u'location'}

DEFAULT_TWEET_LANG = 'en'

class User(object):
	'''
	Auth info for twiter app and access_rights

	Then we can use this to send request (ex. TwitterClient.request(...))
	and pass this to Stats() to change it behavior accordig to 'access_rights'
	'''
	def __init__(self, access):
		consumer = oauth2.Consumer(key=CONSUMER_KEY, secret=CONSUMER_SECRET)
		token = oauth2.Token(key=ACCESS_TOKEN, secret=ACCESS_TOKEN_SECRET)

		self.client = oauth2.Client(consumer, token)
		# Can we use self = oauth2.Client(consumer, token) ???

		if access in ACCESS_RIGHTS:
			self.user = access


class Stats(object):
	'''
	name = word from query
	time = period to get as much tweets as it can.
	get_tweets method (@statisticmethod) - authenticates to Twitter with TwitterAccount, gets 
	TweetContainer - set() to avoid duplicates
	calculate statistics METHODs (get unit of Tweet class)
	statistic ATTRIBUTES
	encode() method
	save to file method
	read from file METHOD
	@decorator for class to give diff user rights
	'''

	def __init__(self, word, User, time_interval=100):
		self.word = word
		self.user = User
		self.time_interval = time_interval
		self.lang = DEFAULT_TWEET_LANG
		self._stats = {	'uniques':Counter(), 'letters_per_word':Counter(), 
						'origin':Counter(), 'global_retweets':0, 
						'global_friends':0, 'global_followers':0}

	@property
	def uniques(self):
		return self._stats['uniques']

	@property
	def letters_per_word(self):
		return self._stats['letters_per_word']

	@property
	def origin(self):
		'''
		Where are tweets from
		'''
		return self._stats['origin']

	def refresh(self):
		'''
		Get new Tweets and generate new stats for curr word
		'''

		self._gen_stats(self._get_tweets())
		#self._gen_stats(T_list)	# TEST DATA!!!

	def view(self):
		'''
		Prints statistics in legible way
		'''
		for key ,value in self._stats.items():
			if isinstance(value, dict):
				print(u'\n[{key}]:\n'.format(key=key))
				for key2, value2 in sorted(value.items()):
					print(u'{key}: {value}'.format(key=key2, value=value2))
			else:
				print(u'\n[{key}]: {value}'.format(key=key, value=value))

	def load(self):
		'''
		Loads data from file (if it exists) and decripts it.

		def reading(self):
		    with open('deed.txt', 'r') as f:
		        s = f.read()
		        self.whip = ast.literal_eval(s)
		'''
		try:
			with open('{}/stats/{}.data'.format(WORK_DIR, self.word), 'r') as f:
				encoded_str = f.read()

			#decoded_str = b64decode(encoded_str)		# Decodes string
			#print('>>>>'+decoded_str)
			reconst_dict = json.loads(encoded_str) 	# Reconstructs original DICT
			#print(reconst_dict)

			if isinstance(reconst_dict, dict):
				self._stats.update(reconst_dict)

		except IOError:
			print('No such file.\nCreating new statistics.\n')
			self.refresh()


	def save(self):
		'''
		Encripts data and saves it to file
		'''
		path = '{}/stats/'.format(WORK_DIR)
		if not os.path.exists(path):
			os.makedirs(path)

		with open('{}{}.data'.format(path, self.word), 'w+') as f:
			f.write(unicode(json.dumps(self._stats)))
		#	f.writelines( b64encode(str(self._stats)) )
	
	def _gen_stats(self, tweet_lst):
		'''
		Generate stats from the data by query
		'''
		def extract_words(s):
			'''
			Split string by white_space and Strips all the punctuation marks.

			TODO:
			Use Stemming.
			'''
			result = map(lambda x: x.strip('!%^&*()_+=-[]{}.,:;\'\"?'), s.split(' ') )
			return result

		stats = self._stats

		for tweet in tweet_lst:

			words = extract_words( tweet[u'text'].lower() )
			stats['uniques'].update( Counter(words) )

			stats['letters_per_word'].update( Counter([len(word) for word in words]) )

			stats['origin'].update( Counter({tweet[u'user'][u'location']:1}) )

			stats['global_retweets'] += int(tweet[u'retweet_count'])

			stats['global_friends'] += int(tweet[u'user'][u'friends_count'])

			stats['global_followers'] += int(tweet[u'user'][u'followers_count'])

			# Add some more sophisticated stats...

	def _get_tweets(self):
		'''

		word - word to seek for 
		time - time interval
		'''
		# Create query
		HTTP_METHOD='GET'
		POST_BODY=''
		HTTP_HEADERS=None
		TWEETS_TO_GET = 10
		RESULT_TYPE = 'mixed'#'recent'
		IDLE = 10	#seconds
		ERROR_CODES = {	'400':'Bad Request',
						'401':'Unauthorized',
						'403':'Forbidden',
						'410':'Gone',
						'429':'Too Many Requests',
						'504':'Gateway timeout'
						}

		query = (
			'https://api.twitter.com/1.1/search/tweets.json?'
			'q={}&count={}&result_type={}'
			''.format(self.word, TWEETS_TO_GET, RESULT_TYPE) 
			)	
		if self.lang != '':
			query += '&lang={}'.format(self.lang)
#		if geocode != '':
#			query += '&geocode={}'.format(geocode)

		client = self.user.client

		# Get as much tweets as possible during the time_interval
		start_time = time.time()
		tweet_lst = []

		while (time.time() - start_time) <= self.time_interval:
			print(time.time() - start_time)
			resp, content = client.request( query, method=HTTP_METHOD, body=POST_BODY,	headers=HTTP_HEADERS )

			response = json.loads(content)
			print(resp['status'])
			if resp['status'] == '200':
				if 'statuses' in response.keys():
					#print(response['statuses'])
					tweet_lst.extend(response['statuses'])
				else:
					time.sleep(IDLE)
			else :
				print('Twitte API Error: [{code}]:{descr}'.format(code=resp['status'], descr=ERROR_CODES[resp['status']]))

		# ADD Remove duplicates

		# Save list of tweets to file (for TEST mode)

		#with open(os.path.join(WORK_DIR, self.word+'_.py'), 'w+') as f:
		#	f.writelines('T_list=')
		#	print>> f, tweet_lst

		return tweet_lst

	@staticmethod
	def _encode(s):

		return result
	@staticmethod
	def _decode(s):

		return result



cur_user = User('admin')

stats = Stats('test', cur_user, 32)

stats = Stats('Dubai', cur_user, 2)

stats.refresh()

#stats.load()

stats.view()

stats.save()