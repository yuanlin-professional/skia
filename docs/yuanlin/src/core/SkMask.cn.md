# SkMask

> 源文件: src/core/SkMask.h, src/core/SkMask.cpp

## 概述

`SkMask` 是 Skia 中描述 alpha 位图的核心数据结构,用于表示各种格式的遮罩数据,包括单色 (1bit)、抗锯齿 (8bit)、3D 效果、LCD 亚像素渲染等。该结构体提供了高效的像素访问接口和迭代器,是 mask filter、文字渲染、混合操作的基础。`SkMaskBuilder` 提供了可修改的遮罩构建能力。

## 架构位置

`SkMask` 位于 Skia 渲染管线的遮罩数据层:
- 被 `SkMaskFilter` 用于滤镜效果处理
- 被 `SkBlitter` 用于像素级混合渲染
- 被文字渲染系统用于存储字形光栅化结果
- 为 LCD 亚像素渲染提供专门格式支持

## 主要类与结构体

### 核心类型

| 类名 | 继承关系 | 说明 |
|------|---------|------|
| SkMask | - | 不可变遮罩视图 |
| SkMaskBuilder | SkMask | 可修改的遮罩构建器 |

### 关键成员变量

**SkMask**:
| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fImage | uint8_t const * const | 像素数据指针 (不可变) |
| fBounds | const SkIRect | 遮罩边界矩形 |
| fRowBytes | const uint32_t | 每行字节数 (步长) |
| fFormat | const Format | 遮罩格式 |

### 遮罩格式枚举

```cpp
enum Format : uint8_t {
    kBW_Format,      // 1bit 单色 (例如单色字形)
    kA8_Format,      // 8bit alpha (抗锯齿)
    k3D_Format,      // 3 个 8bit 平面: alpha, mul, add
    kARGB32_Format,  // SkPMColor 格式
    kLCD16_Format,   // 565 格式的 RGB 亚像素
    kSDF_Format,     // 8bit 有符号距离场
};
```

## 公共 API 函数

### 查询方法

```cpp
// 判断遮罩是否为空
bool isEmpty() const { return fBounds.isEmpty(); }

// 计算单平面图像大小
size_t computeImageSize() const;

// 计算总图像大小 (包括 3D 格式的多平面)
size_t computeTotalImageSize() const;
```

### 像素访问

```cpp
// 访问 1bit 像素所在字节 (kBW_Format)
const uint8_t* getAddr1(int x, int y) const;

// 访问 8bit alpha 像素 (kA8_Format, kSDF_Format)
const uint8_t* getAddr8(int x, int y) const;

// 访问 LCD16 像素 (kLCD16_Format)
const uint16_t* getAddrLCD16(int x, int y) const;

// 访问 32bit ARGB 像素 (kARGB32_Format)
const uint32_t* getAddr32(int x, int y) const;

// 运行时格式的通用访问
const void* getAddr(int x, int y) const;
```

### SkMaskBuilder 专用

```cpp
// 分配图像内存
static uint8_t* AllocImage(size_t bytes, AllocType = kUninit_Alloc);

// 释放图像内存
static void FreeImage(void* image);

// 准备目标遮罩 (预留模糊半径空间)
static SkMaskBuilder PrepareDestination(int radiusX, int radiusY, const SkMask& src);
```

### 可修改访问器

```cpp
// SkMaskBuilder 提供可修改版本的访问方法
uint8_t* getAddr8(int x, int y);
uint32_t* getAddr32(int x, int y);
// ... 其他修改版本
```

## 内部实现细节

### 图像大小计算

```cpp
size_t SkMask::computeImageSize() const {
    return safeMul32(fBounds.height(), fRowBytes);
}

size_t SkMask::computeTotalImageSize() const {
    size_t size = this->computeImageSize();
    if (fFormat == SkMask::k3D_Format) {
        size = safeMul32(SkToS32(size), 3);  // 3 个平面
    }
    return size;
}
```

使用 `safeMul32()` 防止 32 位溢出,返回 0 表示溢出。

### 内存分配

```cpp
uint8_t* SkMaskBuilder::AllocImage(size_t size, AllocType at) {
    size_t aligned_size = SkSafeMath::Align4(size);  // 4 字节对齐
    unsigned flags = SK_MALLOC_THROW;
    if (at == kZeroInit_Alloc) {
        flags |= SK_MALLOC_ZERO_INITIALIZE;
    }
    return static_cast<uint8_t*>(sk_malloc_flags(aligned_size, flags));
}
```

与 `SkBitmap` 使用相同的分配器,允许跨类型内存共享。

### 像素地址计算

```cpp
const uint8_t* SkMask::getAddr8(int x, int y) const {
    SkASSERT(kA8_Format == fFormat || kSDF_Format == fFormat);
    SkASSERT(fBounds.contains(x, y));
    return fImage + (x - fBounds.fLeft) + (y - fBounds.fTop) * fRowBytes;
}
```

坐标相对于 `fBounds` 计算偏移量。

### 格式位移表

