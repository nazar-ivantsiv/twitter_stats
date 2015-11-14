#! /usr/bin/env python
# -*- coding: utf-8 -*-

'''
Twitter statistics


'''
import os
import json
import time
from collections import Counter

import oauth2

from auth_info import *
# File auth_info.py has to be in the same dir. Content:
#CONSUMER_KEY = <key>
#CONSUMER_SECRET = <secret>
#ACCESS_TOKEN = <token>
#ACCESS_TOKEN_SECRET = <token secret>
from T_list import T_list
from T_list2 import T_list2

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

		#self.gen_stats(T_list)	# DUMMY DATA!!!

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
		'''
		pass

	def save(self):
		'''
		Encripts data and saves it to file
		'''
		pass

	
	def _gen_stats(self, lst):
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

		for tweet in lst:
			words = extract_words(tweet[u'text'])
			stats['uniques'].update( Counter(words) )

			stats['letters_per_word'].update( Counter([len(word) for word in words]) )

			stats['origin'].update( Counter({tweet[u'user'][u'location']:1}) )

			stats['global_retweets'] += int(tweet[u'retweet_count'])

			stats['global_friends'] += int(tweet[u'user'][u'friends_count'])

			stats['global_followers'] += int(tweet[u'user'][u'followers_count'])

			# Add some more sophisticated stats...

		Stats.save_list(lst, self.word+'.py')

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
		RESULT_TYPE = 'recent' #'mixed'
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

		# Get as much tweets as possible in time_interval
		start_time = time.time()
		Tweet_lst = []

		while (time.time() - start_time) <= self.time_interval:
			print(time.time() - start_time)
			resp, content = client.request( query, method=HTTP_METHOD, body=POST_BODY,	headers=HTTP_HEADERS )

			response = json.loads(content)
			print(resp['status'])
			if resp['status'] == '200':
				if 'statuses' in response.keys():
					#print(response['statuses'])
					Tweet_lst.extend(response['statuses'])
				else:
					time.sleep(IDLE)
			else :
				print('Twitte API Error: [{code}]:{descr}'.format(code=resp['status'], descr=ERROR_CODES[resp['status']]))

		return Tweet_lst

	@staticmethod
	def save_list(lst, file_name):
		WORK_DIR = os.getcwd()
		tweets_path = os.path.join(WORK_DIR, file_name)

		with open(tweets_path, 'w+') as f:
			for item in lst:
				f.write(str(item))



cur_user = User('admin')

stats = Stats('word', cur_user, 10)

stats.refresh()

stats.view()