#!/usr/bin/env python3
# -*- coding: utf-8 -*- vim:fenc=utf-8:ft=python:et:sw=4:ts=4:sts=4
"""A non-bash xdg-open replacer among many others.

Information about desktop files and xdg-open:
http://standards.freedesktop.org/desktop-entry-spec/latest/
https://wiki.archlinux.org/index.php/Default_Applications
"""

import logging
import locale
import magic
import mimetypes
import shlex
import re
import io
import sys
import os
import os.path
import subprocess
import urllib
import configparser

import wor.desktop_file_parser.parser as df_parser
import wor.tokenizer

from pprint import pprint as pp
from wor.os import nrwalk as walk


# Global config options
CONFIG = {}


class URL(object):
    """Represents xdg-opens input as class."""
    def __init__(self, url, protocol="", target="", mime_type=""):
        """
        Parameters:
            url: str. URL as string.
        """
        self.url = url
        if not protocol or not target:
            p, t = self.__get_protocol_and_target__(url)
            self.protocol = p if not protocol else protocol
            self.target   = t if not target else target
        else:
            self.protocol = protocol
            self.target = target
        self.mime_type = mime_type
        self.desktop_file = None
    def __repr__(self):
        return "<{}|{}|{}>".format(self.url, self.protocol, self.target)
    def __get_protocol_and_target__(self, url_str):
        """Tries to guess urls protocol.

        Returns:
            (str, str). Tuple of protocol and rest of the url without protocol.
        """
        if url_str.startswith("/"):
            return "file", url_str

        m = re.match(r"([a-z]+)://", url_str, re.I)
        if m:
            protocol = m.groups()[0].lower()
            target = urllib.parse.unquote(url_str[m.span()[1]:])
            return protocol, target
        else:
            # Treat url as relative file
            return "file", os.path.join(os.getcwd(), url_str)
        return (None, None)
    def get_url(self):
        return self.url
    def get_f(self):
        return self.target


def desktop_list_parser(desktop_list_fn, mime_type_find=None):
    """Parses desktop list file (defaults.list for example).

    If mime_type_find is given then return just matching desktop file or None if
    not found. If mime_type_find is not given or evaluates to False then return
    all mime type desktop file pairs as a dict.
    """
    mt_df_re = re.compile(
            r"""
            (^[^[]+)    # mimetype, line doesn't start with [
            =
            (.+)[;]?$   # desktop file, ignore possible ';' at the end
            """, re.I|re.X)
    mime_type_desktop_map = {}
    with open(desktop_list_fn) as f:
        for line in f:
            m = mt_df_re.search(line)
            if not m:
                continue
            mime_type = m.groups()[0]
            desktop_file = m.groups()[1]
            if mime_type_find:
                if mime_type == mime_type_find:
                    return desktop_file
                continue
            else:
                mime_type_desktop_map[mime_type] = desktop_file
    return mime_type_desktop_map if mime_type_desktop_map else None


def get_mimetype(url, protocol):
    """Returns the mime type of given url.
    """
    log = logging.getLogger(__name__)
    if protocol == "file":
        # Strip away file protocol
        url = url.replace("file://", "", 1)
        # url = urllib.unquote(url).decode('utf-8') # for python2?
        url = urllib.parse.unquote(url)

        # If file doesn't exist try to guess its mime type from its extension
        # only.
        if not os.path.exists(url):
            file_ext = os.path.splitext(url)[1]
            if len(file_ext) > 1:
                mimetypes.init()
                try:
                    mime_type = mimetypes.types_map[file_ext]
                except KeyError:
                    log.debug("mimetypes could not determine mimetype from extension: {}".format(file_ext))
                    return None
            else:
                return None
        else:
            log.info("Unescaped file url target: {}".format(url))
            # TODO: if no magic, use call "file -b --mime-type {}" to get mime type
            m = magic.open(magic.MIME_TYPE)
            m.load()
            #m.setflags(ma)
            mime_type = m.file(url)
            m.close()

        # Try to fix mime type for certain file types using file extension
        if mime_type == "application/octet-stream":
            if os.path.splitext(url)[1] == ".chm":
                mime_type = "application/x-chm"
    elif protocol == "magnet":
        mime_type = "application/x-bittorrent"
    else:
        # XXX: Is there better way to determine mime type form protocol?
        mime_type = "x-scheme-handler/" + protocol
        log.info("Defaulted protocol '{}' to mime type: '{}'".format(protocol, mime_type))
    return mime_type

