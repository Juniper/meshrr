# meshrr

## Introduction
*meshrr* is a demonstration-grade scale-out, hierarchically-capable, BGP route reflection methodology using Juniper cRPD and intended for deployment on Kubernetes.

At this time and in the project's raw form, *meshrr* should not be considered for production environments. Sufficient testing, error handling, and routing daemon configuration best practices have not been implemented. Community contributions to improve these areas are appreciated.

- [meshrr](#meshrr)
  - [Introduction](#introduction)
  - [Instructions](#instructions)
    - [Prerequisites](#prerequisites)
    - [Usage](#usage)
    - [Environment Variables](#environment-variables)
  - [Containers](#containers)
  - [BGP Group Types](#bgp-group-types)
  - [Examples](#examples)
  - [Example Commands](#example-commands)

## Instructions

### Prerequisites

1. An operational Kubernetes cluster with sufficient resources for the topology you wish to build.
2. The cRPD software. The current tested version is **23.2R1.13**.
2. A cRPD license for the number of nodes you wish to deploy. At the time of writing, Juniper offers [free trial licenses](https://www.juniper.net/us/en/dm/crpd-trial/). Standard licenses are limited to 16 BGP peers and 4M RIB entries.

### Usage

1. (If required) copy a configuration file template from [`the default templates`](meshrr/defaults/) and edit it to your liking.

2.  Either:
    1. Pick an example topology from [`examples`](examples/) and modify the YAML files as required for your topology. Details for how to use examples and reasonable modifications are below in the [Examples](#Examples) section.
    2. Create your own YAML files if you need a completely custom topology.

3.  Populate the Kubernetes manifest YAML files with the required information. You will need to, at a minimum, replace the following:
    1. Names of elements
    2. [Environment Variables](#Environment-Variables)
    3. Licensing mechanism. Examples here currently use a secret exposed as an environment variable in the meshrr-init container which will populate the license into the config. This may be appropriate for bundle licenses where it is appropriate to use the same license file for many similar devices in a deployment or daemonset. You can create this using:
      ```
      kubectl create secret generic crpd-license --from-file=crpd-license=<filepath>
      ```
    Note that `<filepath>` must point to a file that contains the singular license line and not an entire license file.
    4. (If required) Custom configuration Jinja2 templates loaded into ConfigMaps and mapped as volumes. See [Examples](#Examples).
4.  (If required - e.g., for [2regions-hrr](examples/2regions-hrr/) where only certain nodes should host certain clusters of RRs) Apply appropriate labels to the nodes:
    ```bash
    kubectl label nodes <node> <label1>=<value> <label2>=<value>
    ```
5.  Apply your configuration:
    ```bash
    kubectl [-n namespace] apply -f <file1>
    kubectl [-n namespace] apply -f <file2>
    ```

### Environment Variables

| Variable       | Required for        | Optional for | Description                                                  |
| -------------- | ------------------- | ------------ | ------------------------------------------------------------ |
| LICENSE_KEY    | meshrr-init         |              | License key to be used for the cRPD container; expected to be a single line. |
| POD_IP         | meshrr-init, meshrr |              | The pod's IP address. Must be set by Kubernetes manifest in all pod templates for all meshrr containers. This does not need to be set for the cRPD containers. (`valueFrom: fieldRef: fieldPath: status.podIP`) |
| UPDATE_SECONDS |                     | meshrr       | Frequency in seconds that `meshrr` container will attempt to update `crpd` container with changes to peers. (Default: 30) |


## Containers

- Init Container - `meshrr-init`:
  - `run.sh` with arg `init`
  - Creates configuration from default template or mounted template or derives from existing `/config/juniper.conf` if pod uses persistent storage.
- Container - `crpd`:
  - Unmodified cRPD image running Juniper cRPD.
- Container - `meshrr`:
  - Conducts periodic BGP peer configuration changes on `crpd` container via Netconf.

## BGP Group Types

- `mesh`
  - Discovers peers and connects to all or a limited number of them.
  - Currently, the only BGP peer discovery mode is `dns`, which uses a Kubernetes headless service DNS A records to detect peers.
  New peers are added to config, removed peers are removed from config.
  - Supports a `max_peers` setting, which limits the number of peers added in this group. This is suitable for connections to a higher tier in a hierarchical route reflector / route server topology.
- `subtractive`
  - This can be seen as a "wildcard". This is suitable for an environment in which not all peers are strictly defined and uses Junos BGP group `allow` config to permit connections from a range.
  - The `allow` config is dynamically generated based on the list of all prefixes in the meshrr configuration with all peers from any mesh groups removed.

## Examples

- [2regions-hrr](examples/2regions-hrr)
  - Hierarchicial route reflectors broken into two regions with a single core region unifying them.
  - Reachability via static routes and Kubernetes NodeIP Services referencing additional loopbacks on the Kubernetes nodes.
- [load-balanced-route-servers](examples/load-balanced-route-servers)
  - EVPN route servers deployed in a full iBGP mesh with each other serving eBGP peers. Intended to scale DCI for multi-region deployment.
  - Reachability for external devices achieved through use of MetalLB in BGP mode.

## Example Commands

| Command                                                      | Description                                                  |
| ------------------------------------------------------------ | ------------------------------------------------------------ |
| `kubectl [-n NAMESPACE] get pods -o wide`                    | List pods and the nodes on which they run                    |
| `kubectl [-n NAMESPACE] exec -it POD -c crpd -- cli`         | Access the CLI of cRPD                                       |
| `kubectl [-n NAMESPACE] exec POD -c crpd -- cli show bgp summary` | See the `show bgp summary` output of a pod                   |
| `kubectl [-n NAMESPACE] exec POD -c crpd -- cli show bgp group summary \|except \"Allow\|orlonger\|^Default\|^$\"` | See the status of the neighbor groups of a pod               |
| `kubectl [-n NAMESPACE] logs [-f] POD -c meshrr`             | View the logs from the meshrr sidecar container. `-f` will follow the logs. |
| `kubectl [-n NAMESPACE] delete pod POD`                      | Delete POD. Because pods should be created by DaemonSet, StatefulSet, or Deployment, a new pod should be recreated in its place; in this context, this may be considered functionally more similar to a "restart" than to a "delete". |



