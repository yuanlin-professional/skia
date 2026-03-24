---
title: 'SK 命令行工具 (CLI Tool)'
linkTitle: 'SK 命令行工具 (CLI Tool)'
---

## 介绍

`sk` 是一个命令行工具，提供在 Skia 中工作时常用的功能。

## 命令

支持的命令集可能会随时间增长或变化。

### asset

用于管理 Skia 开发者和 CI 中使用的版本化非代码资产。这些存储在 [CIPD](https://chrome-infra-packages.appspot.com/p/skia/bots) 中，其版本在 Skia 的 [//infra/bots/assets](https://skia.googlesource.com/skia/+/main/infra/bots/assets) 下固定。

* add - 为新资产添加条目。这不会创建初始版本。
* remove - 移除现有资产的条目。这不会删除已上传的版本。
* download - 将资产的固定版本下载到指定目录。
* upload - 上传资产的新版本并更新固定版本。如果存在自动化创建资产的脚本，`sk` 会运行该脚本并上传生成的文件。否则，它期望提供一个目标目录。
* get-version - 打印资产的固定版本。
* set-version - 设置资产的固定版本。`sk` 会验证给定版本确实存在于 CIPD 中。
* list-versions - 打印 CIPD 中存在的资产的所有版本。

### release-branch

这自动化了创建 Skia 新发布分支 (release branch) 的相关流程，包括创建 Git 分支本身、在新分支上设置提交队列 (commit queue)（以及停用最旧发布分支的提交队列），以及更新当前 Skia 里程碑。这需要管理员权限。

### try

在当前活跃的 CL 上触发试用作业 (try jobs)。接受零个或多个作业名称或正则表达式。如果未提供，`try` 将列出所有可用的试用作业并退出。

## 开发

`sk` 的代码位于 [Skia Infra 仓库](https://skia.googlesource.com/buildbot)。该仓库中的开发遵循与 Skia 类似的实践。有关入门说明，请参阅 [README.md](https://skia.googlesource.com/buildbot/+/main/README.md)。

`sk` 工具本身的代码位于 [//sk/go/](https://skia.googlesource.com/buildbot/+/main/sk/go/) 下。每个子命令都有一个关联的包。

## 部署

`sk` 的新版本作为 Skia Infra 的 CI/CD 流水线的一部分，会自动构建并上传到 [CIPD](https://chrome-infra-packages.appspot.com/p/skia/tools/sk)。Skia 使用的版本在 [DEPS](https://skia.googlesource.com/skia/+/main/DEPS) 中固定，并由 [autoroller](https://autoroll.skia.org/r/sk-tool-skia) 更新。
