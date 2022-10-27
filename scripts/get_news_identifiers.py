#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import requests
import logging 

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(message)s',
                    handlers=[logging.FileHandler("logs/get_new_identifiers.log"),
                              logging.StreamHandler()])

def validate_date(date):
    # Simple date validation
    try:
        d = date.split('-')
        assert int(d[0]) > 0
        assert 13 > int(d[1]) > 0
        assert 32 > int(d[2]) > 0
    except Exception as e:
        raise Exception("Invalid date")
        

if __name__ == "__main__":
    desc = 'Get TV archive identifiers from Archive.org'
    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument('-n', dest='count', default=1500000,
                        help='Limit number of identifiers (default: 1,500,000)')
    parser.add_argument('-o', '--output', default='search.csv',
                        help='Output file name')
    parser.add_argument('-sd', dest='start_date', default='',
                        help='Starting date filter in YYYY-MM-DD format')

    args = parser.parse_args()
    
    logging.info("Search and download TV archive identifiers, please wait...")

    # Initial query
    query = 'collection:"tvarchive"'

    # Add starting date
    if args.start_date:
        validate_date(args.start_date)
        query += f" AND date:[{args.start_date} TO null]"

    params = {
        'q': query,
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
        logging.info("Done")
    else:
        logging.error("status_code={0:d}".format(r.status_code))
