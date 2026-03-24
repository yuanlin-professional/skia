# SkMipmapHQDownSampler

> 源文件: src/core/SkMipmapHQDownSampler.cpp

## 概述

`SkMipmapHQDownSampler` 是 Skia 中实现高质量（High Quality）mipmap 下采样的核心算法模块。与基于绘制系统的 `SkMipmapDrawDownSampler` 不同，该实现采用直接像素级操作，针对各种像素格式提供了高度优化的模板化过滤算法。

该下采样器支持 8 种不同的过滤器（1x2、1x3、2x1、2x2、2x3、3x1、3x2、3x3），能够处理各向同性和各向异性缩放，以及奇偶尺寸组合。它使用盒式过滤器和三角形过滤器（带权重的 1-2-1 卷积核）来生成平滑且无走样的 mipmap 层级。代码大量使用 SIMD 向量化（通过 `skvx::Vec`）来加速计算。

该实现仅在未定义 `SK_USE_DRAWING_MIPMAP_DOWNSAMPLER` 宏时编译，是 Skia 默认的 mipmap 生成方式。

## 架构位置

`SkMipmapHQDownSampler` 位于 Skia 的 mipmap 生成管道中：

- **接口层**：实现 `SkMipmapDownSampler` 抽象接口
- **同级实现**：与 `SkMipmapDrawDownSampler` 互斥（编译时选择）
- **调用者**：`SkMipmap::Build()` 通过 `MakeDownSampler()` 工厂方法创建实例
- **优化技术**：SIMD 向量化、模板特化、编译时类型分发

在 mipmap 构建流程中，该下采样器负责从较高分辨率层级生成较低分辨率层级，是整个 mipmap 金字塔质量的核心决定因素。

## 主要类与结构体

### ColorTypeFilter 系列

一组模板特化结构体，定义每种像素格式的展开（Expand）和压缩（Compact）操作：

#### ColorTypeFilter_8888

处理 32 位 RGBA/BGRA 格式：

```cpp
struct ColorTypeFilter_8888 {
    typedef uint32_t Type;
    static skvx::Vec<4, uint16_t> Expand(uint32_t x);
    static uint32_t Compact(const skvx::Vec<4, uint16_t>& x);
};
```

- **Expand**：将 8 位通道扩展到 16 位，为累加提供空间
- **Compact**：将 16 位结果压缩回 8 位

#### 其他 ColorTypeFilter 变体

| **结构体** | **像素格式** | **展开类型** | **说明** |
|----------|------------|------------|---------|
| `ColorTypeFilter_565` | RGB_565 | `uint32_t` | 16 位 RGB 格式 |
| `ColorTypeFilter_4444` | ARGB_4444 | `uint32_t` | 16 位 4444 格式 |
| `ColorTypeFilter_8` | Alpha_8/Gray_8 | `unsigned` | 单通道 8 位 |
| `ColorTypeFilter_RGBA_F16` | RGBA_F16 | `skvx::float4` | 半精度浮点（4 通道） |
| `ColorTypeFilter_Alpha_F16` | A16_float | `skvx::float4` | 半精度浮点（单通道） |
| `ColorTypeFilter_88` | R8G8_unorm | `uint32_t` | 双通道 8 位 |
| `ColorTypeFilter_1616` | R16G16_unorm | `uint64_t` | 双通道 16 位 |
| `ColorTypeFilter_16` | A16/R16_unorm | `uint32_t` | 单通道 16 位 |
| `ColorTypeFilter_1010102` | RGBA_1010102 | `uint64_t` | 10-10-10-2 格式 |
| `ColorTypeFilter_F16F16` | R16G16_float | `skvx::float4` | 半精度浮点（双通道） |
| `ColorTypeFilter_16161616` | R16G16B16A16 | `skvx::Vec<4, uint32_t>` | 四通道 16 位 |

### HQDownSampler

主采样器类，存储 8 个过滤器函数指针：

| **特性** | **说明** |
|---------|---------|
| **继承关系** | 继承自 `SkMipmapDownSampler` |
| **类型** | 策略实现类 |

**关键成员变量**：

| **成员变量** | **类型** | **说明** |
|------------|---------|---------|
| `proc_1_2` | `FilterProc*` | 1x2 过滤器（垂直 2x 缩小） |
| `proc_1_3` | `FilterProc*` | 1x3 过滤器（垂直 3x 缩小） |
| `proc_2_1` | `FilterProc*` | 2x1 过滤器（水平 2x 缩小） |
| `proc_2_2` | `FilterProc*` | 2x2 过滤器（双向 2x 缩小） |
| `proc_2_3` | `FilterProc*` | 2x3 过滤器（水平 2x，垂直 3x） |
| `proc_3_1` | `FilterProc*` | 3x1 过滤器（水平 3x 缩小） |
| `proc_3_2` | `FilterProc*` | 3x2 过滤器（水平 3x，垂直 2x） |
| `proc_3_3` | `FilterProc*` | 3x3 过滤器（双向 3x 缩小） |

