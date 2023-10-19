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

import yaml
from yaml import SafeLoader
from os import getenv
from dotenv import load_dotenv
from os.path import isfile

load_dotenv(dotenv_path="/etc/envvars")

class Meshrrconfig:
    def __init__(self):
        if not isfile('/opt/meshrr/conf/meshrr.conf.yml'):
            # Start from default config
            with open('/opt/meshrr/defaults/meshrr.conf.yml') as d:
                c = yaml.load(d,Loader=SafeLoader)

                # Copy in defined environment variables.
                c.update({
                    'encrypted_root_pw': getenv("ENCRYPTED_ROOT_PW", c['encrypted_root_pw']),
                    'asn': getenv("AUTONOMOUS_SYSTEM", c['asn']),
                    'mode': getenv("MESHRR_MODE", c['mode']),
                })

                # Save to live config
                with open('/opt/meshrr/conf/meshrr.conf.yml','w') as w:
                    yaml.dump(c,w)
        with open('/opt/meshrr/conf/meshrr.conf.yml') as f:
            self._config = yaml.load(f,Loader=SafeLoader)
        
        self.encrypted_root_pw = self._config['encrypted_root_pw']
        self.asn = self._config['asn']
        self.mode = self._config['mode']

        self.bgpgroups_mesh = list()
        self.bgpgroups_subtractive = list()
        for group in self._config['bgpgroups']:
            if 'type' not in group or 'name' not in group:
                raise Exception("All bgpgroups require 'type' and 'name' definitions. Offending bgpgroup: "+str(group))
            elif group['type'].casefold() == 'mesh':
                if 'source' not in group:
                    raise Exception("Mesh bgpgroups require 'source.hostname' definitions. Offending bgpgroup: "+str(group))
                self.bgpgroups_mesh.append(group)
            elif group['type'].casefold() == 'subtractive':
                if 'prefixes' not in group:
                    raise(Exception("Subtractive bgpgroups require 'source.hostname' definitions. Offending bgpgroup: "+str(group)))
                self.bgpgroups_subtractive.append(group)
            else:
                raise(Exception("Invalid `type` in bgpgroup: "+str(group)))