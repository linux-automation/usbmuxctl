Welcome to usbmuxctl
====================

|license|
|pypi|

Purpose
-------

This is the control software for the Linux Automation GmbH USB-Mux. This repository contains
a standalone command line application and a python module, both of which may be used to
control USB-Muxes on Linux.

USB-Muxes contain an USB Hub, high speed analog switches, power switches and a microcontroller
for control. USB-Muxes enable the automated testing of embedded USB devices by
allowing the connection of a USB device to a DUT (device under test) without requiring
physical access.

The USB-Mux hardware and software is usually used with `Labgrid <https://github.com/labgrid-project/labgrid>`_,
but can also be made to fit your workflow by using it standalone or in a custom application.

Functional overview
-------------------

``usbmuxctl`` provides the following sub-commands:

* ``usbmuxctl list`` - Get a list of available USB-Muxes
* ``usbmuxctl status`` - Get the current status of a particular USB-Mux
* ``usbmuxctl update`` - Perform firmware upgrades
* ``usbmuxctl disconnect`` - Tear down all USB connections to the DUT and Device ports
* ``usbmuxctl connect`` - Create a connection between USB ports. Possible connections are:

  * ``--dut-device`` - Connect the DUT (e.g. a single board computer) to the Device port (e.g. an USB flash drive)
  * ``--host-dut`` - Connect the Host (e.g. a PC running ``usbmuxctl``) to the DUT (acting as an USB device)
  * ``--host-device`` - Connect the Host to the Device port

* ``usbmuxctl id`` - Set the status of the DUT's ``id`` pin used for USB OTG negotiation

Possible example use cases are:

* Testing the hot-plug reliability by toggling between ``usbmuxctl disconnect``
  and ``usbmuxctl connect --dut-device``.
* Testing USB-based firmware upgrades by sharing a flash drive using ``usbmuxctl --host-device``
  and ``usbmuxctl --dut-device``.
* Testing USB OTG functionality using ``usbmuxctl --dut-device`` (DUT in the USB host role)
  and ``usbmuxctl --host-dut`` (DUT in the USB device role).

Quickstart
----------

You can install usbmuxctl either directly from git or from pypi.
If you just want to give the tool a spin you should use the `pypi`-method.

Install from git
~~~~~~~~~~~~~~~~

Clone this repository and create a virtualenv for usbmuxctl:

.. code-block:: bash

   $ git clone https://github.com/linux-automation/usbmuxctl.git
   $ cd usbmuxctl
   $ python3 -m venv venv
   $ source venv/bin/activate

Install usbmuxctl into the virtualenv:

.. code-block:: bash

   $ pip3 install .

You can now continue to test your installation using the help command.

Install from pypi
~~~~~~~~~~~~~~~~~

Create and activate a virtualenv for usbmuxctl:

.. code-block:: bash

   $ python3 -m venv venv
   $ source venv/bin/activate

Install usbmuxctl into the virtualenv:

.. code-block:: bash

   $ pip3 install usbmuxctl

Test your installation
~~~~~~~~~~~~~~~~~~~~~~

You can now run ``usbmuxctl -h`` to get a list of available sub-commands:

.. code-block:: bash

   $ usbmuxctl -h
   usage: usbmuxctl [-h] [--serial SERIAL] [--path PATH] [--json | --raw] {list,status,update,
   disconnect,connect,id,dfu} ...

   USB-Mux control

   positional arguments:
     {list,status,update,disconnect,connect,id,dfu}
                           Supply one of the following commands to interact with the USB-Mux
       list                Lists all connected USB-Mux
       status              Get the status of a USB-Mux
       update              Update software on the USB-Mux
       disconnect          Clear all connections between the ports of the USB-Mux
       connect             Make connections between the ports of the USB-Mux
       id                  Set the state of the ID-Pin to the DUT
       dfu                 Send the USB-Mux into the USB-Bootloader mode.

   optional arguments:
     -h, --help            show this help message and exit
     --serial SERIAL       Serial number of the USB-Mux
     --path PATH           path to the USB-Mux
     --json                Format output as json. Useful for scripting.
     --raw                 Format output as raw info. Useful for command line scripting.

Using as root
~~~~~~~~~~~~~

