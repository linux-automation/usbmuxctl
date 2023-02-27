#!/usr/bin/env python3

import fastentrypoints

from setuptools import setup

setup(
    include_package_data=True,
    name="usbmuxctl",
    version="0.1.3",
    author="Chris Fiege",
    author_email="python@pengutronix.de",
    license="LGPL-2.1-or-later",
    url="https://github.com/linux-automation/usbmuxctl",
    description="Tool to control an USB-Mux from the command line",
    packages=[
        "usbmuxctl",
        "usbmuxctl.firmware",
    ],
    install_requires=[
        "pyusb",
        "termcolor",
    ],
    entry_points={
        "console_scripts": [
            "usbmuxctl = usbmuxctl.__main__:main",
        ],
    },
    classifiers=["License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)"],
)
