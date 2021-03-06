#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import sys

from helper import abs_path
from model import ServerData, ServerDataEncoder


def get_server_data(line):
    hostname, tag = get_hostname_and_tag(line.split())
    return ServerData(hostname, None, tag)


def get_hostname_and_tag(splitted):
    return splitted[0].strip(), splitted[1:]


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print u'usage : python migrate.py PATH_TO_KNOWN_HOSTS_FILE'
        exit(1)

    server_data_list = []
    with file(sys.argv[1]) as hosts_file:
        for line in hosts_file:
            server_data = get_server_data(line)
            server_data_list.append(server_data)

    json.dump(server_data_list, file(abs_path('server_config.json'), 'w'), cls=ServerDataEncoder, indent=4,
              sort_keys=True)