---
title: '如何下载 Skia'
linkTitle: '下载'

weight: 10
menu:
  main:
    weight: 50
---

## 安装 `depot_tools` 和 Git

按照[安装 Chromium 的 depot_tools](http://www.chromium.org/developers/how-tos/install-depot-tools)
的说明下载 `depot_tools`（包含 gclient、git-cl 和 Ninja）。
以下是必要步骤的概要。

<!--?prettify lang=sh?-->

    git clone 'https://chromium.googlesource.com/chromium/tools/depot_tools.git'
    export PATH="${PWD}/depot_tools:${PATH}"

`depot_tools` 也会在你的系统上安装 Git（如果尚未安装的话）。

### 安装 `bazelisk`
如果你打算添加或删除文件，或更改 #includes，你将需要使用 Bazel 来
重新生成部分 BUILD.bazel 文件。我们建议你安装
[Bazelisk](https://github.com/bazelbuild/bazelisk#installation)，而不是手动安装 Bazel，
它将为你获取适当版本的 [Bazel](https://bazel.build/)（由 //.bazelversion 指定）。

### 安装 `ninja`
Ninja 可以通过 `gclient` 或 `bin/fetch-ninja` 来提供。

## 克隆 Skia 仓库

Skia 可以使用 `git` 或随 `depot_tools` 安装的 `fetch` 工具来克隆。

<!--?prettify lang=sh?-->

    git clone https://skia.googlesource.com/skia.git
    # or
    # fetch skia
    cd skia
    python3 tools/git-sync-deps
    python3 bin/fetch-ninja

## 开始使用 Skia

你现在可能想要[构建](../build) Skia。

## 修改和贡献 Skia

至此，你已拥有构建和使用 Skia 所需的一切！如果
你想做出修改，并可能将其贡献回 Skia
项目，请阅读[如何提交补丁](/docs/dev/contrib/submit/)。
