#!bin/python
# -*- coding: utf-8 -*-
import json

from getpass import getpass
from inspect import getmembers
from inspect import ismethod

from languages import languages
from twitter_stats import *

HELP_LANGUAGES_URL = 'https://api.twitter.com/1.1/help/languages.json'

def login():
    login = raw_input('login: ')
    pwd = getpass('password: ')

    return User(login, pwd)

def execute(instance, command):
    '''
    Execute instance method or print attribute
    '''
    if hasattr(instance, command):
        try:
            getattr(instance, command)()
        except AttributeError:
            print('no permission to use this command')
        except TypeError:   # Works in case if the attr is not CALLABLE
            try:
                print(getattr(instance, command))
            except AttributeError:
                print('no permission to get this attribute')
    else:
        print('no such command')

def show_commands(options_list):
    print('\n'+'*'*60+
          '\nCOMMANDS:\n'
          '|'),
    for item in options_list:
        print('{} |'.format(item)),

def get_lang_list():
    client = Stats.set_client()
    resp, content = \
        client.request(HELP_LANGUAGES_URL)
    if resp['status'] == '200':
        return json.loads(content)
    else:
        return {}

def show_lang(lang_dict, carriage_return=True):
    if carriage_return:
        print('| {:<20} : {:<5} |'.format( \
          lang_dict['name'], lang_dict['code']))
    else:
        print('| {:<20} : {:<5} '.format( \
          lang_dict['name'], lang_dict['code'])),

def show_lang_list(lang_list):
    carr_ret = False

    for item in lang_list:
        show_lang(item, carr_ret)
        carr_ret = not carr_ret


print('### Twitter statistics ###\n')

### LOGIN ###
UserStats = login()

# Create initial instance of Stats
word = raw_input('keyword: ')
if word == '':
    stats = UserStats('test')
else:
    stats = UserStats(word)

# Generate list of commands, languages
languages = get_lang_list()
extra_commands = ['new','time','set_user', 'del_user', 'change_lang']
exclude = ['authorised', 'extract_words', 'tweets_count', 'client', 'set_client']
command_list = [name for name, value in getmembers(stats) if (name[0] != '_') \
                and(name not in exclude)]

# Print WELCOME message, add commad list
if stats.authorised:
    print('\nWelcome, {}!\n'.format(UserStats.user_name))
    command_list.extend(extra_commands)
else:
    print('\n### Limited access. ###\n' 
          'Logged in as \'guest\'.')
    Stats.get(stats)    # Gets stats for GUEST user keyword (only at start)

############

### Command Line INTERFACE ###

while True:
    show_commands(command_list)

    command = raw_input('\n\n({}): '.format(stats.word.upper()))

    # new
    if (command == extra_commands[0])and(stats.authorised):
        word = raw_input('  keyword: ')
        print('keyword changed to: {}'.format(word))
        stats = UserStats(word)
        stats.get()
        continue
    # time
    elif (command == extra_commands[1])and(stats.authorised):
        time = raw_input('  time interval (sec): ')
        stats.time_interval = int(time)
        continue
    # set_user
    elif command == extra_commands[2]:
        execute(UserStats, extra_commands[2])
        continue
    # del_user
    elif command == extra_commands[3]:
        execute(UserStats, extra_commands[3])
        continue
    # lang
    elif command == extra_commands[4]:
        show_lang_list(languages)
        print('current language: {}'.format(stats.lang))
        lang = raw_input('  choose language: ')
        if lang in [d['code'] for d in languages]:
            stats.lang = lang
        else:
            print('wrong code!')
        continue

    elif command == 'exit':
        sys.exit()

    else:
        execute(stats, command)

##################