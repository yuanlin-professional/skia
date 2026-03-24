# SkImageInfo

> 源文件
> - include/core/SkImageInfo.h
> - src/core/SkImageInfo.cpp

## 概述

`SkImageInfo` 是 Skia 中描述像素数据格式和尺寸的核心数据结构。它封装了图像的四个关键属性:宽度、高度、颜色类型(SkColorType)、透明度类型(SkAlphaType)和色彩空间(SkColorSpace)。该类是 Skia 中几乎所有图像处理操作的基础,被 SkBitmap、SkImage、SkPixmap 和 SkSurface 等类广泛使用。

`SkImageInfo` 与 `SkColorInfo` 配合工作,前者包含尺寸信息,后者包含颜色编码信息。这种设计允许独立地描述像素格式和图像尺寸,提供了更好的模块化和复用性。

## 架构位置

`SkImageInfo` 在 Skia 架构中处于基础层,被广泛使用:

```
应用层
    ↓
SkImage / SkBitmap / SkPixmap / SkSurface (使用 SkImageInfo 描述格式)
    ↓
SkImageInfo (尺寸 + SkColorInfo)
    ↓
SkColorType, SkAlphaType, SkColorSpace (基础类型)
```

它是连接高层图像 API 和底层像素表示的桥梁。

## 主要类与结构体

### SkColorInfo

**继承关系:**
- 无继承,值类型

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fColorSpace | sk_sp&lt;SkColorSpace&gt; | 色彩空间(可为空) |
| fColorType | SkColorType | 颜色类型(如 RGBA_8888) |
| fAlphaType | SkAlphaType | 透明度类型(Opaque/Premul/Unpremul) |

**关键方法:**

| 方法 | 说明 |
|------|------|
| colorType() | 返回颜色类型 |
| alphaType() | 返回透明度类型 |
| colorSpace() | 返回色彩空间指针 |
| refColorSpace() | 返回色彩空间智能指针 |
| isOpaque() | 判断是否完全不透明 |
| bytesPerPixel() | 每像素字节数 |
| shiftPerPixel() | 用于位移计算的偏移量 |
| makeAlphaType() | 创建具有不同 alpha 类型的副本 |
| makeColorType() | 创建具有不同颜色类型的副本 |
| makeColorSpace() | 创建具有不同色彩空间的副本 |

### SkImageInfo

**继承关系:**
- 无继承,值类型(struct)

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fColorInfo | SkColorInfo | 颜色信息 |
| fDimensions | SkISize | 尺寸(宽度和高度) |

**关键方法:**

| 方法 | 说明 |
|------|------|
| width() / height() | 获取尺寸 |
| dimensions() | 返回 SkISize |
| bounds() | 返回 SkIRect {0, 0, width, height} |
| colorInfo() | 返回 SkColorInfo |
| isEmpty() | 检查是否为空(宽或高为0) |
| makeWH() / makeDimensions() | 创建不同尺寸的副本 |
| minRowBytes() / minRowBytes64() | 计算最小行字节数 |
| computeByteSize() | 计算像素数据总大小 |
| validRowBytes() | 验证行字节数是否合法 |

## 公共 API 函数

### SkColorTypeBytesPerPixel

```cpp
SK_API int SkColorTypeBytesPerPixel(SkColorType ct);
```

**功能:** 返回给定颜色类型每像素占用的字节数。

**返回值:**
- kUnknown_SkColorType: 0
- kAlpha_8_SkColorType: 1
- kRGB_565_SkColorType: 2
- kRGBA_8888_SkColorType: 4
- kRGBA_F32_SkColorType: 16
- 等等...

### SkColorTypeIsAlwaysOpaque

```cpp
SK_API bool SkColorTypeIsAlwaysOpaque(SkColorType ct);
```

**功能:** 判断颜色类型是否始终完全不透明(没有 alpha 通道)。

**实现:**
```cpp
return !(SkColorTypeChannelFlags(ct) & kAlpha_SkColorChannelFlag);
```

### SkColorTypeValidateAlphaType

```cpp
SK_API bool SkColorTypeValidateAlphaType(SkColorType colorType, SkAlphaType alphaType,
                                         SkAlphaType* canonical = nullptr);
```

**功能:** 验证 alpha 类型是否与颜色类型兼容,并返回规范化的 alpha 类型。

