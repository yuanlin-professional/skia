# CompressedTexture

> 源文件
> - tools/gpu/CompressedTexture.h
> - tools/gpu/CompressedTexture.cpp

## 概述

`CompressedTexture` 是 Skia GPU 工具集中用于生成 BC1（Block Compression 1，也称 DXT1）压缩纹理数据的工具模块。BC1 是一种有损压缩格式，广泛应用于 GPU 纹理压缩，能够将图像数据压缩到原始大小的 1/6 到 1/8，显著减少 GPU 内存占用和带宽消耗。该模块专门处理只包含两种颜色的简化场景：不透明黑色或透明黑色，以及一种自定义颜色。

核心功能是将符合特定模式的 RGBA 图像压缩为 BC1 格式，支持不透明（RGB）和透明（RGBA）两种变体。该模块主要用于测试 Skia 的压缩纹理支持，特别是验证 GPU 后端正确处理 BC1 格式的能力。代码从 `src/gpu/DataUtils.cpp` 中复制了部分实现，以避免在工具代码中引入 GPU 内部依赖。

## 架构位置

`CompressedTexture` 位于 `tools/gpu/` 目录下，属于 GPU 测试工具层。在 Skia 架构中：

1. **测试支持层**：为单元测试和 GM 测试生成压缩纹理数据，验证 GPU 后端的压缩格式处理能力
2. **独立于核心引擎**：代码特意与 `src/gpu/` 隔离，避免在工具代码中使用 `GPU_TEST_UTILS` 定义
3. **格式转换工具**：提供从标准像素数据到特定压缩格式的转换，补充核心引擎的编解码器

该模块依赖的核心类型：
- `SkPixmap`：输入的像素数据容器
- `SkColor`：色彩表示类型
- `SkColorType`：色彩类型枚举

它被以下场景使用：
- 压缩纹理的单元测试
- GPU 后端兼容性测试
- 压缩格式性能基准测试

## 主要类与结构体

### BC1Block

BC1 压缩块的数据结构，每个块表示 4x4 像素区域（共 16 个像素），总大小 64 位（8 字节）。

**成员变量：**
- `uint16_t fColor0`：第一个参考颜色，RGB565 格式（16 位）
- `uint16_t fColor1`：第二个参考颜色，RGB565 格式（16 位）
- `uint32_t fIndices`：16 个像素的索引表，每个像素用 2 位表示（32 位）

**编码方式：**
- 每个像素使用 2 位索引（0、1、2、3）指向四种可能的颜色之一
- 颜色 0：`fColor0`
- 颜色 1：`fColor1`
- 颜色 2 和 3：根据 `fColor0` 和 `fColor1` 的关系插值或设为透明

**透明模式判断：**
- 如果 `fColor0 <= fColor1`（数值比较），则为透明模式（kBC1_RGBA8_UNORM）
  - 颜色 2：`(2*fColor0 + fColor1) / 3`
  - 颜色 3：透明黑色
- 如果 `fColor0 > fColor1`，则为不透明模式（kBC1_RGB8_UNORM）
  - 颜色 2：`(2*fColor0 + fColor1) / 3`
  - 颜色 3：`(fColor0 + 2*fColor1) / 3`

### 辅助函数（匿名命名空间）

#### num_4x4_blocks
```cpp
static int num_4x4_blocks(int size)
```
计算给定尺寸需要多少个 4x4 块，向上取整到 4 的倍数。

#### to565
```cpp
static uint16_t to565(SkColor col)
```
将 32 位 RGBA 颜色转换为 16 位 RGB565 格式：
- R 通道：5 位（红色）
- G 通道：6 位（绿色）
- B 通道：5 位（蓝色）

使用 `SkMulDiv255Round` 确保精确的比例缩放和舍入。

#### create_BC1_block
```cpp
static void create_BC1_block(SkColor col0, SkColor col1, BC1Block* block)
```
创建一个 BC1 块，初始化为指定的两个颜色。

**参数：**
- `col0`：第一个颜色
- `col1`：第二个颜色
- `block`：输出的 BC1 块结构

**行为：**
- 将颜色转换为 RGB565 格式
- 确保 `fColor0 <= fColor1`（强制透明模式）
- 如果 `col0` 是透明黑色，设置所有像素为颜色 3（透明）
- 否则，设置所有像素为颜色 0

