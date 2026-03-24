# DataUtils

> 源文件: src/gpu/DataUtils.h, src/gpu/DataUtils.cpp

## 概述

`DataUtils` 是 Skia GPU 模块中专门处理压缩纹理数据的工具集,提供纹理压缩格式的尺寸计算、行字节数计算以及压缩数据填充功能。该模块支持 ETC2_RGB8、BC1_RGB8 和 BC1_RGBA8 等常见的块压缩格式,为 GPU 纹理的创建、传输和管理提供底层支持。

主要功能包括:压缩块的数量计算、压缩纹理的尺寸对齐、以及用纯色填充压缩纹理数据(常用于测试和占位符纹理)。该模块的设计目标是抽象不同压缩格式的细节差异,为上层提供统一的接口。

## 架构位置

在 Skia 架构中,`DataUtils` 位于以下位置:

- **上游依赖**: 依赖 `SkTextureCompressionType` 定义的压缩格式枚举
- **同级模块**: 与 GPU 资源管理模块协作
- **下游使用**: 被 Ganesh 和 Graphite 的纹理创建路径使用
- **应用场景**: 压缩纹理上传、纹理数据生成、单元测试

该模块是平台无关的,不依赖特定的 GPU API,提供通用的压缩纹理处理逻辑。

## 主要类与结构体

本模块主要提供静态工具函数,内部定义了以下结构体:

### ETC1Block (内部)
```cpp
struct ETC1Block {
    uint32_t fHigh;  // 高32位数据
    uint32_t fLow;   // 低32位数据
};
```
**用途**: ETC1/ETC2 压缩块的数据结构,每个块编码 4×4 像素。

### BC1Block (内部)
```cpp
struct BC1Block {
    uint16_t fColor0;   // 颜色0 (RGB565)
    uint16_t fColor1;   // 颜色1 (RGB565)
    uint32_t fIndices;  // 16个像素的索引 (每个2位)
};
```
**用途**: BC1 (DXT1) 压缩块的数据结构,同样编码 4×4 像素。

### 常量定义

| 常量 | 值 | 说明 |
|------|-----|------|
| `kDiffBit` | `0x2` | ETC1 差分模式标志位 |
| `kNumETC1ModifierTables` | `8` | ETC1 修改器表数量 |
| `kNumETC1PixelIndices` | `4` | ETC1 像素索引数 |

## 公共 API 函数

### NumCompressedBlocks
```cpp
size_t NumCompressedBlocks(SkTextureCompressionType type, SkISize baseDimensions)
```
**功能**: 计算给定尺寸的纹理需要多少个压缩块。
**参数**:
- `type`: 压缩格式类型
- `baseDimensions`: 纹理基础尺寸
**返回**: 压缩块的总数。
**算法**: 对于 4×4 块格式,计算 `ceil(width/4) * ceil(height/4)`。

### CompressedRowBytes
```cpp
size_t CompressedRowBytes(SkTextureCompressionType type, int width)
```
**功能**: 计算压缩纹理一行的字节数(用于数据传输)。
**参数**:
- `type`: 压缩格式
- `width`: 纹理宽度
**返回**: 行字节数。
**计算**: `ceil(width/4) * sizeof(Block)`。

### CompressedDimensions
```cpp
SkISize CompressedDimensions(SkTextureCompressionType type, SkISize baseDimensions)
```
**功能**: 返回压缩纹理的对齐后像素尺寸。
**参数**:
- `type`: 压缩格式
- `baseDimensions`: 原始尺寸
**返回**: 对齐到块边界的尺寸。
**说明**: 1×1 或 2×2 的 mipmap 级别仍占用完整的 4×4 块。

### CompressedDimensionsInBlocks
```cpp
SkISize CompressedDimensionsInBlocks(SkTextureCompressionType type, SkISize baseDimensions)
```
**功能**: 返回以块为单位的纹理尺寸。
**参数**: 同上。
**返回**: 块数量的二维尺寸。
**用途**: 用于内存分配和数据布局计算。

### FillInCompressedData
```cpp
void FillInCompressedData(SkTextureCompressionType type,
                          SkISize dimensions,
                          skgpu::Mipmapped mipmapped,
                          char* dest,
                          const SkColor4f& color)
```
**功能**: 用指定颜色填充压缩纹理数据(包括 mipmap 链)。
**参数**:
- `type`: 压缩格式
- `dimensions`: 基础纹理尺寸
- `mipmapped`: 是否生成 mipmap
- `dest`: 目标缓冲区
- `color`: 填充颜色
**用途**: 测试、占位符纹理生成、调试可视化。
**算法**: 为每个 mipmap 级别依次填充,尺寸逐级减半。

## 内部实现细节

### ETC1 压缩算法

#### 修改器表
ETC1 使用8个预定义的修改器表,每个表包含4个修正值:
```cpp
const int kETC1ModifierTables[8][4] = {
    { 2,   8,  -2,   -8},
    { 5,  17,  -5,  -17},
    ...
    {47, 183, -47, -183}
};
```

#### 块创建流程 (`create_etc1_block`)
1. **颜色量化**: 将 RGB8 转换为 RGB555
2. **颜色扩展**: 将 5 位颜色扩展回 8 位
3. **修改器匹配**: 遍历所有表和索引,找到最接近目标颜色的组合
4. **编码**: 使用差分模式,设置基础颜色和修改器表索引
5. **索引编码**: 根据最佳像素索引设置 `fLow` 的位

#### 优化策略
- 总是使用差分模式(diff bit = 1),简化编码
- 差分值设为0(bits 26-24, 18-16, 10-8),即子块颜色相同
- 使用穷举搜索(8×4=32种组合)找到最小误差

