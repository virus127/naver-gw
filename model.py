# -*- coding: utf-8 -*-


class ServerData:
    def __init__(self, hostname, alias=None, tags=()):
        self.hostname = hostname
        self.alias = alias
        self.tag_list = tags.split() if type(tags) == str else tags

    @property
    def name(self):
        if self.alias:
            return self.alias
        return self.hostname

    @property
    def tags(self):
        return u', '.join(self.tag_list)

    def __repr__(self):
        return str(self.__dict__)
