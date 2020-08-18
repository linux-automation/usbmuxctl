#!/usr/bin/env python3

import argparse
from .usbmuxctl import Mux, UmuxNotFound, NoPriviliges
import json

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
            print("{:11} | {:18} | {:14} | {}".format(
                d["serial"],
                d["path"],
                lock,
                connections
            ))

def show_status(status, raw=False):
    if raw:
        for k,v in sorted(status.items()):
            print("{}: {}".format(k,v))
    else:
        print(artwork[status["data_links"]].format(
            status["device"]["serial_number"],
            status["device"]["usb_path"],
            status["voltage_host"],
            status["dut_otg_input"],
            status["voltage_dut"],
            "LOCKED" if status["dut_power_lockout"] else "     2",
            status["voltage_device"],
        ))

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
            print("Failed to connect to device: {}".format(result["errormessage"]))
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

        if len(links) == 0:
            links = ["None"]

        mux.connect(" ".join(links))

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
            print("Failed to set connection: {}".format(result["errormessage"]))
        else:
            show_status(result["status"], args.raw)

def otg(args):
    result = {
        "command": "otg",
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
            print("Failed to connect to device: {}".format(result["errormessage"]))
        else:
            show_status(result["status"], args.raw)

def dfu(args):
    result = {
        "command": "otg",
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
            print("Failed to connect to device: {}".format(result["errormessage"]))
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

    parser_list = subparsers.add_parser('list', help='Lists all connected USB-Mux')
    parser_list.set_defaults(func=list_usb)

    parser_status = subparsers.add_parser('status', help='Get the status of a USB-Mux')
    parser_status.set_defaults(func=status)

    parser_connect = subparsers.add_parser('connect', help='Make connections between the ports of the USB-Mux')
    parser_connect.set_defaults(func=connect)
    connect_group = parser_connect.add_argument_group()
    connect_group.required = True
    parser_connect.add_argument('--dut-device', help='Connect DUT and Device', action='store_true')
    parser_connect.add_argument('--host-dut', help='Connect Host and DUT', action='store_true')
    parser_connect.add_argument('--host-device', help='Connect Host and Device', action='store_true')

    parser_otg = subparsers.add_parser('otg', help='Set the state of the ID-Pin to the DUT')
    parser_otg.set_defaults(func=otg)

    group_otg = parser_otg.add_mutually_exclusive_group()
    group_otg.required = True
    group_otg.add_argument('--float', help='Let the ID-Pin float', action="store_true")
    group_otg.add_argument('--pull-low', help='Pull the ID-pin low', action="store_true")

    parser_dfu = subparsers.add_parser('dfu', help='Send the USB-Mux into the USB-Bootloader mode.')
    parser_dfu.set_defaults(func=dfu)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
