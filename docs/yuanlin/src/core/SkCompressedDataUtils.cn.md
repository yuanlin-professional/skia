# SkCompressedDataUtils

> 源文件: src/core/SkCompressedDataUtils.h, src/core/SkCompressedDataUtils.cpp

## 概述

`SkCompressedDataUtils` 是 Skia 中处理压缩纹理数据的工具模块,提供了压缩纹理格式(如 ETC1/ETC2 和 BC1)的解压缩、大小计算和相关实用函数。该模块支持纹理压缩格式的元数据查询和实际解压缩操作,是 GPU 纹理处理流水线的重要组成部分。

## 架构位置

`SkCompressedDataUtils` 位于 Skia 核心层(src/core),是纹理和图像处理子系统的一部分。它为 GPU 后端提供压缩纹理支持,连接了高层的图像 API 和底层的 GPU 纹理系统。该模块主要服务于 Graphite 和 Ganesh GPU 后端。

## 主要类与结构体

该文件不定义公开的类,而是提供一组工具函数和内部结构体。

### 内部结构体

#### ETC1Block

| 成员 | 类型 | 说明 |
|------|------|------|
| `fHigh` | `uint32_t` | ETC1 块的高 32 位 |
| `fLow` | `uint32_t` | ETC1 块的低 32 位 |

#### BC1Block

| 成员 | 类型 | 说明 |
|------|------|------|
| `fColor0` | `uint16_t` | 第一个 RGB565 颜色 |
| `fColor1` | `uint16_t` | 第二个 RGB565 颜色 |
| `fIndices` | `uint32_t` | 4x4 像素的索引数据 |

#### IColor

| 成员 | 类型 | 说明 |
|------|------|------|
| `fR`, `fG`, `fB` | `int` | 整数型 RGB 颜色分量 |

## 公共 API 函数

### 格式查询

```cpp
constexpr bool SkTextureCompressionTypeIsOpaque(SkTextureCompressionType compression);
```
- 检查压缩格式是否不透明
- 编译时常量函数
- ETC2_RGB8、BC1_RGB8 返回 true
- BC1_RGBA8 返回 false

```cpp
size_t SkCompressedBlockSize(SkTextureCompressionType type);
```
- 返回单个压缩块的字节大小
- ETC1/ETC2 和 BC1 都是 8 字节

### 数据大小计算

```cpp
size_t SkCompressedDataSize(SkTextureCompressionType, SkISize baseDimensions,
                            skia_private::TArray<size_t>* individualMipOffsets,
                            bool mipmapped);
```
- 计算压缩纹理数据总大小
- 可选返回各级 mipmap 的偏移量
- 支持 mipmap 链计算

```cpp
size_t SkCompressedFormatDataSize(SkTextureCompressionType compressionType,
                                  SkISize dimensions, bool mipmapped);
```
- `SkCompressedDataSize` 的简化版本
- 不返回 mipmap 偏移量

### 解压缩

```cpp
bool SkDecompress(sk_sp<SkData> data, SkISize dimensions,
                  SkTextureCompressionType compressionType,
                  SkBitmap* dst);
```
- 将压缩数据解压缩到 SkBitmap
- 仅解压缩最底层的 mipmap 级别
- 支持 ETC2_RGB8_UNORM、BC1_RGB8_UNORM、BC1_RGBA8_UNORM

## 内部实现细节

### ETC1 解压缩算法

ETC1 使用 4x4 块压缩,每个块分为两个 2x4 或 4x2 子块:

```cpp
static bool decompress_etc1(SkISize dimensions, const uint8_t* srcData, SkBitmap* dst) {
    // 1. 遍历所有 4x4 块
    // 2. 解析块的高/低 32 位
    // 3. 提取 flip bit(T/B 或 L/R 子块布局)
    // 4. 提取 differential bit(差分或独立颜色模式)
    // 5. 计算两个子块的基础颜色
    // 6. 使用修改器表计算每个像素的最终颜色
}
```

**修改器表** (`kETC1ModifierTables`): 8 个表,每个包含 4 个修改值,用于调整基础颜色。

