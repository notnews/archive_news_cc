#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import optparse
import csv

import gzip
import time
import xml.parsers.expat

import requests

from bs4 import BeautifulSoup

META_DIR = './meta/'
HTML_DIR = './html/'

__version__ = 'r4 (2017/11/28)'


def parse_command_line(argv):
    """Command line options parser for the script
    """
    usage = "Usage: %prog [options] <CSV input file>"

    parser = optparse.OptionParser(usage=usage)
    parser.add_option("--meta", action="store",
                      type="string", dest="meta", default=META_DIR,
                      help="Meta files directory (default: '{:s}')".format(META_DIR))
    parser.add_option("--html", action="store",
                      type="string", dest="html", default=HTML_DIR,
                      help="HTML files directory (default: '{:s}')".format(HTML_DIR))
    parser.add_option("-s", "--skip", action="store",
                      type="int", dest="skip", default=0,
                      help="Skip rows (default: 0)")
    parser.add_option("-c", "--compress", action="store_true",
                      dest="compress", default=False,
                      help="Compress downloaded files (default: No)")

    return parser.parse_args(argv)


def download_file(options, url, local_filename):
    # NOTE the stream=True parameter
    print("Downloading...[{:s}]".format(url))
    r = requests.get(url, stream=True)
    if options.compress:
        f = gzip.open(local_filename, 'wb')
    else:
        f = open(local_filename, 'wb')
    for chunk in r.iter_content(chunk_size=1024):
        if chunk:  # filter out keep-alive new chunks
            f.write(chunk)
            f.flush()
    f.close()


if __name__ == "__main__":

    print("{:s} - {:s}\n".format(os.path.basename(sys.argv[0]), __version__))
    (options, args) = parse_command_line(sys.argv)
    if len(args) < 2:
        print("Usage: {:s} [options] <CSV input file>".format(os.path.basename(sys.argv[0])))
        sys.exit(-1)

    if not os.path.exists(options.meta):
        os.mkdir(options.meta)

    if not os.path.exists(options.html):
        os.mkdir(options.html)

    count = 0
    f = open(args[1])
    reader = csv.DictReader(f)
    for i, r in enumerate(reader):
        if i < options.skip:
            continue
        count += 1
        _id = r['identifier']
        print('#{:d}: {:s}'.format(count, _id))
        file_name = os.path.join(options.meta, _id + "_meta.xml")
        if options.compress:
            file_name += ".gz"
        if not os.path.isfile(file_name):
            try:
                rq = requests.get('http://archive.org/download/' + _id)
                if rq.status_code == 200:
                    #print(rq.url)
                    if not rq.url.endswith('/'):
                        rq.url = rq.url + '/'
                    download_file(options, rq.url + _id + "_meta.xml", file_name)
            except Exception as e:
                print("WARN: {!s}".format(e))
                time.sleep(60)
        url = 'http://archive.org/details/' + _id
        file_name = os.path.join(options.html, _id + ".html")
        if options.compress:
            file_name += ".gz"
        if not os.path.isfile(file_name):
            download_file(options, url, file_name)

    f.close()

    print("Total: {0:d}".format(count))
