# Rust PNG 解码器 (PNG Decoder)

本目录包含用于将 `png` Rust crate 暴露给其他 Skia 代码的辅助工具、简化层和封装：

* 暴露给 `SkPngRustCodec`
* 暴露给 `SkPngRustEncoderImpl`

更多详情请参阅以下文档：
https://docs.google.com/document/d/1glx5ue5JDlCld5WzWgTOGK3wsMErQFnkY5N5Dsbi91Y/edit?usp=sharing

## Chromium 构建说明

从 Chromium 构建和测试本目录中的代码：

1. `autoninja -C out/... gfx_unittests blink_platform_unittests chrome`
1. `out/.../gfx_unittests --gtest_filter=*PNG*`
1. `out/.../blink_platform_unittests --gtest_filter=*PNG*`

## Skia 构建说明

### Bazel

从 Skia 构建本目录中的代码（暂不支持通过 Bazel 进行测试）：

```
$ cd skia-repo-root
$ bazelisk build //src/codec:rust_png_decoder //src/encode:rust_png_encoder rust/png/...
```

### gn / ninja

从 Skia 构建本目录中的代码：

1. `gn args out/RustPng` 并设置 `skia_use_rust_png_decode = true`
   以及 `skia_use_rust_png_encode = true`
1. `gn gen out/RustPng`
1. `autoninja -C out/RustPng dm`
```

通过 `tests/SkPngRustDecoderTest.cpp` 和
`tests/SkPngRustEncoderTest.cpp` 测试代码：

```
$ out/RustPng/dm --src tests --nogpu \
    --match RustPngCodec \
            RustEncodePng
```

TODO(https://crbug.com/356875275)：添加支持针对 `SkPngRustCodec` 运行旧版测试（例如 `tests/CodecTest.cpp` 中的测试）。

## `SkPngCodec` 与 `SkRustPngCodec` 之间的区别

* `SkPngCodec`：
    - 不支持 APNG。
    - 不支持 CICP。
* `SkPngRustCodec` 的区别 - 参见
  https://issues.chromium.org/issues?q=parentid:362829876%2B

## `SkPngEncoder` 与 `SkPngRustEncoder` 之间的区别

* `SkPngRustEncoder` 的区别 - 参见
  https://issues.chromium.org/issues?q=parentid:381140294%2B
