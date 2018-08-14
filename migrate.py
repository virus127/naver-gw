# -*- coding: utf-8 -*-

import json
import sys


class ServerData:
    def __init__(self, hostname, tag):
        self.hostname = hostname
        self.tags = [tag]


class SimpleEncoder(json.JSONEncoder):
    def default(self, o):
        return o.__dict__


def get_server_data(line):
    hostname, tag = get_hostname_and_tag(line.split())
    return ServerData(hostname, tag)


def get_hostname_and_tag(splitted):
    return splitted[0].strip(), ' '.join(splitted[1:])


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print 'usage : python migrate.py PATH_TO_KNOWN_HOSTS_FILE'
        exit(1)

    server_data_list = []
    with file(sys.argv[1]) as hosts_file:
        for line in hosts_file:
            server_data = get_server_data(line)
            server_data_list.append(server_data)

    json.dump(server_data_list, file('server_config.json', 'w'), cls=SimpleEncoder, indent=4, sort_keys=True)