## 公共 API 函数

### 工厂方法

```cpp
std::unique_ptr<SkMipmapDownSampler> SkMipmap::MakeDownSampler(const SkPixmap& root);
```

根据源图像的颜色类型，选择合适的过滤器集合并创建 `HQDownSampler` 实例：

```cpp
switch (root.colorType()) {
    case kRGBA_8888_SkColorType:
    case kBGRA_8888_SkColorType:
        proc_1_2 = downsample_1_2<ColorTypeFilter_8888>;
        // ... 其他 7 个过滤器
        break;
    // ... 其他颜色类型
    case kSRGBA_8888_SkColorType:  // sRGB 需要特殊处理
        return nullptr;
}

auto sampler = std::make_unique<HQDownSampler>();
sampler->proc_1_2 = proc_1_2;
// ... 设置其他 7 个过滤器
return sampler;
```

**不支持的格式**：

- `kUnknown_SkColorType`
- `kRGB_888x_SkColorType`、`kRGB_101010x_SkColorType` 等带填充的格式
- `kSRGBA_8888_SkColorType`（需要 gamma 校正）
- `kRGBA_F32_SkColorType`（32 位浮点）

### buildLevel 实现

```cpp
void HQDownSampler::buildLevel(const SkPixmap& dst, const SkPixmap& src) override;
```

根据源和目标尺寸，选择合适的过滤器并执行下采样：

1. **选择过滤器**：根据源尺寸的奇偶性选择 8 种过滤器之一
2. **逐行处理**：遍历目标图像的每一行，调用选定的过滤器
3. **源指针跳跃**：每次处理后源指针跳过 2 行（因为每次读取 2 或 3 行）

## 内部实现细节

### 过滤器选择逻辑

```cpp
FilterProc* proc;
if (height & 1) {  // 源高度为奇数
    if (height == 1) {
        if (width & 1) {
            proc = proc_3_1;  // 3x1 过滤器
        } else {
            proc = proc_2_1;  // 2x1 过滤器
        }
    } else {  // 高度 >= 3（奇数）
        if (width & 1) {
            if (width == 1) {
                proc = proc_1_3;  // 1x3 过滤器
            } else {
                proc = proc_3_3;  // 3x3 过滤器
            }
        } else {
            proc = proc_2_3;  // 2x3 过滤器
        }
    }
} else {  // 源高度为偶数
    if (width & 1) {
        if (width == 1) {
            proc = proc_1_2;  // 1x2 过滤器
        } else {
            proc = proc_3_2;  // 3x2 过滤器
        }
    } else {
        proc = proc_2_2;  // 2x2 过滤器（最常见）
    }
}
```

**设计原理**：

- **偶数尺寸**：使用盒式过滤器（均等权重）
- **奇数尺寸**：使用三角形过滤器（1-2-1 权重），提供平滑过渡

### 过滤器模板函数

#### downsample_2_2（最常见）

```cpp
template <typename F>
void downsample_2_2(void* dst, const void* src, size_t srcRB, int count) {
    auto p0 = static_cast<const typename F::Type*>(src);
    auto p1 = (const typename F::Type*)((const char*)p0 + srcRB);
    auto d = static_cast<typename F::Type*>(dst);

    for (int i = 0; i < count; ++i) {
        auto c00 = F::Expand(p0[0]);
        auto c01 = F::Expand(p0[1]);
        auto c10 = F::Expand(p1[0]);
        auto c11 = F::Expand(p1[1]);

        auto c = c00 + c10 + c01 + c11;  // 4 像素求和
        d[i] = F::Compact(shift_right(c, 2));  // 除以 4
        p0 += 2;
        p1 += 2;
    }
}
```

**操作步骤**：

1. 读取源图像的 2x2 像素块
2. 通过 `Expand` 转换为宽类型（避免溢出）
3. 求和并右移 2 位（除以 4）
4. 通过 `Compact` 转换回原始类型
5. 写入目标

#### downsample_3_3（最复杂）

