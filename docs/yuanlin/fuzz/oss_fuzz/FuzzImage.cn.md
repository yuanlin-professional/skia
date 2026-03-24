# FuzzImage

> 源文件: fuzz/oss_fuzz/FuzzImage.cpp

## 概述

`FuzzImage.cpp` 是 Skia 中用于模糊测试通用图像解码的工具。该模块通过 OSS-Fuzz 框架对多种图像格式的解码器进行自动化安全测试,验证在处理畸形和边界条件图像数据时的稳定性。模糊测试器将任意字节流作为图像数据输入,尝试解码并绘制到光栅化表面,以发现潜在的崩溃、内存问题和安全漏洞。

## 架构位置

- **路径**: `fuzz/oss_fuzz/FuzzImage.cpp`
- **模块层次**: 测试工具层 > 模糊测试子系统 > OSS-Fuzz 集成
- **测试目标**: Skia 的通用图像解码管线

## 主要类与结构体

### 核心函数

#### `FuzzImageDecode`
```cpp
bool FuzzImageDecode(const uint8_t *data, size_t size)
```

**功能**: 执行图像解码和绘制测试
- **参数**: 输入字节流作为图像数据
- **返回值**: 测试是否成功执行
- **核心逻辑**:
  1. 使用 `SkImages::DeferredFromEncodedData` 创建延迟解码图像
  2. 创建 128x128 光栅化表面
  3. 绘制图像到画布
  4. 验证整个流程不崩溃

#### `LLVMFuzzerTestOneInput`
```cpp
extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)
```

**功能**: LibFuzzer 标准入口点
- **输入限制**: 最大 10240 字节(10KB)
- **返回值**: 始终返回 0

## 公共 API 函数

使用的 Skia API:
- `SkImages::DeferredFromEncodedData()`: 创建延迟解码图像
- `SkSurfaces::Raster()`: 创建光栅化表面
- `SkCanvas::drawImage()`: 绘制图像

## 内部实现细节

### 测试流程

```
输入字节流
    ↓
DeferredFromEncodedData (自动检测格式)
    ↓
创建光栅化表面 128x128
    ↓
drawImage (触发实际解码)
    ↓
验证不崩溃
```

### 延迟解码策略

```cpp
auto img = SkImages::DeferredFromEncodedData(SkData::MakeWithoutCopy(data, size));
```

**设计理念**:
- 使用 `MakeWithoutCopy` 避免数据复制
- 延迟解码直到实际需要(drawImage 时)
- 测试完整的解码和渲染管线

### 表面配置

```cpp
auto s = SkSurfaces::Raster(SkImageInfo::MakeN32Premul(128, 128));
```

- **尺寸**: 128x128 像素(足以触发解码逻辑)
- **格式**: N32 预乘 Alpha(标准配置)
- **目的**: 触发实际的像素解码

### 错误处理

```cpp
if (nullptr == img.get()) {
    return false;
}

if (!s) {
    // May return nullptr in memory-constrained fuzzing environments
    return false;
}
```

处理解码失败和内存分配失败的情况。

### 输入大小限制

```cpp
if (size > 10240) {
    return 0;
}
```

限制为 10KB,防止过大图像导致超时。

## 依赖关系

**核心模块**:
- `include/core/SkCanvas.h`: 画布绘制
- `include/core/SkData.h`: 数据封装
- `include/core/SkImage.h`: 图像对象
- `include/core/SkPaint.h`: 绘制属性
- `include/core/SkSurface.h`: 绘制表面

**编解码模块**:
- 自动检测并调用相应的解码器(JPEG, PNG, WebP, GIF 等)

## 设计模式与设计决策

### 1. 格式无关测试

**设计决策**: 不指定图像格式,依赖自动检测
**优点**: 单个测试器覆盖所有支持的格式

### 2. 延迟解码模式

**设计决策**: 使用延迟解码图像
**优点**:
- 测试完整的解码流程
- 模拟实际使用场景
- 触发更多代码路径

### 3. 零复制优化

使用 `MakeWithoutCopy` 提高性能,减少内存开销。

### 4. 最小化验证

不验证解码结果的正确性,仅关注不崩溃。

## 性能考量

### 1. 输入大小限制

10KB 限制平衡了:
- 支持小型完整图像
- 控制解码时间
- 避免内存耗尽

### 2. 表面尺寸选择

128x128 像素:
- 足以触发完整解码路径
- 避免过大的内存分配
- 提高测试吞吐量

### 3. 延迟解码的性能影响

- 仅在需要时解码(drawImage)
- 对于无效数据,提前失败
- 减少不必要的计算

## 相关文件

### 核心依赖

1. **`include/core/SkImage.h`**
   - 图像对象接口
   - 延迟解码支持

2. **编解码器实现**:
   - `src/codec/SkJpegCodec.cpp`
   - `src/codec/SkPngCodec.cpp`
   - `src/codec/SkWebpCodec.cpp`
   - 等其他格式解码器

### 同类型测试器

3. **`fuzz/oss_fuzz/FuzzAnimatedImage.cpp`**
   - 测试动画图像(GIF, WebP)

4. **`fuzz/oss_fuzz/FuzzBMPRustDecoder.cpp`**
   - 专门测试 BMP 解码器

### 测试文件

5. **`tests/CodecTest.cpp`**
   - 编解码器单元测试

6. **`gm/image.cpp`**
   - 图像绘制的视觉测试

该模糊测试器通过简洁的设计,为 Skia 的通用图像解码功能提供了全面的安全性保障,支持多种图像格式,确保在处理任意输入时的稳定性。
