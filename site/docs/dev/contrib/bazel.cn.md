
---
title: "使用 Bazel"
linkTitle: "Using Bazel"

---

## 概述

Skia 目前正在迁移到使用 [Bazel](https://bazel.build/) 作为构建系统 (Build System)，因为它能够更精确地控制构建的内容和方式。

在本文档中引用文件时，我们使用 [Bazel 标签表示法](https://bazel.build/concepts/labels)，因此要引用位于 `$SKIA_ROOT/docs/examples/Arc.cpp` 的文件，我们会写作 `//docs/examples/Arc.cpp`。

## 了解更多关于 Bazel 的信息
Bazel 文档非常好。如果您是 Bazel 新手，建议按以下顺序阅读：
 - [Bazel 和 C++ 入门](https://bazel.build/tutorials/cpp)
 - [WORKSPACE.bazel 和外部依赖](https://bazel.build/docs/external)
 - [目标和标签](https://bazel.build/concepts/labels)
 - [理解构建过程](https://bazel.build/docs/build)
 - [使用 .bazelrc 文件进行配置](https://bazel.build/docs/bazelrc)

Google 员工请查看 [go/bazel-bites](http://go/bazel-bites) 获取更多技巧。

## 使用 Bazel 构建

以下内容假设您已经[下载了 Skia](/docs/user/download)，特别是已使用 `./tools/git-sync-deps` 同步了 third_party 依赖。

### Linux 主机（您在 Linux 机器上运行 Bazel）
您可以运行如下命令：
```
bazel build //example:hello_world_gl
```

这使用了我们组建的密封 C++ 工具链 (Hermetic C++ Toolchain) 在 Linux 主机上编译 Skia（实现在 `//toolchain` 中）。它构建的是在 `//examples/BUILD.bazel` 中定义的名为 "hello_world_gl" 的_目标_，该目标使用了我们设计的 `sk_app` 框架来制作使用 Skia 的简单应用程序。

Bazel 会将此可执行文件放在 `//bazel-bin/example/hello_world_gl`，并在日志中告知您。您可以自己运行此可执行文件，或者通过将命令修改为以下形式让 Bazel 运行它：
```
bazel run //example:hello_world_gl
```

如果您想向 `bazel run` 传递一个或多个标志，请在末尾的 `--` 之后添加它们，例如：
```
bazel run //example:hello_world_gl -- --flag_one=apple --flag_two=cherry
```

### Mac 主机（您在 Mac 机器上运行 Bazel）
您可以运行如下命令：
```
bazel build //example:bazel_test_exe
```

在 Mac 上构建时，我们要求用户在其设备上安装 Xcode，以便在编译时使用系统头文件和 Mac 特定的包含文件。Google 员工请按照惯例，遵循 [go/skia-corp-xcode](http://go/skia-corp-xcode) 的说明安装 Xcode。

我们的 Bazel 工具链假设您的路径中有 `xcode-select`，以便我们可以在工具链的缓存中创建用户当前 Xcode 目录的符号链接 (Symlink)。请确保 `xcode-select -p` 返回有效路径。

## .bazelrc 技巧
您应该在主目录中创建一个 [.bazelrc 文件](https://bazel.build/docs/bazelrc)，在其中指定仅适用于您的设置。这些设置可以补充或替换我们在 `//.bazelrc` 配置文件中定义的设置。

Skia 在 `//bazel/buildrc` 中定义了一些[配置](https://bazel.build/docs/bazelrc#config)，即设置和功能的组合。该文件包含我们经常使用的构建配置（例如，在我们的持续集成系统中）。

如果您想定义 Skia 特定的配置（以及不与其他 Bazel 项目冲突的选项），可以在 `//bazel/user/buildrc` 中创建一个文件，它将被自动读取。此文件受 `.gitignore` 规则覆盖，不应被提交。

您可能希望在 `~/.bazelrc` 或 `//bazel/user/buildrc` 文件中添加以下部分或全部条目。

### 在本地更快地构建 Skia
许多 Linux 机器在 [/dev/shm 挂载了 RAM 磁盘](https://www.cyberciti.biz/tips/what-is-devshm-and-its-practical-usage.html)，将其用作 Bazel 沙箱 (Sandbox) 的位置可以显著提高编译速度，因为[沙箱化](https://bazel.build/docs/sandboxing)已被观察到是 I/O 密集型的。

如果您有 4GB 以上的 `/dev/shm` 分区，请将以下内容添加到 `~/.bazelrc`：
```
build --sandbox_base=/dev/shm
```

Mac 用户应该绕过沙箱化，因为[已知其速度较慢](https://github.com/bazelbuild/bazel/issues/8230)。
```
build --spawn_strategy=local
```

### 在 Linux 虚拟机上认证到 RBE
我们正在为 Bazel 设置远程构建执行 (Remote Build Execution, RBE)。一些用户报告在 Linux 虚拟机上尝试使用 RBE（通过 `--config=linux_rbe`）时出现错误，例如：
```
ERROR: Failed to query remote execution capabilities:
Error code 404 trying to get security access token from Compute Engine metadata for the default
service account. This may be because the virtual machine instance does not have permission
scopes specified. It is possible to skip checking for Compute Engine metadata by specifying the
environment variable NO_GCE_CHECK=true.
```
对于无法在[虚拟机上](https://skia-review.googlesource.com/c/skia/+/525577)设置 `cloud-platform` 范围的情况，可以通过在 `gcloud auth login` 登录后将以下内容添加到 `~/.bazelrc`（将 &lt;user> 替换为自己的用户名）来直接链接到其 GCP 凭据：
```
build:remote --google_credentials=/usr/local/google/home/<user>/.config/gcloud/application_default_credentials.json
```

### 使本地构建与远程构建兼容（例如更好的缓存）
如果您在 Linux x64 机器上，并且希望能够在本地构建和使用 `--config=linux_rbe` 构建之间共享缓存的构建结果，请将以下内容添加到 `//bazel/user/buildrc`：
```
build --host_platform=//bazel/platform:linux_x64_hermetic
```
例如，如果您使用笔记本电脑，在有网络连接时使用 `--config=linux_rbe` 将加速构建，但如果需要离线工作，您仍然可以在本地构建并使用之前远程构建的结果。