```cpp
template <typename F>
void downsample_3_3(void* dst, const void* src, size_t srcRB, int count) {
    auto p0 = static_cast<const typename F::Type*>(src);
    auto p1 = (const typename F::Type*)((const char*)p0 + srcRB);
    auto p2 = (const typename F::Type*)((const char*)p1 + srcRB);
    auto d = static_cast<typename F::Type*>(dst);

    auto c0 = F::Expand(p0[0]);
    auto c1 = F::Expand(p1[0]);
    auto c2 = F::Expand(p2[0]);
    auto c = add_121(c0, c1, c2);  // 1*c0 + 2*c1 + 1*c2

    for (int i = 0; i < count; ++i) {
        auto a = c;

        auto b0 = F::Expand(p0[1]);
        auto b1 = F::Expand(p1[1]);
        auto b2 = F::Expand(p2[1]);
        auto b = shift_left(add_121(b0, b1, b2), 1);  // 2 * (1*b0 + 2*b1 + 1*b2)

        c0 = F::Expand(p0[2]);
        c1 = F::Expand(p1[2]);
        c2 = F::Expand(p2[2]);
        c = add_121(c0, c1, c2);

        auto sum = a + b + c;  // (1+2+1) + 2*(1+2+1) + (1+2+1) = 16
        d[i] = F::Compact(shift_right(sum, 4));  // 除以 16
        p0 += 2;
        p1 += 2;
        p2 += 2;
    }
}
```

**权重矩阵**（归一化前）：

```
1  2  1
2  4  2
1  2  1
```

总和为 16，因此右移 4 位。

#### 各向异性过滤器

如 `downsample_3_1`（水平 3x，垂直 1x）：

```cpp
template <typename F>
void downsample_3_1(void* dst, const void* src, size_t srcRB, int count) {
    auto p0 = static_cast<const typename F::Type*>(src);
    auto d = static_cast<typename F::Type*>(dst);

    auto c02 = F::Expand(p0[0]);
    for (int i = 0; i < count; ++i) {
        auto c00 = c02;
        auto c01 = F::Expand(p0[1]);
        c02 = F::Expand(p0[2]);

        auto c = add_121(c00, c01, c02);  // 1*c00 + 2*c01 + 1*c02
        d[i] = F::Compact(shift_right(c, 2));  // 除以 4
        p0 += 2;
    }
}
```

**重叠采样**：使用滑动窗口，相邻输出像素共享部分输入像素。

### 辅助函数

#### add_121（三角形权重）

```cpp
template <typename T>
T add_121(const T& a, const T& b, const T& c) {
    return a + b + b + c;  // 1*a + 2*b + 1*c
}
```

#### shift_right/shift_left

```cpp
template <typename T>
T shift_right(const T& x, int bits) {
    return x >> bits;
}

skvx::float4 shift_right(const skvx::float4& x, int bits) {
    return x * (1.0f / (1 << bits));  // 浮点数除法
}
```

为整数和浮点类型提供统一的除法接口。

### SIMD 向量化

使用 Skia 的 `skvx::Vec` 模板进行自动向量化：

```cpp
skvx::Vec<4, uint16_t> Expand(uint32_t x) {
    return skvx::cast<uint16_t>(skvx::byte4::Load(&x));
}
```

编译器会将这些操作映射到 SSE、NEON 等 SIMD 指令。

### 像素格式特化示例

#### ColorTypeFilter_8888（最常见）

```cpp
struct ColorTypeFilter_8888 {
    typedef uint32_t Type;
    static skvx::Vec<4, uint16_t> Expand(uint32_t x) {
        return skvx::cast<uint16_t>(skvx::byte4::Load(&x));
    }
    static uint32_t Compact(const skvx::Vec<4, uint16_t>& x) {
        uint32_t r;
        skvx::cast<uint8_t>(x).store(&r);
        return r;
    }
};
```

**Expand**：`[R8, G8, B8, A8]` → `[R16, G16, B16, A16]`
**Compact**：`[R16, G16, B16, A16]` → `[R8, G8, B8, A8]`

#### ColorTypeFilter_565

```cpp
struct ColorTypeFilter_565 {
    typedef uint16_t Type;
    static uint32_t Expand(uint16_t x) {
        return (x & ~SK_G16_MASK_IN_PLACE) | ((x & SK_G16_MASK_IN_PLACE) << 16);
    }
    static uint16_t Compact(uint32_t x) {
        return ((x & ~SK_G16_MASK_IN_PLACE) & 0xFFFF) | ((x >> 16) & SK_G16_MASK_IN_PLACE);
    }
};
```

分离红蓝通道和绿通道，避免位交叉干扰。

#### ColorTypeFilter_RGBA_F16

