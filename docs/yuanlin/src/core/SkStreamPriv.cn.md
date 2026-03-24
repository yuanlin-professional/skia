# SkStreamPriv

> 源文件
> - src/core/SkStreamPriv.h

## 概述

`SkStreamPriv` 是 Skia 流(Stream)系统的私有工具命名空间,提供流复制、数据提取、大端序读写和调试输出等实用功能。该头文件定义了一组辅助函数和类,用于简化流操作,确保跨平台的字节序一致性,并支持内存诊断。这些工具主要用于字体文件解析、图像编解码和序列化等场景。

主要功能:
- 流到数据的转换(`CopyStreamToData`)
- 流间复制(`Copy`)
- 大端序(Big-Endian)读写辅助
- 调试输出流(`DebugfStream`)
- 流长度检查(`RemainingLengthIsBelow`)

## 架构位置

`SkStreamPriv` 在 Skia 中的位置:
- **层级**: 内部工具层,不暴露给公共 API
- **用途**: 支持字体、图像、PDF 等模块的流操作
- **依赖**: 基于 `SkStream` 公共接口构建
- **范围**: 私有命名空间,限制外部访问

## 主要类与结构体

### DebugfStream

调试输出流,将所有写入的数据发送到 `SkDebugf`。

**继承关系**:
```
DebugfStream : public SkWStream
```

**关键成员**:

| 成员 | 类型 | 说明 |
|------|------|------|
| `fBytesWritten` | `size_t` | 已写入的字节数 |

**方法**:

| 方法 | 说明 |
|------|------|
| `bool write(const void* buffer, size_t size) override` | 写入数据并输出到调试 |
| `size_t bytesWritten() const override` | 返回已写入字节数 |

## 公共 API 函数

### 流转换

```cpp
namespace SkStreamPriv {

// 将流复制到 SkData 对象
sk_sp<SkData> CopyStreamToData(SkStream* stream);

// 从当前位置复制流到输出(不会 rewind)
bool Copy(SkWStream* out, SkStream* input);

}  // namespace SkStreamPriv
```

**使用注意**:
- `CopyStreamToData` 要求流在起始位置
- `Copy` 从当前位置开始,不会自动 rewind

### 大端序读取

```cpp
namespace SkStreamPriv {

// 读取大端序 16 位无符号整数
inline bool ReadU16BE(SkStream* s, uint16_t* value);

// 读取大端序 32 位无符号整数
inline bool ReadU32BE(SkStream* s, uint32_t* value);

// 读取大端序 32 位有符号整数
inline bool ReadS32BE(SkStream* s, int32_t* value);

}  // namespace SkStreamPriv
```

**实现**:
```cpp
inline bool ReadU16BE(SkStream* s, uint16_t* value) {
    if (!s->readU16(value)) {
        return false;
    }
    *value = SkEndian_SwapBE16(*value);
    return true;
}
```

### 大端序写入

```cpp
namespace SkStreamPriv {

// 写入大端序 16 位无符号整数
inline bool WriteU16BE(SkWStream* s, uint16_t value);

// 写入大端序 32 位无符号整数
inline bool WriteU32BE(SkWStream* s, uint32_t value);

// 写入大端序 32 位有符号整数
inline bool WriteS32BE(SkWStream* s, int32_t value);

}  // namespace SkStreamPriv
```

**实现**:
```cpp
inline bool WriteU32BE(SkWStream* s, uint32_t value) {
    value = SkEndian_SwapBE32(value);  // 转换为大端序
    return s->write(&value, sizeof(value));
}
```

### 长度检查

```cpp
namespace SkStreamPriv {

// 检查流是否剩余长度不足
bool RemainingLengthIsBelow(SkStream* stream, size_t len);

}  // namespace SkStreamPriv
```

**语义**:
- 返回 `true`: 确定剩余长度不足
- 返回 `false`: 可能足够(不确定)
- 用于早期失败检测

## 内部实现细节

### CopyStreamToData 实现

```cpp
sk_sp<SkData> CopyStreamToData(SkStream* stream) {
    // 要求流在起始位置
    if (stream->hasPosition() && stream->getPosition() != 0) {
        return nullptr;
    }

    size_t length = stream->getLength();
    if (length == 0) {
        return SkData::MakeEmpty();
    }

    // 分配数据缓冲区
    sk_sp<SkData> data = SkData::MakeUninitialized(length);
    void* buffer = data->writable_data();

    // 读取流内容
    size_t bytesRead = stream->read(buffer, length);
    if (bytesRead != length) {
        return nullptr;  // 读取失败
    }

    return data;
}
```

