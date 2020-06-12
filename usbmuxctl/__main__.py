#!/usr/bin/env python3

import argparse
from .usbmuxctl import Mux, UmuxNotFound, NoPriviliges
import json

def list_usb(args):
    if args.json:
        res = {
            "command": "list",
            "list": Mux.find_devices(),
            "error": False,
        }
        print(json.dumps(res))
    else:
        print("Serial               | USB-Path")
        print("-------------------- | -----------")
        for d in Mux.find_devices():
            print("{:20} | {}".format(d["serial"], d["path"]))

def show_status(status):
    print("TODO: Pretty-Print state!")
    for k,v in status.items():
        print("{}: {}".format(k,v))

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
            show_status(result["status"])

def connect(args):
    result = {
        "command": "connect",
        "error": False,
    }
    try:
        mux = find_umux(args)
        links = []
        if args.Host_DUT:
            links.append("DUT-Host")
        if args.Host_Device:
            links.append("Device-Host")
        if args.DUT_Device:
            links.append("DUT-Device")

        if len(links) == 0:
            links = ["None"]

        mux.connect(" ".join(links))

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
            show_status(result["status"])

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
            show_status(result["status"])

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
    parser.add_argument('--json',
                        help="Format output as json",
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
    parser_connect.add_argument('--DUT-Device', help='Connect DUT and Device', action='store_true')
    parser_connect.add_argument('--Host-DUT', help='Connect Host and DUT', action='store_true')
    parser_connect.add_argument('--Host-Device', help='Connect Host and Device', action='store_true')

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