```cpp
struct ColorTypeFilter_RGBA_F16 {
    typedef uint64_t Type;  // 4 个 16 位半精度浮点
    static skvx::float4 Expand(uint64_t x) {
        return from_half(skvx::half4::Load(&x));
    }
    static uint64_t Compact(const skvx::float4& x) {
        uint64_t r;
        to_half(x).store(&r);
        return r;
    }
};
```

半精度浮点转换为单精度进行计算，结果再转回。

## 依赖关系

### 依赖的模块

| **模块** | **用途** |
|---------|---------|
| `skvx::Vec` | SIMD 向量化，加速像素操作 |
| `SkHalf` | 半精度浮点转换 |
| `SkColorData` | 像素格式宏定义（如 `SK_G16_MASK_IN_PLACE`） |
| `SkMipmap` | 下采样器接口定义 |

### 被依赖的模块

| **模块** | **关系** |
|---------|---------|
| `SkMipmap::Build` | 调用 `MakeDownSampler` 创建实例 |
| 编译配置系统 | 由 `SK_USE_DRAWING_MIPMAP_DOWNSAMPLER` 宏控制 |

## 设计模式与设计决策

### 策略模式

`HQDownSampler` 实现 `SkMipmapDownSampler` 接口，提供像素级优化策略。

### 模板元编程

通过 `ColorTypeFilter` 模板和过滤器模板函数，实现编译时类型分发：

- 每种像素格式生成独立的特化代码
- 编译器可内联和优化特定路径
- 避免运行时类型检查开销

### 编译时过滤器选择

`MakeDownSampler` 在编译时为每种像素格式绑定 8 个过滤器函数，运行时只需函数指针调用。

### 滑动窗口优化

3x 过滤器使用滑动窗口技术，复用相邻像素计算：

```cpp
auto c02 = F::Expand(p0[0]);
for (...) {
    auto c00 = c02;  // 复用上一次的 c02
    auto c01 = F::Expand(p0[1]);
    c02 = F::Expand(p0[2]);
    // ...
}
```

减少冗余的像素读取和展开操作。

### 盒式 vs 三角形过滤器

- **盒式过滤器**（2x）：均等权重，简单快速
- **三角形过滤器**（3x）：1-2-1 权重，更平滑的过渡

三角形过滤器接近线性插值，减少块状伪影。

## 性能考量

### SIMD 加速

- **向量化加载/存储**：一次处理多个通道
- **并行计算**：RGBA 4 通道同时处理
- **寄存器利用**：减少内存访问

### 缓存友好

- **逐行扫描**：顺序访问源和目标像素
- **局部性**：每次处理 2-3 行数据，符合缓存行大小
- **预取**：CPU 可有效预取后续数据

### 展开/压缩优化

- **避免溢出**：展开到更宽类型进行累加
- **饱和运算**：压缩时自动截断到有效范围
- **位运算**：使用移位代替除法

### 循环优化

- **循环展开**：编译器可展开小循环
- **寄存器分配**：临时变量尽量保持在寄存器
- **分支预测**：内层循环无分支

### 格式支持广泛性

支持 15+ 种像素格式，覆盖常见场景：

- 8 位整数（sRGB 除外）
- 16 位整数
- 半精度浮点
- 各种通道组合（单通道、双通道、三通道、四通道）

### 性能对比

| **维度** | **HQDownSampler** | **DrawDownSampler** |
|---------|------------------|-------------------|
| **速度** | 快（直接像素操作） | 中等（完整绘制管道） |
| **质量** | 优秀（三角形过滤） | 优秀（三次插值） |
| **代码量** | 大（每种格式特化） | 小（复用绘制系统） |
| **内存访问** | 高度优化 | 依赖绘制系统 |
| **SIMD 利用** | 显式向量化 | 间接（依赖后端） |

### 使用建议

- 对于性能敏感的场景，使用 `HQDownSampler`（默认）
- 对于需要更高质量（如三次插值）的离线处理，考虑 `DrawDownSampler`
- 避免 sRGB 格式的直接生成，需要在线性空间操作
- 大图像 mipmap 生成可考虑多线程并行（当前未实现）

## 相关文件

| **文件路径** | **说明** |
|-------------|---------|
| `src/core/SkMipmapDrawDownSampler.cpp` | 替代实现：基于绘制系统的下采样器 |
| `src/core/SkMipmap.h/cpp` | mipmap 核心类，调用下采样器 |
| `src/base/SkVx.h` | SIMD 向量化抽象库 |
| `src/base/SkHalf.h` | 半精度浮点转换 |
| `src/core/SkColorData.h` | 像素格式宏和工具 |
| `include/core/SkPixmap.h` | 像素映射接口 |
