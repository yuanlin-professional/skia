---
title: '为 Skia 做贡献'
linkTitle: 'Contributing'

weight: 1
menu:
  main:
    weight: 40
---

以下是您可以参与并帮助我们改进 Skia 的一些方式。

## 报告 Bug (Bug)

在 [Skia 问题跟踪器](http://bug.skia.org/) 中查找需要修复的 Bug 或报告新的 Bug。您也可以在 [Chromium 问题跟踪器](http://code.google.com/p/chromium/issues/list) 中搜索与图形或 Skia 相关的 Bug。

## 测试

编写一个应用程序或工具，以不同于我们现有测试集的方式来测试 Skia 代码，并验证 Skia 是否按预期工作。绘制一些有趣的内容并进行性能分析 (Profiling)，以找到加速 Skia 实现的方法。我们无法始终修复所有问题或支持每种场景，但我们欢迎发现任何 Bug，以便我们进行评估和优先级排序。（如果您能_发现并修复_ Bug，那就更好了！）

## 贡献代码

无论您是为 Skia 代码库开发新功能还是修复现有 Bug，都需要一位提交者 (Committer) 来审查和批准更改。以下是一些可以加速审查流程的步骤：

- 保持您的代码提交小巧且有针对性。
- 如果可能，请在提交之前让一位同事提前审查您的更改。
- 通过提交功能 Bug 或在 skia-discuss 上发帖，在开发之前向项目负责人提出新功能建议。

更多信息，请参阅[如何提交补丁](/docs/dev/contrib/submit/)。

有关项目背景和感兴趣的参与方可以承担的角色类型概述，请参阅[项目角色](/docs/roles)。

任何向 Skia 贡献代码的人都必须签署贡献者许可协议 (Contributor License Agreement) 并确保其被列在 AUTHORS 文件中：

- 个人贡献者可以在线完成[个人贡献者许可协议](https://developers.google.com/open-source/cla/individual)。
- 如果您代表公司进行贡献，请填写[企业贡献者许可协议](https://developers.google.com/open-source/cla/corporate)并按该页面所述方式发送。

- 如果这是您第一次提交代码或之前未曾提交过，请在您的 CL 中将您（或您的组织）的名称和联系信息添加到 [AUTHORS 文件](https://skia.googlesource.com/skia/+/main/AUTHORS) 中。

审查者：在您 LGTM 一个更改之前，请验证贡献者是否已列在 AUTHORS 文件中。

如果他们未被列出，Google 员工必须通过搜索 [go/cla-signers](https://goto.google.com/cla-signers) 确认该个人或其公司已签署 CLA。然后在 CL 中将条目添加到 AUTHORS 文件中。
