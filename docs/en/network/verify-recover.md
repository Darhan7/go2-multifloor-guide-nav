# Verify the two networks and recover them after reboot

A saved configuration is not automatically correct. Diagnose four layers separately: interface state, addresses, routing, and name resolution.

## Interface state

```bash
ip -br link
nmcli device status
```

`UP` means the kernel interface is enabled. `connected` means NetworkManager activated a profile. If the device exists but is disconnected, check VMware's **Connected** state and then the profile.

## Addresses

```bash
ip -br addr
```

The project expects a static `192.168.123.222/24` on the Go2 side and a DHCP address on the NAT side. A `169.254.x.x` address usually indicates failed DHCP.

## Route selection

```bash
ip route
ip route get 192.168.123.18
ip route get 8.8.8.8
```

`ip route get` shows the selected interface, source address, and next hop for a concrete destination. Go2 should use the bridged interface; public Internet traffic should use NAT.

## Connectivity and DNS

```bash
ping -c 3 192.168.123.18
ping -c 3 8.8.8.8
getent hosts github.com
resolvectl status
```

ICMP reachability does not prove DDS discovery, and some devices may not answer ping. Use SSH, ROS topics, or known services as additional evidence.

## Persistent profiles

```bash
nmcli connection show
nmcli -f connection.id,connection.interface-name,connection.autoconnect,ipv4.method,ipv4.never-default connection show
```

If an interface name changes after VM cloning or virtual-hardware edits, identify the new names and rerun:

```bash
sudo ./tools/configure_vm_dual_nic.sh <go2-interface> <nat-interface>
```

## When IP works but ROS 2 does not

Then investigate DDS rather than ordinary routing: the CycloneDDS interface, `RMW_IMPLEMENTATION`, ROS domain, multicast, firewall, and sourced Unitree message packages.

```bash
echo "$RMW_IMPLEMENTATION"
echo "$CYCLONEDDS_URI"
ros2 topic list
```

The key principle is to prove the IP path first and diagnose DDS discovery second.
