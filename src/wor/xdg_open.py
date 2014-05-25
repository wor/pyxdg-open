#!/usr/bin/env python3
# -*- coding: utf-8 -*- vim:fenc=utf-8:ft=python:et:sw=4:ts=4:sts=4
# Copyright (C) 2013 Esa Määttä
#
# This file is part of pyxdg-open.
#
# pyxdg-open is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyxdg-open is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyxdg-open.  If not, see <http://www.gnu.org/licenses/>.
"""A non-bash xdg-open replacer among many others.

Information about desktop files and xdg-open:
http://standards.freedesktop.org/desktop-entry-spec/latest/
https://wiki.archlinux.org/index.php/Default_Applications
"""

import configparser
import locale
import logging
import mimetypes as MT
import os
import os.path
import re
import shlex
import subprocess
import sys
import urllib
import tempfile

HAS_MAGIC = True
MM = None
try:
    import magic
except ImportError:
    HAS_MAGIC = False

import wor.desktop_file_parser.parser as df_parser

from collections import namedtuple
from collections import OrderedDict


# Global config options (stored here after parsing)
CONFIG = {}

# Default config options
DEFAULT_CONFIG = OrderedDict(sorted({
        "list_files":
            "mimeapps.list, "
            "defaults.list",
        "desktop_file_paths":
            "~/.local/share/applications/, "
            "/usr/share/applications/, "
            "/usr/local/share/applications/",
        "default_terminal_emulator": "",
        "search_order":
            "list_files, "
            "desktop_file_paths"
        }.items(), key=lambda t: t[0]))


class URL(object):
    """Represents xdg-opens input (an URL) as a class.

    Attributes:
        url
        protocol
        target
        mime_type
        desktop_file
    """
    def __init__(self, url, protocol="", target="", mime_type=""):
        """URL initialization.

        Parameters:
            url: str. URL as string.
            protocol: str. Optional protocol of the URL, if not given it's
                parsed from the `url`.
            target: str. Optional target of the URL, if not given ...
            mime_type: str. Optional mime type as string, if not given ...
        """
        self.url = url
        if not protocol or not target:
            p, t = self.__get_protocol_and_target__()
            self.protocol = p if not protocol else protocol
            self.target   = t if not target else target
        else:
            self.protocol = protocol
            self.target   = target
        self.mime_type = self.__get_mimetype__() \
                if not mime_type else mime_type

        self.desktop_file = None
    def __repr__(self):
        """Returns string representation of a URL.

        Note: Doesn't return string reprentation of contained desktop file.
        """
        return "<{}|{}|{}|{}>".format(self.url, self.protocol, self.target,
                self.mime_type)
    def __get_protocol_and_target__(self):
        """Tries to guess ´self.url´ URLs protocol.

        Derefences symlinks when returning the target to local file url (path).
        In this case modifies self.url to match the target, this helps to
        determine the mime type later on.

        Returns:
            (str, str). Tuple of protocol and rest of the url without protocol,
                or if not found tuple of None.
        """
        if self.url.startswith("/"):
            self.url = os.path.realpath(self.url)
            return "file", self.url

        # Magnet uri starts with 'magnet:?'
        m = re.match(r"([a-z]+):(\?|//)", self.url, re.I)
        if m:
            protocol = m.groups()[0].lower()
            target = urllib.parse.unquote(self.url[m.span()[1]:])
            return protocol, target
        else:
            # Treat url as relative file
            self.url = os.path.realpath(os.path.join(os.getcwd(), self.url))
            return "file", self.url
        return (None, None)
    def __get_mimetype__(self):
        """Tries to guess ´url´ URLs mime type.

        Returns:
            str/None. The mime type of the ´self.url´ URL. Or None if mime type
                could not be determined.
        """
        log = logging.getLogger(__name__)
        url = self.url
        if self.protocol == "file":
            # Strip away file protocol
            url = url.replace("file://", "", 1)
            # url = urllib.unquote(url).decode('utf-8') # for python2?
            url = urllib.parse.unquote(url)

            # If file doesn't exist try to guess its mime type from its extension
            # only.
            if not os.path.exists(url):
                log.debug("Guessing non-existing files mimetype from its extension.")
                file_ext = os.path.splitext(url)[1]
                if len(file_ext) > 1:
                    MT.init()
                    try:
                        mime_type = MT.types_map[file_ext]
                    except KeyError:
                        log.debug("mimetypes could not determine mimetype"
                                " from extension: {}".format(file_ext))
                        return None
                else:
                    return None
            else:
                log.info("Unescaped file url target: {}".format(url))
                mime_type = MT.guess_type(url)[0]
                if HAS_MAGIC: # Debug the differences between mimetypes and magic
                    mime_type_mm = MM.file(url)
                    if mime_type != mime_type_mm:
                        log.debug("-------- mimetypes differed from magic --------")
                        log.debug("{} != {}".format(mime_type, mime_type_mm))
                        log.debug("-----------------------------------------------")
                    if not mime_type and mime_type_mm:
                        log.debug("Preferring something over 'None'")
                        mime_type = mime_type_mm

            # Try to fix mime type for certain file types using file extension
            if mime_type == "application/octet-stream":
                ext = os.path.splitext(url)[1]
                if ext == ".chm":
                    mime_type = "application/x-chm"
                elif ext == ".sdf":
                    mime_type = "application/x-spring-demo"
        elif self.protocol == "magnet":
            mime_type = "application/x-bittorrent"
        else:
            # XXX: Is there still a better way to determine mime type for protocol?
            mime_type = MT.guess_type(self.url)[0]
            if not mime_type:
                mime_type = "x-scheme-handler/" + self.protocol
                log.info("Defaulted protocol '{}' to mime type: '{}'"
                        .format(self.protocol, mime_type))
        return mime_type

    # Getters
    def get_mimetype(self):
        return self.mime_type
    def get_url(self):
        return self.url
    def get_target(self):
        return self.target


