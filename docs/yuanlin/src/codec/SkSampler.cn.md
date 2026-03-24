# SkSampler - 图像采样器基类

> 源文件: `src/codec/SkSampler.h`, `src/codec/SkSampler.cpp`

## 概述

`SkSampler` 是 Skia 编解码模块中图像采样功能的抽象基类。它为图像解码过程中的降采样（跳过像素/行）提供了统一的接口。当用户请求缩放解码时，采样器通过在 X 和 Y 方向上跳过像素来实现高效的降采样，而无需解码完整分辨率的图像。

## 架构位置

```
SkSampler (抽象基类, 不可拷贝)
  ├── SkSwizzler (像素转换 + 采样)
  ├── SkMaskSwizzler (掩码位图采样)
  └── SkBmpRLESampler (RLE BMP 采样)
```

`SkSampler` 是编解码模块内部使用的基础设施类，不直接暴露给公共 API。

## 主要类与结构体

### `SkSampler`
- 继承自 `SkNoncopyable`
- 管理 Y 方向采样参数 (`fSampleY`)
- 定义 X 方向采样的纯虚接口 (`onSetSampleX`)
- 提供目标缓冲区填充的静态方法 (`Fill`)

## 公共 API 函数

### 采样配置
- `setSampleX(int sampleX)`: 设置 X 方向采样率。返回采样后的宽度。内部调用子类的 `onSetSampleX`。
- `setSampleY(int sampleY)`: 设置 Y 方向采样率。
- `sampleY()`: 获取当前 Y 方向采样率。

### 采样判断
- `rowNeeded(int row)`: 判断给定行是否需要输出。基于 `fSampleY` 和起始坐标计算。

### 填充
- `static Fill(const SkImageInfo&, void* dst, size_t rowBytes, SkCodec::ZeroInitialized)`: 用零值填充目标缓冲区。对于带透明度的颜色类型，零值意味着透明；对于 565 和灰度，零值意味着黑色。

### 纯虚接口
- `virtual int fillWidth() const = 0`: 返回填充宽度
- `virtual int onSetSampleX(int) = 0`: 设置 X 采样率的实现

## 内部实现细节

### `Fill` 方法
根据目标颜色类型使用不同的填充策略：
- `kRGBA_8888` / `kBGRA_8888`: 使用 `SkOpts::memset32` 填充 32 位零值
- `kRGB_565`: 使用 `SkOpts::memset16` 填充 16 位零值
- `kGray_8`: 使用标准 `memset` 填充 8 位零值
- `kRGBA_F16`: 使用 `SkOpts::memset64` 填充 64 位零值

### 零初始化优化
如果内存已经被零初始化（`kYes_ZeroInitialized`），`Fill` 直接返回，避免冗余操作。

### 行选择逻辑
`rowNeeded` 使用公式 `(row - GetStartCoord(fSampleY)) % fSampleY == 0` 判断行是否属于输出集。

## 依赖关系

- `SkNoncopyable`: 禁止拷贝的基类
- `SkCodec`: 提供 `ZeroInitialized` 枚举
- `SkCodecPriv`: 提供 `GetStartCoord` 工具函数
- `SkOpts::memset16/32/64`: 平台优化的内存填充
- `SkImageInfo`: 图像信息（颜色类型、尺寸）

## 设计模式与设计决策

### 模板方法模式
`setSampleX` 是模板方法，调用子类的 `onSetSampleX` 实现。这允许不同的采样器以不同的方式处理 X 采样率。

### 关注点分离
X 和 Y 方向的采样被分开处理。Y 方向采样由基类直接管理（简单的模运算），X 方向采样委托给子类（因为涉及像素级别的操作）。

### 静态填充方法
`Fill` 作为静态方法，可在没有采样器实例的情况下使用，适用于解码不完整图像时填充剩余区域。

## 性能考量

- 使用 `SkOpts` 平台优化的 memset 函数，利用 SIMD 指令加速填充
- 零初始化检测避免冗余的内存写入
- 行选择使用简单的模运算，开销极小

## 相关文件

- `src/codec/SkSwizzler.h` / `.cpp`: 主要的采样器实现
- `src/codec/SkMaskSwizzler.h` / `.cpp`: 掩码采样器
- `src/codec/SkBmpRLECodec.cpp`: `SkBmpRLESampler` 定义
- `src/codec/SkCodecPriv.h`: `GetStartCoord`、`GetSampledDimension` 等工具
- `src/core/SkMemset.h`: 优化的内存填充函数
