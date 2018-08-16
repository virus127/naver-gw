# -*- coding: utf-8 -*-

import argparse
import json
import logging
import os

import log
from helper import load_module
from model import ServerData

urwid = load_module(u'urwid')
trie = load_module(u'pygtrie')


log.setup_logger()


# 'class name', 'color', 'background-color'
palette = [
    (u'title', urwid.BLACK, urwid.WHITE),
    (u'background', urwid.WHITE, urwid.BLACK),

    (u'focus', urwid.YELLOW, urwid.BLACK, u'standout'),

    (u'text.important', urwid.WHITE, urwid.BLACK, u'standout'),

    (u'server_list.item', urwid.WHITE, urwid.BLACK),
    (u'server_list.item focus', urwid.LIGHT_BLUE, urwid.BLACK),
]

main_loop = urwid.MainLoop(None, palette, handle_mouse=False)


class GWKitApplication:
    logger = logging.getLogger(u'gwkit.GWKitApplication')

    def __init__(self, server_config, username_config, test_mode, keyword='', *args, **kwargs):
        self._username_index = 0
        self._server_index = self._parse_server_config(server_config)
        self._username_list = self._parse_username_config(username_config)
        self._test_mode = test_mode
        self._username = ''
        self._keyword = keyword

        self.rotate_username()


    def initialize(self):
        self._kinit()

    def get_server_data_list(self):
        if self._keyword:
            generator = self._server_index.itervalues(prefix=self.keyword_upper)
        else:
            generator = self._server_index.itervalues()

        try:
            return sorted(set(s for s in generator), key=lambda s: s.name)
        except KeyError:
            return []

    @property
    def username(self):
        return self._username

    @property
    def keyword(self):
        return self._keyword

    @property
    def keyword_upper(self):
        return self._keyword.upper()

    def rlogin(self, hostname):
        command = u'rlogin -l {0} {1}'.format(self.username, hostname)
        self._do_command(u'clear')
        self._do_command(command)

    def append_keyword(self, key):
        self._keyword = self._keyword + key

    def clear_keyword(self):
        self._keyword = ''

    def delete_keyword(self):
        self._keyword = self._keyword[0:-1]

    def rotate_username(self):
        self._username = self._username_list[self._username_index]
        self._username_index = (self._username_index + 1) % len(self._username_list)

    def _kinit(self):
        command = u'kinit'
        self._do_command(command)

    def _do_command(self, command):
        self.logger.debug(u'do command - {0}'.format(command))
        if not self._test_mode:
            os.system(command)
        main_loop.screen.clear()

    def _parse_server_config(self, server_config):
        self.logger.debug(u'try loading server config from {0}'.format(server_config))
        server_data_list = [ServerData(**data) for data in json.load(file(server_config))]
        self.logger.debug(u'parsed server list - {0}'.format(server_data_list))
        return self._create_server_index(server_data_list)

    def _create_server_index(self, server_list):
        """creates trie of uppercased hostname, tags, and alias"""

        index = trie.CharTrie()
        for server in server_list:
            index[server.hostname.upper()] = server
            if server.alias:
                index[server.alias.upper()] = server
            for tag in server.tag_list:
                index[tag.upper()] = server
        return index

    def _parse_username_config(self, username_config):
        self.logger.debug(u'try loading username config from {0}'.format(username_config))
        username_list = json.load(file(username_config))
        self.logger.debug(u'parsed username list - {0}'.format(username_list))
        return username_list


class StatusBar(urwid.WidgetWrap):
    def __init__(self, username='', keyword=''):
        self.username_edit = urwid.Edit(u'Username : ', edit_text=username)
        self.keyword_edit = urwid.Edit(u'Keyword : ', edit_text=keyword)
        column_widgets = [self.username_edit, self.keyword_edit]
        status_columns = urwid.Columns(column_widgets)
        container = urwid.LineBox(status_columns, u'Status', title_align=urwid.LEFT)

        urwid.WidgetWrap.__init__(self, container)

    def connect_signals(self, gwkit):
        urwid.connect_signal(gwkit, u'username_change', self._update_username)
        urwid.connect_signal(gwkit, u'keyword_change', self._update_keyword)

    def _update_username(self, widget, username):
        self.username_edit.set_edit_text(username)

    def _update_keyword(self, widget, keyword):
        self.keyword_edit.set_edit_text(keyword)


