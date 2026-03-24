# Sk4px

> 源文件
> - src/core/Sk4px.h

## 概述

`Sk4px` 是 Skia 中用于 SIMD（单指令多数据）处理的像素向量化类，能够同时操作 1、2 或 4 个 `SkPMColor` 像素。该类封装了 16 字节的向量寄存器（`skvx::byte16`），利用现代 CPU 的向量指令集（如 SSE、NEON、AVX）实现高性能的像素级并行计算。

主要应用场景包括：
- 颜色混合（alpha 合成）
- 像素格式转换
- 批量像素处理
- 图像特效和滤镜

通过向量化，`Sk4px` 可以在单条指令中处理多个像素，显著提升渲染性能。

## 架构位置

`Sk4px` 位于 Skia 的低级优化层：

```
高级绘制 API (SkPaint, SkShader)
    ↓
混合模式 / 着色器
    ↓
像素处理 (Sk4px)  ← 本层
    ↓
向量抽象层 (skvx)
    ↓
CPU 指令集 (SSE, NEON, AVX)
```

该类主要被以下模块使用：
- **SkBlitter**：像素填充优化
- **SkBlendMode**：混合模式加速
- **SkColor**：颜色空间转换
- **SkXfermode**：传输模式实现

## 主要类与结构体

### Sk4px

**继承关系**：无基类，独立类

**关键成员变量**：

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fV` | `skvx::byte16` | 16 字节向量，存储最多 4 个像素 |

**数据布局**（小端序）：
```
[R0 G0 B0 A0] [R1 G1 B1 A1] [R2 G2 B2 A2] [R3 G3 B3 A3]
 ← 像素 0 →    ← 像素 1 →    ← 像素 2 →    ← 像素 3 →
```

每个像素 4 字节，最多存储 4 个 `SkPMColor`（预乘 RGBA）。

### Sk4px::Wide

嵌套类，表示宽精度（16 位）像素数据。

**继承关系**：无基类

**关键成员变量**：

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fV` | `skvx::Vec<16, uint16_t>` | 16 个 16 位通道 |

**用途**：
- 存储乘法中间结果（8位 × 8位 = 16位）
- 避免溢出
- 提供高精度除法（`div255()`）

## 公共 API 函数

### 构造与加载

| 函数 | 说明 |
|------|------|
| `Sk4px(const skvx::byte16&)` | 从向量构造 |
| `DupPMColor(SkPMColor)` | 复制单个颜色到 4 个像素 |
| `Load4(const SkPMColor[4])` | 加载 4 个像素 |
| `Load2(const SkPMColor[2])` | 加载 2 个像素（低位） |
| `Load1(const SkPMColor[1])` | 加载 1 个像素（低位） |
| `Load4Alphas(const SkAlpha[4])` | 加载 4 个 alpha，扩展到像素 |
| `Load2Alphas(const SkAlpha[2])` | 加载 2 个 alpha，扩展到像素 |

### 存储

| 函数 | 说明 |
|------|------|
| `store4(SkPMColor[4])` | 存储 4 个像素 |
| `store2(SkPMColor[2])` | 存储 2 个像素 |
| `store1(SkPMColor[1])` | 存储 1 个像素 |

### 像素操作

| 函数 | 说明 |
|------|------|
| `alphas()` | 提取 alpha 通道（广播到 RGBA） |
| `inv()` | 取反（255 - 值） |
| `widen()` | 扩展到 16 位精度 |
| `mulWiden(const skvx::byte16&)` | 8位乘法 → 16位结果 |

### 算术运算符

| 运算符 | 说明 |
|--------|------|
| `operator+(const Sk4px&)` | 分量加法（8位，可能溢出） |
| `operator-(const Sk4px&)` | 分量减法（8位，可能下溢） |
| `operator*(const Sk4px&)` | 8位乘法 → 16位 `Wide` 结果 |
| `operator<(const Sk4px&)` | 分量比较，返回掩码 |
| `operator&(const Sk4px&)` | 按位与 |

### 特殊操作

| 函数 | 说明 |
|------|------|
| `approxMulDiv255(const Sk4px&)` | 快速近似 `(a × b) / 255` |
| `saturatedAdd(const Sk4px&)` | 饱和加法（不溢出） |
| `thenElse(const Sk4px&, const Sk4px&)` | 三元选择（基于掩码） |

### 批量处理函数（静态模板）

| 函数 | 签名 | 说明 |
|------|------|------|
| `MapSrc` | `(int n, SkPMColor* dst, const SkPMColor* src, Fn fn)` | 遍历源数组，应用函数 |
| `MapDstSrc` | `(int n, SkPMColor* dst, const SkPMColor* src, Fn fn)` | 同时读取目标和源 |
| `MapDstAlpha` | `(int n, SkPMColor* dst, const SkAlpha* a, Fn fn)` | 应用 alpha 值到目标 |
| `MapDstSrcAlpha` | `(int n, SkPMColor* dst, const SkPMColor* src, const SkAlpha* a, Fn fn)` | 三参数混合 |

这些模板函数自动处理：
- 循环展开（优先处理 8 像素）
- 边界情况（1、2、4 像素）
- 保持单一循环以利于编译器优化

## 内部实现细节

### Alpha 通道提取

`alphas()` 函数提取每个像素的 alpha 通道并广播：

```cpp
// 输入: [R0 G0 B0 A0] [R1 G1 B1 A1] ...
// 输出: [A0 A0 A0 A0] [A1 A1 A1 A1] ...
shuffle<3,3,3,3, 7,7,7,7, 11,11,11,11, 15,15,15,15>(fV)
```

