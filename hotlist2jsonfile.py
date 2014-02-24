# -*- coding: utf-8 -*-

import json
import os

import weechat


SCRIPT_NAME = 'hotlist2jsonfile'
SCRIPT_AUTHOR = 'Jason Kölker'
SCRIPT_VERSION = '0.0.1'
SCRIPT_LICENSE = 'GPL'
SCRIPT_DESC = 'hotlist2jsonfile: writeout the hotlist to a file as json'


SETTINGS = {'output_file': '%h/hotlist.json'}


def write_file(data):
    filename = weechat.config_get_plugin('output_file')

    if not filename:
        return

    weechat_dir = weechat.info_get('weechat_dir', '')
    filename = os.path.expanduser(filename.replace('%h', weechat_dir))

    with open(filename, 'w') as f:
        f.write(json.dumps(data))


def hotlist_changed(data, signal, signal_data):
    hotlist = weechat.infolist_get('hotlist', '', '')

    data = []

    while weechat.infolist_next(hotlist):
        priority = weechat.infolist_integer(hotlist, 'priority')

        plugin_name = weechat.infolist_string(hotlist, 'plugin_name')
        buffer_name = weechat.infolist_string(hotlist, 'buffer_name')

        buffer_number = weechat.infolist_integer(hotlist, 'buffer_number')
        low_messages = weechat.infolist_integer(hotlist, 'count_00')
        channel_messages = weechat.infolist_integer(hotlist, 'count_01')
        private_messages = weechat.infolist_integer(hotlist, 'count_02')
        highlight_messages = weechat.infolist_integer(hotlist, 'count_03')

        buffer_pointer = weechat.infolist_pointer(hotlist, 'buffer_pointer')
        short_name = weechat.buffer_get_string(buffer_pointer, 'short_name')

        data.append({'priority': priority,
                     'plugin_name': plugin_name,
                     'buffer_name': buffer_name,
                     'buffer_number': buffer_number,
                     'low_messages': low_messages,
                     'channel_messages': channel_messages,
                     'private_messages': private_messages,
                     'highlight_messages': highlight_messages,
                     0: low_messages,
                     1: channel_messages,
                     2: private_messages,
                     3: highlight_messages,
                     'short_name': short_name})

    weechat.infolist_free(hotlist)

    write_file({'hotlist': data})

    return weechat.WEECHAT_RC_OK


if __name__ == '__main__':
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                        SCRIPT_LICENSE, SCRIPT_DESC, '', ''):

        for opt, val in SETTINGS.iteritems():
            if not weechat.config_is_set_plugin(opt):
                weechat.config_set_plugin(opt, val)

        weechat.hook_signal('hotlist_changed', 'hotlist_changed', '')

# vim:set shiftwidth=4 tabstop=4 softtabstop=4 expandtab textwidth=80:
