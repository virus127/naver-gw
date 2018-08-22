#!/usr/bin/python
# -*- coding: utf-8 -*-

import argparse
import json
import logging
import os

import log
from helper import abs_path, load_module
from model import ServerData, ServerDataEncoder

urwid = load_module(u'urwid')
trie = load_module(u'pygtrie')

log.setup_logger()


class ClosableOverlay(urwid.Overlay):
    logger = logging.getLogger('gwkit.ClosableOverlay')

    def __init__(self, title, top_w, *args, **kwargs):
        content = urwid.LineBox(urwid.Padding(top_w, left=1, right=1), title=title)
        super(ClosableOverlay, self).__init__(content, *args, **kwargs)
        if isinstance(top_w, ClosableOverlayContent):
            self.logger.debug(u'Content is ClosableOverlayContent, connect signals')
            urwid.connect_signal(top_w, 'close', self.close)

    def keypress(self, size, key):
        if key == u'esc':
            self.close()
        else:
            return super(ClosableOverlay, self).keypress(size, key)

    def close(self, widget=None):
        application.discard_popup()


class ClosableOverlayContent(urwid.WidgetWrap):
    signals = ['close']

    def __init__(self, *args, **kwargs):
        super(ClosableOverlayContent, self).__init__(*args, **kwargs)

    def _close(self):
        self._emit('close')


class RemoteCommandFormPopup(ClosableOverlayContent):
    logger = logging.getLogger('gwkit.RemoteCommandFormPopup')

    def __init__(self, hostnames=()):
        self._target_hostnames = hostnames
        hosts_text = urwid.Text(u'\n'.join(hostnames))
        self._command_edit = urwid.Edit(u'Command : ')
        widgets = [hosts_text, self._command_edit]
        container = urwid.ListBox(urwid.SimpleFocusListWalker(widgets))
        super(RemoteCommandFormPopup, self).__init__(container)

    def keypress(self, size, key):
        if key == u'enter':
            command = self._command_edit.get_edit_text()
            if command:
                application.rsh(self._target_hostnames, command)
            self._close()
        else:
            return super(RemoteCommandFormPopup, self).keypress(size, key)


class ServerDataFormPopup(ClosableOverlayContent):
    logger = logging.getLogger('gwkit.ServerDataFormPopup')

    def __init__(self, hostname='', alias='', tags='', **kwargs):
        self._hostname_edit = urwid.Edit(u'Hostname : ', edit_text=hostname)
        self._alias_edit = urwid.Edit(u'Alias : ', edit_text=alias)
        self._tags_edit = urwid.Edit(u'Tags : ', edit_text=tags)
        self.widgets = [self._hostname_edit, self._alias_edit, self._tags_edit]
        self.list_box = urwid.ListBox(urwid.SimpleFocusListWalker(self.widgets))
        super(ServerDataFormPopup, self).__init__(self.list_box)

    def __getitem__(self, item):
        return getattr(self, item)

    def keypress(self, size, key):
        if key == u'enter':
            if self._focus_next():
                return
            self._submit()
        else:
            return super(ServerDataFormPopup, self).keypress(size, key)

    @property
    def hostname(self):
        return self._hostname_edit.get_edit_text()

    @property
    def alias(self):
        return self._alias_edit.get_edit_text()

    @property
    def tag_list(self):
        return self._tags_edit.get_edit_text().split()

    def _focus_next(self):
        focus_widget, _ = self.list_box.get_focus()
        next_index = self.widgets.index(focus_widget) + 1
        if next_index >= len(self.widgets):
            self.logger.debug(u'There is no next widget')
            return False
        self.logger.debug(u'Focusing to the next widget')
        self.list_box.set_focus(next_index)
        return True

    def _submit(self):
        if not self.hostname:
            return

        data = dict(
            hostname=self.hostname,
            alias=self.alias,
            tag_list=self.tag_list,
        )
        self.logger.debug(u'Submitting changed server data - data:{0}'.format(data))
        application.upsert_server_data(**data)
        self._close()