**规则:**
1. **不透明颜色类型(如 RGB_565):** 强制使用 kOpaque_SkAlphaType
2. **纯 alpha 类型(如 Alpha_8):** kUnpremul 自动转换为 kPremul
3. **普通 RGBA 类型:** 不接受 kUnknown_SkAlphaType

### SkYUVColorSpaceIsLimitedRange

```cpp
SK_API bool SkYUVColorSpaceIsLimitedRange(SkYUVColorSpace cs);
```

**功能:** 判断 YUV 色彩空间是否使用受限范围(limited range)。

**说明:**
- Limited range: Y 范围 [16, 235], U/V 范围 [16, 240]
- Full range: Y/U/V 范围 [0, 255]

### SkImageInfo 工厂方法

#### Make

```cpp
static SkImageInfo Make(int width, int height, SkColorType ct, SkAlphaType at,
                        sk_sp<SkColorSpace> cs = nullptr);
static SkImageInfo Make(SkISize dimensions, SkColorType ct, SkAlphaType at,
                        sk_sp<SkColorSpace> cs = nullptr);
static SkImageInfo Make(SkISize dimensions, const SkColorInfo& colorInfo);
```

**功能:** 通用工厂方法,创建任意配置的 SkImageInfo。

#### MakeN32

```cpp
static SkImageInfo MakeN32(int width, int height, SkAlphaType at,
                           sk_sp<SkColorSpace> cs = nullptr);
```

**功能:** 创建使用平台原生32位颜色格式的 SkImageInfo。

**说明:** kN32_SkColorType 在不同平台可能是 kBGRA_8888 或 kRGBA_8888。

#### MakeS32

```cpp
static SkImageInfo MakeS32(int width, int height, SkAlphaType at);
```

**功能:** 创建 N32 格式 + sRGB 色彩空间的 SkImageInfo。

#### MakeN32Premul

```cpp
static SkImageInfo MakeN32Premul(int width, int height, sk_sp<SkColorSpace> cs = nullptr);
static SkImageInfo MakeN32Premul(SkISize dimensions, sk_sp<SkColorSpace> cs = nullptr);
```

**功能:** 创建 N32 格式 + 预乘 alpha 的 SkImageInfo(最常用的配置)。

#### MakeA8

```cpp
static SkImageInfo MakeA8(int width, int height);
static SkImageInfo MakeA8(SkISize dimensions);
```

**功能:** 创建纯 alpha 通道(8位)的 SkImageInfo。

#### MakeUnknown

```cpp
static SkImageInfo MakeUnknown(int width, int height);
static SkImageInfo MakeUnknown();
```

**功能:** 创建未知格式的 SkImageInfo(用于表示无效或未初始化的图像)。

### 尺寸和内存计算

#### minRowBytes / minRowBytes64

```cpp
size_t minRowBytes() const;
uint64_t minRowBytes64() const;
```

**功能:** 计算最小行字节数。

**公式:**
```cpp
minRowBytes64 = width() * bytesPerPixel()
```

**注意:** minRowBytes() 会检查是否溢出 int32_t,溢出则返回 0。

#### computeByteSize

```cpp
size_t computeByteSize(size_t rowBytes) const;
```

**功能:** 计算给定行字节数下的总像素数据大小。

**公式:**
```cpp
bytes = (height - 1) * rowBytes + width * bytesPerPixel
```

**特殊情况:**
- height 为 0: 返回 0
- 计算溢出: 返回 SIZE_MAX
- 结果超过 SK_MaxS32: 返回 SIZE_MAX (防止有符号 32 位溢出,crbug.com/1264705)

#### computeMinByteSize

```cpp
size_t computeMinByteSize() const;
```

**功能:** 使用 minRowBytes() 计算最小总大小。

#### computeOffset

```cpp
size_t computeOffset(int x, int y, size_t rowBytes) const;
```

**功能:** 计算像素 (x, y) 在内存中的字节偏移。

**公式:**
```cpp
offset = y * rowBytes + (x << shiftPerPixel())
```

#### validRowBytes

```cpp
bool validRowBytes(size_t rowBytes) const;
```

**功能:** 验证行字节数是否合法。

**规则:**
1. rowBytes >= minRowBytes()
2. rowBytes 必须是像素大小的整数倍(对齐要求)

