import subprocess
from time import sleep
from .usbmuxctl import Mux
from .usbmuxctl import path_from_usb_dev
import usb.core
from enum import Enum
import struct
import logging
import argparse

try:
    import coloredlogs
    coloredlogs.install()
except:
    pass

# Vendor/product ID for STM32 DFU bootloader
DFU_VENDOR_ID=0x0483
DFU_PRODUCT_ID=0xdf11

DFU_UTIL_CMD = "dfu-util"

class _DFUComand(Enum):
    DFU_DETACH = 0
    DFU_DNLOAD = 1
    DFU_UPLOAD = 2
    DFU_GETSTATUS = 3
    DFU_CLRSTATUS = 4
    DFU_GETSTATE = 5
    DFU_ABORT = 6

class _bStatus(Enum):
    OK = 0x00
    errTARGET = 0x01
    errFILE = 0x02
    errWRITE = 0x03
    errERASE = 0x04
    errCHECK_ERASED = 0x05
    errPROG = 0x06
    errVERIFY = 0x07
    errADDRESS = 0x08
    errNOTDONE = 0x09
    errFIRMWARE = 0x0a
    errVENDOR = 0x0b
    errUSBR = 0x0c
    errPOR = 0x0d
    errUNKNOWN = 0xe
    errSTALLEDPKT = 0x0f

class _bState(Enum):
    appIDLE = 0
    appDETACH = 1
    dfuIDLE = 2
    dfuDNLOAD_SYNC = 3
    dfuDNBUSY = 4
    dfuDNLOAD_IDLE = 5
    dfuMANIFEST_SYNC = 6
    dfuMANIFEST = 7
    dfuMANIFEST_WAIT_RESET = 8
    dfuUPLOAD_IDLE = 9
    dfuERROR = 10


class NoDFUDeviceFound(IOError):
    pass
class ToManyDFUDeviceFound(IOError):
    def __init__(self, paths):
        self.paths = paths


class DFUException(Exception):
    def __init__(self, status):
        self.status = status

class DFU:
    """STM32 DFU implementation
    only to get out of DFU mode"""

    # See RM0091 32.4.1 MCU device ID code
    STM32_DEVICES = {
            0x444: "STM32F03x",
            0x445: "STM32F04x",
            0x440: "STM32F05x",
            0x448: "STM32F07x",
            0x442: "STM32F09x",
            }

    STM32_VERSIONS = {
            0x1000: "1.0",
            0x1001: "1.1",
            0x2000: "2.0",
            0x2001: "2.1",
            }


    def __init__(self, path):
        def find_filter(dev):
            if not path is None:
                dev_path = path_from_usb_dev(dev)
                return dev_path == path
            return True
        dev = usb.core.find(idVendor=DFU_VENDOR_ID, idProduct=DFU_PRODUCT_ID, custom_match=find_filter, find_all=True)

        # Make sure we got one device
        if dev is None:
            raise NoDFUDeviceFound()

        dev = list(dev)
        if len(dev) == 0:
            raise NoDFUDeviceFound()

        if len(dev) > 1:
            paths = []
            for d in dev:
                path = path_from_usb_dev(d)
                paths.append(path)
            raise ToManyDFUDeviceFound(paths)

        self._dev = dev[0]

        self.log = logging.getLogger("DFU")

        self.interface = 0

        self._dev.set_configuration()

    @staticmethod
    def parse_dfu_status(status):
        """Generate a human readable dict from DFU_STATUS response"""
        out = {}
        out["bStatus"] = _bStatus(status[0])
        out["bState"] = _bState(status[4])
        bwPollTimeout = status[1] | (status[2]<<8) | (status[3]<<16)
        out["bwPollTimeout"] = bwPollTimeout
        return out

    

    def get_path(self):
        return path_from_usb_dev(self._dev)

    def _cmd_out(self, cmd, wValue, data=None, bmRequestType=0x21):
        """Host to device"""
        ret = self._dev.ctrl_transfer(
                bmRequestType = bmRequestType, 
                bRequest = cmd.value, 
                wValue = wValue,
                wIndex = self.interface,
                data_or_wLength = data)
        return ret

    def _cmd_in(self, cmd, wValue, data=None, bmRequestType=0xa1):
        """Device to Host"""
        ret = self._dev.ctrl_transfer(
                bmRequestType = bmRequestType, 
                bRequest = cmd.value, 
                wValue = wValue,
                wIndex = self.interface,
                data_or_wLength = data)
        return ret

    def get_status(self):
        """DFU Command
        Get the device status"""
        ret = self._cmd_in(_DFUComand.DFU_GETSTATUS, 0, 6)
        ret = self.parse_dfu_status(ret)
        self.log.debug("get_status: %s", ret)
        return ret

    def check_status(self):
        """Check the status of the DFU device and raises an DFUException if an error is reported"""
        status = self.get_status()
        if status["bStatus"] != _bStatus.OK:
            raise DFUException(status)
        return status

    def clear_status(self):
        """DFU Command
        Clears status and possible error states"""

        self.log.debug("Clear status")
        ret = self._cmd_out(_DFUComand.DFU_CLRSTATUS, 0)
        self.check_status()

    def abort(self):
        """DFU Command
        Abort currently running command"""
        self.log.debug("Abort")
        ret = self._cmd_out(_DFUComand.DFU_ABORT, 0)
        self.check_status()

    def set_address(self, address):
        """DFU Command
        Set the address to read,write,execute"""
        self.log.debug("Set Adress: %x", address)
        ret = self._cmd_out(_DFUComand.DFU_DNLOAD, 0, struct.pack("<BI",0x21, address))
        self.check_status()

    def read_mem(self, length):
        """DFU Command
        Reads length number of bytes from memory.
        The adress is set by the set_address() command."""
        self.log.debug("Reading memory length: %d", length)

        ret = self._cmd_in(_DFUComand.DFU_UPLOAD, 2, length)

        self.log.debug("Data receving: %s", "".join(["{:02X}".format(i) for i in ret]))
        return ret, self.check_status()

    def get_cmd(self):
        """DFU Command
        Requests a list of supportet commands from the DFU device"""
        raise NotImplementedError()

    def write_mem(self):
        """DFU Command
        """
        raise NotImplementedError()

    def erease(self):
        """DFU Command
        """
        raise NotImplementedError()

    def read_unprotect(self):
        """DFU Command
        """
        raise NotImplementedError()


    def leave_dfu(self):
        """DFU Command
        Executes the code at the address set by set_address()"""
        self.log.debug("Leaving DFU mode")

        ret = self._cmd_out(_DFUComand.DFU_DNLOAD, 0, b"")
        status = self.check_status()

        if status["bState"] != _bState.dfuMANIFEST:
            self.log.error("Leave dfu command faild")
            raise DFUException(status)

    def read_at_addr_len(self, addr, length):
        """Reads length number of bytes from address addr from the device"""
        try:
            self.clear_status()
        except:
            self.clear_status()

        self.abort()

        ## Test
        self.set_address(addr)
        self.check_status()
        self.abort()
        self.check_status()
        ret, _ = self.read_mem(length)
        
        self.abort()
        return ret

    def get_uuid(self):
        uuid = self.read_at_addr_len(0x1FFFF7AC, 12)
        uuid = bytearray(uuid)
        
        self.log.debug("Get UUID: %s", uuid.hex())

        return uuid

    def enter_user_code(self):
        """Finds the entry addresse to the user code in flash and executes it"""
        self.log.debug("Entering user code")

        try:
            self.clear_status()
        except:
            self.clear_status()

        self.abort()

        ret = self.read_at_addr_len(0x08000000, 8)
        addr = struct.unpack("I", ret[4:8])[0]
        self.log.debug("Code entry address: %x", addr)

        self.abort()


        self.set_address(addr)

        self.get_status()

        self.leave_dfu()

