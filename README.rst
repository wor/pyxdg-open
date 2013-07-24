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

    # List files under desktop_file_paths which are first searched for desktop
    # files. If this empty no list files are used.
    list_files = mimeapps.list,
                 defaults.list

    # If default terminal emulator is not specified then first desktop file with
    # TerminalEmulator as Category will be used.
    #default_terminal_emulator = urxtvc

If list_files is defined, desktop files are first searched from existing
list_files located in the ´desktop_file_paths´. Second the desktop files are
searched normally from the defined ´desktop_file_paths´.

Archlinux PKGBUILD
------------------

PKGBUILD files for pyxdg-open and it's dependencies can be found from my
`abs-repo <https://github.com/wor/abs-repo>`_:
`pyxdg-open-git <https://github.com/wor/abs-repo/tree/master/pyxdg-open-git>`_

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

* Document differences to similar programs
* Add info about easy installation
* Read desktop cache files
* Add missing xdg-open functionality

.. _xdg-utils: http://cgit.freedesktop.org/xdg/xdg-utils/