## 内部实现细节

### SkColorInfo 实现

**默认构造:**
```cpp
SkColorInfo::SkColorInfo()
    : fColorSpace(nullptr)
    , fColorType(kUnknown_SkColorType)
    , fAlphaType(kUnknown_SkAlphaType)
{}
```

**相等比较:**
```cpp
bool SkColorInfo::operator==(const SkColorInfo& other) const {
    return fColorType == other.fColorType &&
           fAlphaType == other.fAlphaType &&
           SkColorSpace::Equals(fColorSpace.get(), other.fColorSpace.get());
}
```

**注意:** 色彩空间使用 `SkColorSpace::Equals()` 进行值比较,而不是指针比较。

### shiftPerPixel 计算

```cpp
int SkColorInfo::shiftPerPixel() const {
    return SkColorTypeShiftPerPixel(fColorType);
}
```

**用途:** 将像素索引转换为字节偏移的位移量。

**示例:**
- 1 字节/像素: shift = 0 (x << 0 = x * 1)
- 2 字节/像素: shift = 1 (x << 1 = x * 2)
- 4 字节/像素: shift = 2 (x << 2 = x * 4)
- 8 字节/像素: shift = 3 (x << 3 = x * 8)

### computeByteSize 实现

```cpp
size_t SkImageInfo::computeByteSize(size_t rowBytes) const {
    if (0 == this->height()) {
        return 0;
    }
    SkSafeMath safe;
    size_t bytes = safe.add(safe.mul(safe.addInt(this->height(), -1), rowBytes),
                            safe.mul(this->width(), this->bytesPerPixel()));

    constexpr size_t kMaxSigned32BitSize = SK_MaxS32;
    return (safe.ok() && (bytes <= kMaxSigned32BitSize)) ? bytes : SIZE_MAX;
}
```

**安全检查:**
1. 使用 `SkSafeMath` 检测整数溢出
2. 确保结果不超过 SK_MaxS32(2GB - 1)

**原因:** CPU 后端某些内存操作使用有符号 32 位偏移,超过 2GB 会导致读取错误内存(crbug.com/1264705)。

### validRowBytes 实现

```cpp
bool validRowBytes(size_t rowBytes) const {
    if (rowBytes < this->minRowBytes64()) {
        return false;
    }
    int shift = this->shiftPerPixel();
    size_t alignedRowBytes = rowBytes >> shift << shift;
    return alignedRowBytes == rowBytes;
}
```

**对齐检查:** 确保 rowBytes 是像素大小的整数倍。

**示例:**
- 4 字节/像素 (shift=2): rowBytes 必须是 4 的倍数
- 如果 rowBytes = 15,alignedRowBytes = (15 >> 2) << 2 = 12,不相等,返回 false

### SkColorTypeValidateAlphaType 实现

