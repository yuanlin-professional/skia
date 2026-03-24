# SkImageInfoPriv

> 源文件
> - src/core/SkImageInfoPriv.h

## 概述

`SkImageInfoPriv.h` 是 Skia 内部使用的辅助头文件,提供了一系列用于 SkColorType 和 SkImageInfo 的工具函数。这些函数不是公共 API 的一部分,而是在 Skia 内部实现中广泛使用,用于查询颜色类型的属性、计算像素偏移、验证图像信息的有效性等。

该文件是 `SkImageInfo` 公共 API 的补充,提供了更多底层和性能关键的实用工具。

## 架构位置

`SkImageInfoPriv` 在 Skia 架构中的位置:

```
SkImageInfo (公共 API)
    ↓
SkImageInfoPriv (内部工具函数)
    ↓
Skia 内部实现 (SkBitmap, SkPixmap, SkCodec, etc.)
```

它是连接公共 API 和内部实现的辅助层。

## 主要函数

### SkColorTypeChannelFlags

```cpp
static inline uint32_t SkColorTypeChannelFlags(SkColorType ct);
```

**功能:** 返回颜色类型包含的通道标志。

**返回值:** 通道标志的位掩码,可能的值包括:
- `kAlpha_SkColorChannelFlag`: 包含 alpha 通道
- `kRed_SkColorChannelFlag`: 包含红色通道
- `kGreen_SkColorChannelFlag`: 包含绿色通道
- `kBlue_SkColorChannelFlag`: 包含蓝色通道
- `kGray_SkColorChannelFlag`: 灰度通道
- `kRG_SkColorChannelFlags`: R+G 通道
- `kRGB_SkColorChannelFlags`: R+G+B 通道
- `kRGBA_SkColorChannelFlags`: R+G+B+A 通道
- `kGrayAlpha_SkColorChannelFlags`: 灰度+Alpha

**实现示例:**
```cpp
case kRGBA_8888_SkColorType: return kRGBA_SkColorChannelFlags;
case kRGB_565_SkColorType:   return kRGB_SkColorChannelFlags;
case kAlpha_8_SkColorType:   return kAlpha_SkColorChannelFlag;
case kGray_8_SkColorType:    return kGray_SkColorChannelFlag;
```

### SkColorTypeNumChannels

```cpp
static inline int SkColorTypeNumChannels(SkColorType ct);
```

**功能:** 返回颜色类型的通道数量。

**返回值:**
- 0: kUnknown_SkColorType
- 1: 单通道(Alpha, Red, Gray)
- 2: 双通道(RG, GrayAlpha)
- 3: 三通道(RGB)
- 4: 四通道(RGBA)

**实现:** 基于 `SkColorTypeChannelFlags()` 的结果计算。

### SkColorTypeIsAlphaOnly

```cpp
static inline bool SkColorTypeIsAlphaOnly(SkColorType ct);
```

**功能:** 判断颜色类型是否仅包含 alpha 通道。

**返回值:**
- true: 如 kAlpha_8_SkColorType, kA16_unorm_SkColorType
- false: 其他类型

**实现:**
```cpp
return SkColorTypeChannelFlags(ct) == kAlpha_SkColorChannelFlag;
```

### SkAlphaTypeIsValid

```cpp
static inline bool SkAlphaTypeIsValid(unsigned value);
```

**功能:** 验证 alpha 类型枚举值是否有效。

**实现:**
```cpp
return value <= kLastEnum_SkAlphaType;
```

**用途:** 反序列化验证、边界检查。

### SkColorTypeShiftPerPixel

```cpp
static int SkColorTypeShiftPerPixel(SkColorType ct);
```

**功能:** 返回用于像素索引到字节偏移转换的位移量。

**返回值:**
- 0: 1 字节/像素 (如 Alpha_8, Gray_8)
- 1: 2 字节/像素 (如 RGB_565, ARGB_4444)
- 2: 4 字节/像素 (如 RGBA_8888, BGRA_8888)
- 3: 8 字节/像素 (如 RGBA_F16, RGBA_10x6)
- 4: 16 字节/像素 (如 RGBA_F32)

**用途:** 计算像素偏移
```cpp
offset = y * rowBytes + (x << shift);
```

### SkColorTypeMinRowBytes

```cpp
static inline size_t SkColorTypeMinRowBytes(SkColorType ct, int width);
```