def which(program):
    """Mimics *nix 'which' command.

    Finds given program from path if it's not absolute path. Else just checks
    if it's executable.

    This is quite trivial function is orginally from:
    http://stackoverflow.com/a/377028/538470

    Returns:
        str. Found executable with full path.

    Parameters:
        program: str. Executable name.
    """
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file
    return None


def desktop_list_parser(desktop_list_fn, mime_type_find=None, find_all=False):
    """Parses desktop list file (defaults.list for example).

    If mime_type_find is given then return just first matching desktop file or
    None if not found. If mime_type_find is not given or evaluates to False then
    return all mime type desktop file pairs as a dict.

    Parameters:
        desktop_list_fn: str. Path of a desktop list file.
        mime_type_find: str. Mime type to find from given desktop list file.
        find_all: bool. If true returns a list of desktop files when
            mime_type_find is also given.
    Returns:
        dict/[str]/None. See doc string.
    """
    mt_df_re = re.compile(
            r"""
            (^[^[]+)    # mimetype, line doesn't start with [
            =
            (.+)[;]?$   # desktop file, ignore possible ';' at the end
            """, re.I|re.X)
    mime_type_desktop_map = {}
    desktop_files = []
    with open(desktop_list_fn) as f:
        for line in f:
            m = mt_df_re.search(line)
            if not m:
                continue
            mime_type = m.groups()[0]
            single_mime_dfs = parse_comma_sep_list(m.groups()[1])
            # Just get the desktop files matching the mime type given
            if mime_type_find:
                if mime_type == mime_type_find:
                    if find_all:
                        desktop_files += single_mime_dfs
                    else:
                        return single_mime_dfs
                continue
            # Or get everything..
            else:
                if mime_type in mime_type_desktop_map:
                    mime_type_desktop_map[mime_type] += single_mime_dfs
                else:
                    mime_type_desktop_map[mime_type] = single_mime_dfs

    if find_all:
        return desktop_files
    return mime_type_desktop_map if mime_type_desktop_map else None


def get_df_full_path(desktop_file):
    """Retuns full path of a desktop file.
    """
    # We cannot know where desktop file is found?
    for dp in CONFIG["desktop_file_paths"]:
        test_desktop_file = os.path.join(dp, desktop_file)
        if os.path.isfile(test_desktop_file):
            return test_desktop_file
    return None


def get_desktop_file_from_mime_list(mime_type, list_files, find_all=False):
    """Find desktop file from a mime list file.

    Desktop file paths and list files are read from global CONFIG.

    Parameters:
        mime_type: str. Mime type as string.
        list_files: TODO:
        find_all: TODO:

    Returns:
        DesktopFile() or if find_all==True lists of DesktopFiles.
    """
    def check_list_files():
        """Gets desktop file(s) name from a list file.

        Checks if list_files exist in the current desktop file path (dp) and if
        it's so then tries to find matchin desktop file name for the mime_type.
        If list files defines multiple desktop files in one entry, just takes
        the first one existing if not ´find_all´ defined.

        Uses:
            dp, list_files, mime_type

        Returns:
            [str]. Desktop file names matching the mime_type.
        """
        for lf in list_files:
            p = os.path.join(dp, lf)
            if os.path.exists(p):
                log.debug("Searching list file: {}".format(p))
                df = desktop_list_parser(p, mime_type, find_all)
                if df and df[0]:
                    return df, p
        return None, ""
    log = logging.getLogger(__name__)

    # First parse desktop file lists, and try to find desktop file there
    parsed_desktop_files = []
    for dp in CONFIG["desktop_file_paths"]:
        desktop_files, list_file = check_list_files()
        if not desktop_files: continue
        for desktop_file in desktop_files:
            if desktop_file:
                df_fp = get_df_full_path(desktop_file)
                if not df_fp:
                    log.info("Skipping not found (list) desktop file "
                            "'{}', mentioned in '{}'".format(desktop_file, list_file))
                    continue
                log.info("Found desktop file from list: {}".format(list_file))
                with open(df_fp) as df:
                    parsed_df = df_parser.parse(df)
                    if not find_all:
                        return parsed_df
                    parsed_desktop_files.append(parsed_df)

    return parsed_desktop_files if parsed_desktop_files else None


