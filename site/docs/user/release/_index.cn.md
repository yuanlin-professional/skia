---
title: '发布信息'
linkTitle: '发布'

weight: 2
menu:
  main:
    weight: 10
---

我们建议大多数客户跟踪我们的最新代码 (tip-of-tree)，因为我们努力保持其稳定。
这样做可以给我们及时的反馈，也能让用户最大程度地获得修复。

如果你需要较低频率的更新，我们每四周与 Chrome 一起发布一个稳定的里程碑 (milestone) 版本。

## 发布流程

Chromium（和 Skia）有一个分阶段的分支策略。每四周从
HEAD 附近一个相对稳定的修订版切出一个分支 (branch)，经过六周的稳定化，
然后升级为稳定版 (stable)。

Skia 与 Chromium 同步创建分支，并与其他 Chromium 组件一起
经历分支测试流水线。Chromium 的发布流程在
[Chrome 发布周期](https://chromium.googlesource.com/chromium/src/+/master/docs/process/release_cycle.md)中有详细记录。

分支/发布日期在
[日程表](https://chromiumdash.appspot.com/schedule)中。当前
分支列在 https://chromiumdash.appspot.com/branches。

## 发布说明

所有里程碑的 Skia 发布说明可以在
[Skia Graphics Release Notes](https://skia.googlesource.com/skia/+/refs/heads/main/RELEASE_NOTES.md) 中找到。
