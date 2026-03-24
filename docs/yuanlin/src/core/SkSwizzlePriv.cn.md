# SkSwizzlePriv

> 源文件: src/core/SkSwizzlePriv.h

## 概述

`SkSwizzlePriv` 是 Skia 图形库中像素通道交换的私有实现头文件。它定义了完整的像素格式转换函数指针类型、优化实现的声明,以及一组内联辅助函数。该模块支持多种颜色格式转换,包括 RGBA/BGRA 互换、预乘/非预乘 alpha 转换、灰度扩展、CMYK 转换等。这些函数通过 `SkOpts` 命名空间暴露,实际实现由平台特定的 SIMD 优化代码提供。

## 架构位置

`SkSwizzlePriv` 是像素处理模块的内部接口层,连接公共 API 和平台优化实现。

```
架构层次:
  公共 API (SkSwizzle.h)
    ↓
  私有接口 (SkSwizzlePriv.h) ← 本文件
    ├─ 函数指针类型定义
    ├─ 优化函数声明
    └─ 辅助工具函数
    ↓
  平台实现 (SkSwizzler_opts_*.cpp)
    ↓
  SIMD 指令 (SSE/AVX/NEON/LASX)
```

## 主要类与结构体

### 函数指针类型定义

**SkOpts::Swizzle_8888_u32**
```cpp
using Swizzle_8888_u32 = void (*)(uint32_t*, const uint32_t*, int);
```
**功能:** 32 位像素到 32 位像素的转换

**已定义的函数指针:**

| 函数指针名 | 功能说明 |
|-----------|---------|
| `RGBA_to_BGRA` | 交换 R 和 B 通道 |
| `RGBA_to_rgbA` | 预乘 alpha (非预乘 → 预乘) |
| `RGBA_to_bgrA` | 交换 R/B 并预乘 alpha |
| `rgbA_to_RGBA` | 反预乘 alpha (预乘 → 非预乘) |
| `rgbA_to_BGRA` | 反预乘并交换 R/B |
| `inverted_CMYK_to_RGB1` | 反向 CMYK 转 RGB (不透明) |
| `inverted_CMYK_to_BGR1` | 反向 CMYK 转 BGR (不透明) |

**SkOpts::Swizzle_8888_u8**
```cpp
using Swizzle_8888_u8 = void (*)(uint32_t*, const uint8_t*, int);
```
**功能:** 字节数组到 32 位像素的转换

**已定义的函数指针:**

| 函数指针名 | 功能说明 |
|-----------|---------|
| `RGB_to_RGB1` | RGB 字节 → RGBA (插入不透明 alpha) |
| `RGB_to_BGR1` | RGB 字节 → BGRA (交换并插入 alpha) |
| `gray_to_RGB1` | 灰度 → RGBA (复制到 R/G/B,alpha=255) |
| `grayA_to_RGBA` | 灰度+alpha → RGBA (扩展到三通道) |
| `grayA_to_rgbA` | 灰度+alpha → 预乘 RGBA |

### 辅助内联函数

#### 通道交换

| 函数签名 | 功能说明 |
|---------|---------|
| `skvx::float4 swizzle_rb(const skvx::float4& x)` | 交换 float4 向量的 R 和 B 通道 |
| `skvx::float4 swizzle_rb_if_bgra(const skvx::float4& x)` | 根据平台定义条件交换 R/B |

#### 像素格式转换

| 函数签名 | 功能说明 |
|---------|---------|
| `skvx::float4 Sk4f_fromL32(uint32_t px)` | 32 位整数像素 → float4 (归一化到 [0,1]) |
| `uint32_t Sk4f_toL32(const skvx::float4& px)` | float4 → 32 位整数像素 (量化到 [0,255]) |

## 公共 API 函数

### SkOpts 命名空间函数

**初始化函数:**
```cpp
void Init_Swizzler();
```
执行运行时 CPU 检测,初始化所有函数指针为最优实现。

