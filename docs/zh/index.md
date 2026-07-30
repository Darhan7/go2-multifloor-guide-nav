# Unitree Go2 多楼层语音导览导航原型

<div class="project-lead" markdown>

这个项目从一个很实际的问题开始：**能不能把实验室里的 Unitree Go2 EDU，一步步做成一只能在真实楼层中认路、前往讲解点，并为多楼层语音导览打好基础的机器人？**

答案不是靠某个仓库“一键跑通”，而是从网络、DDS、点云、TF、二维建图、定位和 Nav2 一层层接起来，再补上真正面向导览场景的地图整理、语义地点、安全导航点、楼层关系、电梯交接和语音意图设计。

这套网站既是一份项目展示，也是一份尽量不跳步骤的教程。你可以从头跟着搭建，也可以直接进入自己最关心的章节。

</div>

!!! tip "第一次接触 ROS 2？"
    先从[阅读路线](system/learning-path.md)开始。每个实践页面都会在当前步骤完整解释相关概念、真实代码、验证方法和官方组件，而不是只给出一串命令。

!!! info "克隆仓库不等于安装机器人环境"
    代码、地图和文档可以一次取得；ROS 2 Foxy、CycloneDDS、Unitree 接口和拓展坞依赖仍需按[环境配置](system/environment.md)逐层准备。

<figure class="hero-figure" markdown="span">
  ![将起点移动到安全自由空间后得到的三楼 Nav2 路径](assets/images/planner/03_valid_path_safe_anchor.png)
  <figcaption>三楼虚拟规划验证：调整机器人安全起点后，Nav2 沿走廊自由空间生成了完整路线。</figcaption>
</figure>

## 这一路做了什么

<div class="grid cards" markdown>

-   **先把网络搭稳**

    ---

    VMware 中同时保留桥接网卡和 NAT 网卡：一张连接 Go2 局域网，另一张负责上网、下载依赖和远程协作。

-   **再让三维点云变成二维地图**

    ---

    从 Go2 LiDAR 的 PointCloud2 出发，经过 TF、点云累积和二维激光提取，接入 `slam_toolbox` 完成一楼和三楼地图采集。

-   **把地图变成适合导览的工作区域**

    ---

    不需要为了封闭整张图把整栋楼都跑一遍，而是依据已知场地结构，用栅格边界划定本次演示真正需要的活动范围。

-   **把“人想看的位置”和“机器人适合停的位置”分开**

    ---

    语义兴趣点负责讲解，安全导航点负责规划与停靠；这一步最终解决了起点落入膨胀区导致无法规划的问题。

-   **把两层楼接成一个系统**

    ---

    使用共同的电梯门结构对齐楼层地图，并设计人机协作的电梯交接流程和 building graph。

-   **为语音导览留出清晰接口**

    ---

    语音模块只负责识别“去哪里”，语义层负责找到正确楼层和安全坐标，Nav2 再负责执行。

</div>

## 项目一览

<div class="image-grid image-grid--3" markdown>

<figure markdown="span">
  ![VMware 双网卡状态](assets/images/network/ubuntu_dual_nic_status.png)
  <figcaption>桥接网卡连接 Go2，NAT 网卡承担默认路由。</figcaption>
</figure>

<figure markdown="span">
  ![楼层地图汇总](assets/images/mapping/map_contact_sheet.png)
  <figcaption>一楼、三楼原始地图、工作地图与采集轨迹。</figcaption>
</figure>

<figure markdown="span">
  ![一楼三楼三维分层对齐](assets/images/alignment/floor_alignment_3d_exploded.png)
  <figcaption>以电梯门为共同地标建立楼层级关系。</figcaption>
</figure>

</div>

## 你可以从哪里开始

手边只有电脑，可以先看地图、配置、调试过程和路线结果；有等价的 ROS 2 Foxy/Nav2 环境，可以继续做 planner-only 复现；重新拿到 Go2 和拓展坞后，再沿着实机工作流接回 AMCL、controller 和运动桥。

现场阶段已经完成了建图、底层运动链路和三楼全局规划验证。由于后续离开实验室，电梯切换、一楼语义坐标和完整语音闭环被保留为清晰的下一阶段任务，而不是用未经验证的结果填补。这也让整份教程更适合后来者继续往下做。
