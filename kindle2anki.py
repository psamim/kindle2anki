#!/usr/bin/env python


import card_creator
import sys
import argparse
import csv
import os
import re
import sqlite3
import datetime
import retrying
import service
import urllib
import urllib.parse
import urllib.request
import logging
import pyperclip
from colorama import init, Fore, Back, Style
init()

TIMESTAMP_PATH = os.path.expanduser('~/.kindle')


def get_lookups(db, timestamp=0):
    conn = sqlite3.connect(db)
    res = []
    sql = """
    SELECT w.stem,l.usage, w.timestamp
    FROM `WORDS` as w
    LEFT JOIN `LOOKUPS` as l
    ON w.id=l.word_key where w.timestamp>""" + str(timestamp) + """;
    """
    for row in conn.execute(sql):
        res.append(row)
    conn.close()
    return res


def get_lookups_from_file(filename, last_timestamp=0, max_length=30):
    TITLE_LINE = 0
    CLIPPING_INFO = 1
    CLIPPING_TEXT = 3
    MOD = 5
    words = []

    infile = open(filename, 'r')
    for line_num, x in enumerate(infile):
        # trim \r\n from line
        x = re.sub('[\r\n]', '', x)
        # trim hex bytes at start if they're there
        if x[:3] == '\xef\xbb\xbf':
            x = x[3:]

        # if we're at a title line and it doesn't match the last title
        if line_num % MOD == TITLE_LINE:
            title = x
        elif line_num % MOD == CLIPPING_INFO:
            # include metadata (location, time etc.) if desired
            date = re.findall(
                r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec).*\d\s(?:AM|PM)',
                x)
            timestamp = datetime.datetime.strptime(
                date[0], "%B %d, %Y %I:%M:%S %p").timestamp() * 1000
            logging.debug("timestamp: " + str(timestamp))

        elif line_num % MOD == CLIPPING_TEXT:
            # Skip trying to write if we have no body
            if x == '':
                continue

            if ((last_timestamp == 0 or timestamp > last_timestamp) and
                    len(x) < max_length):
                x = re.sub(',', '', x)
                words.append([x, '', timestamp])

    return words


def get_last_timestamp_from_lookup(db):
    conn = sqlite3.connect(db)
    res = conn.execute(
        'select timestamp from WORDS order by timestamp desc limit 1;').fetchall(
    )
    conn.close()
    last_timestamp = res[0][0] if len(res) > 0 else None
    logging.debug("last timestamp from lookup: " + str(last_timestamp))
    return last_timestamp


def get_last_timestamp():
    try:
        with open(TIMESTAMP_PATH, 'r') as tfile:
            last_timestamp = int(float(tfile.readline().strip()))
            logging.debug("last timestamp from file: " + str(last_timestamp))
            return last_timestamp
    except Exception as e:
        logging.debug(e)
        return 0


def update_last_timestamp(timestamp):
    logging.debug("update timestamp: " + str(timestamp))
    with open(TIMESTAMP_PATH, 'w') as tfile:
        tfile.write('{}'.format(timestamp))


def translate(lingualeo, word):
    result = lingualeo.get_translates(word)

    sound_url = result['sound_url']
    pic_url = result['translate'][0]['pic_url']
    # tr = result['translate'][0]['value']
    tr = [i['value'] for i in result['translate']][:3]
    # remove duplicates
    tr = '<br>'.join(list(set(tr)))
    transcription = result['transcription']

    return (tr, transcription, sound_url, pic_url)


def extract_filename_from_url(url):
    path = urllib.parse.urlparse(url).path
    return os.path.split(path)[-1]


@retrying.retry(stop_max_attempt_number=3)
def download_file(url, path=''):
    res = urllib.request.urlretrieve(url, os.path.join(
        path, extract_filename_from_url(url)))
    return res


def write_to_csv(file, data):
    with open(file, 'w', newline='') as csvfile:
        spamwriter = csv.writer(
            csvfile,
            delimiter='\t',
            dialect='unix',
            quotechar='|',
            quoting=csv.QUOTE_MINIMAL)
        for row in data:
            spamwriter.writerow(row)