**功能:** 计算给定宽度的最小行字节数。

**实现:**
```cpp
return (size_t)(width * SkColorTypeBytesPerPixel(ct));
```

**注意:** 不考虑对齐要求,只是简单的乘法。

### SkColorTypeIsValid

```cpp
static inline bool SkColorTypeIsValid(unsigned value);
```

**功能:** 验证颜色类型枚举值是否有效。

**实现:**
```cpp
return value <= kLastEnum_SkColorType;
```

### SkColorTypeComputeOffset

```cpp
static inline size_t SkColorTypeComputeOffset(SkColorType ct, int x, int y, size_t rowBytes);
```

**功能:** 计算像素 (x, y) 在内存中的字节偏移。

**实现:**
```cpp
SkASSERT(x >= 0);
SkASSERT(y >= 0);
if (kUnknown_SkColorType == ct) {
    return 0;
}
return (size_t)y * rowBytes + ((size_t)x << SkColorTypeShiftPerPixel(ct));
```

**公式:**
```
offset = y * rowBytes + x * bytesPerPixel
       = y * rowBytes + (x << shiftPerPixel)
```

### SkColorTypeIsNormalized

```cpp
static inline bool SkColorTypeIsNormalized(SkColorType ct);
```

**功能:** 判断颜色类型是否使用归一化表示(值范围 [0, 1])。

**返回值:**
- true: 整数类型(如 RGBA_8888, RGB_565),值自动归一化到 [0, 1]
- true: F16Norm 类型(浮点但保证在 [0, 1])
- false: 扩展范围类型(如 RGBA_F16, RGBA_F32, XR 类型)

**用途:** 判断是否需要手动钳制颜色值。

### SkColorTypeMaxBitsPerChannel

```cpp
static inline int SkColorTypeMaxBitsPerChannel(SkColorType ct);
```

**功能:** 返回颜色类型中单个通道的最大位数。

**示例:**
- kRGBA_8888_SkColorType: 8
- kRGB_565_SkColorType: 6 (green 通道有 6 位)
- kRGBA_1010102_SkColorType: 10
- kRGBA_F16_SkColorType: 16
- kRGBA_F32_SkColorType: 32

**用途:** 确定精度需求、选择适当的中间格式。

### SkColorInfoIsValid

```cpp
static inline bool SkColorInfoIsValid(const SkColorInfo& info);
```

**功能:** 验证 SkColorInfo 是否有效。

**实现:**
```cpp
return info.colorType() != kUnknown_SkColorType &&
       info.alphaType() != kUnknown_SkAlphaType;
```

### SkImageInfoIsValid

```cpp
static inline bool SkImageInfoIsValid(const SkImageInfo& info);
```

**功能:** 验证 SkImageInfo 是否有效。

**验证规则:**
1. 宽度和高度必须 > 0
2. 宽度和高度不能超过 SK_MaxS32 >> 2
3. SkColorInfo 必须有效

**实现:**
```cpp
if (info.width() <= 0 || info.height() <= 0) {
    return false;
}
const int kMaxDimension = SK_MaxS32 >> 2;
if (info.width() > kMaxDimension || info.height() > kMaxDimension) {
    return false;
}
return SkColorInfoIsValid(info.colorInfo());
```

**尺寸限制原因:** 防止整数溢出,保证 `width * height * 4` 不会超过 int 范围。

### SkImageInfoValidConversion

```cpp
static inline bool SkImageInfoValidConversion(const SkImageInfo& dst, const SkImageInfo& src);
```

**功能:** 验证是否可以从 src 格式转换到 dst 格式。

**实现:**
```cpp
return SkImageInfoIsValid(dst) && SkImageInfoIsValid(src);
```

**注意:** 当前实现只验证有效性,不检查具体转换是否支持。

## 内部实现细节

### 通道标志的实现

使用大的 switch 语句映射颜色类型到通道标志:

```cpp
static inline uint32_t SkColorTypeChannelFlags(SkColorType ct) {
    switch (ct) {
        case kUnknown_SkColorType:            return 0;
        case kAlpha_8_SkColorType:            return kAlpha_SkColorChannelFlag;
        case kRGB_565_SkColorType:            return kRGB_SkColorChannelFlags;
        case kARGB_4444_SkColorType:          return kRGBA_SkColorChannelFlags;
        case kRGBA_8888_SkColorType:          return kRGBA_SkColorChannelFlags;
        // ... 50+ 个颜色类型
    }
    SkUNREACHABLE;
}
```

