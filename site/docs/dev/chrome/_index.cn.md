
---
title: "Skia 在 Chrome 中"
linkTitle: "Skia in Chrome"

weight: 7

---


Skia 仓库的更改将由自动滚动机器人 (AutoRoll Bot) 每天多次滚动合入 Chromium。

如果您有一个需要在 Chrome 中测试的 Skia 更改，或者需要在该仓库中进行相应的更改，请参阅本节中的指南获取执行技巧。

对于与 Skia 滚动相关的 Chromium 问题：

  * 前往 https://autoroll.skia.org/r/skia-autoroll。使用 google.com 账户登录并点击 STOP 按钮暂停新的滚动。
  * 回退有问题的 DEPS 滚动。
  * 如果在 CL 列表中找不到明显的负责人，请分配给 Skia 值班人员 (Gardener)，该值班人员列在 https://status.skia.org 的值班人员小部件中，也是滚动 CL 的审查者。
  * 如果无法分配给 Skia 值班人员，请抄送他们并将问题分配给 hcm@。

有关 Bug 分类和标签的更多技巧，请参阅[问题跟踪器页面](../../user/issue-tracker/)。

为 Chrome 创建分支
--------------------

每 6 周，我们在 Skia 中切出一个新分支以对应 Chrome 中的新发布分支，例如 [refs/heads/chrome/m75](https://skia.googlesource.com/skia/+/chrome/m75)。通过运行 [tools/chrome_release_branch](https://skia.googlesource.com/skia/+/7a5b6ec0f6c01d3039e3ec30de6f8065ffc8aac4/tools/chrome_release_branch.py') 可以简化此过程。此脚本处理分支本身的创建，以及相关的日常维护工作，如更新下一个版本的 Chrome 里程碑号、为新分支设置[提交队列]('https://skia.googlesource.com/skia/+/infra/config/commit-queue.cfg')。例如：

    tools/chrome_release_branch <commit hash>

