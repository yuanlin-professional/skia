# SkAndroidCodecAdapter

> 源文件: src/codec/SkAndroidCodecAdapter.h, src/codec/SkAndroidCodecAdapter.cpp

## 概述

`SkAndroidCodecAdapter` 是 Android 平台解码器的适配器类，将标准的 `SkCodec` 接口适配为 Android 专用的 `SkAndroidCodec` 接口。该类为支持采样解码（sampled decoding）的编解码器提供包装，使其可以在 Android 系统中使用。

该适配器实现了 Android 特有的缩放和子区域解码功能，通过调用底层 `SkCodec` 的对应方法来完成实际工作。对于不支持采样解码的编解码器，Skia 会使用 `SkSampledCodec` 进行包装。

## 架构位置

在 Android 解码器架构中的位置：

```
SkAndroidCodec (Android 解码器基类)
    ↓
SkAndroidCodecAdapter (适配器)
    ↓
SkCodec (标准解码器)
```

**职责**:
- 适配 `SkCodec` 到 `SkAndroidCodec` 接口
- 转发采样尺寸查询
- 转发子区域支持查询
- 转发像素解码请求

**使用场景**: 当底层 `SkCodec` 已经支持采样和缩放功能时使用此适配器。

## 主要类与结构体

### SkAndroidCodecAdapter 类

**继承关系**: `SkAndroidCodecAdapter → SkAndroidCodec → SkCodec → SkRefCnt`

**构造函数**:
```cpp
explicit SkAndroidCodecAdapter(SkCodec* codec)
```
接收 `SkCodec` 指针并传递给父类 `SkAndroidCodec`。生命周期由父类管理。

## 公共 API 函数

### 尺寸查询

**onGetSampledDimensions**
```cpp
SkISize onGetSampledDimensions(int sampleSize) const override
```
根据采样大小获取缩放后的尺寸：
1. 将采样大小转换为缩放比例（通过 `SkCodecPriv::GetScaleFromSampleSize`）
2. 调用底层编解码器的 `getScaledDimensions` 方法

**参数**: `sampleSize` - 采样大小（例如 2 表示宽高各缩小一半）

### 子区域支持

**onGetSupportedSubset**
```cpp
bool onGetSupportedSubset(SkIRect* desiredSubset) const override
```
查询是否支持指定的子区域解码，并可能调整子区域为支持的范围。直接调用底层编解码器的 `getValidSubset` 方法。

**参数**: `desiredSubset` - 输入/输出参数，期望的子区域矩形

### 像素解码

**onGetAndroidPixels**
```cpp
SkCodec::Result onGetAndroidPixels(const SkImageInfo& info, void* pixels,
                                    size_t rowBytes, const AndroidOptions& options) override
```
执行实际的像素解码，将 Android 特有的选项转换为标准 `SkCodec` 选项并调用底层解码器的 `getPixels` 方法。

**参数**:
- `info` - 目标图像信息
- `pixels` - 输出像素缓冲区
- `rowBytes` - 行字节数
- `options` - Android 解码选项（包含采样、子区域等）

## 内部实现细节

### 采样大小到缩放比例的转换

使用 `SkCodecPriv::GetScaleFromSampleSize` 将整数采样大小转换为浮点缩放比例：
```cpp
float scale = SkCodecPriv::GetScaleFromSampleSize(sampleSize);
// sampleSize = 2 → scale = 0.5
// sampleSize = 4 → scale = 0.25
```

### 选项透传

`AndroidOptions` 是 `SkCodec::Options` 的子类，因此可以直接传递给底层编解码器：
```cpp
return this->codec()->getPixels(info, pixels, rowBytes, &options);
```

这种设计避免了不必要的数据复制和转换。

## 依赖关系

### 直接依赖
- **SkAndroidCodec**: 父类，定义 Android 解码器接口
- **SkCodec**: 底层编解码器
- **SkCodecPriv**: 内部工具函数（采样大小转换）

### 被依赖
- **Android 系统**: 通过 `SkAndroidCodec` 工厂方法创建
- **Skia Android 集成层**: 在 Android 平台上使用

## 设计模式与设计决策

### 适配器模式（Adapter Pattern）

经典的适配器模式实现：
- **目标接口**: `SkAndroidCodec`
- **被适配者**: `SkCodec`
- **适配器**: `SkAndroidCodecAdapter`

**好处**:
- 不修改现有 `SkCodec` 实现
- 统一 Android 平台的接口
- 允许特定于 Android 的优化

### 对象组合优于继承

虽然 `SkAndroidCodecAdapter` 继承自 `SkAndroidCodec`，但它通过组合的方式持有 `SkCodec`（存储在父类中）：
- 避免多重继承
- 清晰的职责分离
- 灵活的实现替换

### 最小化适配器

适配器仅包含三个简单的转发方法，保持极简设计：
- 无额外状态
- 零开销转发
- 易于维护

## 性能考量

### 零拷贝设计

所有方法都直接转发，不进行数据复制：
- 指针直接传递
- 引用传递避免拷贝
- 内联候选（方法很小）

### 虚函数调用开销

作为适配器，每次调用都会经过两层虚函数：
1. `SkAndroidCodecAdapter::onGetAndroidPixels`
2. `SkCodec::getPixels`

对于小批量解码可能有轻微影响，但对于整帧解码可忽略。

### 采样效率

依赖底层 `SkCodec` 的采样实现效率。适配器本身不影响性能。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/codec/SkAndroidCodec.h` | 父类 | Android 解码器基类 |
| `include/codec/SkCodec.h` | 依赖 | 标准解码器接口 |
| `src/codec/SkCodecPriv.h` | 工具 | 内部工具函数 |
| `src/codec/SkSampledCodec.h` | 替代实现 | 不支持采样的编解码器使用 |
| `include/core/SkSize.h` | 数据结构 | 尺寸类型 |
