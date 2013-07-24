pyxdg-open
==========

Python xdg-open (from xdg-utils_) clone. Basically determines how to open and
then opens given URL using system desktop files. Motivation for this is to
provide file opener which works well without a popular desktop environment and
still supports `Desktop Entry Specification
<http://standards.freedesktop.org/desktop-entry-spec/latest/>`_.

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

If ´desktop_file_paths´ are searched for the desktop file then the first desktop
file which has the matching mime type listed is selected. If there are many
desktop files which match certain mime type and one desktop file is preferred,
then the option is to add the mime type, desktop file pair to mimeapps.list or
defaults.list file.

Archlinux PKGBUILD
------------------

PKGBUILD files for pyxdg-open and it's dependencies can be found from my
`abs-repo <https://github.com/wor/abs-repo>`_:
`pyxdg-open-git <https://github.com/wor/abs-repo/tree/master/pyxdg-open-git>`_

Dependecies
-----------

* `desktop_file_parser <https://github.com/wor/desktop_file_parser>`_
* `tokenizer <https://github.com/wor/tokenizer>`_

Similar programs
----------------

* `mimi <https://github.com/taylorchu/mimi>`_
* `buskin <https://github.com/supplantr/busking>`_

`list of xdg-open replacements <https://wiki.archlinux.org/index.php/Xdg-open#xdg-open_replacements>`_

TODO
----

* Document differences to similar programs
* Add info about easy installation
* Read desktop cache files
* Add missing xdg-open functionality

.. _xdg-utils: http://cgit.freedesktop.org/xdg/xdg-utils/
