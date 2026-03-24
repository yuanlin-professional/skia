# Fuzz 主程序

> 源文件: `fuzz/FuzzMain.cpp`

## 概述

此文件是 Skia 独立模糊测试工具的主入口点。它接受模糊数据文件并根据指定类型（如图像解码、SkSL 编译、路径操作等）执行相应的模糊测试。支持类型自动检测和 ClusterFuzz/OSS-Fuzz 兼容的命名约定。

## 架构位置

位于模糊测试框架 (`fuzz/`) 的顶层，是独立运行的命令行模糊测试工具。区别于通过 `DEF_FUZZ` 注册的 libFuzzer 目标。

## 主要类与结构体

无自定义结构体。使用命令行参数和类型分发表驱动执行。

## 公共 API 函数

- `main(argc, argv)` - 命令行入口
- `fuzz_file(path, type)` - 对单个文件执行指定类型的模糊测试
- `try_auto_detect(path, name)` - 根据文件名自动检测模糊测试类型

### 模糊测试分发函数
涵盖 30+ 种类型：`fuzz_android_codec`, `fuzz_image_decode`, `fuzz_sksl2glsl`, `fuzz_sksl2metal`, `fuzz_sksl2spirv`, `fuzz_sksl2wgsl`, `fuzz_skp`, `fuzz_textblob_deserialize`, `fuzz_json`, `fuzz_colrv1`, `fuzz_skruntimeeffect` 等。

## 内部实现细节

- `cf_api_map` 和 `cf_map` 将 ClusterFuzz 测试名映射到 Skia 内部名称
- 支持两种文件名格式的自动检测：ClusterFuzz (`clusterfuzz-testcase-*`) 和 Skia (`api-*-hash`)
- `calculate_option` 通过累加前 1024 字节生成选项值，供需要不同模式的模糊器使用
- 支持循环执行（`--loops`）同一文件的模糊测试
- 支持目录模式：自动遍历目录中所有文件

## 依赖关系

- `fuzz/Fuzz.h` - 模糊测试核心类
- Skia 各模块的解码器、编译器和渲染器
- `tools/flags/CommandLineFlags.h` - 命令行参数解析

## 设计模式与设计决策

- **类型分发**：使用字符串比较进行类型匹配，简单但可扩展
- **ClusterFuzz 兼容**：通过映射表支持 ClusterFuzz 的命名约定
- **自动检测**：正则表达式匹配文件名自动确定模糊测试类型

## 性能考量

每次调用只处理一种类型，无并发。循环模式 (`--loops`) 用于增加单一输入的覆盖。

## 相关文件

- `fuzz/Fuzz.h` - Fuzz 类定义
- `fuzz/oss_fuzz/` - OSS-Fuzz 集成的各个端点
