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

FROM crpd:20.3R1.8 as prebuild

WORKDIR /root

COPY requirements.txt /root/

# This blocks cron startup if not changed
RUN printf '#!/bin/sh\nexit 0\n' > /usr/sbin/policy-rc.d

# Install requirements. Note that cron must be reconfigured later to create user.
RUN apt-get update \
    && apt-get -y --no-install-recommends install cron python3-minimal python3-setuptools python3-pip \
    && rm -fr /var/lib/apt/lists/* \
    && pip3 install wheel \
    && pip3 install -r requirements.txt

FROM prebuild

COPY render_config.py /root/
COPY runit-init.sh /sbin/
COPY juniper.conf.j2 /root/
COPY update_peers.py /root/

RUN chmod +x /sbin/runit-init.sh
RUN chmod +x /root/update_peers.py
RUN chmod +x /root/render_config.py

ENTRYPOINT [ "/sbin/runit-init.sh" ]
STOPSIGNAL 35
