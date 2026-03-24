# SkSpriteBlitter_ARGB32

> 源文件
> - src/core/SkSpriteBlitter_ARGB32.cpp

## 概述

`SkSpriteBlitter_ARGB32.cpp` 实现了针对 32 位 ARGB(N32)格式的精灵(sprite)绘制优化。精灵绘制是指将一个矩形图像块快速复制到目标表面,常用于位图绘制、UI 元素渲染等场景。该模块通过直接调用 `SkBlitRow` 的优化路径,避免通用绘制管道的开销,实现高性能的矩形块传输。

## 架构位置

`SkSpriteBlitter_ARGB32` 位于 Skia 的快速路径(fast path)绘制层:

- **SkSpriteBlitter 家族**: 针对不同像素格式的特化实现
- **SkBlitRow**: 底层像素行处理(可能包含 SIMD 优化)
- **快速路径**: 绕过通用 `SkBlitter` 的优化分支

## 主要类与结构体

### Sprite_D32_S32

**继承关系**:
```
SkBlitter
  └── SkSpriteBlitter
        └── Sprite_D32_S32
```

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fProc32` | `SkBlitRow::Proc32` | 行级混合函数指针 |
| `fAlpha` | `U8CPU` | 全局 alpha 值(0-255) |
| `fSource` | `const SkPixmap` | 源图像数据(继承自 `SkSpriteBlitter`) |
| `fDst` | `SkPixmap` | 目标表面(继承自 `SkSpriteBlitter`) |
| `fLeft`, `fTop` | `int` | 目标位置(继承自 `SkSpriteBlitter`) |

## 公共 API 函数

### SkSpriteBlitter::ChooseL32 (静态工厂函数)

```cpp
SkSpriteBlitter* SkSpriteBlitter::ChooseL32(const SkPixmap& source,
                                            const SkPaint& paint,
                                            SkArenaAlloc* allocator);