def get_desktop_file_from_mime_list(mime_type):
    """
    Returns:
        DesktopFile().
    """
    def get_full_path(desktop_file):
        # We cannot know where desktop file is found?
        for dp in CONFIG["desktop_file_paths"]:
            test_desktop_file = os.path.join(dp, desktop_file)
            if os.path.isfile(test_desktop_file):
                return test_desktop_file
        return None
    def check_file(list_files):
        """
        Returns:
            str. Desktop file name.
        """
        for lf in list_files:
            p = os.path.join(dp, lf)
            if os.path.exists(p):
                df = desktop_list_parser(p, mime_type)
                if df:
                    return df, p
        return None, ""
    log = logging.getLogger(__name__)

    # First parse desktop file lists, and try to find desktop file there
    for dp in CONFIG["desktop_file_paths"]:
        desktop_file, list_file = check_file(["mimeapps.list", "defaults.list"])
        if desktop_file:
            df_fp = get_full_path(desktop_file)
            if not df_fp:
                log.warn("Could not find desktop file named: {}, mentioned in {}".format(desktop_file, list_file))
                return None
            log.info("Found desktop file from list: {}".format(list_file))
            with open(df_fp) as df:
                return df_parser.parse(df)
    return None

def get_desktop_file_by_search(key_value_pair):
    """Finds desktop file by searching from CONFIG["desktop_file_paths"].

    Desktop file which contains given key value pair is returned. Desktop files
    are returned as DesktopFile objects.

    Returns:
        DesktopFile().
    """
    log = logging.getLogger(__name__)

    # Next try to find correct desktop file by parsing invidual desktop files
    search_key   = key_value_pair[0]
    search_value = key_value_pair[1]
    for dp in CONFIG["desktop_file_paths"]:
        for root, dirs, files in walk(dp, filefilter=lambda f,_: not f.endswith(".desktop")):
            for f in files:
                df_name = os.path.join(root, f)
                log.debug("Parsing df: {}".format(df_name))
                with open(df_name) as df_:
                    try:
                        df = df_parser.parse(df_)
                    except wor.tokenizer.TokenizerException as e:
                        log.debug(str(e))
                        log.error("Parsing desktop file '{}' failed!".format(df_name))
                        continue
                mt_entry = df.get_entry_key_from_group(entry_key=search_key)
                if mt_entry == None:
                    continue
                    #log.warn("Desktop file '{}' had no {} entry!".format(df_name, search_key))
                    #continue
                if search_value in mt_entry.value:
                    return df
    return None


def get_desktop_file(key_value_pair=("","")):
    """Finds desktop file by key value pair.

    TODO: Support cached desktop file format.
    TODO: Document where desktop files are searched for.

    Finds desktop file which matches given key_value_pair.

    For example if given key_value_pair is ("Category","TerminalEmulator"), then
    a desktop file which contains "TerminalEmulator" value in "Category" key is
    returned.

    The first desktop file found is returned.

    Parameters:
        mime_type: str.
        key_value_pair: (str, str).
    """
    log = logging.getLogger(__name__)

    df = None
    if key_value_pair[0] == "MimeType":
        # If MimeType key then search first from MimeType/Desktop file list
        # files
        df = get_desktop_file_from_mime_list(key_value_pair[1])
        if df:
            # TODO: transform to absolute dir if needed
            log.debug("Found df from MimeType/desktop file list.")
            return df

    if not df:
        df = get_desktop_file_by_search(key_value_pair)
        if df:
            log.debug("Found df with desktop file search.")

    return df


