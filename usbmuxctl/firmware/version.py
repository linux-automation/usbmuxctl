# SPDX-License-Identifier: LGPL-2.1-or-later

# Copyright (C) 2021 Pengutronix, Jonas Martin <entwicklung@pengutronix.de>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

import os

FIRMWARE_DIR = os.path.dirname(__file__)

FIRMWARE_NAME = "umx-T03_0.1.2.bin"

FIRMWARE_VERSION = list([int(i) for i in FIRMWARE_NAME.rsplit("_", 1)[1].rsplit(".", 1)[0].split(".")])

FIRMWARE_FILE = os.path.join(FIRMWARE_DIR, FIRMWARE_NAME)

def version_from_string(string):
    _, version, _ = string.split(" ", 2)
    version = version.split(".")
    version = list([int(i) for i in version])
    return version
