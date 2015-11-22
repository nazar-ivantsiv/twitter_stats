#!bin/python
# -*- coding: utf-8 -*-

from getpass import getpass
from inspect import getmembers
from inspect import ismethod

from twitter_stats import *

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
                print('no permission to use get this attribute')
    else:
        print('no such command')

def show_commands(options_list):
    print('\nchoose command:\n'
          '|'),
    for item in options_list:
        print('{} |'.format(item)),


print('### Twitter statistics ###\n')

### LOGIN ###
UserStats = login()
#UserStats = User('chip','12345')

# Create initial instance of Stats
word = raw_input('keyword: ')
if word == '':
    stats = UserStats('test')
else:
    stats = UserStats(word)

# Generate list of commands
extra_commands = ['new','time','set_user', 'del_user']
exclude = ['authorised', 'extract_words', 'tweets_count']
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

    command = raw_input('\n({}) >>> '.format(stats.word.upper()))

    # new
    if (command == extra_commands[0])and(stats.authorised):
        word = raw_input('  keyword: ')
        print('Keyword changed to {}:'.format(word))
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
    # del_user
    elif command == extra_commands[3]:
        execute(UserStats, extra_commands[3])

    if command == 'exit':
        sys.exit()

    else:
        execute(stats, command)

##################