class StatusBar(urwid.WidgetWrap):
    def __init__(self, username='', keyword=''):
        self.username_edit = urwid.Edit(u'Username : ', edit_text=username)
        self.keyword_edit = urwid.Edit(u'Keyword : ', edit_text=keyword)
        column_widgets = [self.username_edit, self.keyword_edit]
        status_columns = urwid.Columns(column_widgets)
        container = urwid.LineBox(status_columns, u'Status', title_align=urwid.LEFT)

        self.update_username()
        self.update_keyword()

        super(StatusBar, self).__init__(container)

    def update_username(self):
        self.username_edit.set_edit_text(application.username)

    def update_keyword(self):
        self.keyword_edit.set_edit_text(application.keyword)


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
        super(ServerListItem, self).__init__( columns)

    def selectable(self):
        return True

    def keypress(self, size, key):
        if key == u'enter':
            application.rlogin(self._server_data.hostname)
        elif key == u' ':
            self.logger.debug(u'selecting host - {0}'.format(self._server_data.hostname))
            self._toggle_selected()
        elif key == u'ctrl e':
            self.logger.debug(u'show edit form - host:{0}'.format(self._server_data.hostname))
            popup = ServerDataFormPopup(self._server_data.hostname, self._server_data.alias, self._server_data.tags)
            application.show_popup(popup, u'Edit Server Data')
        else:
            return key

    @property
    def selected(self):
        return self._selected

    @property
    def hostname(self):
        return self._server_data.hostname

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

        self.update_list()
        super(ServerListBox, self).__init__(container)

    def update_list(self):
        server_list_items = [ServerListItem(s) for s in application.get_server_data_list()]
        self._list_box.body = urwid.SimpleFocusListWalker(server_list_items)

    def keypress(self, size, key):
        if key == u'ctrl l':
            self._unselect_all()
        elif key == u'ctrl r':
            hostnames = self._get_all_selected_hostnames()
            application.show_popup(RemoteCommandFormPopup(hostnames), u'Remote Command')
        return super(ServerListBox, self).keypress(size, key)

    def _unselect_all(self):
        for widget in self._list_box.body:
            widget.unselected()

    def _get_all_selected_hostnames(self):
        return [widget.hostname for widget in self._get_all_selected()]

    def _get_all_selected(self):
        return [widget for widget in self._list_box.body if widget.selected]


class MainController(urwid.Frame):
    logger = logging.getLogger(u'gwkit.MainController')

    ARROW_UP = u'↑'
    ARROW_DOWN = u'↓'
    ENTER = u'↵'

    key_mapping = [
        (ARROW_UP, u'Up'),
        (ARROW_DOWN, u'Down'),
        (ENTER, u'Login'),
        (u'Space', u'Select'),
        (u'^R', u'emoteCommand'),
        (u'^E', u'dit'),
        (u'^N', u'ew'),
    ]

    @classmethod
    def get_key_mapping_text(cls):
        return u' '.join([cls.gen_key_desc_text(key, desc) for key, desc in cls.key_mapping])

    @staticmethod
    def gen_key_desc_text(key, desc):
        return u'[{0}]{1}'.format(key, desc)

    def __init__(self):
        title_bar = urwid.AttrMap(urwid.Padding(urwid.Text(u'GWKit', align=urwid.CENTER)), u'title')
        self.status_bar = StatusBar()
        self.server_list_box = ServerListBox()
        footer_text = urwid.Text(self.get_key_mapping_text())
        super(MainController, self).__init__(self.server_list_box, urwid.Pile([title_bar, self.status_bar]),
                                             footer_text)

    def keypress(self, size, key):
        self.logger.debug(u'key pressed - key={0}'.format(key))

        if key == u'backspace':
            application.delete_keyword()
            self._keyword_changed()
        elif len(key) == 1 and key.isalnum():
            application.append_keyword(key)
            self._keyword_changed()
        elif key == u'ctrl k':
            application.clear_keyword()
            self._keyword_changed()
        elif key == u'ctrl _':
            application.rotate_username()
            self._username_changed()
        elif key == u'ctrl n':
            self.logger.debug(u'show register form')
            popup = ServerDataFormPopup(application.keyword)
            application.show_popup(popup, u'Register Server Data')
        else:
            return super(MainController, self).keypress(size, key)

    def server_data_updated(self):
        self.logger.debug(u'Server data updated refresh UI')
        self.server_list_box.update_list()

    def _keyword_changed(self):
        self.status_bar.update_keyword()
        self.server_list_box.update_list()

    def _username_changed(self):
        self.status_bar.update_username()


