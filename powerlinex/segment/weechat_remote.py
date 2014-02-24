# -*- coding: utf-8 -*-

import collections
import hashlib
import json
import os
import string
import subprocess
import sys
import threading
import time

try:
    import Queue as queue

except ImportError:
    import queue


from powerline.lib import threaded
import powerline


HOTLIST_LOW = 0
HOTLIST_MESSAGE = 1
HOTLIST_PRIVATE = 2
HOTLIST_HIGHLIGHT = 3

PRIORITIES = (HOTLIST_LOW, HOTLIST_MESSAGE, HOTLIST_PRIVATE, HOTLIST_HIGHLIGHT)
HOTLIST_SUMMARY = {HOTLIST_LOW: 'low', HOTLIST_MESSAGE: 'msg',
                   HOTLIST_PRIVATE: 'prv', HOTLIST_HIGHLIGHT: 'hl'}

FMT_COUNT = 'count'
FMT_SUMMARY = 'summary'
FMT_BUFFERS = 'buffers'

INOTIFY_CMD = ('bash -c "cat {hotlist_file};echo;'
               'inotifywait -e close_write -m -q {hotlist_file} | while read;'
               'do cat {hotlist_file};echo;done"')
REMOTES = {}


class OutputThread(threading.Thread):
    daemon = True

    def __init__(self, out, q, shutdown):
        threading.Thread.__init__(self)
        self.out = out
        self.q = q
        self.shutdown = shutdown

    def run(self):
        for line in iter(self.out.readline, b''):
            if self.shutdown.is_set():
                break

            self.q.put(line)

            if self.shutdown.is_set():
                break

        self.out.close()


def keys_to_int(data):
    result = {}

    for k, v in data.iteritems():
        # NOTE(jkoelker) this is ok since we only have 0-3 ;)
        if k in string.digits:
            k = int(k)

        if isinstance(v, list):
            v = [keys_to_int(i) for i in v]

        result[k] = v

    return result


def unwind_queue(q, logger=lambda x: None):
    while not q.empty():
        data = q.get(True)
        logger(data)


def start_transport(shutdown, cmd, out_q, err_q, **kwargs):
    null = open(os.devnull)
    p = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, stdin=null, bufsize=1,
                         close_fds=('posix' in sys.builtin_module_names))
    out = OutputThread(p.stdout, out_q, shutdown)
    err = OutputThread(p.stderr, err_q, shutdown)
    out.start()
    err.start()
    return p


def setup_transport(host, command, transport, transport_args):
    cmd = [transport]

    for transport_arg in transport_args.split():
        cmd.append(transport_arg)

    cmd.append(host)
    cmd.append(command)

    out_q = queue.Queue()
    err_q = queue.Queue()
    shutdown = threading.Event()

    transport = None

    return {'out_q': out_q, 'err_q': err_q, 'shutdown': shutdown,
            'transport': transport, 'cmd': cmd, 'host': host}


def shutdown_transport(transport, shutdown, out_q, err_q, logger, **kwargs):

    if transport is not None:
        logger('Terminating transport')
        transport.terminate()

        count = 0
        while transport.poll() is None and count < 50:
            time.sleep(0.1)
            count = count + 1

        if transport.poll() is None:
            logger('Transport did not die, killing')
            transport.kill()

    unwind_queue(out_q)
    unwind_queue(err_q)
    shutdown.set()


def remote_key(host, command, transport, transport_args):
    value = ''.join((host, command, transport, transport_args))
    return hashlib.md5(value).hexdigest()


def get_lines(q, logger):
    lines = []

    while not q.empty():
        try:
            line = q.get(block=True, timeout=0.1)

        except queue.Empty:
            break

        line = line[:-1].decode('utf-8')
        logger(line)
        lines.append(line)

    return lines


