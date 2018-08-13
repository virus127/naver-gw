# -*- coding: utf-8 -*-

import argparse
import json
import logging
import os

import log

try:
    import urwid
except ImportError:
    import sys

    root_dir = os.path.dirname(os.path.abspath(__file__))
    urwid_dir = os.path.join(root_dir, 'urwid')
    sys.path.append(urwid_dir)
    import urwid


log.setup_logger()

# 'class name', 'color', 'background-color'
palette = [
    ('title', urwid.BLACK, urwid.WHITE),
    ('background', urwid.WHITE, urwid.BLACK),

    ('focus', urwid.YELLOW, urwid.BLACK, 'standout'),

    ('text.important', urwid.WHITE, urwid.BLACK, 'standout'),

    ('server_list.item', urwid.WHITE, urwid.BLACK),
    ('server_list.item focus', urwid.LIGHT_BLUE, urwid.BLACK),
]

main_loop = urwid.MainLoop(None, palette, handle_mouse=False)


class ServerData:
    def __init__(self, hostname, alias=None, tags=()):
        self._hostname = hostname
        self._alias = alias
        self._tags = tags

    @property
    def name(self):
        if self._alias:
            return self._alias
        return self._hostname

    @property
    def hostname(self):
        return self._hostname

    @property
    def tags(self):
        return ', '.join(self._tags)


class GWKitApplication:
    logger = logging.getLogger('gwkit.GWKitApplication')

    def __init__(self, server_config, username_config, test_mode, keyword='', *args, **kwargs):
        self._username_index = 0
        self._server_list = self._parse_server_list(server_config)
        self._username_list = self._parse_username_list(username_config)
        self._test_mode = test_mode
        self._username = ''
        self._keyword = keyword

        self.rotate_username()


    def initialize(self):
        self._kinit()

    def get_server_list(self, keyword=None):
        return self._server_list

    @property
    def username(self):
        return self._username

    @property
    def keyword(self):
        return self._keyword

    def rlogin(self, hostname):
        command = 'rlogin -l {0} {1}'.format(self.username, hostname)
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
        command = 'kinit'
        self._do_command(command)

    def _do_command(self, command):
        self.logger.debug('do command - {0}'.format(command))
        if not self._test_mode:
            os.system(command)
        main_loop.screen.clear()

    def _parse_server_list(self, server_config):
        self.logger.debug('try loading server config from {0}'.format(server_config))
        server_list = json.load(file(server_config))
        self.logger.debug('parsed server list - {0}'.format(server_list))
        return server_list

    def _parse_username_list(self, username_config):
        self.logger.debug('try loading username config from {0}'.format(username_config))
        username_list = json.load(file(username_config))
        self.logger.debug('parsed username list - {0}'.format(username_list))
        return username_list


class StatusBar(urwid.WidgetWrap):
    def __init__(self, username='', keyword=''):
        self.username_edit = urwid.Edit('Username : ', edit_text=username)
        self.keyword_edit = urwid.Edit('Keyword : ', edit_text=keyword)
        column_widgets = [self.username_edit, self.keyword_edit]
        status_columns = urwid.Columns(column_widgets)
        container = urwid.LineBox(status_columns, 'Status', title_align=urwid.LEFT)

        urwid.WidgetWrap.__init__(self, container)

    def connect_signals(self, gwkit):
        urwid.connect_signal(gwkit, 'username_change', self._update_username)
        urwid.connect_signal(gwkit, 'keyword_change', self._update_keyword)

    def _update_username(self, widget, username):
        self.username_edit.set_edit_text(username)

    def _update_keyword(self, widget, keyword):
        self.keyword_edit.set_edit_text(keyword)


class ServerListItem(urwid.WidgetWrap):
    logger = logging.getLogger('gwkit.ServerListItem')

    CHECK_MARK_TEXT = '\xE2\x9C\x94'

    def __init__(self, server_data):
        self._server_data = server_data
        self._selected = False

        self._checkbox_text = urwid.Text('')
        self._hostname_text = urwid.AttrWrap(urwid.Text(self._server_data.name, wrap='clip'), 'server_list.item', 'server_list.item focus')
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
        if key == 'enter':
            gw_app.rlogin(self._server_data.hostname)
        elif key == ' ':
            self.logger.debug('selecting host - {0}'.format(self._server_data.hostname))
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
        container = urwid.LineBox(self._list_box, 'Server List')
        urwid.WidgetWrap.__init__(self, container)

    def update_list(self, server_data_list):
        server_list_items = [ServerListItem(ServerData(**server_data)) for server_data in server_data_list]
        self._list_box.body = urwid.SimpleFocusListWalker(server_list_items)

    def keypress(self, size, key):
        if key == 'ctrl l':
            self._unselect_all()
        return super(ServerListBox, self).keypress(size, key)

    def _unselect_all(self):
        for widget in self._list_box.body:
            widget.unselected()


class GWKit(urwid.Frame):
    logger = logging.getLogger('gwkit.GWKit')

    signals = ['keyword_change', 'username_change']

    def __init__(self, *args, **kwargs):
        title_bar = urwid.AttrMap(urwid.Padding(urwid.Text('GWKit', align=urwid.CENTER)), 'title')
        self.status_bar = StatusBar(gw_app.username, gw_app.keyword)
        self.server_list_box = ServerListBox()
        self.server_list_box.update_list(gw_app.get_server_list())
        self.status_bar.connect_signals(self)

        super(GWKit, self).__init__(self.server_list_box, urwid.Pile([title_bar, self.status_bar]))

    def keypress(self, size, key):
        self.logger.debug('key pressed - key={0}'.format(key))

        if key == 'backspace':
            gw_app.delete_keyword()
            self._emit('keyword_change', gw_app.keyword)
        elif len(key) == 1 and key.isalnum():
            gw_app.append_keyword(key)
            self._emit('keyword_change', gw_app.keyword)
        elif key == 'ctrl k':
            gw_app.clear_keyword()
            self._emit('keyword_change', gw_app.keyword)
        elif key == 'ctrl _':
            gw_app.rotate_username()
            self._emit('username_change', gw_app.username)
        else:
            return super(GWKit, self).keypress(size, key)


if __name__ == '__main__':
    logger = logging.getLogger('gwkit')

    parser = argparse.ArgumentParser(description='GWKit')
    parser.add_argument('-s', metavar='SERVER_CONFIG_PATH', type=str, help='path to server list config file',
                        default='server_config.json', dest='server_config')
    parser.add_argument('-u', metavar='USERNAME_CONFIG_PATH', type=str, help='path to username list config file',
                        default='username_config.json', dest='username_config')
    parser.add_argument('-t', help='enable test mode', action='store_true', dest='test_mode')
    parsed_args = vars(parser.parse_args())

    logger.debug('parsed arguments = {0}'.format(parsed_args))

    try:
        urwid.set_encoding('UTF-8')
        gw_app = GWKitApplication(**parsed_args)
        gw_app.initialize()
        gw_kit = GWKit(**parsed_args)
        main_loop = urwid.MainLoop(gw_kit, palette, handle_mouse=False)
        main_loop.run()

    except KeyboardInterrupt, err:
        pass
