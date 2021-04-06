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