class GWKitApplication:
    logger = logging.getLogger(u'gwkit.GWKitApplication')

    # 'class name', 'color', 'background-color'
    palette = [
        (u'title', urwid.BLACK, urwid.WHITE),
        (u'background', urwid.WHITE, urwid.BLACK),

        (u'server_list.item', urwid.WHITE, urwid.BLACK),
        (u'server_list.item focus', urwid.LIGHT_BLUE, urwid.BLACK),
    ]

    def __init__(self, server_config_path, username_config_path, test_mode, *args, **kwargs):
        self._username_index = 0
        self._server_config_path = server_config_path
        self._server_data_index = None
        self._server_data_map = None
        self._load_server_config()
        self._username_list = self._parse_username_config(username_config_path)
        self._test_mode = test_mode
        self._username = ''
        self._keyword = ''

        self.rotate_username()
        self.main_loop = None
        self.main_controller = None

    def run(self):
        self._kinit()
        urwid.set_encoding(u'UTF-8')
        self.main_controller = MainController()
        self.main_loop = urwid.MainLoop(self.main_controller, self.palette, handle_mouse=False)
        self.main_loop.run()

    def get_server_data_list(self):
        if self._keyword:
            generator = self._server_data_index.itervalues(prefix=self.keyword_upper)
        else:
            generator = self._server_data_index.itervalues()

        try:
            return sorted(set(s for s in generator), key=lambda s: s.name)
        except KeyError:
            return []

    def upsert_server_data(self, hostname, alias, tag_list):
        self._server_data_map[hostname] = ServerData(hostname, alias, tag_list)
        self._dump_server_config()
        self._load_server_config()
        self.main_controller.server_data_updated()

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
        self._do_command(command, True)

    def rsh(self, hostnames, remote_command):
        self.logger.debug(u'rsh - hostnames:{0}, command:{1}'.format(hostnames, remote_command))
        for hostname in hostnames:
            command = u"rsh -l {0} {1} '{2}'".format(self.username, hostname, remote_command)
            self._do_command(command, True)

    def append_keyword(self, key):
        self._keyword = self._keyword + key

    def clear_keyword(self):
        self._keyword = ''

    def delete_keyword(self):
        self._keyword = self._keyword[0:-1]

    def rotate_username(self):
        self._username = self._username_list[self._username_index]
        self._username_index = (self._username_index + 1) % len(self._username_list)

    def show_popup(self, popup_content, popup_title=u''):
        original_widget = self.main_loop.widget
        self.main_loop.widget = ClosableOverlay(popup_title, popup_content, original_widget,
                                                'center', 100,
                                                'middle', 10)

    def discard_popup(self):
        overlay = self.main_loop.widget
        if not isinstance(overlay, urwid.Overlay):
            self.logger.error(u'CANNOT_DISCARD_NON_OVERLAY_TYPE')
            return
        self.main_loop.widget = overlay.bottom_w

    def _kinit(self):
        command = u'kinit'
        self._do_command(command)

    def _do_command(self, command, redraw=False):
        if self.main_loop and redraw:
            self.main_loop.stop()
        self.logger.debug(u'do command - {0}'.format(command))
        if not self._test_mode:
            os.system(command)
        if self.main_loop and redraw:
            self.main_loop.start()

    def _load_server_config(self):
        self._server_data_index, self._server_data_map = self._parse_server_config()

    def _parse_server_config(self):
        self.logger.debug(u'Try to load server config from {0}'.format(self._server_config_path))
        with file(self._server_config_path) as f:
            server_data_map = dict((data['hostname'], ServerData(**data)) for data in json.load(f))
        self.logger.debug(u'parsed server configs - {0}'.format(server_data_map))
        return self._create_server_index(server_data_map), server_data_map

    def _dump_server_config(self):
        self.logger.debug(u'Try to dump server config to {0}'.format(self._server_config_path))
        with file(self._server_config_path, 'w') as f:
            json.dump(list(self._server_data_map.itervalues()), f, cls=ServerDataEncoder, indent=4,
                      sort_keys=True)

    def _create_server_index(self, server_list):
        """creates trie of uppercased hostname, tags, and alias"""

        index = trie.CharTrie()
        for server in server_list.itervalues():
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


if __name__ == '__main__':
    logger = logging.getLogger(u'gwkit')

    parser = argparse.ArgumentParser(description=u'GWKit')
    parser.add_argument(u'-s', metavar=u'SERVER_CONFIG_PATH', type=str, help=u'path to server list config file',
                        default=abs_path(u'server_config.json'), dest=u'server_config_path')
    parser.add_argument(u'-u', metavar=u'USERNAME_CONFIG_PATH', type=str, help=u'path to username list config file',
                        default=abs_path(u'username_config.json'), dest=u'username_config_path')
    parser.add_argument(u'-t', help=u'enable test mode', action=u'store_true', dest=u'test_mode')
    parsed_args = vars(parser.parse_args())

    logger.debug(u'parsed arguments = {0}'.format(parsed_args))

    try:
        application = GWKitApplication(**parsed_args)
        application.run()

    except KeyboardInterrupt, err:
        pass
