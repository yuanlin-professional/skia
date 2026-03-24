# FuzzTextBlobDeserialize.cpp - TextBlob 反序列化模糊测试

> 源文件: `fuzz/oss_fuzz/FuzzTextBlobDeserialize.cpp`

## 概述

本文件实现了针对 `SkTextBlob` 反序列化和渲染的模糊测试。`SkTextBlob` 是 Skia 中用于高效存储和绘制文本的不可变数据结构，包含了字形（glyph）ID、位置和字体信息的预处理集合。该测试将随机字节数据尝试反序列化为 TextBlob，然后在画布上渲染，用于发现文本序列化/反序列化和渲染中的安全问题。

## 架构位置

该文件位于 `fuzz/oss_fuzz/` 目录下，覆盖了 Skia 文本渲染子系统中的序列化路径。`SkTextBlob` 的反序列化在处理来自不可信来源的序列化 Skia 数据（如 SKP 文件）时被使用，确保其安全性对于防止远程代码执行和内存损坏至关重要。

## 主要类与结构体

- **`SkTextBlobPriv`**: TextBlob 的私有工具类，提供 `MakeFromBuffer` 方法
- **`SkReadBuffer`**: 安全反序列化缓冲区
- **`SkCanvas`**: 绘图画布
- **`SkSurface`**: 渲染目标
- **`SkPaint`**: 绘图属性

## 公共 API 函数

- **`FuzzTextBlobDeserialize(const uint8_t *data, size_t size)`**: 核心模糊测试函数
- **`LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)`**: LibFuzzer 入口点，输入限制 1024 字节

## 内部实现细节

### 测试流程

1. 创建 `SkReadBuffer` 包装输入数据
2. 调用 `SkTextBlobPriv::MakeFromBuffer()` 尝试反序列化
3. 检查 `buf.isValid()` 验证缓冲区状态
4. 创建 128x128 的 Raster Surface
5. 在位置 (200, 200) 处绘制反序列化的 TextBlob

### 便携字体管理器

LibFuzzer 入口中调用 `ToolUtils::UsePortableFontMgr()`，确保使用可移植的字体管理器，避免依赖系统字体导致不同平台上测试结果不一致。

### 渲染位置

选择 (200, 200) 作为绘制位置，超出 128x128 Surface 的可见范围。这是有意为之，因为目的是测试反序列化和绘制命令的处理，而非实际的像素输出。

## 依赖关系

- **`src/core/SkTextBlobPriv.h`**: TextBlob 私有 API
- **`src/core/SkReadBuffer.h`**: 反序列化缓冲区
- **`include/core/SkCanvas.h` / `SkPaint.h` / `SkSurface.h`**: 渲染 API
- **`tools/fonts/FontToolUtils.h`**: 字体测试工具

## 设计模式与设计决策

- **反序列化+渲染**: 不仅测试反序列化，还测试渲染路径，覆盖端到端流程
- **便携字体**: 使用便携字体管理器确保跨平台的可重现性
- **缓冲区验证**: 通过 `isValid()` 检查捕获反序列化过程中的错误状态
- **1024 字节限制**: TextBlob 序列化数据通常较小，1024 字节足以覆盖典型用例
- **超出范围渲染**: 绘制位置超出 Surface 范围，仍能触发字形解析和光栅化路径

## 性能考量

- 1024 字节输入限制确保极快的迭代速度
- 128x128 Surface 最小化内存分配
- 便携字体管理器避免了系统字体加载的开销
- `drawTextBlob` 即使绘制位置超出 Surface 范围，仍会触发字形解析和测量计算

### TextBlob 序列化格式

`SkTextBlob` 的序列化数据包含：
- 一个或多个 "run"（文本运行），每个包含字形 ID 数组和位置信息
- 每个 run 关联一个字体（包含字体面索引和大小等参数）
- 可选的边界框（bounding box）信息
反序列化时，`SkReadBuffer` 提供的边界检查确保不会读取超出缓冲区的数据。

### 安全攻击向量

TextBlob 反序列化是一个重要的安全攻击向量，因为：
- SKP 文件可能来自不可信来源
- 反序列化创建的字形 ID 可能引用不存在的字形
- 字体索引可能指向无效的字体面
- 位置数据可能包含极端值（如 NaN 或无穷大）

## 相关文件

- `src/core/SkTextBlobPriv.h` - TextBlob 私有头文件
- `src/core/SkTextBlob.cpp` - TextBlob 实现
- `include/core/SkTextBlob.h` - TextBlob 公共头文件
- `tools/fonts/FontToolUtils.h` - 字体测试工具