```

**功能**: 为 32 位目标格式选择合适的精灵 blitter

**返回值**:
- 成功: 指向 `Sprite_D32_S32` 实例的指针
- 失败: `nullptr`(回退到通用路径)

**选择条件**:
1. 源图像格式为 `kN32_SkColorType`(ARGB8888 或 RGBA8888)
2. 混合模式为 `SrcOver`
3. 无颜色滤镜(`ColorFilter`)
4. 无遮罩滤镜(`MaskFilter`)

### Sprite_D32_S32::blitRect (核心绘制函数)

```cpp
void blitRect(int x, int y, int width, int height) override;
```

**功能**: 绘制矩形区域

**参数**:
- `x`, `y`: 目标坐标
- `width`, `height`: 矩形尺寸

## 内部实现细节

### 构造函数 - 函数指针选择

```cpp
Sprite_D32_S32(const SkPixmap& src, U8CPU alpha) : INHERITED(src) {
    unsigned flags32 = 0;

    // 根据 alpha 和源图像透明度选择标志
    if (255 != alpha) {
        flags32 |= SkBlitRow::kGlobalAlpha_Flag32;  // 全局 alpha
    }
    if (!src.isOpaque()) {
        flags32 |= SkBlitRow::kSrcPixelAlpha_Flag32;  // 每像素 alpha
    }

    // 工厂函数返回优化的行混合函数
    fProc32 = SkBlitRow::Factory32(flags32);
    fAlpha = alpha;
}
```

**函数指针选择逻辑**:

| 条件 | 标志 | 优化路径 |
|------|------|---------|
| alpha < 255 | `kGlobalAlpha_Flag32` | 每像素乘以全局 alpha |
| 源不透明 | 0 | 直接复制(memcpy 或 SIMD) |
| 源半透明 | `kSrcPixelAlpha_Flag32` | SrcOver 混合 |
| 两者都有 | 两个标志 | 全局 alpha + SrcOver |

### blitRect 实现 - 逐行处理

```cpp
void blitRect(int x, int y, int width, int height) override {
    // 获取目标和源指针
    uint32_t* SK_RESTRICT dst = fDst.writable_addr32(x, y);
    const uint32_t* SK_RESTRICT src = fSource.addr32(x - fLeft, y - fTop);

    size_t dstRB = fDst.rowBytes();
    size_t srcRB = fSource.rowBytes();
    SkBlitRow::Proc32 proc = fProc32;
    U8CPU alpha = fAlpha;

    do {
        proc(dst, src, width, alpha);  // 处理一行

        // 移动到下一行(字节指针算术)
        dst = (uint32_t* SK_RESTRICT)((char*)dst + dstRB);
        src = (const uint32_t* SK_RESTRICT)((const char*)src + srcRB);
    } while (--height != 0);
}
```

**性能关键点**:
1. **SK_RESTRICT**: 编译器优化提示(指针不重叠)
2. **逐行调用**: `SkBlitRow::Proc32` 可能使用 SIMD 指令
3. **字节偏移**: 支持非标准 rowBytes(如对齐或子图像)

### SkBlitRow::Factory32 选择示例

```cpp
// 简化的伪代码
SkBlitRow::Proc32 Factory32(unsigned flags) {
    if (flags == 0) {
        return &memcpy_optimized;  // 不透明源,无 alpha
    }
    if (flags == kSrcPixelAlpha_Flag32) {
        return &SrcOver_SIMD;      // SSE2/NEON SrcOver 混合
    }
    if (flags == kGlobalAlpha_Flag32) {
        return &SrcCopy_with_alpha;  // 源不透明 + 全局 alpha
    }
    if (flags == (kGlobalAlpha_Flag32 | kSrcPixelAlpha_Flag32)) {
        return &SrcOver_with_global_alpha;  // 完整混合
    }
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkBlitRow` | 行级像素混合函数(核心性能) |
| `SkPixmap` | 像素数据访问接口 |
| `SkPaint` | 绘制参数(alpha, 滤镜等) |
| `SkArenaAlloc` | 快速内存分配器 |

### 被依赖的模块

| 模块 | 说明 |
|------|------|
| `SkDraw` | 调用 `ChooseL32` 选择 blitter |
| `SkCanvas::drawBitmap` | 位图绘制的快速路径 |
| `SkDevice` | 设备相关绘制调度 |

## 设计模式与设计决策

### 1. 工厂方法模式

`ChooseL32` 作为静态工厂函数,根据条件选择实现:

```cpp
SkSpriteBlitter* ChooseL32(...) {
    if (paint.getColorFilter() != nullptr) return nullptr;
    if (paint.getMaskFilter() != nullptr) return nullptr;

    if (source.colorType() == kN32_SkColorType && paint.isSrcOver()) {
        return allocator->make<Sprite_D32_S32>(source, paint.getAlpha());
    }
    return nullptr;  // 回退到通用路径
}
```

### 2. 策略模式

通过函数指针(`fProc32`)切换不同混合策略:
- **策略选择**: 构造函数时确定
- **策略执行**: `blitRect` 中通过函数指针调用

### 3. 快速路径设计

**为什么需要 SkSpriteBlitter?**
- **绕过通用管道**: 避免 `SkDraw` 的变换、抗锯齿等开销
- **矩形优化**: 专注于矩形块传输的极限性能
- **硬件友好**: 连续内存访问利于缓存和 SIMD

**何时回退到通用路径?**
- 有颜色滤镜或遮罩滤镜
- 混合模式不是 SrcOver
- 需要抗锯齿或变换
- 源/目标格式不匹配

## 性能考量

### 1. SIMD 优化潜力

`SkBlitRow::Proc32` 在不同平台有特化实现:

```cpp
// x86: SSE2/AVX2 实现
// ARM: NEON 实现
// 通用: 标量 C++ 实现

// 示例: 4像素并行 SrcOver (伪代码)
void SrcOver_SSE2(uint32_t* dst, const uint32_t* src, int count, U8CPU alpha) {
    __m128i vAlpha = _mm_set1_epi16(alpha);
    for (int i = 0; i < count; i += 4) {
        __m128i vSrc = _mm_loadu_si128((__m128i*)(src + i));
        __m128i vDst = _mm_loadu_si128((__m128i*)(dst + i));
        __m128i vResult = blend_srcover_sse2(vSrc, vDst, vAlpha);
        _mm_storeu_si128((__m128i*)(dst + i), vResult);
    }
}
```

### 2. 内存访问模式

```cpp
// 良好的缓存局部性
for (int row = 0; row < height; row++) {
    // 顺序访问源和目标
    proc(dst_row, src_row, width, alpha);
}
```

### 3. 编译器优化

- **SK_RESTRICT**: 允许编译器假设指针不重叠
- **内联**: `blitRect` 可被内联到调用点
- **循环展开**: 编译器可展开 `do-while` 循环

### 4. 避免虚函数开销

虽然 `blitRect` 是虚函数,但通常通过去虚化优化:

```cpp
// 调用点代码
auto* spriteBlitter = ChooseL32(...);
if (spriteBlitter) {
    // 编译器可静态解析为 Sprite_D32_S32::blitRect
    spriteBlitter->blitRect(x, y, w, h);
}
```

### 5. 性能对比

| 场景 | 通用路径 | Sprite_D32_S32 | 加速比 |
|------|---------|----------------|--------|
| 不透明 ARGB 复制 | ~15 cycles/pixel | ~2 cycles/pixel | 7.5x |
| 半透明 SrcOver | ~25 cycles/pixel | ~8 cycles/pixel | 3x |
| 带全局 alpha | ~30 cycles/pixel | ~10 cycles/pixel | 3x |

*(基于 x86 SSE2 实现的估算值)*

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/core/SkSpriteBlitter_ARGB32.cpp` | 本文件(32位精灵 blitter) |
| `src/core/SkSpriteBlitter.h` | 精灵 blitter 基类 |
| `src/core/SkBlitRow.h` | 行级混合函数接口 |
| `src/opts/SkBlitRow_opts.h` | SIMD 优化实现(SSE/NEON) |
| `src/core/SkDraw.cpp` | 调用精灵 blitter 的主要位置 |
| `src/core/SkBitmapDevice.cpp` | 位图设备绘制调度 |
