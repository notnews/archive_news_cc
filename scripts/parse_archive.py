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

parsed_data = dict()
open_tag = ""
text_list = []


def parse_command_line(argv):
    """Command line options parser for the script
    """
    usage = "Usage: %prog [options] <CSV input file>"

    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-o", "--outfile", action="store",
                      type="string", dest="outfile", default="archive-out.csv",
                      help="Output CSV filename (default: 'archive-out.csv')")
    parser.add_option("--meta", action="store",
                      type="string", dest="meta", default=META_DIR,
                      help="Meta files directory (default: '{:s}')".format(META_DIR))
    parser.add_option("--html", action="store",
                      type="string", dest="html", default=HTML_DIR,
                      help="HTML files directory (default: '{:s}')".format(HTML_DIR))
    parser.add_option("-s", "--skip", action="store",
                      type="int", dest="skip", default=0,
                      help="Skip rows (default: 0)")

    return parser.parse_args(argv)


# 3 handler functions
def start_element(name, attrs):
    global open_tag
    #print('Start element:', name, attrs)
    open_tag = name


def end_element(name):
    global open_tag, text_list
    #print('End element:', name)
    if name == open_tag:
        #print(open_tag, "==>", '\n'.join(text_list))
        if open_tag not in parsed_data:
            parsed_data[open_tag] = []
        parsed_data[open_tag].append('\n'.join(text_list))
        text_list = []
        open_tag = ""
    pass


def char_data(data):
    #print('Character data:', repr(data))
    if data.strip() != "":
        text_list.append(data.strip())
    pass

if __name__ == "__main__":

    print("{:s} - {:s}\n".format(os.path.basename(sys.argv[0]), __version__))
    (options, args) = parse_command_line(sys.argv)
    if len(args) < 2:
        print("Usage: {:s} [options] <CSV input file>".format(os.path.basename(sys.argv[0])))
        sys.exit(-1)

    print("Parse all meta files to extract all possible fields, please wait...")
    count = 0
    columns = set()
    f = open(args[1])
    reader = csv.DictReader(f)
    for i, r in enumerate(reader):
        if i < options.skip:
            continue
        count += 1
        _id = r['identifier']
        file_name = os.path.join(options.meta, _id + "_meta.xml")
        if not os.path.isfile(file_name):
            file_name += ".gz"

        parsed_data = dict()

        if os.path.isfile(file_name):
            if file_name.endswith('.gz'):
                fxml = gzip.open(file_name)
            else:
                fxml = open(file_name)
            xmlstr = fxml.read()
            fxml.close()

            p = xml.parsers.expat.ParserCreate()

            p.StartElementHandler = start_element
            p.EndElementHandler = end_element
            p.CharacterDataHandler = char_data
            try:
                p.Parse(xmlstr)
                #for t in parsed_data:
                #    parsed_data[t] = '|'.join(parsed_data[t])
                columns.update(list(parsed_data))
            except:
                print("WARN: Cannot parse {0}".format(file_name))
    f.close()

    print("Total: {:d}, Meta fields count: {:d}".format(count, len(columns)))

    try:
        if os.path.isfile(options.outfile):
            o = open(options.outfile, encoding='utf-8', newline='')
            reader = csv.DictReader(o)
            columns = reader.fieldnames
            o.close()
            o = open(options.outfile, "at", encoding='utf-8', newline='')
            writer = csv.DictWriter(o, fieldnames=sorted(list(columns)))
        else:
            o = open(options.outfile, "wt", encoding='utf-8', newline='')
            writer = csv.DictWriter(o, fieldnames=sorted(list(columns)) + ['text'])
            writer.writeheader()
    except:
        if os.path.isfile(options.outfile):
            o = open(options.outfile)
            reader = csv.DictReader(o)
            columns = reader.fieldnames
            o.close()
            o = open(options.outfile, "ab")
            writer = csv.DictWriter(o, fieldnames=sorted(list(columns)))
        else:
            o = open(options.outfile, "wb")
            writer = csv.DictWriter(o, fieldnames=sorted(list(columns)) + ['text'])
            writer.writeheader()

    count = 0
    f = open(args[1])
    reader = csv.DictReader(f)
    for i, r in enumerate(reader):
        if i < options.skip:
            continue
        count += 1
        _id = r['identifier']
        print("#{:d}: {:s}".format(count, _id))

        # Parse meta file to extract meta fields
        file_name = os.path.join(options.meta, _id + "_meta.xml")
        if not os.path.isfile(file_name):
            file_name += ".gz"

        parsed_data = dict()

        if os.path.isfile(file_name):
            if file_name.endswith('.gz'):
                fxml = gzip.open(file_name)
            else:
                fxml = open(file_name)
            xmlstr = fxml.read()
            fxml.close()

            p = xml.parsers.expat.ParserCreate()

            p.StartElementHandler = start_element
            p.EndElementHandler = end_element
            p.CharacterDataHandler = char_data
            try:
                p.Parse(xmlstr)
                for t in parsed_data:
                    parsed_data[t] = '|'.join(parsed_data[t]).encode('utf-8')
            except:
                print("WARN: Cannot parse '{0}'".format(file_name))
                continue

            # Parse HTML file for closed-caption
            file_name = os.path.join(options.html, _id + ".html")
            if not os.path.isfile(file_name):
                file_name += ".gz"

            if os.path.isfile(file_name):
                if file_name.endswith('.gz'):
                    fhtml = gzip.open(file_name, 'rb')
                else:
                    fhtml = open(file_name, 'rb')
                htmlstr = fhtml.read()
                fhtml.close()

                soup = BeautifulSoup(htmlstr, 'html.parser')
                htmlstr = soup.prettify()
                soup = BeautifulSoup(htmlstr, 'html.parser')
                text = ""
                for a in soup.find_all('div', {'class': 'snipin nosel'}):
                    text += a.text.strip()

                parsed_data['text'] = text.encode('utf-8')
                writer.writerow(parsed_data)

    f.close()
    o.close()
