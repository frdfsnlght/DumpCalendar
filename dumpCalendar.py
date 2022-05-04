#!/usr/bin/python3

# see https://developers.google.com/identity/protocols/oauth2/limited-input-device
# see https://google-auth-oauthlib.readthedocs.io/en/latest/reference/google_auth_oauthlib.html

# Obtaining Google API credentials:
#
# 1. goto https://console.developers.google.com/apis/dashboard
# 2. create a new project if necessary, or use an existing one
# 3. click 'Credentials' on left menu
# 4. click '+ CREATE CREDENTIALS', choose 'OAuth client ID'
# 5. choose 'TVs and Limited Input devices' and enter a client name
# 6. copy the resulting Client ID and Secret, you'll need them when this script runs for the first time

# Preparing python:
#
# pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
# pip install python-dateutil

import sys, os.path, pickle, argparse, dateutil.parser, time, datetime
from google_auth_oauthlib import get_user_credentials
from googleapiclient.discovery import build

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

GAPI_CREDENTIALS_FILE = os.path.join(SCRIPT_DIR, 'credentials.pickle')
GAPI_TOKEN_FILE = os.path.join(SCRIPT_DIR, 'token.pickle')
GAPI_SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def gapiLogin():
    
    needToken = False
    
    if os.path.exists(GAPI_CREDENTIALS_FILE):
        with open(GAPI_CREDENTIALS_FILE, 'rb') as credsFile:
            creds = pickle.load(credsFile)
    else:
        print()
        print('No client credentials found. Please enter the following information.')
        clientId = input('Client Id: ')
        clientSecret = input('Client secret: ')
        creds = {'clientId': clientId, 'clientSecret': clientSecret}
        with open(GAPI_CREDENTIALS_FILE, 'wb') as credsFile:
            pickle.dump(creds, credsFile)
        print('Client credentials saved.')
        needToken = True
    
    if not needToken and os.path.exists(GAPI_TOKEN_FILE):
        with open(GAPI_TOKEN_FILE, 'rb') as tokenFile:
            token = pickle.load(tokenFile)
        if not token or not token.valid or token.expired:
            needToken = True
    else:
        needToken = True
        
    if needToken:
        print()
        print('Authentication required.')
        token = get_user_credentials(GAPI_SCOPES, creds['clientId'], creds['clientSecret'])
        if not token or not token.valid:
            print('Authentication failed.')
            sys.exit(1)
        with open(GAPI_TOKEN_FILE, 'wb') as tokenFile:
            pickle.dump(token, tokenFile)
        print('Authentication token saved.')
        
    service = build('calendar', 'v3', credentials = token)
    return service


def noCommand(args):
    print('no command was given')
    
def getCalendars(args):
    calendar = gapiLogin()
    
    result = calendar.calendarList().list().execute()
    cals = result['items']
    for cal in cals:
        #print(cal)
        print('{} ({})'.format(cal['summaryOverride'] if 'summaryOverride' in cal else cal['summary'], cal['id']))
    
def getEvents(args):
    calendar = gapiLogin()

    timeMin = datetime.datetime(args.year, 1, 1)
    timeMax = datetime.datetime(args.year, 12, 31, 23, 59, 59)

    result = calendar.calendarList().list().execute()
    cals = result['items']
    calId = None
    for cal in cals:
        if args.calendarName == cal['summary'] or args.calendarName == cal['id'] or ('summaryOverride' in cal and args.calendarName == cal['summaryOverride']):
            calId = cal['id']
            break
    if not calId:
        print('Unknown calendar')
        sys.exit(1)

    events = []
    pageToken = None
    while True:
        eventsResult = calendar.events().list(
            calendarId = calId,
            timeMin = timeMin.isoformat() + 'Z',
            timeMax = timeMax.isoformat() + 'Z',
            singleEvents = True,
            orderBy = 'startTime',
            timeZone = 'America/New_York',
            pageToken = pageToken
        ).execute()
        events.extend(eventsResult.get('items', []))
        pageToken = eventsResult.get('nextPageToken')
        if not pageToken:
            break

    month = 1
    print('{}\t{}\t{}\t{}'.format('Start', 'End', 'Diff', 'Summary'))
    for event in events:
        if 'summary' not in event or 'dateTime' not in event['start'] or 'dateTime' not in event['end']: continue
        #print(json.dumps(event, indent = 4))
        #dt = datetime.strptime(event['start']['dateTime'], 'format)
        #dt = datetime.fromisoformat(event['start']['dateTime'])
        start = dateutil.parser.isoparse(event['start']['dateTime'])
        end = dateutil.parser.isoparse(event['end']['dateTime'])
        diff = end - start
        hours, seconds = divmod(diff.seconds, 3600)
        minutes = int(seconds / 60)
        if month != start.month:
            month = start.month
            print()
        print('{}\t{}\t{}:{:02d}\t{}'.format(start.strftime('%m/%d/%Y %H:%M:%S'), end.strftime('%m/%d/%Y %H:%M:%S'), hours, minutes, event['summary']))



if __name__ == '__main__':

    parser = argparse.ArgumentParser(description = 'Dump Google calendar entries to TSV')
    parser.set_defaults(func = noCommand)
    
    subparsers = parser.add_subparsers()
    
    parser_calendars = subparsers.add_parser('calendars', aliases=['c'], help='show available calendars')
    parser_calendars.set_defaults(func = getCalendars)
    parser_events = subparsers.add_parser('events', aliases = ['e'], help='extract calendar events')
    parser_events.add_argument('calendarName', type = str, help = 'the calendar name')
    parser_events.add_argument('year', type = int, nargs = '?', default = datetime.date.today().year, help = 'the year to extract, or the current year if not specified')
    parser_events.set_defaults(func = getEvents)

    args = parser.parse_args()
    args.func(args)
    
