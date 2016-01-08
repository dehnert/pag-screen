#!/usr/bin/env python
from __future__ import unicode_literals, print_function

import argparse
import datetime
import os
import re
import socket
import subprocess
import sys
import time
import traceback

def parse_args():
    parser = argparse.ArgumentParser(description='utilities for long-running screen sessions')

    # Auto-exit
    parser.add_argument('-S', '--title', help="name of screen (screen's -S option)", default=None)
    parser.add_argument('--no-exit', dest='autoexit', action='store_false', help="do not exit when the screen exits", )

    # DIR cache treatment
    parser.add_argument('-a', '--all', '-d', dest='allcaches', action='store_true', help='renew all caches (potentially multiple realms) in a DIR kerberos ccache', default=None)
    parser.add_argument('-1', '--one', '-f', dest='allcaches', action='store_false', help='renews only the primary cache')

    # Notifications
    user = os.environ.get('ATHENA_USER', os.environ.get('USER'))
    parser.add_argument('-u', '--user', help='user to send notifications to', default=user)
    parser.add_argument('-c', '--notify-cmd', help='command to use for sending notifications')

    args = parser.parse_args()
    if not args.title:
        args.autoexit = False
    if args.allcaches is None:
        args.allcaches = os.environ.get('KRB5CCNAME', '').startswith('DIR:')
    if not args.notify_cmd:
        args.notify_cmd = os.environ.get('ZEPHYR_SCREEN_NOTIFY', None)
    if args.notify_cmd:
        print("Note: notify_cmd will be passed through the shell")
    return args

def find_pid(title):
    cmd = ['screen', '-ls', title]
    env = {'LC_ALL':'C'}
    regex = re.compile("There is a screen on:\r?\n\t(?P<pid>\d+)[.]%s\t" % (title, ))
    count = 10
    while count > 0:
        proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, universal_newlines=True)
        out, err = proc.communicate()
        match = regex.match(out)
        if match:
            return int(match.group('pid'))
        count = count-1
        time.sleep(1)
    return None

expire_re = re.compile(r'^\trenew until (?P<date>\d\d/\d\d/\d{2,4} \d\d:\d\d)(:\d\d)?$', re.MULTILINE)
principal_re = re.compile('^Default principal: (?P<princ>.+)$', re.MULTILINE)

class ContRenewNotify(object):
    def __init__(self, screen_pid, args):
        self.screen_pid = screen_pid
        self.notify_user = args.user
        self.notify_cmd = args.notify_cmd
        self.issues = {}

    def notify(self, message):
        message = message.encode('utf8')
        if self.notify_cmd:
            print("    Sending custom notification...")
            proc = subprocess.Popen(self.notify_cmd, shell=True, stdin=subprocess.PIPE)
            proc.communicate(message)
            if proc.returncode != 0:
                print("      Failed send notification")
        else:
            print("    Sending default notification...")
            cmd = ['zwrite', '-n', self.notify_user]
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            proc.communicate(message)
            if proc.returncode != 0:
                print("      Failed send authenticated notification -- resending with without auth")
                cmd = cmd + ['-d']
                proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
                proc.communicate(message)
                if proc.returncode != 0:
                    print("      Failed send unauthenticated notification")
        print("      Sent")


    def renew_cache(self, name):
        print("\n  Renewing cache " + name)
        host = socket.gethostname()

        now = datetime.datetime.now()
        expire = None
        message = "Unknown issue with %s on %s" % (name, host) 

        try:
            subprocess.check_call(['kinit', '-R', '-c', name])
            renewed = True
        except subprocess.CalledProcessError as e:
            print("    Failed to renew tickets in %s on %s" % (name, host))
            renewed = False
            message = "Your tickets in %s on %s could not be renewed" % (name, host)

        try:
            env = {'LC_ALL':'C', 'LC_TIME':'C'}
            out = subprocess.check_output(['klist', '-c', name], env=env, universal_newlines=True)
            expire_match = expire_re.search(out)
            principal_match = principal_re.search(out)
            if principal_match:
                principal = principal_match.group('princ')
                if expire_match:
                    expire_str = expire_match.group('date')
                    expire_time = datetime.datetime.strptime(expire_str, '%m/%d/%y %H:%M')
                    if (expire_time - now) < datetime.timedelta(hours=24):
                        expire = expire_time
                        if expire_time < now:
                            days = (now - expire_time).days
                            message = "Your tickets for %s on %s expired %d days ago." % (principal, host, days)
                        else:
                            message = "Your tickets for %s on %s will expire within the next 24 hours.\nRun \"kinit -l7d\" to get new renewable tickets." % (principal, host)
                    elif renewed:
                        message = None
                else:
                    message= "You do not have renewable tickets for %s on %s.\nRun \"kinit -l7d\" to get renewable tickets." % (principal, host)
            else:
                message = "Could not parse principal from klist for %s on %s" % (name, host)
        except subprocess.CalledProcessError as e:
            message = "Failed to check tickets for %s on %s" % (name, host)

        if name not in self.issues:
            self.issues[name] = None, None
        old_expire, old_message = self.issues[name]
        if message is not None:
            print("    %s: %s" % (name, message))
            if old_expire!=expire or old_message!=message:
                self.notify(message)
        self.issues[name] = expire, message

def main():
    args = parse_args()
    print(args)

    if args.autoexit:
        screen_pid = find_pid(args.title)
    else:
        screen_pid = None
    print("Found PID %s" % (screen_pid, ))
    renewer = ContRenewNotify(screen_pid, args)
    # Sleep 7 seconds to finish startup?

    while True:
        print("Renewing tickets at %s" % (datetime.datetime.now(), ))

        proc = subprocess.Popen(['klist', '-l'], universal_newlines=True, stdout=subprocess.PIPE)
        out, err = proc.communicate()
        print(out)
        lines = out.strip().split('\n')
        for line in lines[2:]:
            parts = line.split()
            renewer.renew_cache(parts[1])
            print(renewer.issues)
        print("Done\n\n")
        #time.sleep(3600)
        time.sleep(60)

if __name__ == '__main__':
    main()
