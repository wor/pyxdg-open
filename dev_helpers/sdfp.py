#!/usr/bin/env python3
# -*- coding: utf-8 -*- vim:fenc=utf-8:ft=python:et:sw=4:ts=4:sts=4
"""module docstring"""
__author__ = "Esa Määttä"
__copyright__ = "Copyright 2011, Esa Määttä"
__credits__ = ["Esa Määttä"]
#__license__ = "GPL"
__version__ = "0.0.1"
__maintainer__ = "Esa Määttä"
__email__ = "esa.maatta@iki.fi"
#__status__ = "Production"

import sys
import regex as re
#import os
from collections import OrderedDict
import logging



def parse():
    """
    """
    pass

def df_file_gen(desktop_fn):
    """
    Returns:
        (str,()).
    """
    desktop_f = open(desktop_fn, "r")
    text = desktop_f.read()
    print(text)

    reg = r"""(?P<ENTRY>^(.*)(\[.+\])?=(.*)$\n?)|(?P<COMMENT_LINE>^#(.*)\n)|(?P<EMPTY_LINE>^[ \t\r\f\v]*\n)|(?P<GROUP_HEADER>^\[(.+)\]\s*$\n?)"""
    r = re.compile(reg, re.MULTILINE)

    df_file_gen.groups = OrderedDict(sorted(r.groupindex.items(), key=lambda t: t[1]))

    # Make df_file_gen.groups contain mapping from regex group name to submatch
    # range. Submatch range start-1 is the whole match.
    last_i = None
    for i in df_file_gen.groups.items():
        if last_i == None:
            last_i = i
            continue
        df_file_gen.groups[last_i[0]] = (last_i[1], i[1]-1)
        last_i = i
    df_file_gen.groups[last_i[0]] = (last_i[1], r.groups)

    print(df_file_gen.groups)
    pos = 0
    while True:
        m = r.match(text, pos)
        if not m:
            if pos != len(text):
                return None
            break
        pos = m.end()
        #print(m.groups())
        yield m.lastgroup, m.groups()[ df_file_gen.groups[m.lastgroup][0]:
                df_file_gen.groups[m.lastgroup][1]]

def act(desktop_fn):
    """docstring"""
    #log = logging.getLogger(__name__)

    g = df_file_gen(desktop_fn)
    for s in g:
        print(s)
        #print(s.groups()[df_file_gen.groups[s.lastgroup][0]:df_file_gen.groups[s.lastgroup][1]])
        #print(s.group('ENCODING'))
        #print(s.groups()[s.lastindex:])

    return


def process_cmd_line(inputs=sys.argv[1:], parent_parsers=list(), namespace=None):
    """
    Processes command line arguments.

    Returns a namespace with all arguments.

    Parameters:

    - `inputs`: list. List of arguments to be parsed.
    - `parent_parsers`: list. List of parent parsers which are used as base.
    - `namespace`: namespace. Namespace where parsed options are added. Can be
      an existing class for example.
    """
    import argparse
    import wor.argparse.actions

    # initialize the parser object:
    parser = argparse.ArgumentParser(
            parents = parent_parsers,
            formatter_class = argparse.ArgumentDefaultsHelpFormatter,
            description = "Program description.")

    # define arguments and options here:
    #parser.add_argument(
    #    '-f', '--flag',
    #    action='store_true',
    #    dest='flag', default=False,
    #    help="Flag argument.")

    #parser.add_argument(
    #    '-r', '--regex',
    #    #nargs='+',
    #    type=str,
    #    default=r"\.(jpg|png|jpeg|tiff|tif)",
    #    help="Filename match regex example.")

    parser.add_argument(
        '-v',
        nargs='?',
        default=0,
        action=wor.argparse.actions.Verbose_action,
        dest='verbose',
        help="Verbosity level specifier.")

    parser.add_argument(
        '-q',
        nargs='?',
        action=wor.argparse.actions.Quiet_action,
        dest='verbose',
        help="Be more quiet, negatively affects verbosity level.")

    parser.add_argument(
        'desktop_fn',
        metavar='FILENAME',
        #nargs=1, # If defined then a list is produced
        help='Positional argument.')

    return parser.parse_args(inputs)


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

    # Init module level logger with given verbosity level
    lformat = '%(levelname)s:%(funcName)s:%(lineno)s: %(message)s'
    logging.basicConfig(level=wor.utils.convert_int_to_logging_level(args.verbose), format=lformat)

    del args.verbose

    act(**args.__dict__)

    return 0


if __name__ == '__main__':
    status = main()
    sys.exit(status)
