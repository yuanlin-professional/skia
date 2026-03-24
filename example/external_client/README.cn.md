此文件夹演示了外部客户端如何使用自己的 C++ 工具链 (Toolchain) 来依赖和构建 Skia。

首先查看 `WORKSPACE.bazel` 了解设置部分（顺便看一下 `./custom_skia_config`），然后查看 `BUILD.bazel` 了解使用 Skia 模块化构建规则来组装特定任务所需组件的实际规则。
