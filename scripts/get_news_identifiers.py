#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import requests


if __name__ == "__main__":
    desc = 'Get TV archive identifiers from Archive.org'
    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument('-n', dest='count', default=1500000,
                        help='Limit number of identifiers (default: 1,500,000)')
    parser.add_argument('-o', '--output', default='search.csv',
                        help='Output file name')

    args = parser.parse_args()
    
    print("Search and download TV archive identifiers, please wait...")

    params = {
        'q': 'collection:"tvarchive"',
        'fl[]': 'identifier',
        'sort[]': '',
        'rows': args.count,
        'page': 1,
        'callback': 'callback',
        'output': 'csv'
    }

    # Streaming, so we can iterate over the response.
    r = requests.get('https://archive.org/advancedsearch.php', params=params, stream=True)

    if r.status_code == 200:
        chunk_size = (64 * 1024)
        with open(args.output, 'wb') as f:
            for data in r.iter_content(chunk_size):
                f.write(data)
        print("Done")
    else:
        print("ERROR: status_code={0:d}".format(r.status_code))