```cpp
static const int gMaskFormatToShift[] = {
    ~0,  // BW -- 不支持 getAddr()
    0,   // A8  -- 位移 0 (1 字节)
    0,   // 3D  -- 位移 0
    2,   // ARGB32 -- 位移 2 (4 字节)
    1,   // LCD16  -- 位移 1 (2 字节)
    0,   // SDF    -- 位移 0
};
```

用于 `getAddr()` 的运行时格式处理。

### PrepareDestination 实现

为模糊等滤镜预留边界空间:
```cpp
SkMaskBuilder SkMaskBuilder::PrepareDestination(int radiusX, int radiusY,
                                                const SkMask& src) {
    SkMaskBuilder dst;
    size_t dstW = safe.add(src.fBounds.width(), safe.add(radiusX, radiusX));
    size_t dstH = safe.add(src.fBounds.height(), safe.add(radiusY, radiusY));

    dst.bounds().setWH(SkTo<int>(dstW), SkTo<int>(dstH));
    dst.bounds().offset(src.fBounds.x(), src.fBounds.y());
    dst.bounds().offset(-radiusX, -radiusY);  // 向外扩展

    if (src.fImage != nullptr) {
        dst.image() = AllocImage(toAlloc);
    }
    return dst;
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkRect | 边界矩形 |
| SkColorData | 颜色数据访问 |
| SkColorPriv | 颜色格式转换 |
| SkMalloc | 内存分配 |
| SkSafeMath | 安全数学运算 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| SkMaskFilter | 遮罩滤镜处理 |
| SkBlitter | 像素混合 |
| SkDraw | 绘制系统 |
| SkGlyph | 字形光栅化 |
| SkMaskBlurFilter | 模糊算法 |

## 设计模式与设计决策

### 1. 不可变视图模式
`SkMask` 使用 `const` 成员变量强制不可变性:
```cpp
uint8_t const * const fImage;
const SkIRect fBounds;
const uint32_t fRowBytes;
const Format fFormat;
```

`SkMaskBuilder` 通过 const_cast 提供可修改访问:
```cpp
uint8_t*& image() { return *const_cast<uint8_t**>(&fImage); }
```

### 2. 模板迭代器
为不同格式提供统一的迭代接口:
```cpp
template <Format F> struct AlphaIter;

template <> struct SkMask::AlphaIter<SkMask::kA8_Format> {
    AlphaIter& operator++() { ++fPtr; return *this; }
    uint8_t operator*() const { return *fPtr; }
    // ...
};
```

支持正向/反向迭代和行跳转:
```cpp
AlphaIter& operator>>=(uint32_t rb) {  // 跳转到下一行
    fPtr = SkTAddOffset<const uint8_t>(fPtr, rb);
    return *this;
}
```

### 3. RAII 自动释放
```cpp
using SkAutoMaskFreeImage =
    std::unique_ptr<uint8_t, SkFunctionObject<SkMaskBuilder::FreeImage>>;
```

使用示例:
```cpp
SkMaskBuilder srcM;
// ... 分配图像
SkAutoMaskFreeImage autoSrc(srcM.image());  // 自动释放
```

### 4. 构造模式分离
```cpp
enum CreateMode {
    kJustComputeBounds_CreateMode,        // 仅计算边界
    kJustRenderImage_CreateMode,          // 渲染到预分配遮罩
    kComputeBoundsAndRenderImage_CreateMode  // 完整构建
};
```

允许两阶段构建,优化性能。

## 性能考量

### 1. 内存对齐
```cpp
size_t aligned_size = SkSafeMath::Align4(size);
```
4 字节对齐提升 SIMD 访问效率。

### 2. 溢出检测
所有大小计算使用安全数学:
```cpp
static int32_t safeMul32(int32_t a, int32_t b) {
    int64_t size = sk_64_mul(a, b);
    if (size > 0 && SkTFitsIn<int32_t>(size)) {
        return size;
    }
    return 0;  // 溢出返回 0
}
```

### 3. 格式特化迭代器
每种格式单独实现 `AlphaIter`,避免虚函数开销:
- kBW_Format: 位操作提取
- kA8_Format: 直接访问
- kARGB32_Format: 提取 alpha 通道
- kLCD16_Format: RGB 平均

### 4. 坐标断言
Release 版本不检查,Debug 版本通过断言捕获错误:
```cpp
SkASSERT(fBounds.contains(x, y));
```

### 5. 条件编译优化
```cpp
#if defined(SK_CPU_LENDIAN) && defined(SK_CPU_FAST_UNALIGNED_ACCESS)
   return reinterpret_cast<const uint32_t*>(input);  // 零拷贝
#else
   // 拷贝到对齐缓冲区
#endif
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| include/core/SkRect.h | 依赖 | 矩形边界 |
| src/core/SkMaskFilter.h | 使用者 | 遮罩滤镜 |
| src/core/SkBlitter.h | 使用者 | 像素混合 |
| src/core/SkColorPriv.h | 依赖 | 颜色格式 |
| src/base/SkSafeMath.h | 依赖 | 安全运算 |
| include/private/base/SkTemplates.h | 依赖 | 模板工具 |