def run_exec(purls, shell=True, dryrun=False):
    """Evaluates/Runs desktop files Exec value.

    http://standards.freedesktop.org/desktop-entry-spec/desktop-entry-spec-latest.html#exec-variables

    Should be escaped inside double quotes
        double quote character, backtick character ("`"), dollar sign ("$") and backslash character ("\")

    TODO: shell=False not yet implemented, requires exec value parsing.
    """
    log = logging.getLogger(__name__)
    def get_prepared_exec_str(purl, purls):
        """Replaces exec_str fields (%x) and wraps with terminal emulator
        command if terminal True.
        """
        exec_str = purl.desktop_file.get_entry_value_from_group("Exec")

        # Fill fields
        # TODO: '%' char escaping is not considered yet
        # http://standards.freedesktop.org/desktop-entry-spec/latest/ar01s06.html

        # First remove/ignore deprecated
        exec_str = exec_str.replace('%d', "")
        exec_str = exec_str.replace('%D', "")
        exec_str = exec_str.replace('%n', "")
        exec_str = exec_str.replace('%N', "")
        exec_str = exec_str.replace('%v', "")
        exec_str = exec_str.replace('%m', "")

        exec_str = exec_str.replace('%f', shlex.quote(purl.get_f()))
        exec_str = exec_str.replace('%u', shlex.quote(purl.get_url()))

        exec_str = exec_str.replace('%F', " ".join([ shlex.quote(purl.get_f()) for purl in purls]))
        exec_str = exec_str.replace('%U', " ".join([ shlex.quote(purl.get_url()) for purl in purls]))

        icon_value = purl.desktop_file.get_entry_value_from_group("Icon")
        exec_str = exec_str.replace('%i', icon_value if icon_value != None else "")

        # Replace locale dependent name
        if exec_str.find("%c") != -1:
            loc = locale.getlocale()[0]
            name = purl.desktop_file.get_entry_value_from_group("Name[{}]".format(loc))
            if name == None:
                name = purl.desktop_file.get_entry_value_from_group("Name[{}]".format(loc.partition("_")[0]))
            if name == None:
                exec_str = exec_str.replace('%c', "")
            else:
                exec_str = exec_str.replace('%c', shlex.quote(name))

        # TODO: file name in URI form if not local (vholder?)
        exec_str = exec_str.replace('%k', shlex.quote(purl.desktop_file.file_name))

        if purl.desktop_file.get_entry_value_from_group("Terminal"):
            log.info("wrapping exec string with terminal emulator call.")
            if CONFIG["default_terminal_emulator"]:
                exec_str = CONFIG["default_terminal_emulator"] + " -e " + exec_str
            else:
                # If not default terminal emulator specified in the config file then
                # try to find a terminal emulator from desktop files.
                terminal_df = get_desktop_file(("Category", "TerminalEmulator"))
                if terminal_df:
                    exec_str = terminal_df.get_entry_value_from_group("Exec") + " -e " + exec_str
                else:
                    # Just try xterm if no TerminalEmulator desktop file found
                    log.warn("Could not find terminal emulator .desktop file: defaulting to xterm")
                    exec_str = "xterm -e " + exec_str
        return exec_str

    exec_str = purls[0].desktop_file.get_entry_value_from_group("Exec")
    exec_strs = []
    log.info("run_exec: Shell: {} Exec: {}".format(shell, exec_str))

    # If we have %f or %u and length(purls) > 1, then do multiple exec calls
    if exec_str.find('%f') != 1 and \
            exec_str.find('%u') != 1 and \
            len(purls) > 1:
        for purl in purls:
            exec_strs.append(get_prepared_exec_str(purl, purls))
    else:
        exec_strs.append(get_prepared_exec_str(purls[0], purls))

    log.info("Final exec string(s): {}".format(repr(exec_strs)))
    for es in exec_strs:
        log.info("Calling exec string: {}".format(es))
        if not dryrun:
            subprocess.Popen(es, shell=True)


