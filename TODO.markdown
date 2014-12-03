TODO
====

* Add configuration options to fix 'application/octet-stream' detections with
  file ending. azw3 files for example.

* Why mimetypes returns None sometimes while magic doesn't?
    * Try to fix this.
    * There are also cases where mimetypes produces different results.

* Add AUR package:
    * Use PyPI to PKGBUILD
    * pyxdg-open-git
    * desktop_file_parser-git
    * Edit: https://wiki.archlinux.org/index.php/Xdg-open#xdg-open_replacements

* mimi like dmenu when not found, asking for Exec string.
    * Configurable
    * Configurable program to call (dmenu by default)

* Add logging options to direct launched programs output.
    * to config file:
    * no directing
    * target file (e.g. /dev/null)

* Read optionally desktop cache files.
    * Check the spec.

[ DONE ]: add tests
* List files file should accept values as comma separated lists:
    http://www.freedesktop.org/wiki/Specifications/mime-actions-spec/
    * Also skip not found desktop files and continue list file parsing.

* Format better found desktop files with --print-found
    * Also add [matched rule] field for custom searches
    /path/urxvtc.desktop    [custom]    [matched rule]
    /path/xterm.desktop     [search]
    /path/urxvtc.desktop    [search]

* Argument Parsing: Make possible of opening of files named "--print-found", for example.
    * Possible solution is to provide 2 command line executables.

FUTURE
------

* Maybe add option to do automatically something without parameters for current
  dir. Like grouping files by mime/type and the giving promt to select which to
  view.


FEATURES
--------

* Reads desktop cache files.


BUGS
----

Now opening an url with .flac ending opens vlc for example, this of course is
not correct action for url below for example:
http://musicbrainz.org:80/taglookup?tport=8000&artist=World%27s%20End%20Girlfriend&release=Birthday%20Resistance%20Parade&track=Birthday%20Resistance%20Parade&tracknum=1&duration=466770&filename=01_-_birthday_resistance_parade.flac

Should honor header Content-Type:

> curl -I 'http://musicbrainz.org:80/taglookup?tport=8000&artist=World%27s%20End%20Girlfriend&release=Birthday%20Resistance%20Parade&track=Birthday%20Resistance%20Parade&tracknum=1&duration=466770&filename=01_-_birthday_resistance_parade.flac'

HTTP/1.1 200 OK
Date: Sun, 29 Jun 2014 11:56:44 GMT
Content-Type: text/html; charset=utf-8
Connection: keep-alive
Keep-Alive: timeout=20
Server: nginx/1.1.19
Set-Cookie: musicbrainz_server_session=b7c7c4df86ef888fe1e1bb746a02089e101617af;
path=/; expires=Sun, 29-Jun-2014 13:56:44 GMT; HttpOnly
Set-Cookie: javascript=false; path=/


Opening steam desktop game file fails, starts bashwrap vim

$ INFO:xdg_open:789: Got urls: '['Shadowrun Returns.desktop']'
INFO:__get_mimetype__:167: Unescaped file url target: /home/wor/Shadowrun
Returns.desktop
DEBUG:__get_mimetype__:172: -------- mimetypes differed from magic --------
DEBUG:__get_mimetype__:173: None != text/plain
DEBUG:__get_mimetype__:174: -----------------------------------------------
DEBUG:__get_mimetype__:176: Preferring something over 'None'
INFO:xdg_open:797: '/home/wor/Shadowrun Returns.desktop' protocol was: 'file'
INFO:xdg_open:798: '/home/wor/Shadowrun Returns.desktop' target was:
'/home/wor/Shadowrun Returns.desktop'
INFO:xdg_open:799: '/home/wor/Shadowrun Returns.desktop' mime type was:
'text/plain'
INFO:xdg_open:803: ['/home/wor/.local/share/applications/',
'/usr/share/applications/', '/usr/local/share/applications/']
DEBUG:get_desktop_file:574: Running custom config search (('MimeType',
'text/plain')): my_own_mappings
INFO:xdg_open:820: Found desktop file 'Generated Desktop File: !bashwrap vim'
DEBUG:group_purls:786: Formed 1 URL groups.
DEBUG:xdg_open:826: Grouped purls: [[</home/wor/Shadowrun
Returns.desktop|file|/home/wor/Shadowrun Returns.desktop|text/plain>]]
INFO:run_exec:721: run_exec: bashwrap placeholder
INFO:get_prepared_exec_str:679: wrapping exec string with terminal emulator
call.
INFO:run_exec:738: Final exec string(s): ['urxvtc -e bash --rcfile
/tmp/tmpfhkit8s7 -i']
INFO:run_exec:740: Calling exec string: urxvtc -e bash --rcfile /tmp/tmpfhkit8s7
-i


