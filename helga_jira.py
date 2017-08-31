import random
import re

import requests
import smokesignal

from requests.auth import HTTPBasicAuth
from twisted.internet import reactor

from helga import log, settings
from helga.db import db
from helga.plugins import command, match, ACKS, ResponseNotReady
from helga.util.encodings import to_unicode


logger = log.getLogger(__name__)


# These are initialized on client signon
JIRA_PATTERNS = set()


@smokesignal.on('signon')
def init_jira_patterns(*args, **kwargs):
    """
    Signal callback for IRC signon. This pulls down and caches all the stored
    JIRA ticket patterns so we don't have to do it on every message received
    """
    global JIRA_PATTERNS

    if db is None:  # pragma: no cover
        logger.warning('Cannot initialize JIRA patterns. No database connection')
        return

    JIRA_PATTERNS = set(item['re'] for item in db.jira.find() if 're' in item)


def find_jira_numbers(message):
    """
    Finds all jira ticket numbers in a message. This will ignore any that already
    appear in a URL
    """
    global JIRA_PATTERNS

    if not JIRA_PATTERNS:
        return []

    ticket_patterns = r'({0})-[\d]+'.format('|'.join(JIRA_PATTERNS))

    # Remove URLs
    message = re.sub(r'https?://.*?{0}'.format(ticket_patterns), '', message)

    # Find blacklisted items
    blacklist = set(item['blacklist'] for item in db.jira.find() if 'blacklist' in item)
    for x in blacklist:
        message = message.replace(x, '')

    # Get the tickets, but don't be too greedy. Only allow preceeding spaces or commas
    pat = r'(^|[\s,])({0})'.format(ticket_patterns)
    tickets = [m[1] for m in re.findall(pat, message, re.IGNORECASE)]

    return tickets


def add_re(pattern):
    """
    Adds a ticket pattern from the database and local cache
    """
    global JIRA_PATTERNS

    if pattern not in JIRA_PATTERNS:
        logger.info('Adding new JIRA ticket RE: %s', pattern)
        JIRA_PATTERNS.add(pattern)
        re_doc = {'re': pattern}

        # Store in DB
        if not db.jira.find(re_doc).count():
            db.jira.insert(re_doc)
    else:  # pragma: no cover
        logger.info('JIRA ticket RE already exists: %s', pattern)

    return random.choice(ACKS)


def remove_re(pattern):
    """
    Removes a ticket pattern from the database and local cache
    """
    global JIRA_PATTERNS

    logger.info('Removing JIRA ticket RE: %s', pattern)
    JIRA_PATTERNS.discard(pattern)
    db.jira.remove({'re': pattern})

    return random.choice(ACKS)


def add_blacklist(pattern):
    logger.info('Blacklisting string %s', pattern)
    doc = {'blacklist': pattern}

    # Store in DB
    if not db.jira.find(doc).count():
        db.jira.insert(doc)

    return random.choice(ACKS)


def remove_blacklist(pattern):
    logger.info('Removing blacklist string %s', pattern)
    db.jira.remove({'blacklist': pattern})
    return random.choice(ACKS)


def show_blacklist():
    str = ['Current blacklisted strings:']

    for item in db.jira.find():
        logger.info('Checking %s', item)
        if 'blacklist' not in item:
            continue
        str.append('"{}"'.format(item['blacklist']))

    return ' '.join(str)


def jira_command(client, channel, nick, message, cmd, args):
    """
    Command handler for the jira plugin
    """
    try:
        subcmd, pattern = args[:2]
    except ValueError:
        if args[0] == 'show_blacklist':
            return show_blacklist()
        else:
            return None

    if subcmd == 'add_re':
        return add_re(pattern)

    if subcmd == 'remove_re':
        return remove_re(pattern)

    if subcmd == 'add_blacklist':
        return add_blacklist(pattern)

    if subcmd == 'remove_blacklist':
        return remove_blacklist(pattern)

    return None


def _rest_desc(ticket, url, auth=None):
    api_url = to_unicode(getattr(settings, 'JIRA_REST_API', 'http://localhost/api/{ticket}'))
    resp = requests.get(api_url.format(ticket=ticket), auth=auth)

    try:
        resp.raise_for_status()
    except:
        logger.error('Error getting JIRA ticket %s. Status %s', ticket, resp.status_code)
        return

    try:
        return u'[{0}] {1} ({2})'.format(ticket.upper(), resp.json()['fields']['summary'], url)
    except:
        return u'[{0}] {1}'.format(ticket.upper(), url)


def jira_full_descriptions(client, channel, urls):
    """
    Meant to be run asynchronously because it uses the network
    """
    try:
        descriptions = []
        user_pass = getattr(settings, 'JIRA_AUTH', ('', ''))

        if all(user_pass):
            auth = HTTPBasicAuth(*user_pass)
        else:
            auth = None

        for ticket, url in urls.iteritems():
            desc = _rest_desc(ticket, url, auth)
            if desc is not None:
                descriptions.append(desc)

        if descriptions:
            client.msg(channel, '\n'.join(descriptions))
    except Exception:
        logger.exception('OOOOPS')


def jira_match(client, channel, nick, message, matches):
    jira_url = to_unicode(getattr(settings, 'JIRA_URL', 'http://localhost/{ticket}'))
    full_urls = dict((s, jira_url.format(ticket=s)) for s in matches)

    if not getattr(settings, 'JIRA_SHOW_FULL_DESCRIPTION', True):
        return u'{0} might be talking about JIRA ticket: {1}'.format(nick, ', '.join(full_urls.values()))

    # Otherwise, do the fetching with a deferred
    reactor.callLater(0, jira_full_descriptions, client, channel, full_urls)
    raise ResponseNotReady


@match(find_jira_numbers)
@command('jira', help="Add or remove jira ticket patterns, excludeing numbers."
                      "Usage: helga jira (add_re|remove_re|add_blacklist|remove_blacklist|show_blacklist) <pattern>")  # noqa
def jira(client, channel, nick, message, *args):
    """
    A plugin for showing URLs to JIRA ticket numbers. This is both a command to add or remove
    patterns, and a match to automatically show them. The match requires a setting JIRA_URL
    which must contain a ``{ticket}`` substring. For example, ``http://localhost/{ticket}``.

    The command takes a pattern as an argument, minus any numbers. For example, if there are JIRA
    tickets like FOOBAR-1, FOOBAR-2, and FOOBAR-3. Then you could manage the pattern via::

        helga jira add_re FOOBAR
        helga jira remove_re FOOBAR

    Ticket numbers are automatically detected.
    """
    if len(args) == 2:
        fn = jira_command
    else:
        fn = jira_match
    return fn(client, channel, nick, message, *args)
