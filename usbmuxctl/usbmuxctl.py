#!/usr/bin/env python3

import usb.core
from time import sleep


class UmuxNotFound(Exception):
    pass

class NoPriviliges(Exception):
    pass

class Mux():
    """
    This class implements a driver for a USB-Mux device.
    """

    # USB-Commands
    _GET_STATUS = 0
    _SET_POWER = 1
    _SET_DATA = 2
    _SET_OTG  = 3
    _DFU = 42
    _VERSION = 255

    # Be aware: This is a fake VendorID/Product/ID and not meant for production!
    _VENDOR_ID = 0x5824
    _PRODUCT_ID = 0x27dd

    # ADC calibration data
    ADC_RANGE = (1<<16)-1
    ADC_SCALE = 3.3*3

    # Possible Links that can be set by the USB-Mux on power and data links
    # The values of this dict are used for the connect() method.
    _LINKS = {0: "None", 1: "Device-Host", 2: "DUT-Host", 3: "DUT-Host Device-Host", 4: "DUT-Device"}

    @staticmethod
    def find_devices():
        """
        Searches for a list of USB-Mux devices.

        Returns a list of all found devices:
        [{"serial": <SN>, "path": <UsbPath>}, ...]
        """
        devices = usb.core.find(
            find_all=True,
            idVendor=Mux._VENDOR_ID,
            idProduct=Mux._PRODUCT_ID)
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
        """
        Create a new Mux instance.

        Selects the device by the given serial_numer or USB path.
        Both values can be obtained using Mux.find_devices().
        If both are given serial_number has priority over path.
        If neither is given the first found USB-Mux will be used.
        """
        def find_filter(dev):
            if not serial_number is None:
                return dev.serial_number == serial_number
            if not path is None:
                dev_path = ".".join([str(i) for i in dev.port_numbers])
                dev_path = "{}-{}".format(dev.bus, dev_path)
                return dev_path == path
            return True
        self._dev = usb.core.find(idVendor=Mux._VENDOR_ID, idProduct=Mux._PRODUCT_ID, custom_match=find_filter)

        if self._dev is None:
            raise UmuxNotFound()

        try:
            _ = self._dev.product
        except ValueError as e:
            raise NoPriviliges("Could not communicate with USB-device. Check privileges, maybe add udev-rule")

    def _send_cmd(self, cmd, arg=0):
        """
        Sends a low level USB control transfer to the device.
        """
        data = self._dev.ctrl_transfer((1<<7) | (2<<5) | 0,     0xff, cmd, arg, 10)
        return data

    def _parse_return(self, pkg):
        """
        Parses the status returned by most USB commands.

        Returns a dict with the available information on the hardware.
        """
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
                Mux._LINKS[ (pkg[6]>>2)&0b111 ],
            "data_links": \
                Mux._LINKS[ (pkg[6]>>5)&0b111 ],
            "device": {
                "usb_path": path,
                "serial_number": self._dev.serial_number,
                "product_name": self._dev.product,
            },
        }
        return state

    def _connect_power(self, num):
        """
        Applies a connection for the power links on the USB-Mux.
        num must be one of Mux._LINKS.

        If the Host-DUT link is locked in hardware this command will
        still succeed, but this link will not be set. The state returned
        will reflect this.

        Return the bytefiled received by the USB-Mux.
        This can be parsed using self._parse_return()
        """
        if 4 <= num <= 0:
            raise Exception("{} is not a valid power connection id".format(num))
        data = self._send_cmd(self._SET_POWER, num)
        return self._parse_return(data)

    def _connect_data(self, num):
        """
        Applies a connection for the data links on the USB-Mux.
        num must be one of Mux._LINKS.

        If the Host-DUT link is locked in hardware this command will
        still succeed, but this link will not be set. The state returned
        will reflect this.

        Return the bytefiled received by the USB-Mux.
        This can be parsed using self._parse_return()
        """
        if 4 <= num <= 0:
            raise Exception("{} is not a valid data connection id".format(num))
        data = self._send_cmd(self._SET_DATA, num)
        return self._parse_return(data)

    def pull_otg_id_low(self, state):
        """
        Sets the state of the ID pin on the DUT port.

        If state is True: Pulls ID pin low
        If state if False: Leave ID pin floating, a 100k Pull Up is active

        Returns a dict with the state reported by the hardware.
        """
        if state == True:
            id_state = 1
        elif state == False:
            id_state = 0
        else:
            raise Exception("{} is not a valid data for otg_id".format(state))
        data = self._send_cmd(self._SET_OTG, id_state)
        return self._parse_return(data)

    def get_status(self):
        """
        Queries the state of the USB-Mux.

        Returns a dict with the state reported by the hardware.
        """
        data = self._send_cmd(self._GET_STATUS)
        return self._parse_return(data)

    def enter_dfu(self):
        """
        Disconnects all Links and resets the CPU into the DFU-Mude.
        DFU-Mode is provided by the ROM Code.
        This mode is used to transfer firmware onto the device.

        To resume normal operation the USB-Mux must be either reset
        using the DFU-Mode or power cycled.
        """
        self._connect_power(0)
        self._connect_data(0)

        sleep(0.1)
        try:
            self._send_cmd(self._DFU)
        except usb.core.USBError:
            pass

    def connect(self, links, id_pull_low = None):
        """
        Applies a connection between ports of the USB-Mux.

        Before switching to a new connection all current connections
        are being removed and this methods gives the USB-Mux about 0.5 s to settle.
        This will cycle the power to all connected USB devices.
        Afterwards the new links are being connected.

        links must be one of MUX._LINKS.

        id_pull_low affects the ID pin on the DUT port:
        if id_pull_low is None: The ID pin is not altered at all. Use
                                 pull_otg_low() to set the ID pin independent
                                 of the USB links.
        if id_pull_low is True: The ID pin is set floating when the previous connections
                                are being disconnected. The ID pin will be pulled low before
                                the new links are being connected.
        if id_pull_low is False: The ID pin is set floating when the previous connections
                                 are being disconnected. The ID pin will be left floating
                                 when the new links are being connected.
        """
        num = None
        for key, value in Mux._LINKS.items():
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

