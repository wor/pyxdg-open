pyxdg-open
==========

Python xdg-open (from xdg-utils_) clone. Basically determines how to open and
then opens given URL using system desktop files.

Motivation for this is to provide file opener which works well without a popular
desktop environment and still supports `Desktop Entry Specification`_. Also it's
good to provide something which doesn't have plethora of escaping or other input
related bugs, e.g. `xdg-open: be more paranoid in escaping`_. This is much
easier and cleaner to achieve in Python than Bash.

Example config file (by default located at:
~/.config/pyxdg-open/pyxdg-open.conf)::

    # Paths where to search desktop files for in order of preference. Paths are a
    # comma separated list.
    desktop_file_paths = ~/.local/share/applications/,
                          /usr/share/applications/,
                          /usr/local/share/applications/

    # List files under desktop_file_paths which are first searched for desktop
    # files. If this is empty no list files are used.
    list_files = mimeapps.list,
                 defaults.list

    # If default terminal emulator is not specified then first desktop file with
    # TerminalEmulator as Category will be used.
    #default_terminal_emulator = urxtvc

    # Default search order. This means, first use list_files to find the appropriate
    # desktop file and if not found, proceed to searching desktop files from desktop
    # file paths.
    search_order = list_files,
                   desktop_file_paths

´search_order´ defines the order of desktop file searches. By default the
desktop files are first searched from the list files located in the
´desktop_file_paths´ (´list_files´ must be defined). Second the desktop files
are searched normally from the defined ´desktop_file_paths´.

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

Dependencies
------------

* `desktop_file_parser <https://github.com/wor/desktop_file_parser>`_
* `tokenizer <https://github.com/wor/tokenizer>`_

Optional Dependencies
---------------------

* `python-magic <http://darwinsys.com/file/>`_ >> `Arclinux AUR package
  <https://aur.archlinux.org/packages/python-magic/>`_

Similar Programs
----------------

* `mimi <https://github.com/taylorchu/mimi>`_
* `buskin <https://github.com/supplantr/busking>`_

`List of xdg-open replacements on Archlinux wiki`_

TODO
----

* Document differences to similar programs
* Add info about easy installation
* Read desktop cache files
* Add missing xdg-open functionality

.. _xdg-utils: http://cgit.freedesktop.org/xdg/xdg-utils/
.. _`Desktop Entry Specification`: http://standards.freedesktop.org/desktop-entry-spec/latest/
.. _`xdg-open: be more paranoid in escaping`: http://cgit.freedesktop.org/xdg/xdg-utils/commit/?id=2373d9b2b70652e447b413cde7939bff42fb960d
.. _`List of xdg-open replacements on Archlinux wiki`: https://wiki.archlinux.org/index.php/Xdg-open#xdg-open_replacements