def highlight_word_in_context(word, context):
    return re.sub(r'{}'.format(word),
                  '<span class=highlight>{}</span>'.format(word), context)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--vocab-db', help='Path to Kindle vocab DB file (usually vocab.db on Kindle). Provide this either this or --clippings')
    parser.add_argument(
        '--clippings', help='Path to clippings (usually "documents/My Clippings.txt" on Kindle)')
    parser.add_argument('--deck', help='Anki deck name')
    parser.add_argument(
        '-o',
        '--out',
        help='CSV output filename to import into Anki, if not provided words are added to Anki using anki-connect')
    parser.add_argument(
        '-m',
        '--media-path',
        help='Where to store media files (sounds/images) from Lingualeo')
    parser.add_argument('--email', help='LinguaLeo account email/login')
    parser.add_argument(
        '--update-timestamp',
        help='Update local timestamp to now and exit',
        default=False,
        action="store_true")
    parser.add_argument('--pwd', help='LinguaLeo account password')
    parser.add_argument(
        '--max-length',
        help='Maximum length of words from clippings, to avoid importing big sentences',
        default=30)
    parser.add_argument(
        '--verbose',
        help='Show debug messages',
        default=False,
        action="store_true")
    parser.add_argument(
        '--no-ask',
        help='Do not ask for card back in the command line',
        default=False,
        action="store_true")
    parser.add_argument(
        '--clipboard',
        help='Copy each word to clipboard',
        default=False,
        action="store_true")

    args = parser.parse_args()

    if (args.verbose):
        logging.getLogger().setLevel(logging.DEBUG)

    if (args.update_timestamp):
        update_last_timestamp(datetime.datetime.now().timestamp() * 1000)
        sys.exit(0)

    media_path = args.media_path if args.media_path else ''
    timestamp = get_last_timestamp()

    lingualeo = False
    if (args.email and args.pwd):
        lingualeo = service.Lingualeo(email, password)
        res = lingualeo.auth()

    if args.vocab_db:
        lookups = get_lookups(args.vocab_db, timestamp)
    elif args.clippings:
        lookups = get_lookups_from_file(
            args.clippings, timestamp, args.max_length)
    else:
        logging.error("No input specified")
        sys.exit(1)

    card = card_creator.CardCreator(args.deck)

    data = []
    prev_timestamp = 0
    for i, (word, context, timestamp) in enumerate(lookups):
        progress = int(100.0 * i / len(lookups))
        to_print = ('' + Style.DIM + '[{}%]' + Style.RESET_ALL + '\t \n'
                    '' + Fore.GREEN + 'Word: ' + Style.RESET_ALL + '{} \n'
                    '' + Fore.GREEN + 'Context:' + Style.RESET_ALL + ' {} \n')
        print(to_print.format(progress, word, context), end='', flush=True)

        if args.clipboard:
            pyperclip.copy(word)

        if lingualeo:
            tr, transcription, sound_url, img_url = translate(lingualeo, word)
            if sound_url:
                print('ok, get sound...', end='', flush=True)
                try:
                    sound, _ = download_file(sound_url, media_path)
                    sound = os.path.basename(sound)
                except:
                    sound = ''
            if img_url:
                print('ok, get image...', end='', flush=True)
                try:
                    img, _ = download_file(img_url, media_path)
                    img = os.path.basename(img)
                except:
                    img = ''
            print('ok!')

        else:
            desc = ''
            if not args.no_ask:
                print(Style.BRIGHT + "Enter card back:" + Style.RESET_ALL +
                      Style.DIM + '[q/s]' + Style.RESET_ALL)
                desc = input()
                if desc == 'q':
                    if prev_timestamp != 0:
                        update_last_timestamp(prev_timestamp)

                    if args.out:
                        print(
                            '[100%]\tWrite to file {}...'.format(args.out),
                            end='',
                            flush=True)
                        write_to_csv(args.out, data)

                    sys.exit(0)

                if desc == 's':
                    print(
                        Style.DIM + "===============================================================================" + Style.RESET_ALL)
                    prev_timestamp = timestamp
                    continue

        if not context:
            context = ''
        # remove all kinds of quotes/backticks as Anki sometimes has troubles
        # with them
        context = re.sub(r'[\'"`]', '', context)
        context = highlight_word_in_context(word, context)

        if args.out:
            if lingualeo:
                data.append((word, transcription, '[sound:{}]'.format(sound), tr,
                            img, highlight_word_in_context(word, context)))
            else:
                data.append((word, desc + "<br /><br />" +
                             highlight_word_in_context(word, context)))
        else:
            try:
                card.create(word, desc + "<br /><br />" +
                            highlight_word_in_context(word, context))
            except sqlite3.OperationalError as e:
                print(Fore.RED + "Error: " + Style.RESET_ALL +
                      "Is Anki open? Database is locked.")
                if prev_timestamp != 0:
                    update_last_timestamp(prev_timestamp)
                sys.exit(1)

        print(Style.DIM + "===============================================================================" + Style.RESET_ALL)
        prev_timestamp = timestamp

    if len(lookups):
        if args.out:
            print(
                '[100%]\tWrite to file {}...'.format(args.out),
                end='',
                flush=True)
            write_to_csv(args.out, data)

    update_last_timestamp(datetime.datetime.now().timestamp() * 1000)
    sys.exit(0)
