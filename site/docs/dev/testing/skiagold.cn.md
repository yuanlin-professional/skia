---
title: 'Skia Gold'
linkTitle: 'Skia Gold'
---

## 概述

Gold 是一个 Web 应用程序，用于将我们的机器人生成的图像与已知的基线图像进行比较。

主要特性：

- 基线在 Gold 中管理，独立于 Git，但与 Git 提交保持同步。
- 每次提交会生成超过 50 万张图像。
- 在 CL 合入后，与基线的偏差会被分类 (triage)，图像被标记为 `positive`（正面）或 `negative`（负面）。"正面"表示差异被认为是可接受的。"负面"表示差异被认为是不可接受的，需要修复。如果某个 CL 导致 Skia 出现问题，该 CL 会被回退，或者提交额外的 CL 来修复问题。
- 我们在多个维度上进行测试，例如：

  - 操作系统（Windows、Linux、Mac、Android、iOS）
  - 架构（Intel、ARM）
  - 后端 (Backends)（CPU、OpenGL、Vulkan 等）
  - 等等。

- 使用 Go、Polymer 编写，部署在 Google Cloud 上。代码位于
  [Skia Infra 仓库](https://github.com/google/skia-buildbot)。

## 推荐的工作流程

### 如何最好地使用 Gold 解决常见问题

以下说明将引用各种视图，可通过 [gold.skia.org](https://gold.skia.org/) 的左侧导航栏访问。

查看权限是公开的，分类权限授予 Skia 贡献者。你必须登录才能进行分类。

## 问题 #1：作为 Skia 值班人员 (Gardener)，我需要对许多新传入的图像进行分类和"分配"。

当前解决方案：

- 访问 By Blame 视图查看需要分类的摘要及关联的所有者/CL
  - 默认只显示未分类的摘要
  - 归因 (Blame) 没有按特定顺序排序
  - 摘要按运行次数和最小归因集合进行聚类

<img src=../BlameView.png style="margin-left:30px" align="left" width="800"/>
<br clear="left">

- 选择摘要进行分类
  - 摘要将按差异从大到小排列
  - 点击打开摘要详情视图，查看详细信息

<img src=../Digests.png style="margin-left:40px" align="left" width="780"/>
<br clear="left">

- 为确定的所有者打开 bug
  - 摘要详情视图有一个从 UI 打开 bug 的链接
  - 通过 Gold UI 或手动提交 bug 时，将单个摘要的完整 URL 复制到 bug 报告中
  - Issue Tracker 中对摘要的 URL 引用将在 Gold 中将 bug 链接到摘要

<img src="../IssueHighlight.png" style="margin-left:60px" align="left" width="720" border=1/>
<br clear="left">

<br>

未来改进：

- 更智能、更细粒度的归因列表

<br>

## 问题 #2：作为开发者，我需要合入一个可能改变许多图像的 CL。

查找你的结果：

- 提交后立即访问 By Blame 视图，查找与你的 ID 关联的未分类摘要分组
- 点击包含你的 CL 的某个聚类进行分类
- 返回 By Blame 视图，遍历所有涉及你的更改的未分类摘要
- 注意：UI 中尚未实现按 CL 过滤的功能，但可以通过 URL 实现。删除 URL 中的哈希值，只保留你的 CL 的哈希值。

<img src=../BlameView.png style="margin-left:30px" align="left" width="800"/>
<br clear="left">

重新设置基线图像：

- 访问 Ignores 视图，为受影响最大的配置创建一个新的、短间隔（数小时）的忽略规则

<img src=../Ignores.png style="margin-left:30px" align="left" width="800"/>
<br clear="left">

- 点击忽略规则，打开按受影响配置过滤的搜索视图
- 将未分类的图像标记为正面（或负面，如果适当）
- 处理之前的正面图像有两种选择：
  - 保留之前的正面图像不变，如果复发风险较低，让它们随时间自然消失
  - 如果需要向前验证更改，将之前的正面图像标记为负面

未来改进：

- 在提交前支持 Trybot，视图限于你的 CL
- 在提交前进行预分类，CL 合入时保持分类结果

<br>

## 问题 #3：作为开发者或基础设施工程师，我需要添加新的或更新的配置。

（即：新机器人、测试模式、环境变更）

当前解决方案：

- 按照重新设置基线图像的流程操作：
  - 等待机器人/测试/配置被提交并显示在 Gold UI 中
  - 访问 Ignores 视图，为该配置创建一个短间隔的忽略规则
  - 对该配置的忽略规则进行分类以识别正面图像
  - 删除忽略规则

未来改进：

- 新的或更新的测试可以利用试用作业和预分类功能。
- 新配置也可能能够使用这些功能。

<br>

## 问题 #4：作为开发者，我需要分析特定图像摘要的详细信息。

解决方案：

- 访问 By Test 视图

<img src=../ByTest.png style="margin-left:30px" align="left" width="800"/>
<br clear="left">

- 点击放大镜按配置过滤
- 访问 Cluster 视图查看摘要结果的分布
  - 使用 Ctrl+点击选择并直接比较数据点
  - 点击"parameters"下的配置以高亮数据点并进行比较

<img src=../ClusterConfig.png style="margin-left:30px" align="left" width="800"/>
<br clear="left">

- 访问 Grid 视图查看 NxN 差异

<img src=../Grid.png style="margin-left:30px" align="left" width="800"/>
<br clear="left">

- 访问 Dot 图表查看轨迹的提交历史
  - 每个点代表一次提交
  - 每条线代表一个配置
  - 点的颜色区分不同的摘要

<img src=../DotDiagram.png style="margin-left:30px" align="left" width="800"/>
<br clear="left">

<br>

未来改进：

- 大尺寸的图像对比显示

<br>

## 问题 #5：作为开发者，我需要查找特定配置的结果。

解决方案：

- 访问 Search 视图
- 选择任何所需的参数以跨测试搜索

<img src=../Search.png style="margin-left:30px" align="left" width="800"/>
<br clear="left">