## 公共 API 函数

### TwoColorBC1Compress

```cpp
void TwoColorBC1Compress(const SkPixmap& pixmap, SkColor otherColor, char* dstPixels);
```

将只包含两种颜色（黑色和另一种颜色）的像素图压缩为 BC1 格式。

**参数：**
- `pixmap`：输入的像素数据，必须是 `kRGBA_8888_SkColorType` 格式
- `otherColor`：除了黑色之外的另一种颜色
- `dstPixels`：输出缓冲区，必须足够大以容纳所有 BC1 块（大小 = numXBlocks * numYBlocks * 8 字节）

**前提条件：**
- `pixmap` 中的每个像素必须是以下之一：
  - `SK_ColorBLACK`（不透明黑色）
  - `SK_ColorTRANSPARENT`（透明黑色）
  - `otherColor`（用户指定的颜色）

**输出格式：**
- 如果 pixmap 不包含透明像素，输出为 `kBC1_RGB8_UNORM` 格式
- 如果 pixmap 包含透明像素，输出为 `kBC1_RGBA8_UNORM` 格式

**处理细节：**
- 按 4x4 块遍历图像
- 对于不是 4 的倍数的图像或 mipmap 的高层级，超出边界的像素被跳过
- 黑色像素映射到索引 0
- `otherColor` 像素映射到索引 1
- 透明像素映射到索引 3

## 内部实现细节

### BC1 块布局

每个 BC1 块占用 8 字节，表示 4x4 = 16 个像素：

```
字节 0-1：fColor0（RGB565）
字节 2-3：fColor1（RGB565）
字节 4-7：fIndices（16 个 2 位索引）
```

压缩比：16 像素 * 4 字节/像素（RGBA8888）= 64 字节 → 8 字节，压缩比 8:1。

### 索引位排列

`fIndices` 是一个 32 位整数，从低位到高位依次存储 16 个像素的索引：

```
像素排列（4x4）：
(0,0) (1,0) (2,0) (3,0)
(0,1) (1,1) (2,1) (3,1)
(0,2) (1,2) (2,2) (3,2)
(0,3) (1,3) (2,3) (3,3)

位排列（从低到高）：
bit 0-1:   像素 (0,0)
bit 2-3:   像素 (1,0)
...
bit 30-31: 像素 (3,3)
```

实现中使用位移运算构建索引：
```cpp
shift = (i * 4 + j) * 2;  // 每个像素 2 位
block.fIndices |= index << shift;
```

### RGB565 转换细节

`to565()` 函数执行有损压缩：
- **R 和 B 通道**：从 8 位（256 级）量化到 5 位（32 级），丢失 3 位精度
- **G 通道**：从 8 位量化到 6 位（64 级），丢失 2 位精度（人眼对绿色更敏感）

转换公式：
```cpp
r5 = SkMulDiv255Round(31, SkColorGetR(col));  // 31 = 2^5 - 1
g6 = SkMulDiv255Round(63, SkColorGetG(col));  // 63 = 2^6 - 1
b5 = SkMulDiv255Round(31, SkColorGetB(col));
```

`SkMulDiv255Round` 确保正确的舍入：`(value * scale + 127) / 255`。

### 边界处理

对于尺寸不是 4 的倍数的图像：
- 计算块数时向上取整：`num_4x4_blocks = ((size + 3) & ~3) >> 2`
- 边缘块中超出图像边界的像素被跳过，索引保持为 0（黑色）
- 这对 mipmap 的高层级（如 1x1、2x2、3x3）尤为重要

### 透明模式的选择

代码强制使用透明模式（`fColor0 <= fColor1`）：
```cpp
SkASSERT(block->fColor0 <= block->fColor1);  // we always assume transparent blocks
```

这意味着即使图像完全不透明，也会使用 RGBA 变体。这简化了实现，但可能不是最优的存储方式（RGB 变体可以提供更多的颜色插值选项）。

### 特殊处理透明像素

当遇到 `SK_ColorTRANSPARENT` 时，索引设置为 3：
```cpp
if (tmp == SK_ColorTRANSPARENT) {
    block.fIndices |= 3 << shift;  // 索引 3 = 透明黑色
}
```

