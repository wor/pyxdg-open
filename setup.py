# -*- coding: utf-8 -*- vim:fenc=utf-8:ft=python:et:sw=4:ts=4:sts=4
from setuptools import setup, find_packages
from codecs import open # To use a consistent encoding
import sys
import os

here = os.path.abspath(os.path.dirname(__file__))

VERSION = open(os.path.join(here, 'VERSION'), encoding="utf-8").read().strip()
README  = open(os.path.join(here, 'README.rst'), encoding="utf-8").read() if os.path.exists("README.rst") else ""
NEWS    = open(os.path.join(here, 'NEWS.rst'), encoding="utf-8").read() if os.path.exists("NEWS.rst") else ""

author       ='Esa Määttä'
author_email ='esa.maatta@iki.fi'

filt_args = []
exec_name="pyxdg-open"
for i, arg in enumerate(sys.argv):
    if arg.startswith("--exec_name="):
        exec_name=arg[len("--exec_name="):]
        sys.argv.pop(i)
        break

console_scripts = [
        '{}=wor.xdg_open:main'.format(exec_name),
        ]

# Remove console scripts if "--no-console_scripts" option given
if "--no-console-scripts" in sys.argv[1:]:
    console_scripts = []
    sys.argv.remove("--no-console-scripts")


install_requires = [
    'desktop_file_parser',
    'Magic_file_extensions',
]


setup(name='pyxdg-open',
    version=VERSION,
    description="Opens URL or file in user preferred application (xdg-open replacement).",
    long_description=README + '\n\n' + NEWS,
    classifiers=[c.strip() for c in """
         Development Status :: 4 - Beta
         License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)
         Operating System :: POSIX :: Linux
         Programming Language :: Python :: 3
         Topic :: Utilities
         """.split('\n') if c.strip()],
    keywords='python library desktop',
    author=author,
    maintainer=author,
    author_email=author_email,
    url='https://github.com/wor/pyxdg-open',
    license='GPL3',
    packages=find_packages('src'),
    package_dir = {'': 'src'},
    include_package_data=True,
    zip_safe=False,
    # Requirements
    install_requires=install_requires,
    tests_require=['nose'],
    dependency_links = [
            "https://github.com/wor/desktop_file_parser/tarball/master#egg=desktop_file_parser"
            ],
    entry_points={
        'console_scripts': console_scripts
    },
    test_suite='nose.collector',
)
