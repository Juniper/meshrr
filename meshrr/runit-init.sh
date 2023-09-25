#!/bin/bash

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

set -e

printenv > /etc/envvars

# Overwrite with existing configuration if it exists.
if [ -f "/config/juniper.conf" ]; then
	sed "s/^\(.\+router-id\) [0-9]\+\.[0-9]\+\.[0-9]\+\.[0-9]\+/\1 {{ POD_IP }};/" /config/juniper.conf > juniper.conf.j2
fi

./render_config.py -i juniper.conf.j2 -o /config/juniper.conf

# Install crontab. Expect non-zero status for crontab -l
line="* * * * * /root/update_peers.py >> /var/log/update_peers 2>&1"
set +e

# crontab group doesn't seem to be created in docker build.
dpkg-reconfigure cron
(crontab -l 2>/dev/null; echo "$line" ) | crontab -
set -e

exec /sbin/runit-init 0