#!/usr/bin/env python3

# SPDX-License-Identifier: LGPL-2.1-or-later

# Copyright (C) 2021 Pengutronix, Chris Fiege <entwicklung@pengutronix.de>
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

import argparse
import errno
from .usbmuxctl import Mux, UmuxNotFound, NoPriviliges
import json
import sys
import termcolor
import usb.core
from .update import DfuUtilFailedError, DfuUtilNotFoundError

class ConnectionNotPossible(Exception):
    pass

artwork = {}
artwork["DUT-Host Device-Host"] = """                                     +-----------------------+
                                     | USB-Mux               |
                                  +--|                       |
                                  |  | SN:   {:11s}     |
                                  |  | Path: {:16s}|
                                  |  +-----------------------+
       VCC: {:1.2f}V    +---------+  |
Host |>--------------|       1 |--+         ID: {}
                     |         |           VCC: {:1.2f}V
                     |  {:6} |---------------------|> DUT
                     |         |
                     |       3 |---------------------|> Device
                     +---------+           VCC: {:1.2f}V"""

artwork["None"] = """                                     +-----------------------+
                                     | USB-Mux               |
                                  +--|                       |
                                  |  | SN:   {:11s}     |
                                  |  | Path: {:16s}|
                                  |  +-----------------------+
       VCC: {:1.2f}V    +---------+  |
Host |>--------------|       1 |--+         ID: {}
                     |         |           VCC: {:1.2f}V
                     |  {:6} |----x    ------------|> DUT
                     |         |
                     |       3 |----x    ------------|> Device
                     +---------+           VCC: {:1.2f}V"""

artwork["DUT-Host"] = """                                     +-----------------------+
                                     | USB-Mux               |
                                  +--|                       |
                                  |  | SN:   {:11s}     |
                                  |  | Path: {:16s}|
                                  |  +-----------------------+
       VCC: {:1.2f}V    +---------+  |
Host |>--------------|       1 |--+         ID: {}
                     |         |           VCC: {:1.2f}V
                     |  {:6} |---------------------|> DUT
                     |         |
                     |       3 |----x    ------------|> Device
                     +---------+           VCC: {:1.2f}V"""

artwork["Device-Host"] = """                                     +-----------------------+
                                     | USB-Mux               |
                                  +--|                       |
                                  |  | SN:   {:11s}     |
                                  |  | Path: {:16s}|
                                  |  +-----------------------+
       VCC: {:1.2f}V    +---------+  |
Host |>--------------|       1 |--+         ID: {}
                     |         |           VCC: {:1.2f}V
                     |  {:6} |----x    ------------|> DUT
                     |         |
                     |       3 |---------------------|> Device
                     +---------+           VCC: {:1.2f}V"""


artwork["DUT-Device"] = """                                     +-----------------------+
                                     | USB-Mux               |
                                  +--|                       |
                                  |  | SN:   {:11s}     |
                                  |  | Path: {:16s}|
                                  |  +-----------------------+
       VCC: {:1.2f}V    +---------+  |
Host |>--------------|       1 |--+         ID: {}
                     |         |           VCC: {:1.2f}V
                     |  {:6} |----x    +-----------|> DUT
                     |         |         |
                     |       3 |----x    +-----------|> Device
                     +---------+           VCC: {:1.2f}V"""

raw_status_annotations={
    "data_links": "List of active links of USB data lines",
    "device": "The device this status message is printed for",
    "dut_otg_input": "Measured level on the ID pin on the DUT port",
    "dut_otg_output": "State of the open-drain MOSFET on the ID pin on the DUT port",
    "dut_power_lockout": "State of the 'Lock' switch on the USB-Mux",
    "power_links": "List of active links of USB power lines",
    "voltage_device": "Measured voltage on the device port",
    "voltage_dut": "Measured voltage on the DUT port",
    "voltage_host": "Measured voltage on the host port",
}

def _error_and_exit(error_message, rc=1):
    print(
        termcolor.colored(error_message, "red"),
        file=sys.stderr,
    )
    exit(rc)


def _ui_messages(status):
    """
    Generates a list of messages that should be displayed.
    """

    messages_list = []
    if not status["device"]["sw_up_to_date"]:
        messages_list.append("Software update for USB-Mux available")
    if status["voltage_host"] < 4.5:
        messages_list.append(
            termcolor.colored(
                "WARN: Host USB voltage is very low ({:0.1f}V)!".format(status["voltage_host"]),
                "red", attrs=['reverse']
            )
        )
    if status["voltage_host"] > 5.3:
        messages_list.append(
            termcolor.colored(
                "WARN: Host USB voltage is very high ({:0.1f}V)!".format(status["voltage_host"]),
                "red", attrs=['reverse']
            )
        )
    if status["voltage_dut"] > 5.3:
        messages_list.append(
            termcolor.colored(
                "WARN: DUT USB voltage is very high ({:0.1f}V)!".format(status["voltage_host"]),
                "red", attrs=['reverse']
            )
        )
    messages = " ".join(messages_list)
    return messages