def dfu_util_flash_firmware(firmware_path, usb_path):
    try:
        res = subprocess.run([DFU_UTIL_CMD, 
            "-d", "0483:df11",
            "-a", "0",
            "-D", firmware_path,
            "-s", "0x8000000",
            "--path", usb_path])
        if res.returncode != 0:
            raise Exception("dfu-util failed with: {}".format(res))
    except FileNotFoundError:
        raise Exception("dfu-util not found. Might not be installed.")

def dfu_util_flash_config(file_path, usb_path):
    try:
        res = subprocess.run([DFU_UTIL_CMD, 
            "-d", "0483:df11",
            "-a", "0",
            "-D", firmware_path,
            "-s", "0x8007c00",
            "--path", usb_path])
        if res.returncode != 0:
            raise Exception("dfu-util failed with: {}".format(res))
    except FileNotFoundError:
        raise Exception("dfu-util not found. Might not be installed.")

def find_dfu_device(search_path):
    try:
        dfu = DFU(path=search_path)
    except ToManyDFUDeviceFound as e:
        print("Found more then one DFU Device.")
        print("Please provide a path to the DFU Device you want to use")
        for path in e.paths:
            print("  * {}".format(path))
        exit(1)

    except NoDFUDeviceFound:
        print("No DFU device found")
        exit(2)

    return dfu

def flash_firmware(args):
    dfu = find_dfu_device(args.path)

    if args.file is None:
        print("No firmware file specified")
        exit(3)

    dfu_util_flash_firmware(args.file, dfu.get_path())
    

def flash_config(args):
    dfu = find_dfu_device(args.path)

    if args.file is None:
        print("No config file specified")
        exit(3)

    dfu_util_flash_config(args.file, dfu.get_path())

def update_firmware(args):
    mux_list = Mux.find_devices()

    if args.file is None:
        print("No config file specified")
        exit(3)

    selected_mux = None
    for mux in mux_list:
        if args.path == mux["path"]:
            selected_mux = mux
            break
        if args.serial_number == mux["serial"]:
            selected_mux = mux
            break

    print("Updating USBMux {} @ {}".format(selected_mux["serial"], selected_mux["path"]))

    path = selected_mux["path"]
    mux = Mux(path=path)
    mux.enter_dfu()
    sleep(1)

    dfu = find_dfu_device(path)

    dfu_util_flash_firmware(args.file, dfu.get_path())

    dfu.enter_user_code()

def leave_dfu(args):
    dfu = find_dfu_device(path)
    dfu.enter_user_code()

if __name__ == "__main__":

    commands = {
            "flash_firmware": flash_firmware,
            "flash_config": flash_config,
            "update": update_firmware,
            "leave_dfu": leave_dfu,
            }

    parser = argparse.ArgumentParser("can_isp.py")
    parser.add_argument(
        "function",
        help="Function to perform",
        choices=commands,
    )
    parser.add_argument(
        "--file",
        "-f",
        help="File to use as flash or config",
    )
    parser.add_argument(
        "--path",
        "-p",
        help="USB Path to USB device (1-4.1)",
    )
    parser.add_argument(
        "--serial",
        "-s",
        help="USBMux serial numer (00001.00020)",
    )
    parser.add_argument(
        "-v",
        help="Be verbose",
        action="store_true",
    )
    args = parser.parse_args()

    commands[args.function](args)

    


