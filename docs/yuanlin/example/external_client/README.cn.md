# example/external_client - 外部客户端集成示例

## 概述

`external_client/` 演示了外部客户端如何使用自己的 C++ 工具链来依赖和构建
Skia。这是一个完整的独立 Bazel 项目示例，展示了从配置到使用 Skia 模块化
构建规则的完整流程。

## 目录结构

```
external_client/
├── BUILD.bazel              # 构建规则（使用 Skia 的模块化构建）
├── MODULE.bazel             # Bazel 模块声明和 Skia 依赖
├── MODULE.bazel.lock        # 依赖版本锁定
├── README.md                # 原始集成说明
├── custom_skia_config/      # 自定义 Skia 构建配置
└── src/                     # 客户端示例源码
```

## 集成步骤

1. 查看 `MODULE.bazel`，了解如何声明 Skia 作为外部依赖
2. 查看 `custom_skia_config/`，了解如何自定义 Skia 的编译选项
3. 查看 `BUILD.bazel`，了解如何使用 Skia 的构建规则组装所需组件

## 依赖关系

- Bazel 构建系统
- Skia 源码或预编译库

## 相关文档与参考

- Bazel 外部依赖: https://bazel.build/external/overview
- Skia Bazel 构建: `bazel/` 目录
