# third_party/dawn - Dawn WebGPU 实现

## 概述

`third_party/dawn/` 包含 Google Dawn WebGPU 实现的 Skia 构建配置。Dawn 是
WebGPU API 的原生实现，提供跨平台的现代 GPU 抽象层。Skia 的 Graphite 后端
使用 Dawn 作为 WebGPU 渲染后端，支持在浏览器和原生应用中使用 WebGPU。

## 目录结构

```
dawn/
├── BUILD.gn             # GN 构建配置
├── args.gni             # GN 参数定义
├── build_dawn.py        # Dawn 构建脚本
├── build_tint.py        # Tint 着色器编译器构建
├── cmake_utils.py       # CMake 工具函数
└── fetch_and_stamp.py   # 依赖获取和版本标记
```

## 关键文件

- **BUILD.gn**: Dawn 的 Skia 构建配置
- **args.gni**: 可配置的 Dawn 构建参数
- **build_dawn.py**: Python 脚本，处理 Dawn 的复杂构建过程
- **build_tint.py**: 构建 Tint WGSL 着色器编译器

## 依赖关系

- Dawn 源码（通过 DEPS 拉取）
- Tint 着色器编译器（Dawn 的子项目）
- 平台图形 API（Vulkan、Metal、D3D12）

## 相关文档与参考

- Dawn: https://dawn.googlesource.com/dawn
- WebGPU 规范: https://www.w3.org/TR/webgpu/
- Skia Graphite Dawn 后端: `src/gpu/graphite/dawn/`
- WebGPU 实验: `experimental/webgpu-bazel/`