def process_remote(remote, logger):
    log_prefix = logger.prefix + ':' + remote['host']

    if remote['transport'] is None:
        logger.debug('Starting transport', prefix=log_prefix)
        remote['transport'] = start_transport(**remote)

    if remote['transport'].poll() is not None:
        logger.debug('Transport dead, restarting')
        log = lambda x: logger.error('stderr: {}', x,
                                     prefix=log_prefix)
        unwind_queue(remote['err_q'], logger=log)

        log = lambda x: logger.debug('stdout: {}', x,
                                     prefix=log_prefix)
        unwind_queue(remote['out_q'], logger=log)

        remote['shutdown'].set()
        remote['shutdown'] = threading.Event()

        remote['transport'] = start_transport(**remote)

    # NOTE(jkoelker) Keep the stderr queue clean
    log = lambda x: logger.debug('stderr: {}', x,
                                 prefix=log_prefix)
    unwind_queue(remote['err_q'], logger=log)

    log = lambda x: logger.debug('stdout: {}', x,
                                 prefix=log_prefix)

    lines = get_lines(remote['out_q'], log)

    for line in lines:
        for data_queue in remote['data_queues']:
            data_queue.put(line)


class RemoteDispatcher(threading.Thread):
    daemon = True

    def __init__(self, shutdown, logger):
        threading.Thread.__init__(self)
        self.remotes = {}
        self.shutdown = shutdown
        self.logger = logger

    def _shutdown(self):
        self.logger.debug('Shutting down transports')

        for remote in self.remotes.itervalues():
            log_prefix = self.logger.prefix + ':' + remote['host']
            logger = lambda x: logger.debug(x, prefix=log_prefix)
            shutdown_transport(logger=logger, **remote)

    def add_remote(self, host, command, transport='ssh', transport_args=''):
        key = remote_key(host, command, transport, transport_args)

        if key not in self.remotes:
            remote = setup_transport(host, command, transport=transport,
                                     transport_args=transport_args)
            remote['data_queues'] = []

            self.remotes[key] = remote

        data_queue = queue.Queue()
        self.remotes[key]['data_queues'].append(data_queue)
        return data_queue

    def run(self):
        while not self.shutdown.is_set():
            for remote in self.remotes.values():
                process_remote(remote, self.logger)

            time.sleep(0.5)

        self._shutdown()


Key = collections.namedtuple('Key', ('host', 'format', 'min_priority',
                                     'buffers', 'buffers_exclude',
                                     'hotlist_file', 'command', 'transport',
                                     'transport_args'))