def get_desktop_file_by_search(key_value_pair, find_all=False):
    """Finds desktop file by searching from CONFIG["desktop_file_paths"].

    Desktop file which contains given key value pair is returned. Desktop files
    are returned as DesktopFile objects.

    Parameters:
        key_value_pair: (str, str).
        find_all: TODO:

    Returns:
        DesktopFile() or if find_all==True lists of DesktopFiles.
    """
    log = logging.getLogger(__name__)

    # Next try to find correct desktop file by parsing invidual desktop files
    log.debug("Find desktop file by search with key/value: {}".format(key_value_pair))
    search_key   = key_value_pair[0]
    search_value = key_value_pair[1]
    desktop_files = []
    for dp in CONFIG["desktop_file_paths"]:
        for root, dirs, files in nrwalk(
                dp, filefilter=lambda f,_: not f.endswith(".desktop")):
            for f in files:
                df_name = os.path.join(root, f)
                log.debug("Parsing df: {}".format(df_name))
                with open(df_name) as df_:
                    try:
                        df = df_parser.parse(df_)
                    except SyntaxError as e:
                        log.debug(str(e))
                        log.error("Parsing desktop file '{}' failed!"
                                .format(df_name))
                        continue
                mt_entry = df.get_entry_key_from_group(entry_key=search_key)
                if mt_entry == None:
                    continue
                    #log.warn("Desktop file '{}' had no {} entry!"
                    #    .format(df_name, search_key))
                    #continue
                if search_value in mt_entry.value:
                    if not find_all:
                        return df
                    else:
                        desktop_files.append(df)

    if find_all and desktop_files:
        return desktop_files
    return None


def get_desktop_file_by_custom_search(target, mime_type, file_name, find_all=False):
    """Searches matching (pseudo) desktop file from given target.

    Target format is following:
    [0]:
        filename extension
        type/subtype
        type/
        /subtype
    [1]:
        desktop file name
        absolute path desktop file name
        shell command
        special command

    Special commands:
        !bashwrap <command>: wraps given <command> with bash. See:
        http://wor.github.io/bash/2013/07/26/start-bash-and-terminal-program.html

    Returns:
        Existing DesktopFile or if find_all=True then list of dynamically
        created DesktopFile objects
        (wor.desktop_file_parser.parser.DesktopFile()).

    Parameters:
        target: [(str,str)]. List of key value pairs from custom search config.
        mime_type: str. Mime type as a string.
        file_name: str.
        find_all: bool.
    """
    log = logging.getLogger(__name__)

    matches = []
    for pattern, value in target:
        # Filename extension matching
        if pattern.find("/") == -1 and file_name.endswith("." + pattern):
            matches.append(value)
            if not find_all:
                break
        # Mimetype end matching
        elif pattern.startswith("/") and mime_type.endswith(pattern):
            matches.append(value)
            if not find_all:
                break
        # Mimetype start matching
        elif pattern.endswith("/") and mime_type.startswith(pattern):
            matches.append(value)
            if not find_all:
                break
        # Full mimetype matching
        elif pattern == mime_type:
            matches.append(value)
            if not find_all:
                break

    # Now we have the match(es).
    # Let's generate desktop files from them.
    desktop_files = []
    for match in matches:
        # Check if a desktop file
        if match.endswith(".desktop"):
            # Allow absolute paths possibly outside defined desktop_file_dirs
            if os.path.isabs(match):
                if not os.path.exists(match):
                    log.error("Desktop file '{}' from a config file mapping did not exist!".format(match))
                    break
                df = match
            # Find from desktop_file_dirs
            else:
                df = get_df_full_path(match)
                if not df:
                    log.error("Failed to find desktop file '{}' from desktop "
                              "file paths in config file mapping!".format(match))
                    break
            with open(df) as df_f:
                parsed_df = df_parser.parse(df_f)
                if not find_all:
                    return parsed_df
                desktop_files.append(parsed_df)
        # Else treat as a exec string
        else:
            # Create new desktop file identified by given exec string (match).
            # As desktop file name is used to determine their sameness when
            # grouping them, this ensures that generated desktop files are
            # grouped right.
            parsed_df = df_parser.DesktopFile(file_name="Generated Desktop File: " + match)
            field_check_re = re.compile(r'%[uf]', re.IGNORECASE)
            default_field = "%F"
            # Special !bashwrap command
            # bash wrapped programs are expected to be run inside a terminal
            if match.startswith("!bashwrap"):
                cmd = match[len("!bashwrap") + 1:]
                if not field_check_re.search(cmd):
                    cmd += " " + default_field
                # For now we create default desktop file entry, exec string is
                # added later as is cmd expanded. This happens because we set
                # bashwrap_cmd variable for the desktop file.
                parsed_df.setup_with([("Terminal", True), ("Exec", "bashwrap placeholder")])
                parsed_df.bashwrap_cmd = cmd
            else:
                if not field_check_re.search(match):
                    exec_str = match + " " + default_field
                parsed_df.setup_with([("Exec", exec_str)])
            if not find_all:
                return parsed_df
            desktop_files.append(parsed_df)

    return desktop_files


