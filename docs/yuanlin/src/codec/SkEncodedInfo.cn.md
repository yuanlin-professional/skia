# SkEncodedInfo - 编码图像信息

> 源文件: `src/codec/SkEncodedInfo.cpp`

## 概述

`SkEncodedInfo.cpp` 实现了 `SkEncodedInfo` 类的方法，该类存储编码图像的基本属性信息，包括尺寸、颜色类型、alpha 类型、位深度、颜色配置文件和 HDR 元数据。它是编解码器与图像处理管线之间的信息桥梁，将编码格式的原始属性转换为 Skia 的 `SkImageInfo` 表示。

## 架构位置

该文件位于 `src/codec/` 目录下，`SkEncodedInfo` 是所有图像编解码器的核心数据结构之一。每个解码器在初始化时创建一个 `SkEncodedInfo` 实例来描述编码图像的属性。该信息随后用于确定解码目标格式、颜色空间转换需求和像素缓冲区分配。

## 主要类与结构体

### `SkEncodedInfo`
（类定义在 `include/private/SkEncodedInfo.h` 中。）

## 公共 API 函数

### `SkEncodedInfo::makeImageInfo() const`
将编码信息转换为 `SkImageInfo`。颜色类型映射规则：
- `kGray_Color` -> `kGray_8_SkColorType`
- `kXAlpha_Color` -> `kAlpha_8_SkColorType`
- `k565_Color` -> `kRGB_565_SkColorType`
- 其他 -> `kN32_SkColorType`

Alpha 类型映射：`kOpaque_Alpha` -> `kOpaque_SkAlphaType`，其他 -> `kUnpremul_SkAlphaType`。
色彩空间：优先使用配置文件的精确色彩空间，回退到 sRGB。

### `SkEncodedInfo::Make(...)` 系列工厂方法
四个重载，逐步增加参数复杂度：
1. `Make(width, height, color, alpha, bitsPerComponent)`: 基本版本
2. `Make(..., ColorProfile)`: 添加颜色配置文件
3. `Make(..., ColorProfile, colorDepth)`: 添加颜色深度
4. `Make(..., colorDepth, ColorProfile, hdrMetadata)`: 完整版本，包含 HDR 元数据

所有版本都通过 `VerifyColor` 进行颜色/alpha/位深度兼容性验证。

### `SkEncodedInfo::profile() const`
返回底层 `skcms_ICCProfile` 指针（无配置文件时返回 nullptr）。

### `SkEncodedInfo::profileData() const`
返回原始 ICC 配置文件数据（无配置文件时返回 nullptr）。

### `SkEncodedInfo::copy() const`
深拷贝，包括颜色配置文件的克隆。

## 内部实现细节

1. **bitsPerComponent 验证**: 通过 `SkASSERT` 限制为 1、2、4、8、16 之一。

2. **默认颜色深度**: 当不显式指定 colorDepth 时，使用 bitsPerComponent 作为默认值。

3. **默认 HDR 元数据**: 不指定时使用 `skhdr::Metadata::MakeEmpty()` 创建空元数据。

4. **移动语义**: 移动构造和移动赋值使用 `= default`，析构函数也是 `= default`。

5. **色彩空间回退**: `makeImageInfo()` 在 `getExactColorSpace()` 返回 nullptr 时回退到 `MakeSRGB()`。

## 依赖关系

- `include/private/SkEncodedInfo.h`: 类定义
- `src/codec/SkCodecPriv.h`: `SkCodecs::ColorProfile` 类

## 设计模式与设计决策

1. **工厂方法链**: 多个 `Make` 重载通过参数级联调用最完整的版本，保持向后兼容。
2. **不可变语义**: `SkEncodedInfo` 一旦创建，其属性不可修改（除非通过移动）。
3. **所有权管理**: `ColorProfile` 通过 `unique_ptr` 持有，确保唯一所有权。

## 性能考量

- **移动语义**: 支持高效的移动操作，避免不必要的拷贝
- **惰性色彩空间**: `makeImageInfo()` 仅在需要时创建 `SkColorSpace`

## 相关文件

- `include/private/SkEncodedInfo.h`: 类定义
- `src/codec/SkCodecPriv.h`: `ColorProfile` 定义
- `include/core/SkImageInfo.h`: 目标图像信息格式