def xdg_open(urls=None, dryrun=False):
    """
    Tries to find desktop object associated with given url and evaluate it's
    exec value.

    Parameters:
        - url: str. URL to open.
    """
    log = logging.getLogger(__name__)
    def group_purls(purls):
        """Groups purls with same desktop_file together.
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
            if i+1 >= len(purls) or purls[i].desktop_file.file_name != purls[i+1].desktop_file.file_name:
                store = True
        if group:
            grouped_purls.append(group)
        return grouped_purls

    log.info("Got urls: '{}'".format(urls))

    # First create URL objects
    error_opening_url = False
    purls = []
    for url in urls:
        purl = URL(url)
        log.info("'{}' protocol was: '{}'".format(purl.url, purl.protocol))
        log.info("'{}' target was: '{}'".format(purl.url, purl.target))

        # Second find mime type of the url
        purl.mime_type = get_mimetype(purl.url, purl.protocol)
        log.info("'{}' mime type was: '{}'".format(purl.url, purl.mime_type))

        if purl.mime_type:
            # Third find .desktop file handling the mime_type
            log.info(CONFIG["desktop_file_paths"])
            desktop_file = get_desktop_file(("MimeType", purl.mime_type))
            if not desktop_file:
                log.error("Could not find .desktop file associated with mime type '{}'".format(purl.mime_type))
                error_opening_url = True
                continue
        else:
            log.error("Could not get mime type for the given url: '{}'".format(purl.url))
            error_opening_url = True
            continue
        purl.desktop_file = desktop_file
        log.info("Found desktop file '{}'".format(desktop_file.file_name))
        log.info(str(desktop_file))
        purls.append(purl)

    # Group urls with same desktop_file
    grouped_purls = group_purls(purls)

    # TODO: Are there any other possible actions, beside running exec?
    # Run exec should have all urls with same desktop_file
    for purls in grouped_purls: # for every group / list of purls
        run_exec(purls, shell=True, dryrun=dryrun)

    return 0 if not error_opening_url else 1


def process_cmd_line(inputs=sys.argv[1:], parent_parsers=list(), namespace=None):
    """
    Processes command line arguments.

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
                    raise argparse.ArgumentError(self, "Invalid parameter given for verbose: '{}'".format(values))
                verbosity_level = v_count+1

            # Append to previous verbosity level, this allows multiple "-v"
            # switches to be cumulatively counted.
            org_verbosity = getattr(namespace, self.dest)
            verbosity_level += 0 if org_verbosity == None else org_verbosity
            setattr(namespace, self.dest, verbosity_level)
    class Quiet_action(argparse.Action):
        """Argparse action: Cumulative quiet switch '-q' counter"""
        def __call__(self, parser, namespace, values, option_string=None):
            """qalues can be None, "q", "qq", "qqq" or [0-9]+
            """
            if values is None:
                verbosity_level = 1
            elif values.isdigit():
                verbosity_level = int(values)
            else: # [q]+
                q_count = values.count('q')
                if q_count != len(values):
                    raise argparse.ArgumentError(self, "Invalid parameter given for quiet: '{}'".format(values))
                verbosity_level = q_count+1

            # Append to previous verbosity level, this allows multiple "-q"
            # switches to be cumulatively counted.
            org_verbosity = getattr(namespace, self.dest)
            if org_verbosity == None:
                org_verbosity = 0
            verbosity_level = org_verbosity - verbosity_level
            setattr(namespace, self.dest, verbosity_level)

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
        """Generator which wraps config_file and gives DEFAULT section header as the
        first line.

        Parameters:
            config_file: file like object. Open config file.
        """
        yield "[DEFAULT]\n"
        # Next yield the actual config file next
        for line in config_file:
            yield line
    def parse_comma_sep_list(csl_str):
        sl = csl_str.split(",")
        sl = [ os.path.expanduser(s.strip()) for s in sl ]
        return sl
    def store_opt(opts, opt_name, proc_func=None):
        opt = config.get("DEFAULT", opt_name, fallback=defaults[opt_name])
        opts[opt_name] = opt if not proc_func else proc_func(opt)

    config = configparser.ConfigParser()

    # Defaults
    defaults = {
            "desktop_file_paths": "~/.local/share/applications/, /usr/share/applications/, /usr/local/share/applications/",
            "default_terminal_emulator": "",
            }

    # Parse config file
    config_file_path = os.path.expanduser(config_file_path)

    # Overwrite defaults from config file if it exists
    if os.path.exists(config_file_path):
        with open(config_file_path) as cf:
            config.read_file(headerless_config_file(cf), source=config_file_path)

    options_dict = {}
    store_opt(options_dict, "desktop_file_paths", parse_comma_sep_list)
    store_opt(options_dict, "default_terminal_emulator")
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
    logging.basicConfig(level=wor.utils.convert_int_to_logging_level(args.verbose), format=lformat)

    #log = logging.getLogger(__name__)
    #log.info("Verbosity level set at: {}".format(args.verbose))

    global CONFIG
    CONFIG = read_config_options(args.config_file)

    del args.config_file
    del args.verbose

    return xdg_open(**args.__dict__)
