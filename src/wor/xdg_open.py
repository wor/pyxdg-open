#!/usr/bin/env python3
# -*- coding: utf-8 -*- vim:fenc=utf-8:ft=python:et:sw=4:ts=4:sts=4
"""A non-bash xdg-open replacer among many others.

Information about desktop files and xdg-open:
http://standards.freedesktop.org/desktop-entry-spec/latest/
https://wiki.archlinux.org/index.php/Default_Applications
"""

import logging
import magic
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

        log.info("Unescaped file url target: {}".format(url))
        # TODO: if no magic, use call "file -b --mime-type {}" to get mime type
        m = magic.open(magic.MIME_TYPE)
        m.load()
        mime_type = m.file(url)

        # Try to fix mime type for certain file types using file extension
        if mime_type == "application/octet-stream":
            if os.path.splitext(url)[1] == ".chm":
                mime_type = "application/x-chm"

        m.close()
    else:
        # TODO
        mime_type = None

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


def run_exec(exec_str, purl, terminal=False, shell=True):
    """Evaluates/Runs desktop files Exec value.

    http://standards.freedesktop.org/desktop-entry-spec/desktop-entry-spec-latest.html#exec-variables

    Should be escaped inside double quotes
        double quote character, backtick character ("`"), dollar sign ("$") and backslash character ("\")
    """
    log = logging.getLogger(__name__)
    log.info("run_exec: Shell: {} Exec: {}".format(shell, exec_str))

    # Fill fields
    # TODO: '%' char escaping is not considered yet
    exec_str = exec_str.replace('%f', purl.get_f())
    exec_str = exec_str.replace('%u', purl.get_url())

    # TODO: replace all format fields
    if exec_str.find('%') != -1:
        log.error("TODO: format fields not all replaced: {}".format(exec_str))
        sys.exit(1)

    if terminal:
        terminal_df = get_desktop_file(("Category", "TerminalEmulator"))
        # TODO: configure default terminal
        if not terminal_df:
            log.warn("Could not find terminal emulator .desktop file: defaulting to xterm")
            exec_str = "xterm -e " + exec_str
        else:
            exec_str = terminal_df.get_entry_value_from_group("Exec")

    log.info("Final exec string: {}".format(exec_str))
    subprocess.call(exec_str, shell=True)
    log.info("Called exec string.")


def xdg_open(url=None):
    """
    Tries to find desktop object associated with given url and evaluate it's
    exec value.

    Parameters:
        - url: str. URL to open.
    """
    log = logging.getLogger(__name__)
    log.info("Got url: '{}'".format(url))

    # First create URL object
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
            return 1
    else:
        log.error("Could not get mime type for the given url: '{}'".format(purl.url))
        return 1

    log.info("Found desktop file '{}'".format(desktop_file.file_name))
    log.info(str(desktop_file))

    # TODO: Are there any other possible actions?
    run_exec(desktop_file.get_entry_value_from_group("Exec"),
            purl,
            desktop_file.get_entry_value_from_group("Terminal"))

    return


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
        'url',
        metavar='URL',
        help='Positional argument.')

    return parser.parse_args(inputs)


def read_config_options(config_file_path):
    """
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

    config = configparser.ConfigParser()

    # Defaults
    defaults = {
            "desktop_file_paths": "~/.local/share/applications/, /usr/share/applications/, /usr/local/share/applications/"
            }
    config.read_dict({"DEFAULT": defaults})

    # Parse config file
    config_file_path = os.path.expanduser(config_file_path)

    # Overwrite defaults from config file if it exists
    if os.path.exists(config_file_path):
        with open(config_file_path) as cf:
            config.read_file(headerless_config_file(cf), source=config_file_path)

    options_dict = {}
    options_dict["desktop_file_paths"] = parse_comma_sep_list(config["DEFAULT"]["desktop_file_paths"])
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