def get_desktop_file(key_value_pair, file_name, print_found=False):
    """Finds desktop file by key value pair.

    TODO: Memory cache values per run. Now can be run multiple times for same
          type of key/value/file_name
    TODO: Support cached desktop file format.

    Finds desktop file which matches given key_value_pair. First from list files
    and then by systematic desktop file search.

    For example if given key_value_pair is ("Categories","TerminalEmulator"), then
    a desktop file which contains "TerminalEmulator" value in "Categories" key is
    returned.

    The first desktop file found is returned.

    Parameters:
        key_value_pair: (str, str).
        file_name: str. File name to be opened. Some searches need this.
        print_found: bool. Print found desktop files and don't stop when first
            is found.
    """
    log = logging.getLogger(__name__)
    def update_search_results(df, found_desktop_files):
        assert(isinstance(df, list))
        if df_temp:
            if not print_found:
                df.append(df_temp)
                return True
            else:
                df += df_temp
                for d in df_temp:
                    found_desktop_files.append(d.file_name + " [" + search + "]" + os.linesep)
        return False

    df = []
    found_desktop_files = [] # list of strings
    # Do desktop file searchs in given order (config file)
    for search in CONFIG["search_order"]:
        if search == "list_files":
            log.debug("Running list_files search.")
            # If MimeType key then search first from MimeType/Desktop file list files.
            # Configuration option list files must also be specified for this.
            if key_value_pair[0] == "MimeType" and CONFIG["list_files"]:
                df_temp = get_desktop_file_from_mime_list(
                        key_value_pair[1],
                        CONFIG["list_files"],
                        find_all=print_found)
                if update_search_results(df, found_desktop_files):
                    break
        elif search == "desktop_file_paths":
            log.debug("Running desktop_file_paths search.")
            df_temp = get_desktop_file_by_search(key_value_pair, find_all=print_found)
            if update_search_results(df, found_desktop_files):
                break
        elif search in CONFIG["custom_searchs"].keys():
            log.debug("Running custom config search ({}): {}".format(key_value_pair, search))
            if key_value_pair[0] == "MimeType":
                df_temp = get_desktop_file_by_custom_search(
                        CONFIG["custom_searchs"][search],
                        key_value_pair[1],
                        file_name,
                        find_all=print_found)
                if update_search_results(df, found_desktop_files):
                    break

    if print_found:
        print("Found desktop files:")
        print("".join(found_desktop_files))

    return df[0] if df else None


