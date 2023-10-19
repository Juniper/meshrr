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

from os import getenv
from random import randrange

from dns import resolver
from jnpr.junos import Device
from jnpr.junos.utils.config import Config
from netaddr import IPSet

from config import Meshrrconfig

mconf=Meshrrconfig()

# Load necessary environment variables
pod_ip = getenv("POD_IP")
if not pod_ip:
    raise (Exception("POD_IP environment variable not set"))

class ConfigUpdate(Config):
    # Child class to maintain lists of selected peers in managed groups

    def __init__(self, device, mode=None, **kwargs):
        self.__selected_peers = dict()
        super().__init__(device, mode, **kwargs)

    def initiate_group(self, group_name, force=False):
        """Initiate the group from live configuration only if it's not inventoried yet. Override with force=True"""
        if group_name not in self.__selected_peers or force:
            # Get the list of neighbors in the group
            xmlfilter = f"<configuration><groups><name>MESHRR</name><protocols><bgp><group><name>{group_name}</name><neighbor><name/></neighbor></group></bgp></protocols></groups></configuration>"
            data = dev.rpc.get_config(filter_xml=xmlfilter)
            configured_peers = data.xpath(
                f"groups/protocols/bgp/group[name='{group_name}']/neighbor/name/text()"
            )
            self.__selected_peers.update({group_name: configured_peers})
            return True
        else:
            return False

    def get_allowed_peers(self, bgpgroup):
        """
        Returns the allowed_base minus any explicitly configured managed peers
        This is required, otherwise configured peers may end up in the wrong group.
        allowed_base is the maximum subnet to allow
        """

        disallowed = IPSet(cu.get_all_selected_peers())
        allowed = IPSet(bgpgroup['prefixes'])
        allowed = allowed-disallowed
        return allowed

    def update_bgpgroup_mesh(self, bgpgroup):
        detected_peers = list()

        # Get peers for DNS based BGP group [DEFAULT]
        if 'sourcetype' not in bgpgroup['source'] or bgpgroup['source']['sourcetype'].casefold() == 'dns':
            try:
                result = resolver.resolve(
                    bgpgroup['source']['hostname'], "A", search=True
                )
            except (resolver.NXDOMAIN, resolver.NoAnswer) as err:
                print(err.msg, f"- Skipping processing of {bgpgroup['name']}.")
                return

            for r in result:
                if r.address != pod_ip:
                    detected_peers.append(r.address)
        else:
            raise(Exception(f"Invalid source type for group {bgpgroup['name']}: {bgpgroup['source']['sourcetype']}"))

        # Identify peers that should be active after this commit.
        # Currently configured peers that are still detected via DNS are prioritized.
        # Additional peers will be selected at random from detected_peers until `max_peers` are selected.
        configured_peers = self.get_selected_peers(bgpgroup['name'])
        selected_peers = list()
        for peer_ip in configured_peers:
            if 'max_peers' not in bgpgroup or len(selected_peers) < bgpgroup['max_peers']:
                if peer_ip in detected_peers:
                    selected_peers.append(peer_ip)
                    detected_peers.remove(peer_ip)
            else:
                # The peer group is full with selected_peers. No need to continue this loop.
                break
        while len(detected_peers) and (
            'max_peers' not in bgpgroup or len(selected_peers) < bgpgroup['max_peers']
        ):
            # Add a peer at random from those detected to fill to max_peers.
            selected_peers.append(detected_peers.pop(randrange(len(detected_peers))))

        # Compare detected_peers (up-to-date list) with configured_peers.
        # Add detected_peers not in configured_peers.
        # Remove configured_peers not in detected_peers.
        peers_to_add = set(selected_peers) - set(configured_peers)
        for peer_ip in peers_to_add:
            self.add_selected_peer(bgpgroup['name'], peer_ip)

        peers_to_remove = set(configured_peers) - set(selected_peers)
        for peer_ip in peers_to_remove:
            self.remove_selected_peer(bgpgroup['name'], peer_ip)

    def update_bgpgroup_subtractive(self, bgpgroup):
        allowed = self.get_allowed_peers(bgpgroup)
        allowed_string = " ".join([str(network) for network in allowed.iter_cidrs()])
        self.load(
            f"delete groups MESHRR protocols bgp group {bgpgroup['name']} allow",
            format="set",
        )
        self.load(
            f"set groups MESHRR protocols bgp group {bgpgroup['name']} allow [ {allowed_string} ]",
            format="set",
        )

    def get_selected_peers(self, group_name):
        self.initiate_group(group_name)
        return self.__selected_peers[group_name]

    def get_all_selected_peers(self):
        result = list()
        for groupname in self.__selected_peers:
            result.extend(self.__selected_peers[groupname])
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


if __name__ == "__main__":

    # Confirm that a mesh BGP group has been defined.
    if not mconf.bgpgroups_mesh:
        raise(Exception("No mesh BGP groups defined."))

    # Open a connection to the device
    dev = Device(host="127.0.0.1",user="meshrr",ssh_private_key_file="/secret/ssh/id_ed25519")
    dev.open()
    with ConfigUpdate(dev, mode="private") as cu:
        for group in mconf.bgpgroups_mesh:
            cu.update_bgpgroup_mesh(
                bgpgroup=group
            )
        for group in mconf.bgpgroups_subtractive:
            cu.update_bgpgroup_subtractive(
                bgpgroup=group
            )
        if cu.diff():
            print("Writing changes:")
            cu.pdiff()
            cu.commit()