在透明模式下（`fColor0 <= fColor1`），索引 3 被 GPU 解释为完全透明的黑色。

## 依赖关系

### 核心依赖

- **SkColorType**：色彩类型枚举（如 `kRGBA_8888_SkColorType`）
- **SkPixmap**：像素数据容器，提供 `getColor()` 等方法
- **SkColor**：32 位 RGBA 颜色类型
- **SkMulDiv255Round**：精确的颜色通道缩放函数（隐式依赖）

### 标准库依赖

- **<cstdint>**：`uint16_t`、`uint32_t` 类型（通过 Skia 头文件间接包含）

### 被依赖

- 压缩纹理单元测试（`tests/CompressedTextureTest.cpp` 或类似）
- GPU 后端兼容性测试
- 压缩格式性能基准测试

### 相关文件

- `src/gpu/DataUtils.cpp` - 原始实现所在位置，包含更完整的压缩功能
- `include/gpu/GpuTypes.h` - GPU 类型定义，包括压缩格式枚举

## 设计模式与设计决策

### 简化的两色模型

只支持两种颜色加透明：
- **优点**：实现简单，适合测试场景
- **局限**：不能处理复杂的多色图像，但对于验证 GPU 支持已足够

### 强制透明模式

即使图像完全不透明，也使用透明 BC1 模式（`fColor0 <= fColor1`）：
- **原因**：简化逻辑，避免判断是否需要透明支持
- **代价**：可能浪费一个颜色插值槽位（在不透明模式下有 4 个插值颜色，透明模式下只有 3 个）

### 代码复制而非共享

从 `src/gpu/DataUtils.cpp` 复制代码而非引用：
- **原因**：避免在工具代码中使用 `GPU_TEST_UTILS` 定义，保持工具层与核心 GPU 代码的隔离
- **代价**：代码重复，需要手动同步修改
- **注释说明**："Ideally we would copy the test function into DataUtils.cpp instead"，表明这是临时方案

### 块级处理

以 4x4 块为单位处理图像：
- 符合 BC1 格式的自然粒度
- 便于处理内存布局和索引计算
- 自动处理非 4 倍数尺寸的边界情况

### 直接位操作

使用位移和按位或构建索引表：
```cpp
block.fIndices |= index << shift;
```
- **优点**：高效，直接操作底层位表示
- **风险**：代码可读性较差，需要仔细计算位偏移

## 性能考量

### 压缩比

BC1 格式提供固定 8:1 压缩比：
- 原始 RGBA8888：16 像素 * 4 字节 = 64 字节
- 压缩 BC1：8 字节
- 显著减少 GPU 内存和带宽需求

### 质量损失

BC1 是有损压缩：
- RGB565 量化导致颜色精度损失
- 每个 4x4 块只能表示少数几种颜色（2 个参考色 + 插值色）
- 对于两色图像，质量损失相对较小

### 编码性能

该实现采用简单的逐像素扫描：
- 时间复杂度：O(width * height)
- 没有复杂的优化或并行化
- 对于测试场景已足够快，但不适合实时编码

### 内存访问模式

按块顺序遍历（外层 Y 块，内层 X 块，最内层 4x4 像素）：
- 对于输出缓冲区（块数组）是顺序访问，缓存友好
- 对于输入 pixmap 可能跳跃访问，取决于 `getColor()` 的实现

### 适用范围

该实现专为简单测试场景设计：
- 适合生成测试数据
- 不适合处理真实世界的复杂图像
- 不支持颜色优化或误差扩散

## 相关文件

### 核心依赖

- `include/core/SkColorType.h` - 色彩类型定义
- `include/core/SkPixmap.h` - 像素数据容器
- `include/core/SkColor.h` - 颜色类型和工具函数

### GPU 相关

- `src/gpu/DataUtils.h` - GPU 数据工具（原始实现）
- `include/gpu/GpuTypes.h` - GPU 类型定义，包括压缩格式

### 测试使用

- `tests/` - 压缩纹理测试用例
- `gm/` - 可能的 GM 测试（如果有使用压缩纹理的测试）

### 相关工具类

- `tools/gpu/ManagedBackendTexture.h` - 后端纹理管理（可能用于上传压缩数据）
- `tools/gpu/BackendSurfaceFactory.h` - 后端表面创建工具
