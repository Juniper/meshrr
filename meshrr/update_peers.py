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

from os import getenv
from random import randrange

from dns import resolver
from dotenv import load_dotenv
from jnpr.junos import Device
from jnpr.junos.utils.config import Config
from netaddr import IPNetwork, IPAddress, IPSet, cidr_exclude, cidr_merge

load_dotenv(dotenv_path="/etc/envvars")


class ConfigUpdate(Config):
    # Child class to maintain lists of selected peers in managed groups

    def __init__(self, dev, mode=None, **kwargs):
        self.__selected_peers = dict()
        super().__init__(dev, mode, **kwargs)

    def initiate_group(self, group_name, force=False):
        """Initiate the group from live configuration only if it's not inventoried yet. Override with force=True"""
        if group_name not in self.__selected_peers or force:
            # Get the list of neighbors in the group
            filter = f"<configuration><groups><name>MESHRR</name><protocols><bgp><group><name>{group_name}</name><neighbor><name/></neighbor></group></bgp></protocols></groups></configuration>"
            data = dev.rpc.get_config(filter_xml=filter)
            configured_peers = data.xpath(
                f"groups/protocols/bgp/group[name='{group_name}']/neighbor/name/text()"
            )
            self.__selected_peers.update({group_name: configured_peers})
            return True
        else:
            return False

    def get_allowed_peers(self, allowed_base=getenv("MESHRR_CLIENTRANGE")):
        """
        Returns the allowed_base minus any explicitly configured managed peers
        This is required, otherwise configured peers may end up in the wrong group.
        allowed_base is the maximum subnet to allow
        """

        disallowed = IPSet(cu.get_all_selected_peers())
        allowed = [IPNetwork(allowed_base)]
        for disallowed_ip in disallowed:
            for network in allowed:
                if disallowed_ip in network:
                    allowed.remove(network)
                    allowed.extend(cidr_exclude(network, disallowed_ip))
                    break
        allowed = cidr_merge(allowed)
        return allowed

    def commit_peerupdate(self, **kwargs):
        allowed = self.get_allowed_peers()
        allowed_string = " ".join([str(network) for network in allowed])
        self.load(
            f"delete groups MESHRR protocols bgp group MESHRR-CLIENTS allow",
            format="set",
        )
        self.load(
            f"set groups MESHRR protocols bgp group MESHRR-CLIENTS allow [ {allowed_string} ]",
            format="set",
        )
        self.commit()

    def get_selected_peers(self, group_name):
        self.initiate_group(group_name)
        return self.__selected_peers[group_name]

    def get_all_selected_peers(self):
        result = list()
        for group in self.__selected_peers:
            result.extend(self.__selected_peers[group])
        return result

    def add_selected_peer(self, group_name, peer_ip):
        self.initiate_group(group_name)
        self.__selected_peers[group_name].append(peer_ip)
        self.load(
            f"set groups MESHRR protocols bgp group {group_name} neighbor {peer_ip}",
            format="set",
        )

    def remove_selected_peer(self, group_name, peer_ip):
        self.initiate_group(group_name)
        self.__selected_peers[group_name].remove(peer_ip)
        self.load(
            f"delete groups MESHRR protocols bgp group {group_name} neighbor {peer_ip}",
            format="set",
        )


def update_peergroup(cu, group_name, service_name, max_peers=None):
    detected_peers = list()
    try:
        result = resolver.resolve(
            f"{service_name}.{kube_namespace}.{service_root_domain}", "A"
        )
    except (resolver.NXDOMAIN, resolver.NoAnswer) as err:
        print(err.msg, f"- Skipping processing of {group_name}.")
        return cu

    for r in result:
        if r.address != pod_ip:
            detected_peers.append(r.address)

    # Identify peers that should be active after this commit.
    # Currently configured peers that are still detected via DNS are prioritized.
    # Additional peers will be selected at random from detected_peers until `max_peers` are selected.
    configured_peers = cu.get_selected_peers(group_name)
    selected_peers = list()
    for peer_ip in configured_peers:
        if max_peers is None or len(selected_peers) < max_peers:
            if peer_ip in detected_peers:
                selected_peers.append(peer_ip)
                detected_peers.remove(peer_ip)
        else:
            # The peer group is full with selected_peers. No need to continue this loop.
            break
    while len(detected_peers) and (
        max_peers is None or len(selected_peers) < max_peers
    ):
        selected_peers.append(detected_peers.pop(randrange(len(detected_peers))))

    # Compare detected_peers (up-to-date list) with configured_peers.
    # Add detected_peers not in configured_peers.
    # Remove configured_peers not in detected_peers.
    peers_to_add = set(selected_peers) - set(configured_peers)
    for peer_ip in peers_to_add:
        cu.add_selected_peer(group_name, peer_ip)

    peers_to_remove = set(configured_peers) - set(selected_peers)
    for peer_ip in peers_to_remove:
        cu.remove_selected_peer(group_name, peer_ip)
    return cu


if __name__ == "__main__":
    # Load necessary environment variables
    pod_ip = getenv("POD_IP")
    if not pod_ip:
        raise (Exception("POD_IP environment variable not set"))

    mesh_service_name = getenv("MESH_SERVICE_NAME")

    upstream_service_name = getenv("UPSTREAM_SERVICE_NAME")

    if not mesh_service_name and not upstream_service_name:
        raise (
            Exception(
                "MESH_SERVICE_NAME and UPSTREAM_SERVICE_NAME environment variables not set"
            )
        )

    kube_namespace = getenv("KUBE_NAMESPACE", "default")
    service_root_domain = getenv("SERVICE_ROOT_DOMAIN", "svc.cluster.local")

    # Open a connection to the device
    dev = Device()
    dev.open()
    with ConfigUpdate(dev, mode="private") as cu:

        groups = list()
        if mesh_service_name:
            groups.append(
                {
                    "name": "MESHRR-MESH",
                    "service_name": mesh_service_name,
                    "max_peers": None,
                }
            )

        if upstream_service_name:
            groups.append(
                {
                    "name": "MESHRR-UPSTREAM",
                    "service_name": upstream_service_name,
                    "max_peers": 2,
                }
            )

        for group in groups:
            cu = update_peergroup(
                cu,
                group_name=group["name"],
                service_name=group["service_name"],
                max_peers=group["max_peers"],
            )
        if cu.diff():
            cu.commit_peerupdate()
