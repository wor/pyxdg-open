pyxdg-open
==========

Python xdg-open (from xdg-utils_) clone. Basically determines how to open and
then opens given URL using system desktop files.

Example config file (by default located at:
~/.config/pyxdg-open/pyxdg-open.conf)::

    # Paths where to search desktop files for in order of preference. Paths are a
    # comma separated list.
    desktop_file_paths = ~/.local/share/applications/,
                          /usr/share/applications/,
                          /usr/local/share/applications/


Depends
-------

* `desktop_file_parser <https://github.com/wor/desktop_file_parser>`_
* `tokenizer <https://github.com/wor/tokenizer>`_

Similar programs
----------------

* `mimi <https://github.com/taylorchu/mimi>`_
* `buskin <https://github.com/supplantr/busking>`_

TODO
----

* Document desktop list file usage
* Add info about easy installation
* Read desktop cache files
* Add missing xdg-open functionality

.. _xdg-utils: http://cgit.freedesktop.org/xdg/xdg-utils/