```cpp
bool SkColorTypeValidateAlphaType(SkColorType colorType, SkAlphaType alphaType,
                                  SkAlphaType* canonical) {
    switch (colorType) {
        case kUnknown_SkColorType:
            alphaType = kUnknown_SkAlphaType;
            break;
        case kAlpha_8_SkColorType:
        case kA16_unorm_SkColorType:
        case kA16_float_SkColorType:
            if (kUnpremul_SkAlphaType == alphaType) {
                alphaType = kPremul_SkAlphaType;  // 规范化
            }
            [[fallthrough]];
        case kRGBA_8888_SkColorType:
            // ... 其他支持 alpha 的类型
            if (kUnknown_SkAlphaType == alphaType) {
                return false;  // 必须指定 alpha 类型
            }
            break;
        case kRGB_565_SkColorType:
            // ... 不透明类型
            alphaType = kOpaque_SkAlphaType;  // 强制不透明
            break;
    }
    if (canonical) {
        *canonical = alphaType;
    }
    return true;
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkColorType | 颜色类型定义 |
| SkAlphaType | 透明度类型定义 |
| SkColorSpace | 色彩空间 |
| SkRect / SkIRect | 矩形和尺寸 |
| SkRefCnt | 引用计数 |
| SkSafeMath | 安全整数运算 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|----------|
| SkBitmap | 描述位图格式 |
| SkImage | 描述图像格式 |
| SkPixmap | 描述像素映射格式 |
| SkSurface | 描述绘制表面格式 |
| SkImageGenerator | 图像解码器输出格式 |
| SkCodec | 图像编解码器 |
| GPU 纹理 | 纹理格式描述 |

## 设计模式与设计决策

### 值语义设计

`SkImageInfo` 和 `SkColorInfo` 都使用值语义:
- **优势:** 简单、高效、线程安全
- **复制成本:** 由于包含 `sk_sp<SkColorSpace>`,复制会增加引用计数

**设计决策:** SkColorSpace 不经常变化,引用计数的共享优于深拷贝。

### 组合模式

`SkImageInfo` 包含 `SkColorInfo`:
```cpp
struct SkImageInfo {
    SkColorInfo fColorInfo;
    SkISize fDimensions;
};
```

**优势:**
- **模块化:** 独立描述颜色和尺寸
- **复用:** `SkColorInfo` 可以独立使用
- **灵活性:** 可以轻松创建不同尺寸但相同颜色配置的 ImageInfo

### 工厂方法模式

提供多个静态工厂方法:
- `Make()`: 通用
- `MakeN32()`: 原生格式
- `MakeS32()`: sRGB
- `MakeN32Premul()`: 最常用配置
- `MakeA8()`: alpha 通道
- `MakeUnknown()`: 未知格式

**优势:**
- 表达意图清晰
- 减少参数传递错误
- 提供合理的默认值

### 不可变性与副本方法

`make*()` 方法返回新的 SkImageInfo:
```cpp
SkImageInfo makeAlphaType(SkAlphaType newAlphaType) const;
SkImageInfo makeColorType(SkColorType newColorType) const;
SkImageInfo makeColorSpace(sk_sp<SkColorSpace> cs) const;
SkImageInfo makeWH(int newWidth, int newHeight) const;
```

**优势:**
- 不可变性简化并发
- 避免意外修改
- 函数式风格,易于理解

### 安全整数运算

使用 `SkSafeMath` 检测溢出:
```cpp
SkSafeMath safe;
size_t bytes = safe.add(safe.mul(...), safe.mul(...));
return safe.ok() ? bytes : SIZE_MAX;
```

**设计理由:**
- 避免安全漏洞
- 明确处理异常情况
- SIZE_MAX 作为特殊标记值

### 2GB 限制

`computeByteSize()` 强制限制为 SK_MaxS32:

**背景:** CPU 后端使用有符号 32 位偏移访问内存,超过 2GB 会导致负偏移。

**权衡:** 限制单个图像大小,但避免了内存安全问题。

## 性能考量

### 内联小方法

许多访问器方法在头文件中实现:
```cpp
int width() const { return fDimensions.width(); }
int height() const { return fDimensions.height(); }
bool isEmpty() const { return fDimensions.isEmpty(); }
```

编译器可以内联这些方法,零运行时开销。

### 引用计数共享

`SkColorSpace` 使用 `sk_sp` 引用计数:
- **优势:** 避免深拷贝色彩空间数据
- **成本:** 原子操作增减引用计数

**权衡:** SkColorSpace 通常很小(几个常见的 sRGB, AdobeRGB 等),共享是值得的。

### 位移优化

使用位移而不是乘法计算偏移:
```cpp
offset = y * rowBytes + (x << shiftPerPixel());
```

位移通常比乘法快(尤其在简单的 CPU 上)。

### 缓存计算结果

某些方法使用缓存策略:
```cpp
int bytesPerPixel() const {
    return SkColorTypeBytesPerPixel(fColorType);  // 静态 switch,可能被编译器优化
}
```

编译器可能将 `SkColorTypeBytesPerPixel()` 内联,消除函数调用。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| include/core/SkColorType.h | 依赖 | 颜色类型定义 |
| include/core/SkAlphaType.h | 依赖 | 透明度类型定义 |
| include/core/SkColorSpace.h | 依赖 | 色彩空间 |
| src/core/SkImageInfoPriv.h | 扩展 | 内部辅助函数 |
| include/core/SkBitmap.h | 使用者 | 位图类 |
| include/core/SkImage.h | 使用者 | 图像类 |
| include/core/SkPixmap.h | 使用者 | 像素映射类 |
| include/core/SkSurface.h | 使用者 | 绘制表面类 |
| src/base/SkSafeMath.h | 依赖 | 安全整数运算 |