def get_prepared_exec_str(purl, purls):
    """Expands field (%x) variables in Exec strings.

    Replaces Exec string fields (%x) and wraps with terminal emulator
    command if terminal True.

    All given URLs are expected to have same desktop file.

    Paramters:
        purl: URL. Parsed url, Exec string is got from associated desktop file.
        purls: [URL]. List of parsed urls. Used for expanding '%F' and '%U'
            fields. First parameter purl should be included in this list.
    """
    log = logging.getLogger(__name__)
    def expand_fields(string):
        """Expands or removes field variables from the given string.
        """
        # Fill fields
        # TODO: '%' char escaping is not considered yet
        # http://standards.freedesktop.org/desktop-entry-spec/latest/ar01s06.html

        # First remove/ignore deprecated
        string = string.replace('%d', "")
        string = string.replace('%D', "")
        string = string.replace('%n', "")
        string = string.replace('%N', "")
        string = string.replace('%v', "")
        string = string.replace('%m', "")

        string = string.replace('%f', shlex.quote(purl.get_target()))
        string = string.replace('%u', shlex.quote(purl.get_url()))

        string = string.replace('%F', " ".join(
                [ shlex.quote(_purl.get_target()) for _purl in purls]))
        string = string.replace('%U', " ".join(
                [ shlex.quote(_purl.get_url()) for _purl in purls]))

        icon_value = purl.desktop_file.get_entry_value_from_group("Icon")
        string = string.replace('%i',
                icon_value if icon_value != None else "")

        # Replace locale dependent name
        if string.find("%c") != -1:
            loc = locale.getlocale()[0]
            name = purl.desktop_file.get_entry_value_from_group(
                    "Name[{}]".format(loc))
            if name == None:
                name = purl.desktop_file.get_entry_value_from_group(
                        "Name[{}]".format(loc.partition("_")[0]))
            if name == None:
                string = string.replace('%c', "")
            else:
                string = string.replace('%c', shlex.quote(name))

        # TODO: file name in URI form if not local (vholder?)
        string = string.replace(
                '%k', shlex.quote(purl.desktop_file.file_name))
        return string

    if purl.desktop_file.bashwrap_cmd:
        # Expand bashwrap command and create a custom bashrc with it
        cmd = expand_fields(purl.desktop_file.bashwrap_cmd)
        rc_file = tempfile.NamedTemporaryFile(mode='a+b', delete=False)

        # Let's add orginal bashrc file if it exits
        try:
            with open(os.path.expanduser("~/.bashrc"), "r") as org_rc_file:
                rc_file.write(org_rc_file.read().encode("ascii"))
        except IOError:
            pass

        # rm is used in the custom bashrc to delete it self
        rm_path = "/usr/bin/rm"
        if not which("rm_path"):
            rm_path = which("rm")

        additional = """export PROMPT_COMMAND=""" + \
            """'{}; export PROMPT_COMMAND=""'\n{} '{}'\n""".format(
                    cmd, rm_path, rc_file.name)
        rc_file.write(additional.encode("ascii"))
        rc_file.flush()
        exec_str = "bash --rcfile " + rc_file.name + " -i"
    else:
        exec_str = purl.desktop_file.get_entry_value_from_group("Exec")
        exec_str = expand_fields(exec_str)

    # Finally do terminal wrapping if needed
    if purl.desktop_file.get_entry_value_from_group("Terminal"):
        log.info("wrapping exec string with terminal emulator call.")
        if CONFIG["default_terminal_emulator"]:
            exec_str = CONFIG["default_terminal_emulator"] + \
                    " -e " + exec_str
        else:
            # If not default terminal emulator specified in the config file
            # then try to find a terminal emulator from desktop files.
            log.debug("Trying to find the terminal emulator from desktop files.")
            terminal_df = get_desktop_file(("Categories", "TerminalEmulator"), file_name=None)
            if terminal_df:
                exec_str = terminal_df.get_entry_value_from_group("Exec") + \
                        " -e " + exec_str
            else:
                # Just try xterm if no TerminalEmulator desktop file found
                log.warn("Could not find terminal emulator .desktop file:"
                        " defaulting to xterm")
                exec_str = "xterm -e " + exec_str
    return exec_str


def run_exec(purls, dryrun=False):
    """Evaluates/Runs desktop files Exec value.

    http://standards.freedesktop.org/desktop-entry-spec/desktop-entry-spec-latest.html#exec-variables

    TODO:
        Should be escaped inside double quotes, double quote character, backtick
        character ("`"), dollar sign ("$") and backslash character ("\")

    Parameters:
        purls. [URL]. List of URLs with same desktop file.
        dryrun. bool. If True Don't actually evaluate anything.
    """
    log = logging.getLogger(__name__)

    # XXX: Debug assert, condition for this function is that all desktop files
    # attached to given URLs are the same.
    for url in purls:
        assert(url.desktop_file.file_name == purls[0].desktop_file.file_name)

    exec_str = purls[0].desktop_file.get_entry_value_from_group("Exec")
    exec_strs = []
    log.info("run_exec: {}".format(exec_str))

    # If we have %f or %u and length(purls) > 1, then do multiple exec calls
    if len(purls) > 1:
        # If bashwrap_cmd then it contains the to-be-expanded field variables
        if purls[0].desktop_file.bashwrap_cmd:
            check_string = purls[0].desktop_file.bashwrap_cmd
        else:
            check_string = exec_str
        if check_string.find('%f') != -1 or check_string.find('%u') != -1:
            for purl in purls:
                exec_strs.append(get_prepared_exec_str(purl, purls))
        else:
            exec_strs.append(get_prepared_exec_str(purls[0], purls))
    else:
        exec_strs.append(get_prepared_exec_str(purls[0], purls))

    log.info("Final exec string(s): {}".format(repr(exec_strs)))
    for es in exec_strs:
        log.info("Calling exec string: {}".format(es))
        if not dryrun:
            subprocess.Popen(es, shell=True)


