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

	def __init__(self, word, User, time_interval=60):
		self.word = word
		self.user = User
		self.time_interval = time_interval
		self.lang = DEFAULT_TWEET_LANG
		self._stats = {	'uniques': Counter(), 'letters_per_word': Counter(),
						'origin': Counter(), 'global_retweets':0, 
						'global_length':0, 'global_length_wws':0, 
						'global_words_count':1, 'global_sentences':0}

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

	def get(self):
		'''
		Load tweets from file if it exists or run .refresh() method otherwise
		'''
		path = '{}/stats/{}.data'.format(WORK_DIR, self.word) 
		if not os.path.isfile(path):	# Check if FILE exist
			self.refresh()
		else:
			self.load()

	def refresh(self):
		'''
		Get new Tweets and generate new stats for current word
		'''
		self._gen_stats(T_list)
		#self._gen_stats(self._get_tweets())
		#self.save()

	def view(self, print_dicts=1):
		'''
		Prints statistics in legible way
		'''
		for key ,value in sorted(self._stats.items()):
			if isinstance(value, dict):
				if print_dicts:
					print(u'\n[{key}]:\n'.format(key=key))

					for key2, value2 in sorted(value.items()):
						print(u'{key}: {value}'.format(key=key2, value=value2))
			else:
				print(u'\n[{key}]: {value}'.format(key=key, value=value))

	def load(self):
		'''
		Loads data from file and decripts it.
		'''
		try:
			with open('{}/stats/{}.data'.format(WORK_DIR, self.word), 'r') as f:
				encrypted_str = f.read()
			#print(encrypted_str)
			decrypted_str = Stats._decrypt(encrypted_str)	# Decodes string
			#print('>>>>'+decrypted_str)
			reconst_dict = json.loads(decrypted_str) 	# Reconstructs original DICT

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
		if not os.path.exists(path):	# Create FOLDER if not exist
			os.makedirs(path)

		with open('{}{}.data'.format(path, self.word), 'w+') as f:
			data_to_write = unicode(json.dumps(self._stats))
			f.write( Stats._encrypt(data_to_write) )
		#	f.writelines( b64encode(str(self._stats)) )
	
	def _gen_stats(self, tweet_lst):
		'''
		Generate stats from the data (lst of dicts) by query

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

			total length
			w/o white-spaces - len(''.join(words))
			len(words)
			self-standing count('.') - sentences count
			total words
			unique words
			length of words
			total words / sentences
		'''
		EXCLUDE_SET = {'', 'http'}
		BIAS = 20	# Max word len bias


		def extract_words(s):
			'''
			Split string by white_space and Strips all the punctuation marks.
			TODO:
			Use Stemming. To generalize stats (requires external module).


			'''
			result = filter(lambda x: x != '', map(\
				lambda x: x.strip('!%^&*()_+=-[]{}.,:;\'\"?'), s.split(' ')) )
			return filter(lambda x: not x.count('http') ,result)


		stats = self._stats

		for tweet in tweet_lst:

			words = extract_words( tweet[u'text'].lower() )

			stats['uniques'].update( Counter(words) )

			stats['letters_per_word'].update( Counter([len(word) for word in words]) )

			stats['origin'].update( Counter({tweet[u'user'][u'time_zone']:1}) )

			stats['global_retweets'] += int(tweet[u'retweet_count'])

			stats['global_length']	+=  len(tweet)

			stats['global_length_wws']	+= 	len(''.join(words))	

			stats['global_words_count'] += len(words)

			stats['global_sentences'] += tweet[u'text'].count('. ')

		tweets_count = len(tweet_lst)
		# Remove too big words
		stats['letters_per_word'] = \
			{k:v for k,v in stats['letters_per_word'].items() if k < BIAS}

		stats['avg_retweets'] = stats['global_retweets'] / tweets_count

		stats['avg_lenght'] = stats['global_length'] / tweets_count

		stats['avg_lenght_wws'] = stats['global_length_wws'] / tweets_count

		stats['avg_words_count'] = stats['global_words_count'] / tweets_count

		stats['avg_sentences'] = stats['global_sentences'] / tweets_count

		stats['unique_words_count'] = len(stats['uniques'].keys())

		stats['unique_words_count_per'] = \
			len(stats['uniques']) / stats['global_words_count']
		stats['shortest_word'] = \
			stats['letters_per_word'].get( min(stats['letters_per_word'].keys()),0)
		stats['longest_word'] = \
			stats['letters_per_word'].get( max(stats['letters_per_word'].keys()),0)
		stats['avg_word_len'] = sum(stats['letters_per_word'].keys()) /\
			sum(stats['letters_per_word'].values())
		stats['avg_words_per_sentence'] = stats['avg_sentences'] /\
			stats['avg_words_count']

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
		IDLE = 20	#seconds
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
		tweet_id = set()

		while (time.time() - start_time) <= self.time_interval:
			#print(round(time.time() - start_time, 2))
			resp, content = client.request( query, method=HTTP_METHOD, body=POST_BODY,	headers=HTTP_HEADERS )

			print( '\n{}: server code {}'.format(time.ctime().split(' ')[3], resp['status']) )


			response = json.loads(content)

			if resp['status'] == '200':
				if 'statuses' in response.keys():
					#print(response['statuses'])
					for tweet in response['statuses']:
						if not tweet['id'] in tweet_id:	# Excludes DUPLICATES
							tweet_id.add(tweet['id'])
							tweet_lst.append(tweet)
					print('{} unique tweets downloaded.'.format(len(tweet_lst)))
					time.sleep(IDLE)
				elif (resp['status'] == '429')and(self.time_interval > 910):
					time.sleep(900)	# 15 minutes
			else :
				print('Twitte API Error: [{code}]:{descr}'.format(code=resp['status'], descr=ERROR_CODES[resp['status']]))
				break

		# ADD Remove duplicates

		# Save list of tweets to file (for TEST mode)

		#with open(os.path.join(WORK_DIR, self.word+'_.py'), 'w+') as f:
		#	f.writelines('T_list=')
		#	print>> f, tweet_lst

		return tweet_lst

	@staticmethod
	def _encrypt(s):
		result = b64encode(s)
		return result

	@staticmethod
	def _decrypt(s):
		result = b64decode(s)
		return result



cur_user = User('admin')

#stats = Stats('Dubai', cur_user, 2)

#stats = Stats('soccer', cur_user, 60)

stats = Stats('test', cur_user, 60)

stats.refresh()

#stats.get()

stats.view(0)

#print(stats.uniques)
#print(stats.letters_per_word)
#print(stats.letters_per_word)

#stats.save()