### 内联辅助函数详解

**swizzle_rb**
```cpp
static inline skvx::float4 swizzle_rb(const skvx::float4& x) {
    return skvx::shuffle<2, 1, 0, 3>(x);
}
```
使用 SIMD shuffle 指令交换通道:
- 输入: `[R, G, B, A]`
- 输出: `[B, G, R, A]`

**swizzle_rb_if_bgra**
```cpp
static inline skvx::float4 swizzle_rb_if_bgra(const skvx::float4& x) {
#if defined(SK_PMCOLOR_IS_BGRA)
    return swizzle_rb(x);
#else
    return x;
#endif
}
```
根据平台的原生颜色格式条件编译:
- **Windows/某些配置**: `SK_PMCOLOR_IS_BGRA` 定义,执行交换
- **其他平台**: 直接返回,无操作

**Sk4f_fromL32**
```cpp
static inline skvx::float4 Sk4f_fromL32(uint32_t px) {
    return skvx::cast<float>(skvx::byte4::Load(&px)) * (1 / 255.0f);
}
```
转换流程:
1. 加载 4 字节为 `byte4` 向量
2. 转换为 `float4`
3. 归一化:`[0, 255] → [0.0, 1.0]`

**Sk4f_toL32**
```cpp
static inline uint32_t Sk4f_toL32(const skvx::float4& px) {
    uint32_t l32;
    skvx::cast<uint8_t>(
        skvx::pin(px * 255.f + 0.5f,          // 缩放并四舍五入
                  skvx::float4(0.f),           // 下界
                  skvx::float4(255.f))         // 上界
    ).store(&l32);
    return l32;
}
```
转换流程:
1. 缩放:`[0.0, 1.0] → [0.0, 255.0]`
2. 加 0.5 实现四舍五入
3. 钳制到 `[0, 255]`
4. 转换为 uint8 并存储

## 内部实现细节

### 颜色格式术语

- **RGBA**: Red-Green-Blue-Alpha (非预乘)
- **rgbA**: 预乘 alpha 的 RGBA (小写表示预乘)
- **BGRA**: Blue-Green-Red-Alpha (字节序反转)
- **RGB1**: RGB + 不透明 alpha (255)
- **Gray**: 单通道灰度
- **CMYK**: Cyan-Magenta-Yellow-blacK (印刷色彩空间)

### 预乘 Alpha

**概念:**
预乘 alpha 是将颜色通道预先乘以 alpha 值:
```
非预乘: (R, G, B, A)
预乘:   (R*A, G*A, B*A, A)
```

**优势:**
- 简化混合计算:`C_result = C_src + C_dst * (1 - A_src)`
- GPU 混合模式直接支持
- 避免除法运算

**转换公式:**
```cpp
// 预乘
r' = r * a / 255
g' = g * a / 255
b' = b * a / 255

// 反预乘
r = r' * 255 / a  (需要处理 a == 0 的情况)
```

### CMYK 转换

**反向 CMYK (inverted CMYK):**
某些图像格式存储的是反向值:
```cpp
R = (1 - C) * (1 - K)
G = (1 - M) * (1 - K)
B = (1 - Y) * (1 - K)
```

实际存储可能是:
```cpp
R = C * K  // 其中 C 和 K 已经是反向值
```

### 平台条件编译

```cpp
#if defined(SK_PMCOLOR_IS_BGRA)
```

**SK_PMCOLOR_IS_BGRA 定义场景:**
- Windows 系统(GDI+ 使用 BGRA)
- 某些 GPU 后端(优化纹理格式)
- 用户显式配置

**影响:**
- 改变 `SkPMColor` 的字节序
- 影响 `swizzle_rb_if_bgra` 的行为
- 优化跨平台数据传输

### 数值精度