class ServerListItem(urwid.WidgetWrap):
    logger = logging.getLogger(u'gwkit.ServerListItem')

    CHECK_MARK_TEXT = '\xE2\x9C\x94'

    def __init__(self, server_data):
        self._server_data = server_data
        self._selected = False

        self._checkbox_text = urwid.Text('')
        self._hostname_text = urwid.AttrWrap(urwid.Text(self._server_data.name, wrap=u'clip'), u'server_list.item',
                                             u'server_list.item focus')
        hostname_wrap = urwid.Padding(self._hostname_text, left=1, right=1)
        tags_text = urwid.Text(self._server_data.tags)
        columns = [
            (3, urwid.Padding(self._checkbox_text, left=1, right=1)),
            (24, hostname_wrap),
            tags_text,
        ]

        columns = urwid.Columns(columns, focus_column=1)
        urwid.WidgetWrap.__init__(self, columns)

    def selectable(self):
        return True

    def keypress(self, size, key):
        if key == u'enter':
            gw_app.rlogin(self._server_data.hostname)
        elif key == u' ':
            self.logger.debug(u'selecting host - {0}'.format(self._server_data.hostname))
            self._toggle_selected()
        else:
            return key

    def unselected(self):
        self._selected = False
        self._update_checkbox()

    def _toggle_selected(self):
        self._selected = not self._selected
        self._update_checkbox()

    def _update_checkbox(self):
        if self._selected:
            self._checkbox_text.set_text(self.CHECK_MARK_TEXT)
        else:
            self._checkbox_text.set_text('')


class ServerListBox(urwid.WidgetWrap):
    def __init__(self):
        self._list_box = urwid.ListBox(urwid.SimpleFocusListWalker([]))
        container = urwid.LineBox(self._list_box, u'Server List')
        urwid.WidgetWrap.__init__(self, container)

        self._update_list()

    def connect_signals(self, gwkit):
        urwid.connect_signal(gwkit, u'keyword_change', self._update_list)

    def _update_list(self, widget=None, keyword=None):
        server_list_items = [ServerListItem(s) for s in gw_app.get_server_data_list()]
        self._list_box.body = urwid.SimpleFocusListWalker(server_list_items)

    def keypress(self, size, key):
        if key == u'ctrl l':
            self._unselect_all()
        return super(ServerListBox, self).keypress(size, key)

    def _unselect_all(self):
        for widget in self._list_box.body:
            widget.unselected()


class GWKit(urwid.Frame):
    logger = logging.getLogger(u'gwkit.GWKit')

    signals = [u'keyword_change', u'username_change']

    def __init__(self, *args, **kwargs):
        title_bar = urwid.AttrMap(urwid.Padding(urwid.Text(u'GWKit', align=urwid.CENTER)), u'title')
        self.status_bar = StatusBar(gw_app.username, gw_app.keyword)
        self.server_list_box = ServerListBox()

        self.status_bar.connect_signals(self)
        self.server_list_box.connect_signals(self)

        super(GWKit, self).__init__(self.server_list_box, urwid.Pile([title_bar, self.status_bar]))

    def keypress(self, size, key):
        self.logger.debug(u'key pressed - key={0}'.format(key))

        if key == u'backspace':
            gw_app.delete_keyword()
            self._emit(u'keyword_change', gw_app.keyword)
        elif len(key) == 1 and key.isalnum():
            gw_app.append_keyword(key)
            self._emit(u'keyword_change', gw_app.keyword)
        elif key == u'ctrl k':
            gw_app.clear_keyword()
            self._emit(u'keyword_change', gw_app.keyword)
        elif key == u'ctrl _':
            gw_app.rotate_username()
            self._emit(u'username_change', gw_app.username)
        else:
            return super(GWKit, self).keypress(size, key)


if __name__ == '__main__':
    logger = logging.getLogger(u'gwkit')

    parser = argparse.ArgumentParser(description=u'GWKit')
    parser.add_argument(u'-s', metavar=u'SERVER_CONFIG_PATH', type=str, help=u'path to server list config file',
                        default=u'server_config.json', dest=u'server_config')
    parser.add_argument(u'-u', metavar=u'USERNAME_CONFIG_PATH', type=str, help=u'path to username list config file',
                        default=u'username_config.json', dest=u'username_config')
    parser.add_argument(u'-t', help=u'enable test mode', action=u'store_true', dest=u'test_mode')
    parsed_args = vars(parser.parse_args())

    logger.debug(u'parsed arguments = {0}'.format(parsed_args))

    try:
        urwid.set_encoding(u'UTF-8')
        gw_app = GWKitApplication(**parsed_args)
        gw_app.initialize()
        gw_kit = GWKit(**parsed_args)
        main_loop = urwid.MainLoop(gw_kit, palette, handle_mouse=False)
        main_loop.run()

    except KeyboardInterrupt, err:
        pass