def list_usb(args):
    if args.json:
        res = {
            "command": "list",
            "list": Mux.find_devices(),
            "error": False,
        }
        print(json.dumps(res))
    else:
        print("Serial      | USB-Path           | Host-DUT Lock? | Connections")
        print("----------- | ------------------ | -------------- | -----------")
        for d in Mux.find_devices():
            mux = Mux(path=d["path"])
            status = mux.get_status()
            if status["data_links"] == "":
                connections = "None"
            else:
                connections = status["data_links"]
            lock = "locked" if status["dut_power_lockout"] == True else "unlocked"

            messages = _ui_messages(status)
            print("{:11} | {:18} | {:14} | {:14} {}".format(
                d["serial"],
                d["path"],
                lock,
                connections,
                messages,
            ))


def show_status(status, raw=False):
    if raw:
        for k,v in sorted(status.items()):
            if k in raw_status_annotations:
                print("# {}".format(raw_status_annotations[k]))
            print("{}: {}".format(k,v))
            print()
    else:
        print(artwork[status["data_links"]].format(
            status["device"]["serial_number"],
            status["device"]["usb_path"],
            status["voltage_host"],
            "High" if status["dut_otg_input"] else "Low",
            status["voltage_dut"],
            "LOCKED" if status["dut_power_lockout"] else "     2",
            status["voltage_device"],
        ))
        messages = _ui_messages(status)
        print(messages)

def find_umux(args):
    mux = Mux(serial_number=args.serial, path=args.path)
    return mux

def status(args):
    result = {
        "command": "status",
        "error": False,
    }
    try:
        mux = find_umux(args)
        status = mux.get_status()
        result["status"] = status
    except UmuxNotFound as e:
        result["error"] = True
        result["errormessage"] = "Failed to find the defined USB-Mux"

    if args.json:
        print(json.dumps(result))
    else:
        if result["error"]:
            _error_and_exit("Failed to connect to device: {}".format(result["errormessage"]))
        else:
            show_status(result["status"], args.raw)

def disconnect(args):
    result = {
        "command": "disconnect",
        "error": False,
    }
    try:
        mux = find_umux(args)
        id_pull_low = None if args.no_id else False

        mux.connect("None", id_pull_low)

        result["status"] = mux.get_status()
    except UmuxNotFound as e:
        result["error"] = True
        result["errormessage"] = "Failed to find the defined USB-Mux"
    except ConnectionNotPossible as e:
        result["error"] = True
        result["errormessage"] = str(e)

    if args.json:
        print(json.dumps(result))
    else:
        if result["error"]:
            _error_and_exit("Failed to set connection: {}".format(result["errormessage"]))
        else:
            show_status(result["status"], args.raw)

def connect(args):
    result = {
        "command": "connect",
        "error": False,
    }
    try:
        mux = find_umux(args)
        state = mux.get_status()
        links = []
        id_pull_low = False
        if args.host_dut:
            links.append("DUT-Host")
            if state["dut_power_lockout"] == True:
                raise ConnectionNotPossible(
                    "DUT-to-host connection is locked in hardware. "+\
                    "Refusing to set connection. "+\
                    "Maybe set 'Lock' switch in the other position?")
        if args.host_device:
            links.append("Device-Host")
        if args.dut_device:
            links.append("DUT-Device")
            id_pull_low = True

        if len(links) == 0:
            links = ["None"]

        if args.no_id:
            id_pull_low = None
        mux.connect(" ".join(links), id_pull_low)

        result["status"] = mux.get_status()
    except UmuxNotFound as e:
        result["error"] = True
        result["errormessage"] = "Failed to find the defined USB-Mux"
    except ConnectionNotPossible as e:
        result["error"] = True
        result["errormessage"] = str(e)

    if args.json:
        print(json.dumps(result))
    else:
        if result["error"]:
            _error_and_exit("Failed to set connection: {}".format(result["errormessage"]))
        else:
            show_status(result["status"], args.raw)

def id(args):
    result = {
        "command": "id",
        "error": False,
    }
    try:
        mux = find_umux(args)

        if args.float:
            state = False
        if args.pull_low:
            state = True

        mux.pull_otg_id_low(state)

        result["status"] = mux.get_status()
    except UmuxNotFound as e:
        result["error"] = True
        result["errormessage"] = "Failed to find the defined USB-Mux"

    if args.json:
        print(json.dumps(result))
    else:
        if result["error"]:
            _error_and_exit("Failed to connect to device: {}".format(result["errormessage"]))
        else:
            show_status(result["status"], args.raw)