索引 3、7、11、15 对应每个像素的 alpha 字节（假设小端序）。

### 近似除法 `approxMulDiv255()`

实现快速的 `(a × b) / 255` 近似：

```cpp
approx_scale(fV, o.fV)  // 内部实现：(a * b + 128) >> 8
```

**误差**：
- 可能偏差 ±1
- 当 `a == 0` 或 `a == 255` 或 `b == 0` 或 `b == 255` 时精确

**优势**：
- 避免昂贵的整数除法
- 比 `(a * b * 257 + 256) >> 16` 更快

### 精确除法 `Wide::div255()`

宽精度版本提供精确结果：

```cpp
div255(fV)  // 内部实现：(v + 127 + (v >> 8)) >> 8
```

这是标准的 `(x + 127) / 255` 取整方法。

### 批量处理优化

`MapSrc` 等函数采用分层处理：

1. **主循环**：优先处理 8 像素块
   - 保持步长一致，利于循环展开
   - 减少循环开销

2. **尾部处理**：依次处理 4、2、1 像素
   - 覆盖所有可能的余数
   - 避免越界访问

3. **单一循环结构**：
   - 使用 `continue` 保持在同一循环
   - 帮助编译器进行循环不变量提升

### SIMD 指令映射

底层向量操作通过 `skvx` 映射到硬件指令：

| 操作 | x86 (SSE) | ARM (NEON) |
|------|-----------|------------|
| 加法 | `_mm_add_epi8` | `vaddq_u8` |
| 减法 | `_mm_sub_epi8` | `vsubq_u8` |
| 饱和加 | `_mm_adds_epu8` | `vqaddq_u8` |
| 乘法 | `_mm_mullo_epi16` | `vmullq_u8` |
| Shuffle | `_mm_shuffle_epi8` | `vtbl` |

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `skvx` | 跨平台向量抽象层 |
| `SkColor` | 颜色类型定义 |
| `SkColorData` | 颜色位操作（如 `SkGetPackedR16`） |

### 被依赖的模块

| 模块 | 说明 |
|------|------|
| `SkBlitter` 及其子类 | 使用 `Sk4px` 加速像素填充 |
| `SkXfermode` | 混合模式的向量化实现 |
| `SkBlendMode` | 颜色混合加速 |
| `SkOpts` | 平台特定的优化实现 |

## 设计模式与设计决策

### SIMD 抽象模式

`Sk4px` 提供高级接口，隐藏底层 SIMD 细节：
- 统一 API 跨平台
- 编译器选择最优指令集
- 易于维护和扩展

### 窄/宽精度分离

通过 `Wide` 类分离精度级别：
- 8 位用于存储和快速运算
- 16 位用于中间计算，防止溢出
- 明确的精度转换点

### 模板驱动批处理

`MapSrc` 等函数使用模板：
- 函数对象内联，无虚函数开销
- 编译时优化整个处理管线
- 类型安全

### 零成本抽象

`Sk4px` 的设计目标：
- 与手写 SIMD 代码性能相当
- 更高的可读性和可维护性
- 编译时优化掉抽象层

## 性能考量

### 向量化带来的加速

理论加速比：
- SSE：一次处理 16 字节 = 4 像素，**4×** 加速
- AVX：一次处理 32 字节 = 8 像素，**8×** 加速
- NEON：一次处理 16 字节 = 4 像素，**4×** 加速

实际加速取决于：
- 内存带宽
- 循环展开
- 指令流水线

### 内存对齐

虽然 `Sk4px` 不强制对齐，但对齐访问更快：
- SSE：16 字节对齐避免跨缓存行
- 某些指令要求对齐（如 `_mm_load_si128`）

### 批量处理的优势

1. **循环开销减少**：每次迭代处理多个像素
2. **指令流水线**：并行执行多条指令
3. **缓存效率**：连续内存访问

### 快速近似 vs. 精确计算

`approxMulDiv255()` vs. `Wide::div255()`：
- 近似版本更快（~2×），适用于大多数场景
- 精确版本用于关键质量路径
- 选择取决于视觉质量要求

### 编译器优化友好

设计特点：
- 简单的控制流
- 无分支的核心操作
- 内联友好的小函数

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/core/Sk4px.h` | 类定义和实现（仅头文件） |
| `src/base/SkVx.h` | 底层向量抽象 |
| `include/core/SkColor.h` | 颜色类型定义 |
| `src/core/SkColorData.h` | 颜色位操作宏 |
| `src/core/SkBlitter.cpp` | 使用 `Sk4px` 的像素填充 |
| `src/core/SkBlendMode.cpp` | 混合模式向量化 |
| `src/opts/` | 平台特定优化（可能使用 `Sk4px`） |

## 使用示例

### 基本像素处理

```cpp
// 加载 4 个像素
Sk4px pixels = Sk4px::Load4(src);

// 反转颜色
Sk4px inverted = pixels.inv();

// 存储结果
inverted.store4(dst);
```

### Alpha 混合

```cpp
// src_over 混合：dst = src + dst * (1 - src_alpha)
Sk4px src = Sk4px::Load4(srcPixels);
Sk4px dst = Sk4px::Load4(dstPixels);

Sk4px srcAlpha = src.alphas();
Sk4px invAlpha = srcAlpha.inv();

Sk4px result = src + dst.approxMulDiv255(invAlpha);
result.store4(dstPixels);
```

### 批量转换

```cpp
// 将所有像素乘以 alpha
Sk4px::MapSrc(count, dst, src, [alpha](const Sk4px& s) {
    return s.approxMulDiv255(alpha);
});
```