### BC1 压缩算法

#### 颜色转换 (`to565`)
```cpp
r5 = r8 * 31 / 255
g6 = g8 * 63 / 255
b5 = b8 * 31 / 255
```
使用 `SkMulDiv255Round` 保证正确的舍入。

#### 块创建流程 (`create_BC1_block`)
1. **颜色转换**: 将 RGBA8888 转换为 RGB565
2. **透明处理**: 保证 `fColor0 <= fColor1` (透明块约定)
3. **索引设置**:
   - 透明色: 所有像素使用索引3 (`fIndices = 0xFFFFFFFF`)
   - 不透明色: 所有像素使用索引0 (`fIndices = 0`)

#### 限制
当前实现只支持纯色填充,不支持任意图像的 BC1 压缩(需要更复杂的聚类算法)。

### 块尺寸计算

#### num_4x4_blocks
```cpp
static int num_4x4_blocks(int size) {
    return ((size + 3) & ~3) >> 2;
}
```
**算法**: 向上对齐到4的倍数,然后除以4。
**等价**: `ceil(size / 4.0)`。

### Mipmap 生成
`FillInCompressedData` 支持 mipmap 链的生成:
- 计算 mipmap 级别数: `SkMipmap::ComputeLevelCount()`
- 为每个级别填充数据
- 尺寸按 `max(1, size/2)` 递减
- 使用 `SkCompressedDataSize()` 计算每级的数据大小

### 错误处理
- 检查 `SkIsFinite()` 防止 NaN/Infinity
- 检查溢出(如 `sixSigma > SK_MaxS32/4 + 1`)
- 分配失败时返回空结果

## 依赖关系

### 依赖的模块

| 模块 | 依赖内容 | 用途 |
|------|----------|------|
| `include/core/SkTextureCompressionType.h` | `SkTextureCompressionType` | 压缩格式枚举 |
| `include/core/SkColor.h` | `SkColor`, `SkColor4f` | 颜色类型 |
| `include/gpu/GpuTypes.h` | `skgpu::Mipmapped` | Mipmap 标志 |
| `src/core/SkCompressedDataUtils.h` | `SkCompressedDataSize` | 数据大小计算 |
| `src/core/SkMipmap.h` | `ComputeLevelCount` | Mipmap 级别计算 |
| `src/base/SkMathPriv.h` | `SkMulDiv255Round`, `SkTAbs` | 数学工具 |

### 被依赖的模块

| 模块 | 使用内容 | 用途 |
|------|----------|------|
| Ganesh 纹理创建 | `FillInCompressedData` | 压缩纹理生成 |
| Graphite 纹理管理 | 尺寸计算函数 | 资源分配 |
| 单元测试 | 所有公共函数 | 压缩纹理测试 |
| 纹理上传路径 | `CompressedRowBytes` | 数据传输 |

## 设计模式与设计决策

### 1. 工具函数集合
采用静态函数而非类设计,避免不必要的抽象层,直接提供功能。

### 2. 格式抽象
通过 `SkTextureCompressionType` 枚举抽象不同格式,使用 switch-case 分发到具体实现。

### 3. 对齐策略
压缩纹理的尺寸总是向上对齐到块边界(4的倍数),符合 GPU 硬件要求。

### 4. 纯色优化
当前实现针对纯色填充优化,避免复杂的图像压缩算法:
- ETC1: 使用最佳修改器匹配
- BC1: 使用单一颜色索引

### 5. 字节序处理
ETC1 块使用 `SkBSwap32()` 进行字节序转换,确保跨平台兼容性。

### 6. 防御性编程
- 所有可能溢出的计算都有检查
- 使用 `SkASSERT` 验证假设
- 使用 `SkUNREACHABLE` 标记不应到达的路径

## 性能考量

### 1. 算法复杂度
- **块数计算**: O(1)
- **ETC1 编码**: O(32) 每块(8表×4索引)
- **BC1 编码**: O(1) (纯色模式)
- **Mipmap 填充**: O(n) 其中 n 是总块数

### 2. 内存效率
- 压缩格式减少 4-6 倍的内存占用(相比 RGBA8)
- ETC1/BC1 每块8字节,覆盖16像素
- Mipmap 链额外占用约 1/3 的基础级别大小

### 3. 缓存友好
- 块结构紧凑(8字节)
- 线性内存布局
- 批量填充减少缓存未命中

### 4. 查找表优化
ETC1 修改器表为 `static constexpr`,编译时初始化,无运行时开销。

### 5. 分支预测
`switch(type)` 语句会被编译器优化为跳转表,高效分发。

### 6. SIMD 潜力
虽然当前实现未使用 SIMD,但块处理的结构化特性使其易于向量化优化(未来工作)。

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/gpu/DataUtils.h` | 定义 | 数据工具接口 |
| `src/gpu/DataUtils.cpp` | 实现 | 压缩数据处理实现 |
| `include/core/SkTextureCompressionType.h` | 依赖 | 压缩格式定义 |
| `src/core/SkCompressedDataUtils.h` | 依赖 | 压缩数据大小计算 |
| `src/gpu/ganesh/GrTexture.cpp` | 使用者 | Ganesh 纹理创建 |
| `src/gpu/graphite/Texture.cpp` | 使用者 | Graphite 纹理管理 |
| `tests/CompressedBackendAllocationTest.cpp` | 测试 | 压缩纹理测试 |

**备注**: 该模块专注于压缩纹理的底层数据处理,是 GPU 纹理管理的基础设施。虽然当前实现主要用于测试和占位符,但为未来完整的压缩纹理支持提供了框架。
