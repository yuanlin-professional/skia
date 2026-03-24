---
title: 'Skia Swarming 机器人'
linkTitle: 'Skia Swarming 机器人'
---

## 概述

Skia 的 Swarming 机器人 (bots) 托管在三个地方：

- Google Compute Engine。这是不需要在物理硬件上运行的机器人的首选位置，即不需要 GPU 或特定硬件配置的任何内容。我们的大多数编译机器人都在这里，以及一些在 Linux 和 Windows 上的非 GPU 测试机器人。尽管对物理硬件几乎没有保证，但我们从 GCE 获得了令人惊讶的稳定性能数据。
- Chrome Golo。这是需要 GCE 不支持的特定硬件或操作系统配置的机器人的首选位置。我们在 Golo 中有几台 Mac、Linux 和 Windows 机器人。
- Skolo（位于 Chapel Hill 的本地 Skia 实验室）。我们在 GCE 或 Golo 中无法获得的任何设备都在这里。这包括更多种类的 GPU 以及所有 Android、ChromeOS、iOS 和其他设备。

[go/skbl](https://goto.google.com/skbl) 列出了所有 Skia Swarming 机器人。

### <a name="connecting-to-swarming-bots">连接到 Swarming 机器人</a>

如果你需要在机器人/设备上进行更改，请先与 Infra 值班人员 (Gardener) 或其他 Infra 团队成员确认。大多数机器人/设备可以刷机/镜像恢复到干净状态，但有些不行。

- 机器名称类似 "skia-e-gce-NNN"、"skia-ct-gce-NNN"、"skia-i-gce-NNN"、"ct-gce-NNN"、"ct-xxx-builder-NNN" -> GCE

  - 首先确定机器人所属的项目：
    - skia-e-gce-NNN、skia-ct-gce-NNN：
      [skia-swarming-bots](https://console.cloud.google.com/compute/instances?project=skia-swarming-bots)
    - skia-i-gce-NNN：
      [google.com:skia-buildbots](https://console.cloud.google.com/compute/instances?project=google.com:skia-buildbots)
    - ct-gce-NNN、ct-xxx-builder-NNN：
      [ct-swarming-bots](https://console.cloud.google.com/compute/instances?project=ct-swarming-bots)
  - 要登录 GCE 中的 Linux 机器人，使用
    `gcloud compute ssh --project <project> default@<machine name>`。选择 VM 详情页面上列出的区域（请参阅上面的链接）。你也可以使用 `--zone` 命令行标志指定区域。
  - 要登录 GCE 中的 Windows 机器人，首先进入 VM 的详情页面并点击"Set Windows password"按钮。（或者，询问 Infra 团队如何以 chrome-bot 身份登录。）有两种连接选项：
    - SSH：按照 Linux 的说明操作，使用你的用户名而不是 `default`。
    - RDP：在 VM 的详情页面上，点击"RDP"按钮。（如果尚未安装 Chrome RDP Extension for GCP，系统会提示你安装。）

- 机器名称以 "a9"、"m3"、"m5" 结尾。或名称匹配模式 {lin, mac, win}-NNN-g580 ->
  Chrome Golo/Labs

  - 要登录 Golo 机器人，请参阅
    [go/chrome-infra-build-access](https://goto.google.com/chrome-infra-build-access)。

- 机器名称以 "skia-e-"、"skia-i-"（除 "skia-i-gce-NNN" 外）、"skia-rpi-" 开头 -> Chapel Hill 实验室（又名 Skolo）<br/> 要登录 Skolo 机器人，请参阅 [Skolo 维护文档][remote access] 的远程访问部分。以下是特定操作系统的说明：<br/>
  - [远程调试 Skolo 中的 Android 设备][remotely debug android]
  - [VNC 连接到 Skolo Windows 机器人][vnc to skolo windows]
  - [ChromeOS 调试][chromeos debugging]

## 调试

如果你需要在特定机器/设备上运行代码来调试问题，最简单的选择是运行试用作业 (tryjobs)（在向相关代码添加调试输出后）。在某些情况下，你可能还需要[创建或修改试用作业](../automated_testing#adding-new-jobs)。

对于 Google 员工：如果你需要更多控制（例如运行 GDB）并且需要直接在 swarming 机器人上运行，你可以使用 [leasing.skia.org](https://leasing.skia.org)。<br/> 如果那不起作用，[当前 infra 值班人员][current infra gardener]可以帮助你将设备带到你的办公桌上，连接到 GoogleGuest Wifi 或 [Google 测试网络](http://go/gtn-criteria)。

如果你需要在机器人/设备上进行更改，请先与 Infra 值班人员或其他 Infra 团队成员确认。大多数机器人/设备可以刷机/镜像恢复到干净状态，但有些不行。

如果需要在机器上进行永久性更改（例如操作系统或驱动程序更新），请[提交 bug][infra bug] 并分配给 jcgregorio 进行重新分配。

为了方便起见，机器 skolo-builder 可用于在 Skolo 中检出和编译代码。有关更多信息，请参阅 [Skolo 维护文档][remote access] 的远程访问部分。

[current infra gardener]:
  https://rotations.corp.google.com/rotation/4617277386260480
[remote access]:
  https://docs.google.com/document/d/1zTR1YtrIFBo-fRWgbUgvJNVJ-s_4_sNjTrHIoX2vulo/edit#heading=h.v77cmwbwc5la
[infra bug]:
  https://bugs.chromium.org/p/skia/issues/entry?template=Infrastructure+Bug
[remotely debug android]:
  https://docs.google.com/document/d/1nxn7TobfaLNNfhSTiwstOnjV0jCxYUI1uwW0T_V7BYg/
[vnc to skolo windows]:
  https://docs.google.com/document/d/1zTR1YtrIFBo-fRWgbUgvJNVJ-s_4_sNjTrHIoX2vulo/edit#heading=h.7cqd856ft0s
[chromeos debugging]:
  https://docs.google.com/document/d/1yJ2LLfLzV6pXKjiameid1LHEz1mj71Ob4wySIYxlBdw/edit#heading=h.9arg79l59xrf

## 维护任务

请参阅 [Skolo 维护文档][skolo maintenance]。

[skolo maintenance]:
  https://docs.google.com/document/d/1zTR1YtrIFBo-fRWgbUgvJNVJ-s_4_sNjTrHIoX2vulo/edit
