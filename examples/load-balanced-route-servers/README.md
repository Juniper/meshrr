# Example: Fully-meshed Multi-region Route Servers

## Description
* This topology has two regions, `1` and `2`.
* cRPD is used as route servers for EVPN connectivity to minimize peering requirements in a many-DC environment.
* The two regions have route servers fully meshed together.
* Route servers, and Kubernetes nodes, are defined as "a" or "b" side.
* These route servers are deployed as StatefulSets for configuration persistence.
* **Redundancy groups and anycast addressing:**
  * Each node is assigned to redundancy group ("side") `a` or `b`.
  * cRPD pods are scheduled via StatefulSets, and will only be scheduled on a node of their appropriate side. They will prefer to be scheduled on a node of their region. With minor modification to the manifest, backup region(s) can be configured to avoid them being scheduled to just any side-compliant node.
  * In this example, the same IP address is configured as a loopback on each device connecting to a k8s node. This enables to use of only one MetalLB `BGPPeer` manifest globally.
  * MetalLB is used to provide external addressing for BGP connectivity to the cRPD route servers, as well as load balancing if the StatefulSet's `replicas` setting is greater than 1 (or multiple deployments provide endpoints for the same service).
  * MetalLB is also used in this example to provide external addressing for traditional management connectivity (SSH) to the cRPD route servers.
  * `LoadBalancer` services use a `Local` `externalTrafficPolicy`. This is important to ensure that:
    * MetalLB only announces the external peering IP address of the route servers on nodes hosting route servers
    * cRPD's view of the peer shows the physical router's peering IP address (not critical for function but important for operational clarity)

## Requirements
* Kubernetes environment with at least two nodes (one `side=a` and one `side=b`) and with coredns active. For this example, we used microk8s.
* Available storage class. Longhorn was used for this example:
  ```zsh
  helm repo add longhorn https://charts.longhorn.io
  helm install longhorn longhorn/longhorn --namespace longhorn-system --create-namespace --version 1.4.0 --set defaultSettings.defaultDataPath="/longhorn" --set csi.kubeletRootDir="/var/snap/microk8s/common/var/lib/kubelet"
  ```
* MetalLB:
  ```zsh
  helm repo add metallb https://metallb.github.io/metallb
  helm install -n metallb --create-namespace metallb metallb/metallb
  ```

## Usage

1.  Follow the instructions in [Quickstart](../../README.md#Quickstart) using the example YAML files in [examples/load-balanced-route-servers](.).

2.  Configure your routers servicing the nodes:
    1.  With IP connectivity to the nodes.
    2.  With the loopback IP address with which your MetalLB BGPPeer will peer. Do *not* advertise this IP address into a routing protocol.
    3.  BGP peering to the Kubernetes nodes' physical interface IPs carrying unicast IPv4 routes for the spines' and leafs' loopback addresses.
   
    Configuration on the router may look like:

    ##### Junos
    ```junos
    interfaces lo0 {
      unit 100 {
        family inet {
          address 10.0.0.0/32
        }
      }
    }
    routing-instances {
      DCI {
          instance-type vrf;
          protocols {
              bgp {
                  group DCI-RS {
                      type external;
                      multihop {
                          ttl 2;
                      }
                      local-address 10.0.0.0;
                      peer-as 65000;
                      allow 10.1.0.0/24;
                  }
              }
          }
          interface lo0.100;
      }
    }
    ```

    ##### IOS-XR
    ```ios-xr
    interface Loopback100
     vrf DCI
     ipv4 address 10.0.0.0 255.255.255.255
    !
    router bgp 100
     vrf DCI
       neighbor 10.1.0.0/24
       remote-as 65000
       ebgp-multihop 2
       update-source Loopback100
       address-family ipv4 unicast
         route-policy PASS in
         route-policy PASS out
       !
      !
     !
    !
    route-policy PASS
      pass
    end-policy
    !
    ```

3.  (Optional) Modify configuration templates as necessary. Customizations can be applied using several approaches, including configmaps mapped onto volumes. Such is not included or necessary in this example; see [2regions-hrr](../2regions-hrr/) if you require an example of this.

4.  Modify the YAML files to your needs. At the least, `<registryURL>` will need to be replaced to reference your private registry. Load the YAML files for the Deployments, IPAddressPools, BGPAdvertisements, BGPPeers, and Services into Kubernetes as per [Quickstart](../../README.md#Quickstart).

## Required Kubernetes Manifests

- `meshrr-core.service.yml`
  - `Service/meshrr-core` - Provides a headless service coordinating the meshrr function of automatically forming full-mesh iBGP peerings between route servers. Also includes the IPAddressPool and corresponding L2Advertisement for the management network connectivity of the route servers. (In a lab environment, a single L2 domain for cRPD management was sufficient.)
- `metallb-bgppeer-global.yml`
  - `bgppeers.metallb.io/asn100-global-lo100` - Peers MetalLB to the loopback deployed for on each router connecting to the Kubernetes cluster.
- `routeserver-<region>-<side>.yml`
  - `ipaddresspools.metallb.io/routeserver-<region>-<side>` - Creates a pool containing the single address for the service per region per side. `autoAssign: false` ensures that the address is not allocated unless specifically requested by the service.
  - `bgpadvertisements.metallb.io/routeserver-<region>-<side>` - Advertises the address to all peers (by default) from all nodes that host and endpoint for the service.
  - `Service/routeserver-<region>-<side>` - Allocates the address based on the pool defined previously and uses it as an external address load balancing BGP to all healthy pods matching the criteria.
  - `Deployment/routeserver-<region>-<side>` - Creates a deployment of the service for the region and side. In the `routerserver-1-b` example, `replicas: 2`, but for most production deployments, 1 should be sufficient and operationally simpler.