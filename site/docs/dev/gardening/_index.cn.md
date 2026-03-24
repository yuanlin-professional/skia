---
title: 'Skia 园丁文档'
linkTitle: 'Skia Gardener Documentation'

weight: 8
---

### 目录

- [Skia 园丁 (Gardener) 做什么？](#what_is_a_skia_gardener)
  - [Skia 代码树](#skia_tree)
  - [问题分类](#triage)
  - [Blamer 工具](#blamer)
  - [自动滚动器](#autorollers)
  - [Gold 和 Perf](#gold_and_perf)
  - [文档](#skia_gardener_doc)
- [为你的轮值做准备](#preparations)
  - [有用的书签](#useful_bookmarks)
  - [聊天室](#chat_rooms)
- [查看当前和即将到来的轮值](#view_current_upcoming_rotations)
- [如何交换轮值班次](#how_to_swap)
- [Skia 园丁小贴士](#tips)
  - [何时提交 bug](#when_to_file_bugs)
  - [如何关闭或重新开放代码树](#how_close_tree)
  - [如何回滚一个 CL](#how_to_revert)
  - [DEPS 滚动失败时该怎么办](#deps_roll_failures)
  - [如何重新设定基线](#how_to_rebaseline)

<a name="what_is_a_skia_gardener"></a>

## Skia 园丁做什么？

---

Skia 园丁 (Gardener) 负责关注代码树、DEPS 滚动、Gold 工具、Perf 工具，以及对 Chrome 的 bug 进行分类。

以下是园丁对每项任务所做工作的简要概述：

<a name="skia_tree"></a>

### Skia 代码树

- 了解[测试基础设施](https://skia.org/docs/dev/testing/automated_testing)。
- 开始关注[状态页面](https://status.skia.org)上的机器人 (bot) 故障。
- 追踪导致故障的责任人，如果没有简单的修复方案则回滚有问题的更改。你可以使用 [blamer](#blamer) 来帮助追踪此类更改。
   - 对于干净的回滚，如果作者不在无法 +1 该更改，你需要添加 "Rubber Stamper"。详见 [go/rubber-stamper-user-guide](http://go/rubber-stamper-user-guide)。
   - 对于不干净的回滚，你可以使用 [go/skia-break-glass](http://go/skia-break-glass) 来快速处理。
- 关闭和开放[代码树](http://tree-status.skia.org)。
- 保持[状态页面](https://status.skia.org)上的构建器注释为最新状态。
- 提交或跟进
  [BreakingTheBuildbots bug](https://bugs.chromium.org/p/skia/issues/list?q=label:BreakingTheBuildbots)。
  参见关于[何时提交 bug](#when_to_file_bugs) 的提示。
- 阅读并更新交接文档中的
  [进行中的问题部分](https://docs.google.com/document/d/1y2jUf4vXI0fwhu2TiCLVIfWC1JOxFcHXGw39y7i-y_I/edit#heading=h.tpualuc3p7z0)。
- （可选）在交接文档的
  [每周交接备注部分](https://docs.google.com/document/d/1y2jUf4vXI0fwhu2TiCLVIfWC1JOxFcHXGw39y7i-y_I/edit#heading=h.y49irwbutzr)
  中记录你值班期间发生的重大事件。

<a name="triage"></a>

### 问题分类 (Triage)

你应该对出现在[状态页面](https://status.skia.org)"未分类 Bug"下的 Chromium、Skia 和 OSS-fuzz 的 bug 进行分类。Android 园丁将负责分类未分类的 Android Bug。如需更详细的 bug 视图，请参见
[Skia Bug 中心](https://bugs-central.skia.org/)。

要访问 oss-fuzz 的 bug，请参见 [go/skia-fuzz](http://go/skia-fuzz)。

<a name="blamer"></a>

### Blamer 工具

如果你安装了 Go，可以使用一个命令行工具来搜索 git 历史记录，并对完整的补丁文本和提交消息进行文本搜索。要安装 blamer 请运行：

    go get go.skia.org/infra/blamer/go/blamer

然后在 Skia 检出目录中运行 blamer。例如，搜索字符串 "SkDevice" 是否出现在最近 10 次提交中：

    $ $GOPATH/bin/blamer --match SkDevice --num 10

    commit ea70c4bb22394c8dcc29a369d3422a2b8f3b3e80
    Author: robertphillips <robertphillips@google.com>
    Date:   Wed Jul 20 08:54:31 2016 -0700

        Remove SkDevice::accessRenderTarget virtual
        GOLD_TRYBOT_URL= https://gold.skia.org/search?issue=2167723002

        Review-Url: https://codereview.chromium.org/2167723002

<a name="autorollers"></a>

### 自动滚动器 (AutoRollers)

- 确保[状态页面](https://status.skia.org)上列出的所有自动滚动器都在成功运行。

<a name="gold_and_perf"></a>

### Gold 和 Perf

- 注意新的 [Perf](https://perf.skia.org/) 和
  [Gold](https://gold.skia.org/) 警报（通过点击[状态页面](https://status.skia.org)右上角的铃铛图标）。
- 园丁在此处的职责是确保当开发者引入新图片或新的性能回退时，他们了解发生了什么，并使用这些工具采取适当的行动。

<a name="skia_gardener_doc"></a>

### 文档

- 为未来的园丁改进/更新此文档页面，特别是[小贴士部分](#tips)。

总的来说，园丁应该强烈倾向于保持代码树绿色并开放的行动；如果简单的回滚就能解决问题，园丁<b>应该先回滚，后提问</b>。

<a name="preparations"></a>

## 为你的轮值做准备

---

<a name="useful_bookmarks"></a>

### 有用的书签

- [Chromium 主控制台](https://ci.chromium.org/p/chromium/g/main/console)。
- [Flutter 引擎控制台](https://ci.chromium.org/p/flutter/g/engine/console)。
- [Skia 客户端搜索](http://go/skia-client-search)，
  一个同时搜索所有 Skia 客户端代码库的工具。公开版本请参见 //tools/skia-client-search.html。

<a name="chat_rooms"></a>

### 聊天室

- [Flutter Engine Sherriff](https://chat.google.com/room/AAAAm69vf-M) 聊天室，用于关注由 Skia bug 引起或需要我们团队协助的 Flutter 问题。

<a name="view_current_upcoming_rotations"></a>

## 查看当前和即将到来的轮值

---

Skia 园丁列表在[此处](http://go/skia-gardener-rotation)指定。[状态页面](https://status.skia.org)上的园丁小部件也会显示当前的园丁。

<a name="how_to_swap"></a>

## 如何交换轮值班次

---

如果你需要与他人交换班次（因为生病或休假），请获得你希望交换的人的同意，然后直接通过[轮值页面](http://go/skia-gardener-rotation)进行交换。

<a name="tips"></a>

## Skia 园丁小贴士

---

<a name="when_to_file_bugs"></a>

### 何时提交 bug

密切关注[状态页面](https://status.skia.org)中的"失败"视图。查看所有现有的
[BreakingTheBuildbots bug](https://bug.skia.org/?q=label:BreakingTheBuildbots)。
如果列表保持最新，那么它应该准确地代表所有导致失败的原因。如果不是，请相应地提交/更新 bug。

<a name="how_close_tree"></a>

### 如何关闭或重新开放代码树

1. 前往 [tree-status.skia.org](https://tree-status.skia.org)。
2. 更改状态。

- 要关闭代码树，在状态中包含 "closed" 一词。
- 要开放代码树，在状态中包含 "open" 一词。
- 要将代码树设为警告状态，在状态中包含 "caution" 一词。

<a name="how_to_submit_when_tree_closed"></a>

### 代码树关闭时如何提交

- 使用 "git cl land" 命令加上 --bypass-hooks 标志手动提交。
- 在你的 CL 描述中添加 "No-Tree-Checks: true"，然后像平常一样使用 CQ。

<a name="how_to_revert"></a>

### 如何回滚一个 CL

参见[此处](https://skia.org/docs/dev/contrib/revert)的回滚文档。

<a name="deps_roll_failures"></a>

### DEPS 滚动失败时该怎么办

DEPS 滚动失败的常见原因是布局测试 (layout tests)。通过检查 DEPS 滚动中的提交哈希范围找到有问题的 Skia CL 并回滚（如果提交作者在线则与其沟通）。如果你进行了回滚，请关注下一次 DEPS 滚动以确保它成功。

如果一个 Skia CL 更改了布局测试，但新图片看起来没问题，则测试需要重新设定基线 (rebaseline)。参见[重新设定布局测试基线](#how_to_rebaseline)。

<a name="how_to_rebaseline"></a>

### 重新设定布局测试基线（即添加抑制规则）

- 首先创建一个 Chromium bug：

  - 前往 [crbug.com](https://crbug.com)
  - 确保你已使用 Chromium 凭据登录
  - 点击 "New Issue"
  - 摘要："Skia image rebaseline"
  - 描述：
    - DEPS 滚动编号
    - 关于出了什么问题的有用信息（例如，"Skia r#### 中对光照缩放的更改影响了以下图片："）
    - 受影响的布局测试
    - 你应该从失败机器人的 stdio 中复制受影响的列表
  - 状态：Assigned
  - 所有者：你自己
  - 抄送：bsalomon@、robertphillips@ 以及负责更改的开发者
  - 标签：OS-All 和 Cr-Blink-LayoutTests
  - 如果与滤镜 (filter) 相关，抄送 senorblanco@

- （不推荐但更快）编辑
  [skia/skia_test_expectations.txt](https://chromium.googlesource.com/chromium/+/refs/heads/trunk/skia/skia_test_expectations.txt)

  - 添加关于更改内容的 # 注释（我通常会复述 crbug 的文本）
  - 在注释后添加如下行：
    - crbug.com/<bug#youjustcreated> foo/bar/test-name.html [ ImageOnlyFailure ]
  - 注意：此更改通常在 DEPS 滚动补丁本身中完成

- （推荐但更慢）通过编辑 LayoutTests/TestExpectations 创建一个单独的 Blink 补丁

  - 添加关于更改内容的 # 注释（我通常会复述 crbug 的文本）
  - 在注释后添加如下行：
    - crbug.com/<bug#youjustcreated> foo/bar/test-name.html [ Skip ] # needs
      rebaseline
  - 提交你创建的补丁并等待它合入并滚动到 Chrome 中

- 重试 DEPS 滚动（对于第一种/不推荐的选项，这通常意味着只需重试布局机器人）
- 通过编辑 LayoutTests/TestExpectations 创建一个 Blink 补丁

  - 添加关于更改内容的 # 注释
  - 在注释后添加如下行：
    - crbug.com/<bug#youjustcreated> foo/bar/test-name.html [ Skip ] # needs
      rebaseline
      - （如果你使用了上面的第二种选项，你只需编辑已有的行）

- 如果你使用了上面第一种/不推荐的选项：
  - 等待 Blink 补丁滚动到 Chrome 中
  - 创建一个 Chrome 补丁，从 skia/skia_test_expectations.txt 中移除你的抑制规则
