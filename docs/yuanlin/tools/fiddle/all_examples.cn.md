# all_examples - Fiddle 示例汇总文件

> 源文件: `tools/fiddle/all_examples.cpp`

## 概述

all_examples.cpp 是一个由脚本自动生成的 C++ 翻译单元，通过 `#include` 指令汇总了 `docs/examples/` 目录下的所有 Fiddle 示例文件。该文件使 Fiddle 构建系统能够在单次编译中包含所有文档示例，用于 Fiddle 在线代码运行服务。

## 架构位置

位于 `tools/fiddle/` 目录，是 Fiddle 构建系统的核心组件。由 `make_all_examples_cpp.py` 脚本生成，不应手动编辑。

## 主要类与结构体

无。本文件仅包含 `#include` 指令序列。

## 公共 API 函数

无。所有 API 由被包含的示例文件提供。

## 内部实现细节

- 文件第一行是版权头
- 其余行按字母顺序 `#include` 所有 `docs/examples/*.cpp` 文件
- 截至当前版本，包含约 1000 个示例文件
- 路径格式为相对路径 `docs/examples/xxx.cpp`

## 依赖关系

- `docs/examples/` 目录下的所有 `.cpp` 示例文件
- 这些示例文件依赖 `skia.h` 和 `tools/fiddle/fiddle_main.h`

## 设计模式与设计决策

- **聚合编译**: 将所有示例聚合到单个翻译单元中，简化构建配置
- **自动生成**: 通过脚本维护，避免手动添加新示例时遗漏

## 性能考量

- 单个大翻译单元的编译时间较长，但简化了构建系统复杂度
- 适合 CI/CD 环境中的一次性构建

## 相关文件

- `tools/fiddle/make_all_examples_cpp.py` - 生成此文件的脚本
- `tools/fiddle/draw.cpp` - 示例 Fiddle 实现
- `tools/fiddle/fiddle_main.h` - Fiddle 主框架头文件
