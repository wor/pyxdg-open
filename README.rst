pyxdg-open
==========

Python xdg-open (from xdg-utils_) clone. Basically determines how to open and
then opens given URL using system desktop files.

Motivation for this is to provide file opener which works well without a popular
desktop environment and still supports `Desktop Entry Specification`_. Also it's
good to provide something which doesn't have plethora of escaping or other input
related bugs, e.g. `xdg-open: be more paranoid in escaping`_. This is much
easier and cleaner to achieve in Python than in Bash.

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

    # An example of a custom search which can be added to the 'search_order' list,
    # in this case, with name 'my_own_mappings'.
    #
    # Matching can be done with either mime type or file name ending. Mime type can
    # be either full "type/subtype", or partial "type/" or "/subtype".
    #
    # Target can be either a command to which file name is appended before
    # executing, or relative, or absolute path to a desktop file. Relative paths are
    # interpreted to be relative to given desktop_file_paths.
    #[my_own_mappings]
    #application/pdf = zathura
    #video/          = vlc
    #audio/          = vlc
    #rar             = file-roller
    #tar.gz         = /tmp/some_app.desktop
    #inode/directory = urxvtc.desktop

´search_order´ defines the order of desktop file searches. By default the
desktop files are first searched from the list files located in the
´desktop_file_paths´ (´list_files´ must be defined). Second the desktop files
are searched normally from the defined ´desktop_file_paths´.

pyxdg-open also support mimi_ like custom configs which can be added to the
´search_order´ list.

If ´desktop_file_paths´ are searched for the desktop file then the first desktop
file which has the matching mime type listed is selected. If there are many
desktop files which match certain mime type and one desktop file is preferred,
then the option is to add the mime type, desktop file pair to mimeapps.list or
defaults.list file. Another way is to just add own custom mappings to the config
file as seen from the example and add this sections name as first in the
´search_order´ list.

Examples
--------

Print all found desktop files, which open PDF files without really opening
anything. Useful for finding all possible desktop files, in this case for PDF::

    $ xdg-open --dryrun --print-found some.pdf
    Found desktop files:
    /usr/share/applications/zathura.desktop [list_files]
    /usr/share/applications/zathura.desktop [desktop_file_paths]
    /home/wor/.local/share/applications/wine-extension-pdf.desktop [desktop_file_paths]
    /usr/share/applications/xpdf.desktop [desktop_file_paths]
    /usr/share/applications/zathura-pdf-poppler.desktop [desktop_file_paths]
    /usr/share/applications/gimp.desktop [desktop_file_paths]


Let's say that I have following in my config file::

    ...
    search_order = my_own_mappings,
                   list_files,
                   desktop_file_paths

    [my_own_mappings]
    application/pdf = zathura.desktop
    audio/          = vlc.desktop
    ...

Now running following runs correctly vlc with two parameters, so that both audio
tracks end up in the vlc playlist. This is because default ´vlc.desktop´ file
has ´%U´ in the `Exec key`_ value. If this had been, for example, ´%u´ or ´%f´,
two instances of vlc would be launched simultaneously playing ´track01.mp3´ and
´track02.mp3´::

    $ xdg-open -v1 --dryrun track01.mp3 track02.mp3
    ...
    INFO:run_exec:613: Calling exec string: /usr/bin/vlc track01.mp3 track02.mp3

As ´zathura.desktop´ contains ´%f´ in the Exec string, only one file is
accepted and pyxdg-open launches two instances::

    $ xdg-open -v1 --dryrun test0.pdf test1.pdf
    ...
    INFO:run_exec:613: Calling exec string: zathura /tmp/test0.pdf
    INFO:run_exec:613: Calling exec string: zathura /tmp/test1.pdf

This also works correctly with following, as can be seen::

    $ xdg-open -v1 --dryrun test0.pdf test1.pdf audio.mp3 audio.flac
    ...
    INFO:run_exec:613: Calling exec string: /usr/bin/vlc audio.mp3 audio.flac
    ...
    INFO:run_exec:613: Calling exec string: zathura /tmp/test0.pdf
    INFO:run_exec:613: Calling exec string: zathura /tmp/test1.pdf


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

* mimi_
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
.. _`Exec key`: http://standards.freedesktop.org/desktop-entry-spec/latest/ar01s06.html
.. _`xdg-open: be more paranoid in escaping`: http://cgit.freedesktop.org/xdg/xdg-utils/commit/?id=2373d9b2b70652e447b413cde7939bff42fb960d
.. _`List of xdg-open replacements on Archlinux wiki`: https://wiki.archlinux.org/index.php/Xdg-open#xdg-open_replacements
.. _mimi: https://github.com/taylorchu/mimi