def xdg_open(urls=None, dryrun=False, print_found=False):
    """Find and use found program to open given URLs.

    Tries to find desktop object associated with given url and evaluate it's
    exec value.

    Parameters:
        urls: list[str]. URLs to open as list of strings.
        dryrun: bool. Don't actually evaluate exec value/command. Useful for
            testing with high verbosity level.
        print_found: bool. Print found desktop files and don't stop when first
            is found.

    Returns:
        int. 0 if everything ok nonzero value if not.
    """
    log = logging.getLogger(__name__)
    def group_purls(purls):
        """Groups purls with same desktop_file together.

        The sameness is determined by desktop files name.

        Returns:
            [[URL]].
        """
        purls.sort(key=lambda k: k.desktop_file.file_name)
        grouped_purls = []
        group = []
        store = False
        for i in range(0, len(purls)):
            if store:
                store = False
                grouped_purls.append(group)
                group = []
            group.append(purls[i])
            if (i+1 >= len(purls) or
                    purls[i].desktop_file.file_name !=
                        purls[i+1].desktop_file.file_name):
                store = True
        if group:
            grouped_purls.append(group)
        log.debug("Formed {} URL groups.".format(len(grouped_purls)))
        return grouped_purls

    log.info("Got urls: '{}'".format(urls))

    # 1. Create URL objects
    # 2. Find related .desktop files, one per URL object.
    error_opening_url = False
    purls = []
    for url in urls:
        purl = URL(url)
        log.info("'{}' protocol was: '{}'".format(purl.url, purl.protocol))
        log.info("'{}' target was: '{}'".format(purl.url, purl.target))
        log.info("'{}' mime type was: '{}'".format(purl.url, purl.mime_type))

        if purl.mime_type:
            # Find .desktop file handling the URLs mime_type
            log.info(CONFIG["desktop_file_paths"])
            desktop_file = get_desktop_file(
                    ("MimeType", purl.mime_type),
                    file_name=purl.target,
                    print_found=print_found)
            if not desktop_file:
                log.error("Could not find .desktop file"
                        " associated with mime type '{}'"
                        .format(purl.mime_type))
                error_opening_url = True
                continue
        else:
            log.error("Could not get mime type for the given url: '{}'"
                    .format(purl.url))
            error_opening_url = True
            continue
        purl.desktop_file = desktop_file
        log.info("Found desktop file '{}'".format(desktop_file.file_name))
        #log.debug(str(desktop_file))
        purls.append(purl)

    # Group URLs with same desktop_file
    grouped_purls = group_purls(purls)
    log.debug("Grouped purls: {}".format(str(grouped_purls)))

    # TODO: Are there any other possible actions, beside running exec?
    # Run exec should have all URLs with same desktop_file
    for purls in grouped_purls: # for every group / list of purls
        run_exec(purls, dryrun=dryrun)

    return 0 if not error_opening_url else 1


