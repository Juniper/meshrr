#!/bin/sh

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

set -e

printenv > /etc/envvars

if [ $# -eq 0 ]; then
	echo "One of the following arguments required: init, sidecar"
	exit 1
elif [ $1 = 'init' ]; then
	echo "Initializing pod"
	# Overwrite with existing configuration if it exists.
	if [ -f "/config/juniper.conf" ]; then
		echo "Existing configuration detected; overwriting pod IP only."
		sed "s/^\(.\+router-id\) [0-9]\+\.[0-9]\+\.[0-9]\+\.[0-9]\+/\1 {{ POD_IP }};/" /config/juniper.conf > conf/juniper.conf.j2
	elif ! test -f conf/juniper.conf.j2; then
		if [[ "$MESHRR_MODE" == 'evpnrs' ]] || [[ "$MESHRR_MODE" == 'routeserver' ]] ; then
			template='juniper-evpnrs.conf.j2'
		elif [[ "$MESHRR_MODE" == 'ipv4rr' ]] || [[ "$MESHRR_MODE" == 'routereflector' ]] || [[ -z $MESHRR_MODE ]]; then
			template='juniper-ipv4rr.conf.j2'
		else 
			echo "Invalid MESHRR_MODE set. Must be empty or one of [ 'evpnrs' 'ipv4rr' ]."
			exit 1
		fi
		echo "Initializing fresh configuration from defaults/${template}."
		cp defaults/${template} conf/juniper.conf.j2
	else # Don't overwrite template since it's been explicitly mounted.
		echo "Custom configuration provided; using conf/juniper.conf.j2 template."
	fi
	# Generate a fresh SSH key and apply to configuration template.
	ssh-keygen -q -t ed25519 -f /secret/ssh/id_ed25519 -P ""
	PUBKEY=`cat \/secret\/ssh\/id_ed25519.pub | tr -d '\r\n'`
	# Cannot overwrite in place as this may be a mounted configmap
	sed "/user meshrr/,/SECRET-DATA/ s~ssh-ed25519.*~ssh-ed25519 \"$PUBKEY\"; ## SECRET-DATA~" conf/juniper.conf.j2 > /config/juniper.conf.j2
	./render_config.py -i /config/juniper.conf.j2 -o /config/juniper.conf
elif [ $1 = 'sidecar' ]; then
	# Wait for cRPD container to become available for netconf.
	./connect_wait.py
	echo "Initializing peer maintenance every ${UPDATE_SECONDS:=30} seconds."
	while true; do
		./update_peers.py
		sleep ${UPDATE_SECONDS}
	done
else
	echo "Invalid argument: $1"
fi


