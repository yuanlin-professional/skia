# DeserialProcsUtils

> 源文件：tools/DeserialProcsUtils.h, tools/DeserialProcsUtils.cpp

## 概述

`DeserialProcsUtils` 是 Skia 工具库中提供默认反序列化处理器的模块。该模块为工具代码提供标准的 `SkDeserialProcs` 配置，用于正确反序列化 SKP（Skia Picture）文件中的图像和字体数据。它统一了图像解码策略（使用 PNG 解码器）和字体反序列化策略（使用测试字体管理器），确保工具和测试程序能一致地加载 SKP 文件。

## 架构位置

- 位于 `tools/` 目录
- 在 `ToolUtils` 命名空间中
- 依赖 PNG 解码器（支持 Rust 或传统实现）
- 与字体测试工具集成
- 用于 Viewer、debugger 等 SKP 播放工具

## 主要类与结构体

无类定义，仅提供函数。

### get_default_skp_deserial_procs

```cpp
SkDeserialProcs get_default_skp_deserial_procs()
```
- **功能**：返回工具默认的 SKP 反序列化处理器
- **返回值**：配置好的 `SkDeserialProcs` 结构体
- **配置**：
  - `fImageDataProc`：PNG 图像数据处理器
  - `fTypefaceStreamProc`：字体流处理器

## 内部实现细节

### 图像数据处理

```cpp
procs.fImageDataProc = [](sk_sp<SkData> data, std::optional<SkAlphaType> at, void*) {
    #if defined(SK_CODEC_DECODES_PNG_WITH_RUST)
        auto codec = SkPngRustDecoder::Decode(...);
    #else
        auto codec = SkPngDecoder::Decode(...);
    #endif
    return SkCodecs::DeferredImage(codec, at)->makeRasterImage(nullptr);
};
```
- 支持 Rust PNG 解码器（如果启用）
- 使用延迟图像创建，立即光栅化
- 不使用 GPU 上下文（nullptr）

### 字体流处理

```cpp
procs.fTypefaceStreamProc = [](SkStream& stream, void*) {
    return SkTypeface::MakeDeserialize(&stream, ToolUtils::TestFontMgr());
};
```
- 使用测试字体管理器
- 支持 FreeType 或原生字体后端
- 处理 SKP 中嵌入的字体数据

## 依赖关系

**Skia 核心**：
- `include/core/SkSerialProcs.h`
- `include/core/SkFontMgr.h`
- `include/codec/SkCodec.h`

**PNG 解码器**：
- `include/codec/SkPngDecoder.h` 或
- `include/codec/SkPngRustDecoder.h`

**字体工具**：
- `tools/fonts/FontToolUtils.h`

## 设计模式与设计决策

### 策略模式
通过函数指针/lambda 配置不同的反序列化策略。

### 工厂模式
作为默认处理器的工厂函数。

### 关键决策
1. **统一配置**：所有工具使用相同的反序列化策略
2. **条件编译**：支持 Rust PNG 解码器的可选编译
3. **测试字体管理器**：确保字体在测试环境中可用
4. **无 GPU**：使用栅格图像，避免 GPU 依赖

## 性能考量

- 延迟解码后立即光栅化，适合工具场景
- 不使用 GPU，降低依赖但性能较低
- 适用于调试和测试，非生产环境

## 相关文件

- `include/core/SkSerialProcs.h` - 序列化处理器接口
- `tools/fonts/FontToolUtils.h` - 测试字体管理器
- `tools/viewer/` - Viewer 工具使用此配置
- `src/core/SkPictureData.cpp` - SKP 反序列化实现
