Powerline eXtenstion for Weechat
================================

This segment extension pulls in your hotlist from a remote
`Weechat <http://weechat.org>`_ instance to your
`Powerline <https://github.com/Lokaltog/powerline>`_ statusbar.


Examples
--------

``count`` format:

.. image:: https://raw.github.com/jkoelker/powerlinex-segment-weechat-remote/master/images/count.png

``summary`` format:

.. image:: https://raw.github.com/jkoelker/powerlinex-segment-weechat-remote/master/images/summary.png


Installation
------------

On the host running `Powerline <https://github.com/Lokaltog/powerline>`_ run:

.. code-block:: bash

    pip install git+https://github.com/jkoelker/powerlinex-segment-weechat-remote.git

On the remote `Weechat <http://weechat.org>`_ server first install the
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

The script by default will output the contents of the hotlist as json to the
file named ``hotlist.json`` in the Weechat dir (by default this will be
``$HOME/.weechat``). The option ``output_file`` can be set for the plugin to
specify a different file. ``%h`` in the filename will be replaced with the
Weechat dir.

For example to output to the file ``/tmp/hotlist.json``:

.. code-block:: bash

    /set plugins.var.python.hotlist2file.output_file '/tmp/hotlist.json'

Or to just rename the file within the Weechat dir:

.. code-block:: bash

    /set plugins.var.python.hotlist2file.output_file '%h/myhotlist.json'


Powerline Usage
---------------

Two different segment formats are availible. ``count`` shows a single count of
all messages in buffers in the hotlist at or above the ``min_priority``
setting. ``summary`` shows the count of message in hotlist buffers at or above
the ``min_priority`` for each priority.


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

**NOTE** By default ``ssh <host>`` will be called with the args to use
``inotifywatch`` to output the contents of ``$HOME/.weechat/hotlist.json``.
You must have ssh keys setup and have installed ``inotify-utils`` on the
Weechat server for the default minimal configuration to work.


Full Configuration
------------------

As shown above only the ``host`` argument is required to be specified in the
configuraion file. The following shows the full configuration with the default
values:

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
              "space_divider": false
            }
          }
        ]
      }
    }

+---------------------+-------------------+----------------------------------+
| Arg                 | Valid Values      | Description                      |
+=====================+===================+==================================+
| ``host``            | Any String        | Host to connect to               |
+---------------------+-------------------+----------------------------------+
| ``format``          | ``count``         | Segment display format           |
|                     | ``summary``       |                                  |
+---------------------+-------------------+----------------------------------+
| ``summary_format``  | Dictionary w/keys | Format string of each priority   |
|                     | ``low``, ``msg``, | passed the keyword ``count``     |
|                     | ``prv``, ``hl``   | to ``string.format()``           |
+---------------------+-------------------+----------------------------------+
| ``min_priority``    | ``0``, ``1``,     | The minimum priority level to    |
|                     | ``2``, ``3``      | include in output                |
+---------------------+-------------------+----------------------------------+
| ``buffers``         | List of strings   | List of buffer names to include  |
|                     |                   | in the output calculation        |
+---------------------+-------------------+----------------------------------+
| ``buffers_exclude`` | List of strings   | List of buffer names to exclude  |
|                     |                   | in the output calculation        |
+---------------------+-------------------+----------------------------------+
| ``hotlist_file``    | Any string        | Path on the weechat server to    |
|                     |                   | the hostlist json file           |
+---------------------+-------------------+----------------------------------+
| ``transport``       | Any string        | Command to execute to start the  |
|                     |                   | transport                        |
+---------------------+-------------------+----------------------------------+
| ``transport_args``  | Any string        | Arguments passed to the          |
|                     |                   | transport                        |
+---------------------+-------------------+----------------------------------+
| ``command``         | Any string        | Command to execute on the        |
|                     |                   | transport                        |
+---------------------+-------------------+----------------------------------+
| ``space_divider``   | Boolean           | Use a space instead of ``soft``  |
|                     |                   | divider between summary segments |
+---------------------+-------------------+----------------------------------+

The arguments ``transport``, ``transport_args``, ``host``, and ``command`` are
used to build a command that is expected to simulate ``tail -f`` of a
hotlist.json file. The command is built as:

.. code-block:: bash

    <transport> <transport_args> <host> <command>


Therefore you may use this execute any arbitray command that will yield the
hotlist.json file. For example if you were running Weechat locally you
could set the values as such:

.. code-block:: javascript

    {
      "segments": {
        "right": [
          {
            "module": "powerlinex.segment.weechat_remote",
            "name": "hotlist",
            "args": {
              "host": ""
              "transport": "tail",
              "transport_args": "-f /path/to/hotlist.json",
              "command": ""
            }
          }
        ]
      }
    }

This will end up executing the command:

.. code-block:: bash

    tail -f /path/to/hotlist.json


Color Scheme Support
--------------------

Bolth the ``count`` and ``summary`` formats will use the groups ``hotlist``
then ``email_alert``. The ``summary`` format will also preprend the group
``hotlist_low``, ``hotlist_msg``, ``hotlist_prv``, or ``hotlist_hl`` to the
group list depending on which priority the segment is currently rendering.

For example the ``count`` format will use:

.. code-block:: python

    ['hotlist', 'email_alert']

And the ``summary`` format for the ``prv`` messages count will use:

.. code-block:: python

    ['hotlist_prv', 'hotlist', 'email_alert']

The ``summary`` format will also set the divider groups to:

.. code-block:: python

    ['hotlist:divider', 'background:divider']

This allows adding the following ``hotlist:divider`` group to the color scheme
(e.g. ``$HOME/.config/powerline/colorschemes/tmux/default.json``) which will
blend in nicely with the ``email_alert`` color group:

.. code-block:: javascript

    {
      "groups": {
        "hotlist:divider": { "fg": "gray10", "bg": "brightred"},
        "email_alert": { "fg": "white", "bg": "brightred", "attr": ["bold"] }
      }
    }
