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

from argparse import ArgumentParser, FileType
from os import getenv
from jinja2 import Template

from config import Meshrrconfig

mconf=Meshrrconfig()

if __name__ == "__main__":

    parser = ArgumentParser(
        description="Render configuration file from env and template"
    )
    parser.add_argument("-i", "--inputfile", type=FileType("r"), required=True)
    parser.add_argument("-o", "--outputfile", type=FileType("w"), required=True)

    args = parser.parse_args()

    template = Template(args.inputfile.read())

    configvars = dict()

    # Populate variables to be used in templates that must come from env
    configvars.update({"LICENSE_KEY": getenv("LICENSE_KEY", None)})
    if not configvars["LICENSE_KEY"]:
        raise (Exception("LICENSE_KEY is not set."))
    configvars.update({"POD_IP": getenv("POD_IP", None)})
    if not configvars["POD_IP"]:
        raise (Exception("POD_IP is not set."))

    # Populate variables to be used in termplates that will come from Meshrrconfig / YAML
    configvars.update({
        "encrypted_root_pw": mconf.encrypted_root_pw,
        "asn": mconf.asn,
        "bgpgroups_mesh": mconf.bgpgroups_mesh,
        "bgpgroups_subtractive": mconf.bgpgroups_subtractive
        })

    crpd_config = template.render(configvars)
    args.outputfile.write(crpd_config)
    args.outputfile.flush()
