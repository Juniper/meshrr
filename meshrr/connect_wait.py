#!/usr/bin/env python3

# Copyright (c) Juniper Networks, Inc., 2023. All rights reserved.
#
# Notice and Disclaimer: This code is licensed to you under the MIT License (the
# "License"). You may not use this code except in compliance with the License.
# This code is not an official Juniper product.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Third-Party Code: This code may depend on other components under separate
# copyright notice and license terms. Your use of the source code for those
# components is subject to the terms and conditions of the respective license as
# noted in the Third-Party source code file.

from jnpr.junos import Device
from jnpr.junos.exception import ConnectTimeoutError,ConnectRefusedError
from time import sleep

if __name__ == "__main__":
    # Attempt to open a connection to the device
    dev = Device(host="127.0.0.1",user="meshrr",ssh_private_key_file="/secret/ssh/id_ed25519")
    while True:
        try:
            dev.open()
            break
        except ConnectTimeoutError:
            print("connect_wait.py: Connection timed out; retrying.")
        except ConnectRefusedError:
            print("connect_wait.py: Connection refused; retrying.")
            sleep(1)
    # Create /tmp/connected-to-crpd to inform startup probes
    open("/tmp/connected-to-crpd","x")
    