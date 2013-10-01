# -*- coding: utf-8 -*- vim:fenc=utf-8:ft=python:et:sw=4:ts=4:sts=4
from setuptools import setup, find_packages
import sys
import os

here = os.path.abspath(os.path.dirname(__file__))

README = open(os.path.join(here, 'README.rst')).read() if os.path.exists("README.rst") else ""
NEWS = open(os.path.join(here, 'NEWS.rst')).read() if os.path.exists("NEWS.rst") else ""

version = '0.1'

filt_args = []
exec_name="pyxdg-open"
for i, arg in enumerate(sys.argv):
    if arg.startswith("--exec_name="):
        exec_name=arg[len("--exec_name="):]
        sys.argv.pop(i)
        break

console_scripts = [
        # example entry point in wor/__init__.py:main
        # 'wor=wor:main'
        #'tokenize-desktop-file=wor.desktop_file_parser.desktop_file_parser:main',
        '{}=wor.xdg_open:main'.format(exec_name),
        ]

# Remove console scripts if "--no-console_scripts" option given
if "--no-console-scripts" in sys.argv[1:]:
    console_scripts = []
    sys.argv.remove("--no-console-scripts")


install_requires = [
    # List your project dependencies here.
    # For more details, see:
    # http://packages.python.org/distribute/setuptools.html#declaring-dependencies
    'desktop_file_parser',
    'python-magic',
]


setup(name='pyxdg-open',
    version=version,
    description="xdg-open python clone.",
    long_description=README + '\n\n' + NEWS,
    # Get classifiers from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[c.strip() for c in """
         Development Status :: 4 - Beta
         License :: OSI Approved :: GNU General Public License (GPL)
         Operating System :: OS Independent
         Programming Language :: Python :: 2.7
         Programming Language :: Python :: 3
         Topic :: Software Development :: Libraries :: Python Modules
         """.split('\n') if c.strip()],
    keywords='python library desktop',
    author='Esa Määttä',
    author_email='wor@iki.fi',
    url='http://github.com/wor/pyxdg-open',
    license='GPL3',
    packages=find_packages('src'),
    package_dir = {'': 'src'},include_package_data=True,
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
