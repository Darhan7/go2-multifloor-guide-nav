# 故障排查

## 虚拟机能上网但无法连接 Go2

- 确认桥接网卡绑定到正确物理接口；
- 确认存在 `192.168.123.0/24` 地址；
- 确认该网段路由走桥接网卡；
- ping 拓展坞 `192.168.123.18`。

## 能连接 Go2 但 DNS 失败

- 确认默认路由位于 NAT 网卡；
- 检查 `resolvectl status`；
- 重新激活 NAT profile。

## `Package 'go2_core' not found`

工作空间没有编译，或没有 source `install/setup.bash`。

## 缺少 `/scan`

检查点云输入、`cloud_accumulation`、到 `base_link` 的 TF 和转换节点。

## planner 节点名称错误

使用 `-r __node:=planner_server` 启动，确保 lifecycle 和参数命令指向 `/planner_server`。

## 路径直线穿墙

不要视为有效规划。检查 map server、planner lifecycle、static layer、global costmap 尺寸和占用统计。

## planner 返回空路径

检查起点或终点是否位于障碍、未知区或膨胀区，并建立独立的机器人安全导航点。

## 脚本只能在 `/home/unitree` 运行

归档脚本使用绝对路径。应改成接收项目根目录、地图 YAML、语义 YAML 和输出目录参数。
