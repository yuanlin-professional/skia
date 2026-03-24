# rust/icc - Rust ICC 配置文件解析器

## 概述

`rust/icc/` 包含使用 `moxcms` Rust crate 实现的 ICC（国际色彩联盟）配置文件
解析器。该模块为 `SkPngRustCodec` 和 `SkBmpRustCodec` 提供色彩配置文件的
安全解析功能。所有 ICC 数据的解析都在 Rust 中完成，防止恶意 ICC 数据引发的
内存安全漏洞。

## 架构

```
图像编解码器 -> ICC 字节 -> rust_icc::parse_icc_profile()
                                ↓ (moxcms 解析)
                           IccProfile 结构体
                                ↓
                      rust_icc::ToSkcmsIccProfile()
                                ↓
                           skcms_ICCProfile
                                ↓
                      Skia 色彩变换系统
```

## 目录结构

```
icc/
├── BUILD.bazel      # Bazel 构建配置
├── FFI.cpp          # C++ 侧 FFI 实现
├── FFI.h            # FFI 头文件
├── FFI.rs           # Rust 侧 CXX 桥接定义
└── README.md        # 原始文档
```

## 支持的配置文件类型

- 基于矩阵的配置文件（RGB/Gray，带 toXYZD50 矩阵 + 传输曲线）
- CICP 元数据（HDR/广色域色彩空间）
- 复杂的 LUT 配置文件（A2B/B2A 多维查找表变换）

## 构建与测试

```bash
# Bazel 构建
$ bazelisk build //rust/icc:ffi_rs
$ bazelisk test //rust/icc:ffi_rs_test

# GN 构建（随 Rust 编解码器自动启用）
$ gn args out/RustEnabled  # 设置 skia_use_rust_png_decode = true
```

## 依赖关系

- **cxx**: FFI 桥接
- **moxcms** 0.7.9: ICC 配置文件解析器
- **rust/common**: 共享 FFI 工具
- Skia skcms 色彩管理系统

## 相关文档与参考

- ICC 规范: https://www.color.org/specification/ICC.1-2022-05.pdf
- moxcms crate: https://crates.io/crates/moxcms
- skcms 模块: `modules/skcms/`
