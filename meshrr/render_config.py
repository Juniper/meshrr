#!/usr/bin/env python3

# Copyright (c) Juniper Networks, Inc., 2020. All rights reserved.
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

from argparse import ArgumentParser, FileType
from os import getenv

from jinja2 import Template

if __name__ == "__main__":

    parser = ArgumentParser(
        description="Render configuration file from env and template"
    )
    parser.add_argument("-i", "--inputfile", type=FileType("r"), required=True)
    parser.add_argument("-o", "--outputfile", type=FileType("w"), required=True)

    args = parser.parse_args()

    template = Template(args.inputfile.read())

    configvars = dict()
    configvars.update({"ENCRYPTED_ROOT_PW": getenv("ENCRYPTED_ROOT_PW", None)})
    if not configvars["ENCRYPTED_ROOT_PW"]:
        raise (Exception("ENCRYPTED_ROOT_PW is not set."))
    configvars.update({"AUTONOMOUS_SYSTEM": getenv("AUTONOMOUS_SYSTEM", None)})
    if not configvars["AUTONOMOUS_SYSTEM"]:
        raise (Exception("AUTONOMOUS_SYSTEM is not set."))
    configvars.update({"POD_IP": getenv("POD_IP", None)})
    if not configvars["POD_IP"]:
        raise (Exception("POD_IP is not set."))
    configvars.update({"MESHRR_CLIENTRANGE": getenv("MESHRR_CLIENTRANGE", None)})
    if not configvars["MESHRR_CLIENTRANGE"]:
        raise (Exception("MESHRR_CLIENTRANGE is not set."))
    configvars.update({"UPSTREAM_SERVICE_NAME": getenv("UPSTREAM_SERVICE_NAME", None)})

    # Default to Route Reflector Mode
    configvars.update({"MESHRR_MODE": getenv("MESHRR_MODE", "routereflector")})
    # Default AS Range for Route Server mode is 65001 to 65000
    configvars.update({"MESHRR_ASRANGE": getenv("MESHRR_ASRANGE", "65001-65000")})
    # Default to inet unicast only
    configvars.update({"MESHRR_FAMILY_INET": getenv("MESHRR_FAMILY_INET", "true")})
    configvars.update({"MESHRR_FAMILY_EVPN": getenv("MESHRR_FAMILY_EVPN", "false")})

    crpd_config = template.render(configvars)
    args.outputfile.write(crpd_config)
    args.outputfile.flush()
