# SkPngChunkReader

> 源文件: `include/codec/SkPngChunkReader.h`

## 概述

SkPngChunkReader 是用于从 PNG 图像解码过程中提取元数据和自定义数据块(chunk)的回调接口基类。它允许应用程序在解码 PNG 文件时访问未知或自定义的数据块,实现元数据提取、版权信息读取等高级功能,是 Skia PNG 解码器的扩展机制。

## 架构位置

SkPngChunkReader 位于 Skia 图像解码子系统的扩展接口层,属于 PNG 编解码模块。它与 SkCodec 配合使用,在解码流程的特定阶段被调用,提供了访问 PNG 底层结构的能力。该类通过引用计数管理生命周期,支持在多线程环境中安全使用。

## 主要类与结构体

### SkPngChunkReader

**职责描述**: 提供纯虚函数接口,定义 PNG 数据块读取的回调协议,由用户派生实现具体的数据块处理逻辑。

**继承关系**: SkRefCnt → SkPngChunkReader

**说明**: 继承自 SkRefCnt 使用引用计数管理对象生命周期,支持通过 sk_sp 智能指针安全传递和共享。

## 公共 API 函数

### `virtual bool readChunk(const char tag[], const void* data, size_t length) = 0`

**功能**: 解码器遇到未知数据块时的回调函数

**参数**:
- `tag`: 4 字符的数据块类型标识(如 "tEXt", "iTXt", "eXIf")
- `data`: 数据块内容的指针
- `length`: 数据块内容的字节长度

**返回值**:
- `true`: 继续解码图像
- `false`: 中止解码,SkCodec 将返回错误

**调用时机**:
根据数据块在 PNG 文件中的位置,readChunk 可能在以下阶段被调用:
1. **工厂方法**: SkCodec::NewFromStream/NewFromData
2. **getPixels**: 完整解码图像时
3. **startScanlineDecode**: 开始逐行解码时
4. **getScanlines/skipScanlines**: 首次调用时

**线程安全**:
- 回调可能在不同线程中执行(如果 SkCodec 被传递到其他线程)
- 实现必须是线程安全的或使用适当的同步机制

**多次调用**:
- 如果 SkCodec 被多次使用,同一数据块的回调可能被调用多次
- 实现应该处理重复调用的情况

## PNG 数据块类型

### 标准数据块 (Skia 自动处理)

Skia 自动解析以下标准数据块,不会触发 readChunk:
- **IHDR**: 图像头(宽度、高度、位深度等)
- **PLTE**: 调色板
- **IDAT**: 图像数据
- **IEND**: 文件结束标记
- **tRNS**: 透明度
- **gAMA**: 伽马校正
- **cHRM**: 色度信息
- **sRGB**: sRGB 颜色空间

### 辅助数据块 (可通过 readChunk 访问)

以下数据块通常作为"未知块"传递给 readChunk:
- **tEXt**: 文本元数据(未压缩)
- **zTXt**: 文本元数据(压缩)
- **iTXt**: 国际化文本(UTF-8)
- **tIME**: 最后修改时间
- **pHYs**: 物理像素尺寸
- **eXIf**: EXIF 元数据
- **自定义块**: 应用程序特定数据

## 使用场景

### 场景 1: 提取版权信息

```cpp
class CopyrightReader : public SkPngChunkReader {
public:
    bool readChunk(const char tag[], const void* data, size_t length) override {
        if (strncmp(tag, "tEXt", 4) == 0) {
            std::string text(static_cast<const char*>(data), length);
            if (text.find("Copyright") != std::string::npos) {
                copyright_ = text;
            }
        }
        return true; // 继续解码
    }

    const std::string& getCopyright() const { return copyright_; }

private:
    std::string copyright_;
};
```

### 场景 2: 提取 EXIF 数据

```cpp
class ExifReader : public SkPngChunkReader {
public:
    bool readChunk(const char tag[], const void* data, size_t length) override {
        if (strncmp(tag, "eXIf", 4) == 0) {
            exif_data_.assign(static_cast<const uint8_t*>(data),
                             static_cast<const uint8_t*>(data) + length);
            // 可以进一步解析 EXIF 二进制数据
        }
        return true;
    }

private:
    std::vector<uint8_t> exif_data_;
};
```

### 场景 3: 过滤特定数据块

```cpp
class SelectiveReader : public SkPngChunkReader {
public:
    bool readChunk(const char tag[], const void* data, size_t length) override {
        // 只处理感兴趣的数据块
        if (strncmp(tag, "tIME", 4) == 0) {
            // 提取时间戳
            processTimeChunk(data, length);
        } else if (strncmp(tag, "pHYs", 4) == 0) {
            // 提取物理尺寸
            processPhysicalDimensions(data, length);
        }
        // 忽略其他未知块
        return true;
    }

private:
    void processTimeChunk(const void* data, size_t length);
    void processPhysicalDimensions(const void* data, size_t length);
};
```

## 内部实现细节

### 引用计数管理

SkPngChunkReader 继承 SkRefCnt:
```cpp
sk_sp<SkPngChunkReader> reader = sk_make_sp<MyChunkReader>();
// 智能指针自动管理生命周期
```

优点:
- 避免内存泄漏
- 支持多个 SkCodec 共享同一个 reader
- 线程安全的引用计数

### 与 SkCodec 的集成