To communicate with the USB-Muxes ``usbmuxctl`` needs permissions to access the
USB-connected microcontroller. The section below describes the correct way to
grant these permissions to your user.

To rule out issues with the configuration of these permissions for the initial test
you can run ``usbmuxctl`` as root by using ``sudo`` and a path to the
``usbmuxctl`` file inside the previously set up virtualenv [1]_:

.. code-block:: text

   $ sudo venv/bin/usbmuxctl list
   Serial      | USB-Path           | Host-DUT Lock? | Connections
   ----------- | ------------------ | -------------- | -----------
   22          | 1-3.1              | unlocked       | None

   $ sudo venv/bin/usbmuxctl --serial 22 connect --host-device
                                        +-----------------------+
                                        | USB-Mux               |
                                     +--|                       |
                                     |  | SN:   22              |
                                     |  | Path: 1-3.1           |
                                     |  +-----------------------+
          VCC: 4.95V    +---------+  |
   Host |>--------------|       1 |--+         ID: High
                        |         |           VCC: 0.00V
                        |       2 |----x    ------------|> DUT
                        |         |
                        |       3 |---------------------|> Device
                        +---------+           VCC: 4.62V


.. [1] The ``sudo`` command discards most environment variables when executing commands,
       making it incompatible with the usual virtual env workflow.

Using as non-root user
~~~~~~~~~~~~~~~~~~~~~~

To use ``usbmuxctl`` as non-root user you should use an ``udev`` rule to grant access
to the USB-Mux device to your user.
An example rule for Debian and Debian based distributions (like Ubuntu or Mint) [2]_
is included in the ``contrib/udev`` folder of this repository.
The content of this rule file should be placed in a file in the
``/etc/udev/rules.d/`` directory. An example installation, including the reloading of
``udev`` rules is shown below:

.. code-block:: text

   $ echo 'ATTRS{idVendor}=="33f7", ATTRS{idProduct}=="0001", TAG+="uaccess", GROUP="plugdev"' \
    | sudo tee /etc/udev/rules.d/99-usbmux.rules
   $ sudo udevadm control --reload-rules

After reattaching the USB-Mux you should be able to able to use it without
requiring ``sudo`` permissions.

.. [2] The ``plugdev`` group may not be present in your Linux distribution of choice.
       Please adapt the rule according to the groups provided by your distribution.


Contributing
------------

Thank you for considering a contribution to this project!
Changes should be submitted via a
`Github pull request <https://github.com/linux-automation/usbmuxctl/pulls>`_.

This project uses the `Developer's Certificate of Origin 1.1
<https://developercertificate.org/>`_ with the same `process
<https://www.kernel.org/doc/html/latest/process/submitting-patches.html#sign-your-work-the-developer-s-certificate-of-origin>`_
as used for the Linux kernel:

  Developer's Certificate of Origin 1.1

  By making a contribution to this project, I certify that:

  (a) The contribution was created in whole or in part by me and I
      have the right to submit it under the open source license
      indicated in the file; or

  (b) The contribution is based upon previous work that, to the best
      of my knowledge, is covered under an appropriate open source
      license and I have the right under that license to submit that
      work with modifications, whether created in whole or in part
      by me, under the same open source license (unless I am
      permitted to submit under a different license), as indicated
      in the file; or

  (c) The contribution was provided directly to me by some other
      person who certified (a), (b) or (c) and I have not modified
      it.

  (d) I understand and agree that this project and the contribution
      are public and that a record of the contribution (including all
      personal information I submit with it, including my sign-off) is
      maintained indefinitely and may be redistributed consistent with
      this project or the open source license(s) involved.

Then you just add a line (using ``git commit -s``) saying:

  Signed-off-by: Random J Developer <random@developer.example.org>

using your real name (sorry, no pseudonyms or anonymous contributions).

.. |license| image:: https://img.shields.io/badge/license-LGPLv2.1-blue.svg
    :alt: LGPLv2.1
    :target: https://raw.githubusercontent.com/linux-automation/usbmuxctl/master/COPYING

.. |pypi| image:: https://img.shields.io/pypi/v/usbmuxctl.svg
    :alt: pypi.org
    :target: https://pypi.org/project/usbmuxctl
