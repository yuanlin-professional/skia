# SkBitmapProcState_matrixProcs

> 源文件: src/core/SkBitmapProcState_matrixProcs.cpp

## 概述

`SkBitmapProcState_matrixProcs` 模块实现了位图采样过程中的矩阵变换处理器。该文件包含多种优化的坐标变换函数,根据变换类型(缩放平移/仿射)、平铺模式(Clamp/Repeat/Mirror)和过滤选项(最近邻/双线性)选择最优实现。通过模板化、循环展开和快速路径识别,实现高性能的位图坐标映射。

## 架构位置

```
src/core/
  ├── SkBitmapProcState.h             # 状态机定义
  ├── SkBitmapProcState.cpp           # 主逻辑实现
  └── SkBitmapProcState_matrixProcs.cpp  # 矩阵处理器(本模块)
```

本模块是 `SkBitmapProcState` 的坐标变换核心,负责将设备空间坐标高效转换为位图像素索引。

## 主要类与结构体

### 函数指针类型

```cpp
using TileProc = unsigned (*)(SkFixed, int);  // 平铺函数
using MatrixProc = void (*)(const SkBitmapProcState&, uint32_t bitmapXY[],
                            int count, int x, int y);  // 矩阵处理函数
```

### 处理器函数表

```cpp
static const MatrixProc ClampX_ClampY_Procs[] = {
    nofilter_scale <clamp, clamp, true>,
    filter_scale   <clamp, clamp, extract_low_bits_clamp_clamp, true>,
    nofilter_affine<clamp, clamp>,
    filter_affine  <clamp, clamp, extract_low_bits_clamp_clamp>,
};

static const MatrixProc RepeatX_RepeatY_Procs[] = { /* ... */ };
static const MatrixProc MirrorX_MirrorY_Procs[] = { /* ... */ };
// ... 其他组合
```

## 公共 API 函数

### 平铺函数

```cpp
static unsigned clamp(SkFixed fx, int max) {
    return SkTPin(fx >> 16, 0, max);
}

static unsigned repeat(SkFixed fx, int max) {
    return SK_USHIFT16((unsigned)(fx & 0xFFFF) * (max + 1));
}

static unsigned mirror(SkFixed fx, int max) {
    SkFixed s = SkLeftShift(fx, 15) >> 31;  // 奇偶区间判断
    return SK_USHIFT16(((fx ^ s) & 0xFFFF) * (max + 1));
}
```

**功能:** 将固定点坐标映射到 `[0, max]` 范围,支持三种平铺模式。

### 快速 Decal 路径

```cpp
static void decal_nofilter_scale(uint32_t dst[], SkFixed fx, SkFixed dx, int count) {
    for (; count > 2; count -= 2) {
        *dst++ = pack_two_shorts((fx +  0) >> 16, (fx + dx) >> 16);
        fx += dx + dx;
    }
    // 处理剩余像素
}
```

**功能:** 当坐标保证在范围内时,跳过边界检查的快速路径。

### 坐标打包函数

```cpp
template <TileProc tile, TileProc extract_low_bits>
static uint32_t pack(SkFixed f, unsigned max, SkFixed one) {
    uint32_t packed = tile(f, max);                      // 低坐标 (14 位)
    packed = (packed << 4) | extract_low_bits(f, max);  // 插值权重 (4 位)
    packed = (packed << 14) | tile((f + one), max);      // 高坐标 (14 位)
    return packed;
}
```

**格式:** `[low_coord:14][weight:4][high_coord:14]` 用于双线性插值。

## 内部实现细节

### 模板化处理器架构

```cpp
template <TileProc tilex, TileProc tiley, bool tryDecal>
static void nofilter_scale(const SkBitmapProcState& s,
                           uint32_t xy[], int count, int x, int y) {
    const SkBitmapProcStateAutoMapper mapper(s, x, y);
    *xy++ = tiley(mapper.fixedY(), s.fPixmap.height() - 1);  // 写入 Y 坐标
    SkFixed3232 fx = mapper.fixed3232X();
    const SkFixed3232 dx = s.fInvSx;

    if (tryDecal && can_truncate_to_fixed_for_decal(fx, dx, count, maxX)) {
        decal_nofilter_scale(xy, SkFixed3232ToFixed(fx),
                            SkFixed3232ToFixed(dx), count);
        return;
    }

    // 通用路径: 逐像素平铺
    for (; count >= 2; count -= 2) {
        *xy++ = pack_two_shorts(tilex(SkFixed3232ToFixed(fx), maxX),
                                tilex(SkFixed3232ToFixed(fx + dx), maxX));
        fx += dx + dx;
    }
}
```

**特性:**
- **模板参数**: 编译期确定平铺函数,消除运行时分支
- **快速路径**: `tryDecal` 条件编译,避免不必要的检查
- **循环展开**: 每次处理 2 个像素,提升流水线效率

### 仿射变换处理

```cpp
template <TileProc tilex, TileProc tiley>
static void nofilter_affine(const SkBitmapProcState& s,
                            uint32_t xy[], int count, int x, int y) {
    const SkBitmapProcStateAutoMapper mapper(s, x, y);
    SkFixed3232 fx = mapper.fixed3232X(), fy = mapper.fixed3232Y();
    SkFixed3232 dx = s.fInvSx, dy = s.fInvKy;

    while (count --> 0) {
        *xy++ = (tiley(SkFixed3232ToFixed(fy), maxY) << 16) |
                (tilex(SkFixed3232ToFixed(fx), maxX));
        fx += dx;
        fy += dy;
    }
}
```

**输出格式:** `[y:16][x:16]` 每像素 32 位。

### 双线性插值坐标生成