传递给 SkCodec:
```cpp
sk_sp<SkPngChunkReader> chunkReader = sk_make_sp<MyChunkReader>();
std::unique_ptr<SkCodec> codec = SkPngDecoder::Decode(
    stream, &result, chunkReader.get());
```

DecodeContext 类型转换:
```cpp
// SkCodecs::DecodeContext 期望 SkPngChunkReader*
SkCodecs::DecodeContext ctx = static_cast<SkCodecs::DecodeContext>(
    chunkReader.get());
```

### 数据块结构

PNG 数据块的通用结构:
```
[长度: 4字节] [类型: 4字节] [数据: N字节] [CRC: 4字节]
```

传递给 readChunk 的:
- `tag`: 类型字段(4 字节 ASCII)
- `data`: 数据字段(不包含长度、类型和 CRC)
- `length`: 数据字段长度

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| SkRefCnt.h | 引用计数基类 |
| SkTypes.h | 基础类型定义和 SK_API 宏 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| SkPngDecoder | 解码时调用 readChunk 回调 |
| SkCodec | 通用解码器接口的一部分 |

## 设计模式与设计决策

### 回调接口模式

优势:
- 解耦解码逻辑和元数据处理
- 用户可选择性处理数据块
- 避免 Skia 核心依赖元数据解析库

### 返回值作为控制流

返回 `false` 可中止解码:
- 检测到损坏数据时安全退出
- 验证失败时拒绝加载图像
- 实现访问控制(如版权检查)

### 纯虚基类设计

强制用户实现 readChunk:
- 避免忘记实现回调
- 明确接口契约
- 编译期检查

## 性能考量

### 回调开销

每个未知数据块都会触发虚函数调用:
- 典型 PNG: 5-20 个数据块
- 虚函数调用: 微小开销(纳秒级)
- 数据拷贝: 避免在回调中大量拷贝

### 内存管理

数据块内容的生命周期:
- `data` 指针仅在回调期间有效
- 需要保留数据时必须拷贝
- 大数据块应考虑内存压力

### 最佳实践

```cpp
class EfficientReader : public SkPngChunkReader {
public:
    bool readChunk(const char tag[], const void* data, size_t length) override {
        // 快速过滤不感兴趣的块
        if (strncmp(tag, "myAp", 4) != 0) {
            return true; // 跳过
        }

        // 仅在需要时拷贝数据
        if (length < 1024 * 1024) { // 1MB 限制
            my_data_.assign(static_cast<const char*>(data), length);
        } else {
            // 记录警告但继续解码
            SkDebugf("Chunk too large, skipping\n");
        }

        return true;
    }

private:
    std::string my_data_;
};
```

## 常见陷阱与最佳实践

### 陷阱 1: 数据生命周期错误

```cpp
// 错误: 存储指针而非拷贝数据
class BadReader : public SkPngChunkReader {
public:
    bool readChunk(const char tag[], const void* data, size_t length) override {
        data_ = data; // 危险! data 在回调返回后失效
        length_ = length;
        return true;
    }

private:
    const void* data_; // 悬空指针
    size_t length_;
};

// 正确: 拷贝数据
class GoodReader : public SkPngChunkReader {
public:
    bool readChunk(const char tag[], const void* data, size_t length) override {
        data_.assign(static_cast<const uint8_t*>(data),
                    static_cast<const uint8_t*>(data) + length);
        return true;
    }

private:
    std::vector<uint8_t> data_; // 拥有数据
};
```

### 陷阱 2: 线程安全问题

```cpp
// 危险: 无同步的成员变量访问
class UnsafeReader : public SkPngChunkReader {
public:
    bool readChunk(const char tag[], const void* data, size_t length) override {
        counter_++; // 竞态条件
        return true;
    }

    int getCounter() const { return counter_; }

private:
    int counter_ = 0;
};

// 安全: 使用互斥锁
class SafeReader : public SkPngChunkReader {
public:
    bool readChunk(const char tag[], const void* data, size_t length) override {
        std::lock_guard<std::mutex> lock(mutex_);
        counter_++;
        return true;
    }

    int getCounter() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return counter_;
    }

private:
    mutable std::mutex mutex_;
    int counter_ = 0;
};
```

### 最佳实践: 错误处理

```cpp
class RobustReader : public SkPngChunkReader {
public:
    bool readChunk(const char tag[], const void* data, size_t length) override {
        try {
            // 验证数据块
            if (length > kMaxChunkSize) {
                SkDebugf("Chunk too large: %zu\n", length);
                return false; // 中止解码
            }

            // 处理数据
            processChunk(tag, data, length);
            return true;

        } catch (const std::exception& e) {
            SkDebugf("Exception in readChunk: %s\n", e.what());
            return false; // 安全失败
        }
    }

private:
    static constexpr size_t kMaxChunkSize = 10 * 1024 * 1024; // 10MB
    void processChunk(const char tag[], const void* data, size_t length);
};
```

## 相关文件

| 文件 | 关系 |
|------|------|
| include/core/SkRefCnt.h | 基类,提供引用计数 |
| include/codec/SkCodec.h | 使用 ChunkReader 的解码器接口 |
| include/codec/SkPngDecoder.h | PNG 解码器,调用 ChunkReader |
| src/codec/SkPngCodec.cpp | 实际调用 readChunk 的实现 |