**设计考量**:
- 检查流位置避免部分读取
- 使用 `MakeUninitialized` 避免零初始化
- 验证实际读取长度

### Copy 实现

```cpp
bool Copy(SkWStream* out, SkStream* input) {
    constexpr size_t kBufferSize = 4096;
    char buffer[kBufferSize];

    while (true) {
        size_t bytesRead = input->read(buffer, kBufferSize);
        if (bytesRead == 0) {
            return true;  // 读取完成
        }
        if (!out->write(buffer, bytesRead)) {
            return false;  // 写入失败
        }
    }
}
```

**设计特点**:
- 使用固定大小缓冲区(4KB)
- 避免大内存分配
- 流式处理,适用于大文件

### 字节序转换

**平台差异处理**:
```cpp
// src/base/SkEndian.h 中定义
#if defined(SK_CPU_BENDIAN)
    #define SkEndian_SwapBE32(n) (n)
#else
    #define SkEndian_SwapBE32(n) SkBSwap32(n)
#endif
```

**跨平台一致性**:
- 大端平台: 无操作
- 小端平台: 字节交换
- 确保文件格式一致

### RemainingLengthIsBelow 实现

```cpp
bool RemainingLengthIsBelow(SkStream* stream, size_t len) {
    if (!stream->hasPosition() || !stream->hasLength()) {
        return false;  // 无法判断,返回 false
    }

    size_t current = stream->getPosition();
    size_t total = stream->getLength();

    if (current > total) {
        return true;  // 异常情况,认为不足
    }

    size_t remaining = total - current;
    return remaining < len;
}
```

**用途示例**:
```cpp
// 字体解析中的安全检查
if (SkStreamPriv::RemainingLengthIsBelow(stream, sizeof(Header))) {
    return false;  // 提前退出,避免读取失败
}
```

### DebugfStream 实现

```cpp
bool DebugfStream::write(const void* buffer, size_t size) {
    // 将数据转换为字符串并输出
    SkString str(static_cast<const char*>(buffer), size);
    SkDebugf("%s", str.c_str());
    fBytesWritten += size;
    return true;
}

size_t DebugfStream::bytesWritten() const {
    return fBytesWritten;
}
```

**使用场景**:
```cpp
DebugfStream debugStream;
serializable->serialize(&debugStream);
// 输出被写入到调试日志
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkStream` | 基础流接口 |
| `SkData` | 数据容器 |
| `SkEndian` | 字节序转换 |
| `SkDebugf` | 调试输出 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| 字体解析 | 读取 TrueType/OpenType 文件 |
| 图像编解码 | 读取 PNG、JPEG 等格式 |
| PDF 生成 | 写入 PDF 结构 |
| 序列化 | 二进制数据读写 |

## 设计模式与设计决策

### 设计决策

1. **命名空间隔离**:
   - 使用 `SkStreamPriv` 命名空间
   - 避免污染公共 API
   - 清晰标记内部使用

2. **内联函数**:
   - 大端序读写函数全部内联
   - 消除函数调用开销
   - 编译器可内联优化

3. **错误处理**:
   - 返回 bool 表示成功/失败
   - 失败时不抛异常(C 风格)
   - 调用者负责检查

4. **缓冲区大小**:
   - `Copy` 使用 4KB 缓冲区
   - 平衡内存使用和性能
   - 适合大多数文件大小

5. **位置检查**:
   - `CopyStreamToData` 验证起始位置
   - 避免部分读取的歧义
   - 明确语义,减少错误

6. **调试工具**:
   - `DebugfStream` 辅助开发调试
   - 不影响生产代码性能
   - 实现简单,易于使用

## 性能考量

1. **内联优化**:
   - 大端序函数内联消除调用开销
   - 编译器可进一步优化字节交换

2. **缓冲复制**:
   - 4KB 缓冲区适合 L1 缓存
   - 避免频繁系统调用
   - 流式处理,内存占用小

3. **避免重复分配**:
   - `CopyStreamToData` 一次分配
   - 不使用动态增长策略
   - 需要预知流长度

4. **早期失败**:
   - `RemainingLengthIsBelow` 快速检查
   - 避免不必要的读取尝试
   - 提高错误检测效率

5. **零拷贝**:
   - `Copy` 使用固定缓冲区
   - 避免动态内存分配
   - 栈分配,速度快

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/core/SkStream.h` | 流基类定义 |
| `include/core/SkData.h` | 数据容器 |
| `src/base/SkEndian.h` | 字节序工具 |
| `include/private/base/SkDebug.h` | 调试输出 |
| `src/ports/SkFontHost_*.cpp` | 字体解析(使用示例) |
| `src/codec/SkPngCodec.cpp` | PNG 解码(使用示例) |
