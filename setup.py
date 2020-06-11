#!/usr/bin/env python3

import fastentrypoints

from setuptools import setup

setup(
    name="usbmux",
    version="0.1.0",
    author="Chris Fiege",
    author_email="python@pengutronix.de",
    license="LGPL-2.1-or-later",
    url="FIXME",
    description="Tool to control an USB-Mux from the command line",
    packages=['usbmuxctl'],
    entry_points={
        'console_scripts': [
            'usbmux = usbmuxctl.__main__:main',
        ],
    },
    classifiers=[
        "License :: OSI Approved :: GNU Lesser General Public License v2.1 or later (LGPLv2.1+)"
    ]
)
