# -*- coding: utf-8 -*-

import json


class ServerDataEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ServerData):
            d = dict(
                hostname=o.hostname,
                alias=o.alias,
                tag_list=o.tag_list
            )
            return dict((key, value) for (key, value) in d.iteritems() if value is not None)
        return super(ServerDataEncoder, self).default(o)


class ServerData:
    def __init__(self, hostname, alias='', tag_list=()):
        self.hostname = hostname
        self.alias = alias
        self.tag_list = list(tag_list)

    @property
    def name(self):
        if self.alias:
            return self.alias
        return self.hostname

    @property
    def tags(self):
        return u' '.join(self.tag_list)

    def __repr__(self):
        return str(self.__dict__)
