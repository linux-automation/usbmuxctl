#!/usr/bin/env python3

import usb.core
from time import sleep


class UmuxNotFound(Exception):
    pass

class NoPriviliges(Exception):
    pass

class Mux():
    GET_STATUS = 0
    SET_POWER = 1
    SET_DATA = 2
    SET_OTG  = 3
    DFU = 42
    VERSION = 255

    VENDOR_ID = 0x5824
    PRODUCT_ID = 0x27dd

    ADC_RANGE = (1<<16)-1
    ADC_SCALE = 3.3*3
    LINKS = {0: "None", 1: "Device-Host", 2: "DUT-Host", 3: "DUT-Host Device-Host", 4: "DUT-Device"}

    @staticmethod
    def find_devices():
        devices = usb.core.find(
            find_all=True,
            idVendor=Mux.VENDOR_ID,
            idProduct=Mux.PRODUCT_ID)
        found = []
        for dev in devices:
            path = ".".join([str(i) for i in dev.port_numbers])
            path = "{}-{}".format(dev.bus, path)
            found.append({
                "serial": dev.serial_number,
                "path": path,
            })
        return found

    def __init__(self, serial_number=None, path=None):
        def find_filter(dev):
            if not serial_number is None:
                return dev.serial_number == serial_number
            if not path is None:
                dev_path = ".".join([str(i) for i in dev.port_numbers])
                dev_path = "{}-{}".format(dev.bus, dev_path)
                return dev_path == path
            return True
        self._dev = usb.core.find(idVendor=Mux.VENDOR_ID, idProduct=Mux.PRODUCT_ID, custom_match=find_filter)

        if self._dev is None:
            raise UmuxNotFound()

        try:
            hardware = self._dev.product
        except ValueError as e:
            raise NoPriviliges("Could not communicate with USB-device. Check privileges, maybe add udev-rule")

    def _send_cmd(self, cmd, arg=0):
        data = self._dev.ctrl_transfer((1<<7) | (2<<5) | 0,     0xff, cmd, arg, 10)
        return data

    def _parse_return(self, pkg):
        if len(pkg) != 8:
            raise Exception("Invalied Package length")

        path = ".".join([str(i) for i in self._dev.port_numbers])
        path = "{}-{}".format(self._dev.bus, path)
        state = {
            "voltage_host": \
                (pkg[0]<<8 | pkg[1]) * Mux.ADC_SCALE / Mux.ADC_RANGE,
            "voltage_device": \
                (pkg[2]<<8 | pkg[3]) * Mux.ADC_SCALE / Mux.ADC_RANGE,
            "voltage_dut": \
                (pkg[4]<<8 | pkg[5]) * Mux.ADC_SCALE / Mux.ADC_RANGE,
            "dut_power_lockout": \
                (pkg[6] & 1) != 0,
            "dut_otg_output": \
                (pkg[6] & 2) != 0,
            "dut_otg_input": \
                (pkg[7] & 128) != 0,
            "power_links": \
                Mux.LINKS[ (pkg[6]>>2)&0b111 ],
            "data_links": \
                Mux.LINKS[ (pkg[6]>>5)&0b111 ],
            "device": {
                "usb_path": path,
                "serial_number": self._dev.serial_number,
                "product_name": self._dev.product,
            },
        }
        return state

    def _connect_power(self, num):
        if 4 <= num <= 0:
            raise Exception("{} is not a valid power connection id".format(num))
        data = self._send_cmd(self.SET_POWER, num)
        return self._parse_return(data)

    def _connect_data(self, num):
        if 4 <= num <= 0:
            raise Exception("{} is not a valid data connection id".format(num))
        data = self._send_cmd(self.SET_DATA, num)
        return self._parse_return(data)

    def pull_otg_id_low(self, state):
        if state == True:
            id_state = 1
        elif state == False:
            id_state = 0
        else:
            raise Exception("{} is not a valid data for otg_id".format(state))
        data = self._send_cmd(self.SET_OTG, id_state)
        return self._parse_return(data)

    def get_status(self):
        data = self._send_cmd(self.GET_STATUS)
        return self._parse_return(data)

    def enter_dfu(self):
        self._connect_power(0)
        self._connect_data(0)

        sleep(0.1)
        try:
            self._send_cmd(self.DFU)
        except usb.core.USBError:
            pass

    def connect(self, links, id_pull_low = None):
        num = None
        for key, value in Mux.LINKS.items():
            if value == links:
                num = key
        if num is None:
            raise Exception("Invalid connection {}".format(links))

        self._connect_power(0)
        self._connect_data(0)
        if not id_pull_low == None:
            self.pull_otg_id_low(False)

        sleep(0.5) # Gives switches time to settle and devices to power off

        self._connect_power(num)
        self._connect_data(num)
        if not id_pull_low == None:
            self.pull_otg_id_low(id_pull_low)

        sleep(0.3) # Wait a little moment for switches to settle

    def __str__(self):
        path = ".".join([str(i) for i in self._dev.port_numbers])
        path = "{}-{}".format(self._dev.bus, path)
        path = "Connected to:\n- ID:   {}\n- Path: {}\n- Name: {}".format(self._dev.serial_number, path, self._dev.product)
        return path

