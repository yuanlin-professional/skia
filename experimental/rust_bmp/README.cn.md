# Rust BMP 解码器

此目录包含用于将自定义 Rust BMP 解码器暴露给其他 Skia 代码的辅助工具、简化封装和包装器：

* 提供给 `SkBmpRustCodec`

## Chromium 构建说明

从 Chromium 构建和测试此目录中的代码：

1. `autoninja -C out/... gfx_unittests blink_platform_unittests chrome`
1. `out/.../gfx_unittests --gtest_filter=*BMP*`
1. `out/.../blink_platform_unittests --gtest_filter=*BMP*`

## Skia 构建说明

### Bazel

从 Skia 构建此目录中的代码：

```
$ cd skia-repo-root
$ bazelisk build //src/codec:rust_bmp_decoder //experimental/rust_bmp/...
```

运行单元测试 (Unit Test)：

```
$ bazelisk test //experimental/rust_bmp/ffi:test_bmp_ffi
```

构建模糊测试器 (Fuzzer)：

```
$ bazelisk build //experimental/rust_bmp/ffi:fuzz_rust_bmp
```

使用语料库 (Corpus) 运行模糊测试器：

```
$ for bmp in experimental/rust_bmp/fuzz/corpus/*.bmp; do
    cat "$bmp" | bazel-bin/experimental/rust_bmp/ffi/fuzz_rust_bmp
  done
```

详细的测试文档请参见 `validation_artifacts/TESTING.md`，模糊测试文档请参见 `validation_artifacts/FUZZING.md`。

### gn / ninja

从 Skia 构建此目录中的代码：

1. `gn args out/RustBmp` 并设置 `skia_use_rust_bmp_decode = true`
1. `gn gen out/RustBmp`
1. `autoninja -C out/RustBmp dm`
```

测试代码：

```
$ out/RustBmp/dm --src tests --nogpu \
    --match Codec_bmp
```

## 功能特性

### **完整的格式支持**

- **位深度 (Bit Depth)**：1 位、4 位、8 位、16 位、24 位、32 位
- **压缩 (Compression)**：未压缩 (BI_RGB)、RLE4、RLE8、位域 (BI_BITFIELDS)
- **高级特性**：OS/2 位图变体
- **色彩空间 (Color Space)**：sRGB、嵌入式 ICC 配置文件（如可用）

### **安全性与健壮性**

- **内存安全 (Memory Safety)**：使用 u64 算术的完整溢出保护
- **输入验证 (Input Validation)**：全面的头部和流验证
- **损坏检测 (Corruption Detection)**：对畸形文件的高级检测
- **标准合规 (Standards Compliance)**：100% 符合 bmptestsuite-0.9

### **性能与集成**

- **零拷贝 (Zero-Copy)**：高效的内存处理，最少的分配
- **FFI 优化**：通过 CXX 桥接实现的清晰 Rust 到 C++ 接口
- **条件构建 (Conditional Build)**：与 Skia 的构建系统集成

## 架构

```
experimental/rust_bmp/
├── ffi/                              # Rust implementation core
│   ├── lib.rs                        # Crate root
│   ├── FFI.rs                        # C++ interface bridge
│   ├── bmp_decoder.rs                # Main BMP decoding logic
│   ├── bmp_header.rs                 # BMP header parsing and validation
│   ├── bmp_constants.rs              # Format constants and definitions
│   ├── bmp_types.rs                  # Type definitions
│   ├── bmp_icc.rs                    # ICC profile support through moxcms crate
│   ├── bmp_jpeg_decoder.rs           # Embedded JPEG handling through zune-jpeg crate
│   ├── bmp_png_decoder.rs            # Embedded PNG handling through png crate
│   └── BUILD.bazel                   # Bazel build configuration
├── decoder/                          # C++ integration layer
│   ├── SkBmpRustDecoder.h/.cpp       # Skia SkCodec factory
│   ├── impl/
│   │   └── SkBmpRustCodec.h/.cpp     # Core codec implementation
│   └── BUILD.bazel                   # Bazel build configuration
└── README.md                         # This file
```

## `SkBmpCodec` 与 `SkBmpRustCodec` 之间的差异

* `SkBmpCodec`：
    - 使用手动内存管理的 C++ 实现
    - 积累了技术债务的遗留代码库
* `SkBmpRustCodec` 的差异：
    - 内存安全的 Rust 实现
    - 使用 u64 算术的全面溢出保护
    - 对畸形文件增强的损坏检测
    - 改进的 BMP 标准合规性
