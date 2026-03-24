# gn_to_bp_utils.py - Android.bp 生成工具库

> 源文件: `gn/gn_to_bp_utils.py`

## 概述
为 `gn_to_bp.py` 提供核心工具函数,包括 GN JSON 生成、依赖值收集、编译标志清理、架构特定源文件获取和用户配置文件写入等功能。

## 架构位置
Skia Android 构建系统的核心工具模块。

## 公共 API 函数

- **`GenerateJSONFromGN(gn_cmd, gn_args)`**: 执行 GN 生成 JSON 项目描述
- **`GrabDependentValues(js, name, value_type, list, exclude)`**: 递归收集目标依赖的指定类型值
- **`CleanupCFlags(cflags)`**: 清理 C 编译标志(仅保留警告标志,添加 Android 所需标志)
- **`CleanupCCFlags(cflags_cc)`**: 清理 C++ 编译标志
- **`GetArchSources(opts_file)`**: 从 `opts.gni` 获取架构特定源文件列表
- **`WriteUserConfig(path, defines)`**: 生成 `SkUserConfig.h` 文件

## 内部实现细节

`GrabDependentValues` 递归遍历目标依赖树,跳过 third_party 和 none 目标。`CleanupCFlags` 添加 Android 特有标志(如 `-DATRACE_TAG`, `-DSKIA_DLL`)并移除 `-Weverything`。`GetArchSources` 通过 Python `exec` 执行 GNI 文件获取架构源列表。

## 依赖关系
- GN 工具链
- Python subprocess, json, tempfile

## 设计模式与设计决策
将通用功能提取为独立模块,被 `gn_to_bp.py` 和其他脚本共享使用。

## 相关文件
- `gn/gn_to_bp.py`, `gn/skqp_gn_args.py`
