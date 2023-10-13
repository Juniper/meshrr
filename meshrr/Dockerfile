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

FROM alpine:3.18 as meshrr-prebuild

WORKDIR /opt/meshrr

COPY requirements.txt /opt/meshrr/

RUN apk add --update --no-cache python3 py3-pip openssh \
    && pip3 install -r requirements.txt \
    && mkdir -p /config /secret/ssh

FROM meshrr-prebuild

COPY render_config.py /opt/meshrr/
COPY run.sh /opt/meshrr/
COPY juniper.conf.j2 /opt/meshrr/
COPY update_peers.py /opt/meshrr/

RUN chmod +x /opt/meshrr/run.sh
RUN chmod +x /opt/meshrr/update_peers.py
RUN chmod +x /opt/meshrr/render_config.py

ENTRYPOINT [ "/opt/meshrr/run.sh" ]