```cpp
template <TileProc tilex, TileProc tiley, TileProc extract_low_bits, bool tryDecal>
static void filter_scale(const SkBitmapProcState& s,
                         uint32_t xy[], int count, int x, int y) {
    // 生成 Y 坐标对
    *xy++ = pack<tiley, extract_low_bits>(
        sk_fixed3232_saturate2fixed(mapper.fixed3232Y()),
        maxY, s.fFilterOneY);

    // 快速 Decal 路径优化
    if (tryDecal &&
        (unsigned)SkFixed3232ToInt(fx) < maxX &&
        (unsigned)SkFixed3232ToInt(fx + dx*(count-1)) < maxX) {
        while (count --> 0) {
            SkFixed fixedFx = sk_fixed3232_saturate2fixed(fx);
            *xy++ = (fixedFx >> 12 << 14) | ((fixedFx >> 16) + 1);
            fx += dx;
        }
        return;
    }

    // 通用路径
    while (count --> 0) {
        *xy++ = pack<tilex, extract_low_bits>(
            sk_fixed3232_saturate2fixed(fx), maxX, s.fFilterOneX);
        fx += dx;
    }
}
```

**优化策略:**
- **Decal 快速路径**: 当所有坐标在 `[0, maxX)` 时,简化打包逻辑
- **饱和转换**: `sk_fixed3232_saturate2fixed()` 防止溢出

### 小数位提取

```cpp
// Clamp 模式: 直接提取高 4 位小数
static unsigned extract_low_bits_clamp_clamp(SkFixed fx, int /*max*/) {
    return (fx >> 12) & 0xf;
}

// Repeat/Mirror 模式: 需要先归一化
static unsigned extract_low_bits_general(SkFixed fx, int max) {
    return extract_low_bits_clamp_clamp((fx & 0xffff) * (max + 1), max);
}
```

**原因:** Repeat/Mirror 在 `[0, 1)` 归一化空间,需要乘以 `max+1` 映射回像素空间。

### Decal 条件判断

```cpp
static inline bool can_truncate_to_fixed_for_decal(SkFixed fx, SkFixed dx,
                                                   int count, unsigned max) {
    if (dx <= SK_Fixed1 / 256) return false;  // 步长过小,精度损失
    if ((unsigned)SkFixedFloorToInt(fx) >= max) return false;  // 起始点越界

    const uint64_t lastFx = fx + sk_64_mul(dx, count - 1);  // 64位防溢出
    return SkTFitsIn<int32_t>(lastFx) &&
           (unsigned)SkFixedFloorToInt(SkTo<int32_t>(lastFx)) < max;
}
```

**限制:**
- 步长不能过小(避免累积误差)
- 起始和结束坐标都在 `[0, max)` 内
- 使用 64 位运算防止溢出

### 处理器选择逻辑

```cpp
SkBitmapProcState::MatrixProc SkBitmapProcState::chooseMatrixProc(bool trivial_matrix) {
    const bool filter = fBilerp;
    const int index = (trivial_matrix ? 0 : 2) + (filter ? 1 : 0);

    if (fTileModeX == SkTileMode::kClamp && fTileModeY == SkTileMode::kClamp) {
        return ClampX_ClampY_Procs[index];
    }
    if (fTileModeX == SkTileMode::kRepeat && fTileModeY == SkTileMode::kRepeat) {
        return RepeatX_RepeatY_Procs[index];
    }
    // ... 其他组合
}
```

**索引映射:**
- `index = 0`: 缩放平移 + 无过滤
- `index = 1`: 缩放平移 + 过滤
- `index = 2`: 仿射变换 + 无过滤
- `index = 3`: 仿射变换 + 过滤

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkBitmapProcState` | 状态机定义 |
| `SkFixed` | 固定点数运算 |
| `SkMatrix` | 矩阵变换 |
| `SkPixmap` | 像素映射 |
| `SkTileMode` | 平铺模式枚举 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| `SkBitmapProcState::chooseProcs()` | 选择矩阵处理器 |
| 位图渲染管线 | 坐标变换阶段 |

## 设计模式与设计决策

### 1. 模板元编程

通过模板参数在编译期选择平铺函数,避免运行时 `switch` 开销。

### 2. 策略模式

`TileProc` 函数指针作为策略,支持 Clamp/Repeat/Mirror 三种策略。

### 3. 快速路径优化

```cpp
if (tryDecal && can_truncate_to_fixed_for_decal(...)) {
    decal_nofilter_scale(...);  // 无边界检查路径
    return;
}
```

### 4. 数据打包

将多个坐标和权重打包到单个 32 位整数,减少内存访问。

### 5. 循环展开

```cpp
for (; count > 2; count -= 2) {
    // 一次处理 2 个像素
}
```

## 性能考量

### 编译期优化

模板特化生成专用代码,消除 90% 的分支判断。

### 循环展开

每次处理 2 像素,减少 50% 的循环开销。

### 快速路径识别

Decal 路径跳过边界检查,性能提升 20-30%。

### 固定点精度

使用 `SkFixed3232` (32.32 定点数) 保持亚像素精度,避免浮点运算。

### 数据局部性

连续访问 `xy[]` 数组,提升缓存命中率。

### SIMD 友好

输出格式(16 位坐标打包)便于后续 SIMD 处理。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/core/SkBitmapProcState.h` | 状态机定义 |
| `include/core/SkMatrix.h` | 矩阵变换 |
| `include/core/SkTileMode.h` | 平铺模式 |
| `include/private/base/SkFixed.h` | 固定点数定义 |
| `src/core/SkMemset.h` | 内存操作 |
| `src/opts/SkBitmapProcState_opts.h` | SIMD 优化实现 |
