Powerline eXtenstion for Weechat
================================

This segment extension pulls in your hotlist from a remote
`Weechat <http://weechat.org>`_ instance to your
`Powerline <https://github.com/Lokaltog/powerline>`_ statusbar.


Installation
------------

On the host running `Powerline <https://github.com/Lokaltog/powerline>`_ run:

.. code-block:: bash

    pip install git+https://github.com/jkoelker/powerlinex-segment-weechat-remote.git

On the remote `Weechat <http://weechat.org>`_ server first instal the
hotlist2jsonfile script:

.. code-block:: bash

    cd $HOME/.weechat/python
    wget https://raw.github.com/jkoelker/powerlinex-segment-weechat-remote/master/hotlist2jsonfile.py


Weechat Setup
-------------

Activate the hostlist2jsonfile.py script  in Weechat:

.. code-block:: bash

    /script load hotlist2jsonfile.py
    /script autoload hotlist2jsonfile.py

The script by default will output the contents of the hotlist as json to the file
named ``hotlist.json`` in the Weechat dir (by default this will be ``$HOME/.weechat``).
The option ``output_file`` can be set for the plugin to specify a different file. ``%h``
in the filename will be replaced with the Weechat dir.

For example to output to the file ``/tmp/hotlist.json``:

.. code-block:: bash

    /set plugins.var.python.hotlist2file.output_file '/tmp/hotlist.json'

Or to just rename the file within the Weechat dir:

.. code-block:: bash

    /set plugins.var.python.hotlist2file.output_file '%h/myhotlist.json'


Powerline Usage
---------------

Two different segment formats are availible. ``count`` shows a single count of all
messages in buffers in the hotlist at or above the ``min_priority`` setting. ``summary``
shows the count of message in hotlist buffers at or above the ``min_priority`` for each
priority.


Minimal Configuration
---------------------

Add (or merge) the following to your theme's config (e.g.
``$HOME/.config/powerline/themes/tmux/default.json``):

.. code-block:: javascript

    {
      "segments": {
        "right": [
          {
            "module": "powerlinex.segment.weechat_remote",
            "name": "hotlist",
            "args": {
              "host": "weechat.irc.hostname"
            }
          }
        ]
      }
    }

**NOTE** By default ``ssh <host>`` will be called with the args to use ``inotifywatch``
to output the contents of ``$HOME/.weechat/hotlist.json``. You must have ssh keys setup
and have installed ``inotify-utils`` on the Weechat server for the default minimal
configuration to work.


Full Configuration
------------------

As shown above only the ``host`` argument is required to be specified in the configuraion
file. The following shows the full configuration with the default values:

.. code-block:: javascript

    {
      "segments": {
        "right": [
          {
            "module": "powerlinex.segment.weechat_remote",
            "name": "hotlist",
            "args": {
              "host": "weechat.irc.hostname"
              "format": "count",
              "summary_format": {
                "low": "L:{count}",
                "msg": "M:{count}",
                "prv": "P:{count}",
                "hl": "H:{count}"
              }
              "min_priority": 2,
              "buffers": [],
              "buffers_exclude": [],
              "hotlist_file": "$HOME/.weechat/hotlist.json",
              "transport": "ssh",
              "transport_args": ""
              "command": "bash -c \"cat {hotlist_file};echo;inotifywait -e close_write -m -q {hotlist_file} | while read;do cat {hotlist_file};echo;done\"",
            }
          }
        ]
      }
    }

