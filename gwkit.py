# -*- coding: utf-8 -*-

import os

try:
    import urwid
except ImportError:
    import sys
    root_dir = os.path.dirname(os.path.abspath(__file__))
    urwid_dir = os.path.join(root_dir, 'urwid')
    sys.path.append(urwid_dir)
    import urwid


# 'class name', 'color', 'background-color'
palette = [
    ('title', 'black', 'white'),
    ('list_header', 'black', 'light gray'),
    ('list_item', 'black', 'white'),
    ('background', 'black', 'dark blue')
]


class GWKit:
    def __init__(self):
        self.txt = urwid.AttrMap(urwid.Text(u'hello world'), 'title')
        self.fill = urwid.AttrMap(urwid.Filler(self.txt, 'top'), 'background')

    def run(self):
        loop = urwid.MainLoop(self.fill, palette, unhandled_input=self.handle_input)
        loop.run()

    def handle_input(self, key):
        if key in ('q', 'Q'):
            raise urwid.ExitMainLoop()
        self.txt.set_text(repr(key))


if __name__ == "__main__":
    try:
        GWKit().run()
    except KeyboardInterrupt, err:
        pass