def dfu(args):
    result = {
        "command": "dfu",
        "error": False,
    }
    try:
        mux = find_umux(args)
        mux.enter_dfu()
    except UmuxNotFound as e:
        result["error"] = True
        result["errormessage"] = "Failed to find the defined USB-Mux"

    if args.json:
        print(json.dumps(result))
    else:
        if result["error"]:
            _error_and_exit("Failed to connect to device: {}".format(result["errormessage"]))
        else:
            print("OK")

def software_update(args):
    result = {
        "command": "software_update",
        "error": False,
    }

    # Make sure there is a USB-Mux selected
    if args.serial is None and args.path is None:
        result["error"] = True
        result["errormessage"] = "No serial number or path"
    else:
        try:
            mux = find_umux(args)
            mux.update_software()
        except UmuxNotFound as e:
            result["error"] = True
            result["errormessage"] = "Failed to connect to device: Failed to find the defined USB-Mux"
        except DfuUtilNotFoundError:
            result["error"] = True
            result["errormessage"] = "Could not find tool 'dfu-util'. Please install using your package manager and re-run this command."
        except DfuUtilFailedError as e:
            result["error"] = True
            result["errormessage"] = "'dfu-util' failed: '{}'. Please check the log above for hints how to fix this.".format(e)
        except usb.core.USBError as err:
            if err.errno == errno.EACCES:
                result["error"] = True
                result["errormessage"] = "'dfu-util' failed. This probably happend because of " +\
                                        "insufficient permissions: {} ".format(err) +\
                                        "Disconnect and reconnect the USB-Mux."
            else:
                result["error"] = True
                result["errormessage"] = "Unhandled USBError: {}".format(err)

    if args.json:
        print(json.dumps(result))
    else:
        if result["error"]:
            _error_and_exit(result["errormessage"])
        else:
            print("OK")

def main():
    parser = argparse.ArgumentParser(description='USB-Mux control')
    parser.add_argument('--serial',
                       help='Serial number of the USB-Mux')
    parser.add_argument('--path',
                       help='path to the USB-Mux')
    format_parser = parser.add_mutually_exclusive_group()
    format_parser.add_argument('--json',
                        help="Format output as json. Useful for scripting.",
                        action="store_true")
    format_parser.add_argument('--raw',
                               help="Format output as raw info. Useful for command line scripting.",
                               action="store_true")

    subparsers = parser.add_subparsers(help='Supply one of the following commands to interact with the USB-Mux')
    subparsers.required = True
    subparsers.dest = 'command'

    # list subcommand
    parser_list = subparsers.add_parser('list', help='Lists all connected USB-Mux')
    parser_list.set_defaults(func=list_usb)

    # status subcommand
    parser_status = subparsers.add_parser('status', help='Get the status of a USB-Mux')
    parser_status.set_defaults(func=status)

    # update subcommand
    parser_update = subparsers.add_parser('update', help='Update software on the USB-Mux')
    parser_update.set_defaults(func=software_update)

    # disconnect/connect subcommands and arguments
    parser_disconnect = subparsers.add_parser('disconnect', help='Clear all connections between the ports of the USB-Mux')
    parser_disconnect.set_defaults(func=disconnect)

    parser_connect = subparsers.add_parser('connect', help='Make connections between the ports of the USB-Mux')
    parser_connect.set_defaults(func=connect)
    connect_group = parser_connect.add_argument_group()
    connect_group.required = True
    parser_connect.add_argument('--dut-device', help='Connect DUT and Device', action='store_true')
    parser_connect.add_argument('--host-dut', help='Connect Host and DUT', action='store_true')
    parser_connect.add_argument('--host-device', help='Connect Host and Device', action='store_true')

    for subparser in (parser_connect, parser_disconnect):
        subparser.add_argument(
            '--no-id',
            help="Do not change ID pin if DUT-Port is switched. "+\
            "Allows to switch the ID pin independent of the connections.",
            action="store_true",
        )

    # id subcommand and arguments
    parser_id = subparsers.add_parser('id', help='Set the state of the ID-Pin to the DUT')
    parser_id.set_defaults(func=id)

    group_id= parser_id.add_mutually_exclusive_group()
    group_id.required = True
    group_id.add_argument('--float', help='Let the ID-Pin float', action="store_true")
    group_id.add_argument('--pull-low', help='Pull the ID-pin low', action="store_true")

    # DFU subcommand (enter dfu without acutally performing the flashing)
    parser_dfu = subparsers.add_parser('dfu', help='Send the USB-Mux into the USB-Bootloader mode.')
    parser_dfu.set_defaults(func=dfu)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
