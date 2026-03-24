# skqp_gn_args.py - SkQP GN 构建参数

> 源文件: `gn/skqp_gn_args.py`

## 概述
定义 SkQP (Skia Quality Program) 构建所需的 GN 参数字典。提供 `GetGNArgs()` 函数,根据 API 级别、调试模式、架构和 NDK 路径返回适当的构建配置。

## 架构位置
Skia 构建系统的配置模块,被 `gn_to_bp.py` 等构建脚本使用。

## 公共 API 函数
- **`GetGNArgs(api_level, debug, arch, ndk, is_android_bp)`**: 返回 GN 参数字典

## 内部实现细节
Android Blueprint 模式(`is_android_bp=True`)下使用 `target_os="android"` 和 `target_cpu="none"`。禁用多数非核心功能(PDF、Skottie、SVG 等),启用 Vulkan 和 Graphite。

## 依赖关系
被 `gn_to_bp.py` 导入使用。

## 设计模式与设计决策
最小化构建配置,SkQP 仅需核心渲染和测试功能。

## 性能考量
精简的构建配置减少编译时间和二进制体积。

## 相关文件
- `gn/gn_to_bp.py`