### BC1 解压缩算法

BC1 也使用 4x4 块压缩,使用两个 RGB565 颜色和 2-bit 索引:

```cpp
static bool decompress_bc1(SkISize dimensions, const uint8_t* srcData,
                           bool isOpaque, SkBitmap* dst) {
    // 1. 从 RGB565 转换基础颜色到 RGB888
    // 2. 根据 color0 和 color1 的大小关系计算插值颜色:
    //    - color0 > color1: 4 色模式(两个插值色)
    //    - color0 <= color1: 3 色模式 + 透明色
    // 3. 使用 2-bit 索引选择最终颜色
}
```

### 辅助函数

#### 位扩展

```cpp
static inline int extend_4To8bits(int b) {
    int c = b & 0xf;
    return (c << 4) | c;  // 0xF -> 0xFF
}

static inline int extend_5To8bits(int b) {
    int c = b & 0x1f;
    return (c << 3) | (c >> 2);  // 0x1F -> 0xFF
}
```
用于将低位宽颜色扩展到 8 位,保持相对比例。

#### 块计算

```cpp
static int num_4x4_blocks(int size) {
    return ((size + 3) & ~3) >> 2;
}
```
计算覆盖指定尺寸所需的 4x4 块数,自动向上取整。

## 依赖关系

**依赖的模块:**

| 模块 | 用途 |
|------|------|
| `SkBitmap` | 作为解压缩输出目标 |
| `SkData` | 存储压缩数据 |
| `SkTextureCompressionType` | 定义压缩格式枚举 |
| `SkColorData` | 颜色数据操作 |
| `SkColorPriv` | 颜色转换工具 |
| `SkMipmap` | Mipmap 级别计算 |

**被依赖的模块:**

| 模块 | 关系 |
|------|------|
| GPU 后端 (Graphite/Ganesh) | 使用压缩纹理功能 |
| 图像解码器 | 可能生成压缩纹理数据 |
| `SkImage` | 可能包含压缩纹理数据 |

## 设计模式与设计决策

### 格式特定的静态函数

每种压缩格式有独立的解压缩函数,而不是使用多态:
- 便于编译器优化
- 减少运行时开销
- 每种格式的算法差异较大,不适合统一接口

### 分离元数据和数据操作

- 元数据函数(如 `SkCompressedBlockSize`)是 constexpr 或简单计算
- 数据操作函数(如 `SkDecompress`)处理实际的解压缩

### 仅解压缩最底层级别

`SkDecompress` 只处理基础 mipmap 级别:
- 简化 API
- 大多数用例不需要完整的 mipmap 链解压缩
- 可以按需解压缩其他级别

## 性能考量

### 块级并行化潜力

解压缩算法是块独立的,理论上可以并行化,但当前实现是串行的。

### 边界处理

对于非 4 的倍数的纹理尺寸,使用边界检查:
```cpp
if (offsetX + j >= dst->width() || offsetY + i >= dst->height()) {
    continue;  // 跳过超出边界的像素
}
```

### 字节序处理

ETC1 使用大端字节序:
```cpp
uint32_t high = SkBSwap32(curBlock1->fHigh);
uint32_t low = SkBSwap32(curBlock1->fLow);
```

### 查找表优化

使用预计算的修改器表 (`kETC1ModifierTables`) 而不是运行时计算,提高解压缩速度。

### 内联辅助函数

位扩展和颜色转换函数都声明为 `static inline`,减少函数调用开销。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/core/SkBitmap.h` | 输出 | 解压缩数据的目标 |
| `include/core/SkData.h` | 输入 | 压缩数据的容器 |
| `include/core/SkTextureCompressionType.h` | 定义 | 压缩格式枚举 |
| `src/core/SkColorData.h` | 依赖 | 颜色数据操作 |
| `src/core/SkColorPriv.h` | 依赖 | 颜色转换工具 |
| `src/core/SkMipmap.h` | 依赖 | Mipmap 计算 |
| `src/gpu/graphite/TextureProxy.h` | 使用者 | GPU 纹理代理 |