**四舍五入策略:**
```cpp
px * 255.f + 0.5f
```
加 0.5 后截断等价于四舍五入:
- `0.4 * 255 + 0.5 = 102.5 → 102`
- `0.5 * 255 + 0.5 = 128.0 → 128`

**钳制 (pin/clamp):**
确保结果在有效范围,处理:
- 浮点运算误差
- 超出范围的输入
- 数值溢出

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkVx` | SIMD 向量数学库 |
| `SkColorData` | 颜色数据类型定义 |
| `SkOpts` | 运行时优化选择框架 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `SkSwizzle.cpp` | 实现公共 API |
| `SkSwizzler_opts_*.cpp` | 实现优化版本 |
| `SkColorSpaceXform` | 颜色空间转换 |
| `SkRasterPipeline` | 光栅化管线 |
| GPU 后端 | 纹理格式转换 |

## 设计模式与设计决策

### 设计模式

1. **策略模式**: 函数指针实现可替换的算法
2. **模板方法模式**: 提供通用接口,具体实现由平台决定
3. **内联优化**: 小型辅助函数内联避免调用开销

### 设计决策

**1. 为何区分 u32 和 u8 输入?**
- **u32**: 像素到像素转换,内存布局已知
- **u8**: 字节流到像素,需要组装
- 不同场景的优化策略不同

**2. 为何使用函数指针数组?**
- 运行时选择最优实现
- 同一个二进制支持多种 CPU
- 易于添加新的优化实现

**3. 为何需要 inverted CMYK?**
- 某些图像格式(如 Adobe Photoshop)使用反向存储
- 直接支持避免额外转换步骤
- 常见的图像处理需求

**4. 为何提供浮点转换工具?**
- 高精度颜色计算需要浮点
- 图像滤镜和效果处理
- 颜色空间转换的中间表示

**5. 为何使用 shuffle 而非位运算?**
- SIMD shuffle 是单指令操作
- 位运算需要多个 AND/OR/SHIFT 指令
- shuffle 可以同时处理多个像素

## 性能考量

### SIMD 向量化

所有辅助函数都使用 `skvx` 向量库:
- **向量长度**: 4 个元素(对应 RGBA 四通道)
- **数据类型**: `float4`, `byte4`
- **指令映射**: 编译器自动选择 SSE/AVX/NEON

### 性能特点

| 操作 | 性能特点 |
|------|---------|
| `swizzle_rb` | 单指令 shuffle,极快 |
| `Sk4f_fromL32` | 加载 + 转换 + 乘法,~3 指令 |
| `Sk4f_toL32` | 乘法 + 钳制 + 转换 + 存储,~5 指令 |

### 优化技巧

1. **避免分支**: 使用 shuffle 和向量指令替代条件语句
2. **避免除法**: 使用乘法 `* (1/255)` 替代 `/ 255`
3. **钳制而非检查**: 向量 pin 比条件检查快
4. **内联**: 所有辅助函数声明为 `static inline`

### 数值精度权衡

- **归一化误差**: `1/255.0f` 的浮点表示不精确
- **四舍五入**: 加 0.5 的策略对正数有效
- **可接受性**: 对于 8 位颜色,误差在 ±1 以内不可见

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/core/SkSwizzle.h` | 公共 API 头文件 |
| `src/core/SkSwizzle.cpp` | 公共 API 实现 |
| `src/core/SkSwizzler_opts.cpp` | 默认实现和初始化 |
| `src/core/SkSwizzler_opts_ssse3.cpp` | SSSE3 优化 |
| `src/core/SkSwizzler_opts_hsw.cpp` | AVX2 优化 |
| `src/core/SkSwizzler_opts_lasx.cpp` | LoongArch 优化 |
| `src/opts/SkSwizzler_opts.inc` | 实际 SIMD 实现 |
| `src/base/SkVx.h` | 向量数学库 |
| `src/core/SkColorData.h` | 颜色数据定义 |
| `src/core/SkCpu.h` | CPU 特性检测 |