class Hotlist(threaded.KwThreadedSegment):
    drop_interval = 0

    def __init__(self, *args, **kwargs):
        threaded.KwThreadedSegment.__init__(self, *args, **kwargs)

        self.data_queues = {}
        self.state_cache = {}

    def shutdown(self, *args, **kwargs):
        self._dispatcher_shutdown.set()
        self.dispatcher.join(0.02)
        threaded.KwThreadedSegment.shutdown(self, *args, **kwargs)

    def start(self, *args, **kwargs):
        self._dispatcher_shutdown = threading.Event()
        self.dispatcher = RemoteDispatcher(self._dispatcher_shutdown,
                                           self.logger)

        self.dispatcher.start()
        threaded.KwThreadedSegment.start(self, *args, **kwargs)

    def startup(self, pl, *args, **kwargs):
        self.logger = powerline.PowerlineLogger(pl.use_daemon_threads,
                                                pl.logger,
                                                pl.ext)
        self.logger.prefix = self.__class__.__name__.lower()
        threaded.KwThreadedSegment.startup(self, self.logger, *args, **kwargs)

    @staticmethod
    def key(host, format=FMT_COUNT, min_priority=2, buffers=None,
            buffers_exclude=None, hotlist_file='$HOME/.weechat/hotlist.json',
            command=INOTIFY_CMD, transport='ssh', transport_args='', **kwargs):

        if buffers is None:
            buffers = []

        if buffers_exclude is None:
            buffers_exclude = []

        buffers = tuple(buffers)
        buffers_exclude = tuple(buffers_exclude)
        min_priority = int(min_priority)

        command = command.format(hotlist_file=hotlist_file, host=host,
                                 transport=transport, **kwargs)

        return Key(host=host, format=format, min_priority=min_priority,
                   buffers=buffers, buffers_exclude=buffers_exclude,
                   hotlist_file=hotlist_file, command=command,
                   transport=transport, transport_args=transport_args)

    def _get_data(self, data_queue, host):
        if data_queue.empty():
            return

        try:
            data = data_queue.get_nowait()

        except queue.Empty:
            return

        # NOTE(jkoelker) gaurd against the queue becoming backed up
        queue_size = data_queue.qsize()
        if queue_size > 1:
            self.logger.debug('Dropping {} messages from {}', queue_size, host)

            for _count in xrange(queue_size):
                try:
                    data = data_queue.get_nowait()

                except queue.Empty:
                    break

        if not data:
            return

        # NOTE(jkoelker) Simple 'sure, it looks like json' check
        if data[0] != '{' or data[-1] != '}':
            self.logger.debug('Data does not look like json: {}', data)
            return

        try:
            data = json.loads(data)

        except ValueError:
            self.exception('Data is not JSON: {}', data)
            return

        data = keys_to_int(data)
        return data

    def compute_state(self, key):
        if not key.host:
            self.logger.warn('Host not defined in config')
            return None

        if key not in self.data_queues:
            data_queue = self.dispatcher.add_remote(key.host,
                                                    key.command,
                                                    key.transport,
                                                    key.transport_args)
            self.data_queues[key] = data_queue

        data_queue = self.data_queues[key]
        data = self._get_data(data_queue, key.host)

        if not data:
            return self.state_cache.get(key)

        priorities = [p for p in PRIORITIES if p >= key.min_priority]

        state = {}
        if key.format == FMT_COUNT:
            state[FMT_COUNT] = self._count(data, priorities,
                                           key.buffers,
                                           key.buffers_exclude)

        elif key.format == FMT_SUMMARY:
            state[FMT_SUMMARY] = self._summary(data, priorities,
                                               key.buffers,
                                               key.buffers_exclude)

        if not state:
            return self.state_cache.get(key)

        self.state_cache[key] = state
        self.logger.debug(str(state))
        return state

    @staticmethod
    def _count(data, priorities, buffers, buffers_exclude):
        count = 0

        # TODO(jkoelker) remove the double loop
        for priority in priorities:
            for i in data['hotlist']:
                if i['buffer_name'] in buffers_exclude:
                    continue

                elif i['short_name'] in buffers_exclude:
                    continue

                if buffers:
                    if i['buffer_name'] not in buffers:
                        continue

                    elif i['short_name'] not in buffers:
                        continue

                count = count + i[priority]

        if count:
            return count

    @staticmethod
    def _summary(data, priorities, buffers, buffers_exclude):
        content = {}

        # TODO(jkoelker) remove the double loop
        for priority in priorities:
            count = 0

            for i in data['hotlist']:
                if i['buffer_name'] in buffers_exclude:
                    continue

                elif i['short_name'] in buffers_exclude:
                    continue

                if buffers:
                    if i['buffer_name'] not in buffers:
                        continue

                    elif i['short_name'] not in buffers:
                        continue

                count = count + i[priority]

            content[priority] = count

        if content:
            return content

    @staticmethod
    def render_one(state, format=FMT_COUNT, **kwargs):
        if not state:
            return

        result = []
        default_groups = ['hotlist', 'email_alert']
        dividers = ['hotlist:divider', 'background:divider']

        if format == FMT_COUNT:
            if state.get(FMT_COUNT):
                result.append({'contents': str(state[FMT_COUNT]),
                               'divider_highlight_group': 'background:divider',
                               'highlight_group': default_groups})

        elif format == FMT_SUMMARY:
            fmt = kwargs.get('summary_format', {'low': 'L:{count}',
                                                'msg': 'M:{count}',
                                                'prv': 'P:{count}',
                                                'hl': 'H:{count}'})
            use_space_as_divider = kwargs.get('use_space_as_divider', False)
            draw_inner_divider = not use_space_as_divider

            if state.get(FMT_SUMMARY):
                for p, count in state[FMT_SUMMARY].iteritems():
                    contents = fmt[HOTLIST_SUMMARY[p]].format(count=count)
                    groups = ['hotlist_' + HOTLIST_SUMMARY[p]] + default_groups

                    if use_space_as_divider:
                        contents = contents + ' '

                    result.append({'contents': contents,
                                   'divider_highlight_group': dividers,
                                   'highlight_group': groups,
                                   'draw_inner_divider': draw_inner_divider})

            if (result and use_space_as_divider and
                    result[-1]['contents'][-1] == ' '):
                result[-1]['contents'] = result[-1]['contents'][:-1]

        return result


hotlist = Hotlist()
