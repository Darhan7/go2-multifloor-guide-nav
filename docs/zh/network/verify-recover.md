# 验证双网卡，并让配置在重启后稳定恢复

配置完成不等于网络一定正确。验证时要把问题拆成四层：接口是否在线、地址是否正确、路由是否正确、名称解析是否正确。

## 1. 接口层：网卡是否被系统识别

```bash
ip -br link
nmcli device status
```

`UP` 表示内核接口被启用；`connected` 表示 NetworkManager 已把某个 profile 激活。接口存在但 `disconnected` 时，先检查 VMware 的 **Connected**，再检查 profile。

## 2. 地址层：每张网卡属于哪个子网

```bash
ip -br addr
```

本项目期望：

```text
Go2 接口：192.168.123.222/24
NAT 接口：由 DHCP 分配的 192.168.244.x/24
```

`127.0.0.1` 是本机回环地址；`169.254.x.x` 常表示 DHCP 没有成功获得正常地址。

## 3. 路由层：一个目标实际会走哪张网卡

```bash
ip route
ip route get 192.168.123.18
ip route get 8.8.8.8
```

`ip route get` 比只看路由表更直接，它会告诉你内核针对某个具体目标选择的接口、源地址和下一跳。

期望：

```text
192.168.123.18 → ens33
8.8.8.8        → ens37 / NAT gateway
```

如果 Go2 地址走 NAT，说明缺少专用网段路由；如果默认流量走 Go2 网卡，说明 `never-default` 或网关配置有问题。

## 4. 连通层：分别测试局域网与互联网

```bash
ping -c 3 192.168.123.18
ping -c 3 8.8.8.8
```

Ping 使用 ICMP，只能证明基本 IP 可达，并不能证明 ROS 2 DDS 已经发现节点。Go2 可能禁用某些 ICMP 响应，因此还要结合 SSH、ROS topic 或实际端口判断。

## 5. DNS 层：域名是否能够解析

```bash
getent hosts github.com
resolvectl status
```

若 IP 能通而域名失败，检查 NAT profile 的 DNS、`systemd-resolved` 和 `/etc/resolv.conf`，不要去修改 Go2 静态地址。

## 6. NetworkManager profile 是否会自动恢复

```bash
nmcli connection show
nmcli -f connection.id,connection.interface-name,connection.autoconnect,ipv4.method,ipv4.never-default connection show
```

重启后：

```bash
nmcli connection up <Go2-profile>
nmcli connection up <NAT-profile>
```

仓库脚本已经设置 `connection.autoconnect yes`。仍然不自动连接时，检查 profile 是否绑定了旧接口名、是否有重复 profile，以及 VMware 是否在开机时连接虚拟网卡。

## 7. 接口名改变怎么办

复制虚拟机、修改虚拟硬件或系统规则后，`ens33` 可能变成其他名称。先运行：

```bash
nmcli device status
ip -br link
```

再重新执行：

```bash
sudo ./tools/configure_vm_dual_nic.sh <Go2接口> <NAT接口>
```

脚本把接口名作为参数，就是为了避免把某台虚拟机的命名当成通用事实。

## 8. 网络正常，ROS 2 仍然看不到 Go2

这时问题已经不在普通 IP 路由，而可能在 DDS：

- CycloneDDS XML 绑定了错误接口；
- `RMW_IMPLEMENTATION` 没有设置；
- ROS Domain 不一致；
- multicast 被网络或防火墙限制；
- Unitree 消息 package 没有 source。

继续检查：

```bash
echo "$RMW_IMPLEMENTATION"
echo "$CYCLONEDDS_URI"
ros2 topic list
```

网络排查的原则是：**先证明 IP 路径，再排查 DDS 发现；不要把所有问题都归为“网卡没配好”。**
