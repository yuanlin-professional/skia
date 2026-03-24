# Rust ICC 配置文件解析器 (ICC Profile Parser)

本目录包含用于将 `moxcms` Rust crate 中的 ICC（国际色彩联盟，International Color Consortium）配置文件解析功能暴露给 Skia 编解码器的辅助工具和封装：

* 被 `SkPngRustCodec` 和 `SkBmpRustCodec` 使用

## 架构

```
Image Codec → ICC bytes → rust_icc::parse_icc_profile()
                               ↓ (moxcms parsing)
                          IccProfile struct
                               ↓
                     rust_icc::ToSkcmsIccProfile()
                               ↓
                          skcms_ICCProfile
                               ↓
                     Skia color transformations
```

### 内存安全

所有 ICC 配置文件的解析都使用 `moxcms` crate 在 Rust 中完成。这可以防止因格式错误的 ICC 数据导致的内存安全漏洞。经过验证和解析的数据随后被转换为 `skcms_ICCProfile` 结构体，供 Skia 的颜色管理系统 (skcms) 使用。

### 配置文件支持

该解析器支持：
- 基于矩阵的配置文件（具有 toXYZD50 矩阵 + 传输曲线的 RGB/Gray 配置文件）
- CICP 元数据（用于 HDR/广色域色彩空间）
- 复杂的基于查找表 (LUT) 的配置文件（具有多维查找表的 A2B/B2A 变换）

## 构建

### Bazel

```
$ cd skia-repo-root
$ bazelisk build //rust/icc:ffi_rs
$ bazelisk test //rust/icc:ffi_rs_test
```

### gn / ninja

当启用 Rust 编解码器时会自动启用：

```
$ gn args out/RustEnabled
# Set: skia_use_rust_png_decode = true
$ gn gen out/RustEnabled
$ autoninja -C out/RustEnabled
```

## 测试

### 单元测试

**Rust 单元测试**（测试 Rust 端的解析和 FFI 数据结构）：

```bash
$ bazelisk test //rust/icc:ffi_rs_test --test_output=all
```

**C++ 单元测试**（测试完整的 FFI 桥接到 skcms）：

通过 Skia 的 `dm` 测试运行器构建并运行：

```bash
$ gn gen out/Debug --args='skia_use_rust_png_decode=true'
$ ninja -C out/Debug dm
$ out/Debug/dm --src tests --match RustIcc
```

C++ 测试位于 `tests/RustIccTest.cpp`。

## 依赖

- **cxx**：Rust 和 C++ 之间的 FFI 桥接
- **moxcms** 0.7.9：ICC 配置文件解析器
- **rust/common**：共享 FFI 工具

## 参考

- ICC 规范：https://www.color.org/specification/ICC.1-2022-05.pdf
- moxcms：https://crates.io/crates/moxcms
- skcms：https://skia.googlesource.com/skcms/