**优化:** 编译器可以生成跳转表或二分查找,查询效率高。

### shift 值的计算

shiftPerPixel 也使用 switch:

```cpp
static int SkColorTypeShiftPerPixel(SkColorType ct) {
    switch (ct) {
        case kUnknown_SkColorType:            return 0;
        case kAlpha_8_SkColorType:            return 0;  // 1 字节
        case kRGB_565_SkColorType:            return 1;  // 2 字节
        case kRGBA_8888_SkColorType:          return 2;  // 4 字节
        case kRGBA_F16_SkColorType:           return 3;  // 8 字节
        case kRGBA_F32_SkColorType:           return 4;  // 16 字节
        // ...
    }
    SkUNREACHABLE;
}
```

**关系:**
```
bytesPerPixel = 1 << shiftPerPixel
```

### 位数表的实现

maxBitsPerChannel 返回最大通道位数:

```cpp
case kRGB_565_SkColorType:
    return 6;  // green 有 6 位,red 和 blue 只有 5 位
case kRGBA_1010102_SkColorType:
    return 10;  // RGB 各有 10 位,alpha 只有 2 位
```

返回"最大"位数,而不是平均位数。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkColor | 通道标志定义 |
| SkColorType | 颜色类型枚举 |
| SkImageInfo | 图像信息结构 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|----------|
| SkImageInfo.cpp | 公共 API 实现 |
| SkBitmap | 位图内部实现 |
| SkPixmap | 像素映射 |
| SkCodec | 编解码器 |
| SkSurface | 绘制表面 |
| GPU 后端 | 纹理格式查询 |

## 设计模式与设计决策

### 内联函数设计

所有函数都是 `static inline`:
- **优势:** 零函数调用开销
- **位置:** 在头文件中实现,编译器可见性好

**权衡:** 增加编译时间,但运行时效率最高。

### Switch vs 表查找

使用 switch 而不是查找表:
- **优势:** 编译器可以优化为跳转表或二分查找
- **优势:** 添加新颜色类型时会有编译错误(missing case)
- **劣势:** 代码较长

**设计理由:** 类型安全和可维护性优于代码简洁性。

### 分离通道信息和字节信息

分别提供 `SkColorTypeChannelFlags` 和 `SkColorTypeBytesPerPixel`:
- **灵活性:** 可以独立查询不同属性
- **性能:** 避免返回复杂结构体

### 尺寸限制设计

`SkImageInfoIsValid` 限制最大尺寸为 `SK_MaxS32 >> 2`:

**原因:**
```cpp
const int kMaxDimension = SK_MaxS32 >> 2;
```

**计算:**
```
SK_MaxS32 = 2^31 - 1
kMaxDimension = (2^31 - 1) / 4 = 536,870,911
```

**保证:**
```
width * height * 4 (RGBA) < 2^31
```

防止在计算总大小时整数溢出。

## 性能考量

### 内联优化

所有函数内联,常用路径零开销:
```cpp
// 内联后
offset = y * rowBytes + (x << 2);  // 直接计算,无函数调用
```

### 编译器优化

Switch 语句可以被编译器优化:
- **小范围:** 比较链
- **连续值:** 跳转表
- **稀疏值:** 二分查找

### 位移优化

使用位移而不是乘法:
```cpp
(x << shiftPerPixel)  // 比 x * bytesPerPixel 更快
```

在简单的 CPU 上,位移通常单周期,乘法多周期。

### SkUNREACHABLE 宏

Switch 语句末尾使用 `SkUNREACHABLE`:
```cpp
switch (ct) {
    // ... 所有 case
}
SkUNREACHABLE;
```

**作用:**
- 告诉编译器不需要默认分支
- 未处理的枚举值会产生编译警告
- 生成更优化的代码

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| include/core/SkImageInfo.h | 补充 | 公共 API |
| include/core/SkColorType.h | 依赖 | 颜色类型定义 |
| include/core/SkColor.h | 依赖 | 通道标志定义 |
| src/core/SkImageInfo.cpp | 使用者 | 公共 API 实现 |
| src/core/SkBitmap.cpp | 使用者 | 位图实现 |
| src/core/SkPixmap.cpp | 使用者 | 像素映射实现 |
| src/codec/SkCodec.cpp | 使用者 | 编解码器 |