def nrwalk(top, mindepth=0, maxdepth=sys.maxsize,
         dirfilter=None, filefilter=None,
         topdown=True, onerror=None, followlinks=False):
    """Non-recursive directory tree generator.

    This is from pyworlib python utility lib, Copyright (C) Esa Määttä 2011,
    license GPL3.

    Resembles os.walk() with additional min/max depth pruning and additional
    dirfilter and filefilter functions.

    Dir and file filter functions take two arguments, first is the dir/file and
    the second is the root directory where the dir/file is located.

    Yields a 3-tuple as does os.walk(): dirpath, dirnames, filenames

    Parameters:
        top: str.
        mindepth: int. Minimum depth of descent into subdirs.
        maxdepth: int. Maximum depth of descent into subdirs.
        dirfilter: bool func(str, str). If returns True for a dir then the dir
            is filtered away.
        filefilter: bool func(str, str). If returns True for a file then the
            file is filtered away. Receives filename and root path as
            parameters.
        topdown: bool. See os.walk().
        onerror: func. See os.walk().
        followlinks: bool. See os.walk().
    """
    def process_dir(root):
        try:
            names = os.listdir(root)
        except os.error as err:
            if onerror is not None:
                onerror(err)
            return [], []

        dirs, nondirs = [], []
        for name in names:
            if isdir(join(root, name)):
                dirs.append(name)
            else:
                nondirs.append(name)

        # Filter nondirs with filefilter and dirs with dirfilter, if filter
        # returns True for a file # then the file is filtered away
        if dirfilter:
            dirs = [ x for x in dirs if not dirfilter(x, root) ]
        if filefilter:
            nondirs = [ x for x in nondirs if not filefilter(x, root) ]

        return dirs, nondirs

    islink, join, isdir = os.path.islink, os.path.join, os.path.isdir

    Dir_node = namedtuple('Dir_node', [ 'root', 'dirs', 'nondirs' ])
    travelsal_stack = list()
    travelsal_stack.append(Dir_node(top, *process_dir(top)))
    if maxdepth >= len(travelsal_stack)-1 >= mindepth:
        yield travelsal_stack[0]
    while True:
        if not travelsal_stack:
            break

        # TODO: implement followlinks option
        if travelsal_stack[len(travelsal_stack)-1].dirs and \
                maxdepth >= len(travelsal_stack):
            _new_root = join(travelsal_stack[len(travelsal_stack)-1].root,
                    travelsal_stack[len(travelsal_stack)-1].dirs.pop())
            travelsal_stack.append(Dir_node(_new_root, *process_dir(_new_root)))
            if len(travelsal_stack)-1 >= mindepth:
                yield travelsal_stack[len(travelsal_stack)-1]
        else:
            travelsal_stack.pop()

    return


def parse_comma_sep_list(csl_str):
    """Parses comma separated list string to a list.

    Parameters:
        cls_str: str. Comma separated list as a string.
    """
    sl = csl_str.split(",")
    sl = [ os.path.expanduser(s.strip()) for s in sl ]
    return sl


def process_cmd_line(inputs=sys.argv[1:], parent_parsers=list(),
        namespace=None):
    """Processes command line arguments.

    Returns a namespace with all arguments.

    Parameters:
        inputs: list. List of arguments to be parsed.
        parent_parsers: list. List of parent parsers which are used as base.
        namespace: namespace. Namespace where parsed options are added. Can be
            an existing class for example.
    """
    import argparse
    class Verbose_action(argparse.Action):
        """Argparse action: Cumulative verbose switch '-v' counter"""
        def __call__(self, parser, namespace, values, option_string=None):
            """Values can be None, "v", "vv", "vvv" or [0-9]+
            """
            if values is None:
                verbosity_level = 1
            elif values.isdigit():
                verbosity_level = int(values)
            else: # [v]+
                v_count = values.count('v')
                if v_count != len(values):
                    raise argparse.ArgumentError(self, 
                            "Invalid parameter given for verbose: '{}'"
                            .format(values))
                verbosity_level = v_count+1

            # Append to previous verbosity level, this allows multiple "-v"
            # switches to be cumulatively counted.
            org_verbosity = getattr(namespace, self.dest)
            verbosity_level += 0 if org_verbosity == None else org_verbosity
            setattr(namespace, self.dest, verbosity_level)
    class Quiet_action(argparse.Action):
        """Argparse action: Cumulative quiet switch '-q' counter"""
        def __call__(self, parser, namespace, values, option_string=None):
            """Values can be None, "q", "qq", "qqq" or [0-9]+
            """
            if values is None:
                verbosity_level = 1
            elif values.isdigit():
                verbosity_level = int(values)
            else: # [q]+
                q_count = values.count('q')
                if q_count != len(values):
                    raise argparse.ArgumentError(self,
                            "Invalid parameter given for quiet: '{}'"
                            .format(values))
                verbosity_level = q_count+1

            # Append to previous verbosity level, this allows multiple "-q"
            # switches to be cumulatively counted.
            org_verbosity = getattr(namespace, self.dest)
            if org_verbosity == None:
                org_verbosity = 0
            verbosity_level = org_verbosity - verbosity_level
            setattr(namespace, self.dest, verbosity_level)
    class Print_default_config_action(argparse.Action):
        """Argparse action: print default config and exit."""
        def __call__(self, parser, namespace, values=None, option_string=None):
            sep = " = "
            for k in DEFAULT_CONFIG.keys():
                print(k + sep, end="")
                if DEFAULT_CONFIG[k].find(", ") != -1:
                    csl = parse_comma_sep_list(DEFAULT_CONFIG[k])
                    print(csl[0] + ",")
                    for i in range(1,len(csl)):
                        print((len(k) + len(sep))*" " + csl[i], end="")
                        if i < len(csl)-1:
                            print(",", end="")
                        print()
                else:
                    print(DEFAULT_CONFIG[k])
            argparse.ArgumentParser.exit(0)

    # initialize the parser object:
    parser = argparse.ArgumentParser(
            parents = parent_parsers,
            formatter_class = argparse.ArgumentDefaultsHelpFormatter,
            description = "xdg-open (from xdg-utils) replacement.")

    parser.add_argument(
        '-v',
        nargs='?',
        default=None,
        action=Verbose_action,
        dest='verbose',
        help="Verbosity level specifier.")

    parser.add_argument(
        '-q',
        nargs='?',
        action=Quiet_action,
        dest='verbose',
        help="Be more quiet, negatively affects verbosity level.")

    parser.add_argument(
        '-c', '--config-file',
        type=str,
        default="~/.config/pyxdg-open/pyxdg-open.conf",
        help="Config file to be used.")

    parser.add_argument(
        '--dryrun',
        default=False,
        action='store_true',
        help="Don't evaluate final exec value.")

    parser.add_argument(
        '--print-found',
        default=False,
        action='store_true',
        help="Print ALL found desktop files.")

    parser.add_argument(
        '--print-default-config',
        nargs=0,
        default=argparse.SUPPRESS,
        action=Print_default_config_action,
        help="Print default config used and exit.")

    parser.add_argument(
        'urls',
        nargs='+',
        metavar='URL',
        help='Positional argument.')

    return parser.parse_args(inputs)


def read_config_options(config_file_path):
    """Reads config file options and returns them as dict.

    Parameters:
        config_file_path: str. Path of a config file to be opened and parsed.

    Returns:
        dict. A mapping from option name to option value.
    """
    def headerless_config_file(config_file):
        """Generator which wraps config_file and gives DEFAULT section header as
        the first line.

        Parameters:
            config_file: file like object. Open config file.
        """
        # As DEFAULT is included in all other sections when reading
        # items/options add empty DEFAULT section and use BASE as base config
        # section.
        yield "[DEFAULT]\n"
        yield "[" + base_config_name + "]\n"
        # Next yield the actual config file next
        for line in config_file:
            yield line
    def store_opt(opts, opt_name, proc_func=None):
        """Store options to opts.

        DEFAULT_CONFIG provides default config used as fallback.
        """
        opt = config.get(base_config_name, opt_name, fallback=DEFAULT_CONFIG[opt_name])
        opts[opt_name] = opt if not proc_func else proc_func(opt)
    base_config_name = "BASE43rfdf03jjdf"

    config = configparser.ConfigParser()

    config_file_path = os.path.expanduser(config_file_path)

    # Parse config file to the config
    if os.path.exists(config_file_path):
        with open(config_file_path) as cf:
            config.read_file(headerless_config_file(cf),
                    source=config_file_path)

    # Read options from config to options_dict
    options_dict = {}
    store_opt(options_dict, "list_files", parse_comma_sep_list)
    store_opt(options_dict, "desktop_file_paths", parse_comma_sep_list)
    store_opt(options_dict, "default_terminal_emulator")
    store_opt(options_dict, "search_order", parse_comma_sep_list)

    # Read custom searchs from config file
    options_dict["custom_searchs"] = {}
    for section in config.sections():
        if section == base_config_name:
            continue
        options_dict["custom_searchs"][section] = config.items(section=section)

    return options_dict


def main():
    """
    Main entry to the program when used from command line. Registers default
    signals and processes command line arguments from sys.argv.
    """
    import signal
    import wor.utils

    def term_sig_handler(signum, frame):
        """Handles terminating signal."""
        print()
        sys.exit(1)

    signal.signal(signal.SIGINT, term_sig_handler) # for ctrl+c

    args = process_cmd_line()

    # Set verbose level, prefer verbosity set on command line over
    # XDG_UTILS_DEBUG_LEVEL environment variable.
    if args.verbose == None:
        xdg_utils_dl = os.getenv("XDG_UTILS_DEBUG_LEVEL")
        if xdg_utils_dl != None and xdg_utils_dl.isnumeric():
            args.verbose = int(xdg_utils_dl)
        else:
            args.verbose = 0

    # Init module level logger with given verbosity level
    lformat = '%(levelname)s:%(funcName)s:%(lineno)s: %(message)s'
    logging.basicConfig(
            level=wor.utils.convert_int_to_logging_level(args.verbose),
            format=lformat)

    global CONFIG
    CONFIG = read_config_options(args.config_file)

    del args.config_file
    del args.verbose

    # Init mimetypes
    global MM
    global MT
    if HAS_MAGIC:
        MM = magic.open(magic.MIME_TYPE)
        MM.load()
    MT.init()

    return xdg_open(**args.__dict__)
