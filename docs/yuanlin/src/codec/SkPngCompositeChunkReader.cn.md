# SkPngCompositeChunkReader

> 源文件: src/codec/SkPngCompositeChunkReader.h, src/codec/SkPngCompositeChunkReader.cpp

## 概述

`SkPngCompositeChunkReader` 是 Skia PNG 解码框架中的复合块读取器，用于处理多种 PNG 未知块（unknown chunks）的组合读取需求。PNG 规范允许文件包含自定义块，但 libpng API 一次只能注册一个未知块回调。该类通过包装模式解决了这个限制，同时处理两类未知块：

1. **Skia 内部需要的块**：如 Gainmap（高动态范围图像映射）和 HDR 元数据块
2. **客户端提供的回调**：允许应用层监听其他自定义块

这种设计使得 Skia 能够在支持现代图像特性（HDR、Gainmap）的同时，不影响客户端对自定义块的处理能力。

## 架构位置

```
SkPngChunkReader (抽象基类)
  ├── SkPngCompositeChunkReader (复合读取器)
  │     ├── 内部处理：gmAP, gdAT, cLLI, mDCV
  │     └── 委托给：客户端 SkPngChunkReader
  └── [客户端自定义实现]
```

在 PNG 解码流程中的位置：

```
libpng 解码器
  → 遇到未知块
  → 调用 readChunk() 回调
  → SkPngCompositeChunkReader::readChunk()
        ├── 委托给客户端 reader（如有）
        ├── 检查 gmAP → 解析 SkGainmapInfo
        ├── 检查 gdAT → 存储 Gainmap 数据流
        ├── 检查 cLLI → 解析内容光照级别信息
        └── 检查 mDCV → 解析显示主色域
```

## 主要类与结构体

### SkPngCompositeChunkReader

PNG 复合块读取器，实现 `SkPngChunkReader` 接口。

**成员变量：**
- `sk_sp<SkPngChunkReader> fChunkReader`: 客户端提供的可选块读取器
- `std::optional<SkGainmapInfo> fGainmapInfo`: 解析的 Gainmap 信息
- `std::unique_ptr<SkStream> fGainmapStream`: Gainmap 图像数据流
- `skhdr::Metadata fHdrMetadata`: HDR 元数据（包含 CLLI 和 MDCV）

**核心方法：**
- `readChunk()`: 处理未知块的主回调
- `takeGaimapStream()`: 获取并转移 Gainmap 流的所有权
- `getGainmapInfo()`: 获取 Gainmap 信息
- `getHdrMetadata()`: 获取 HDR 元数据

## 公共 API 函数

### 构造函数

```cpp
explicit SkPngCompositeChunkReader(SkPngChunkReader* chunkReader)
```

创建复合读取器，可选地接受客户端块读取器。

**参数：**
- `chunkReader`: 客户端块读取器（可为 nullptr）

### readChunk

```cpp
bool readChunk(const char tag[], const void* data, size_t length) override
```

处理 PNG 未知块的回调函数，由 libpng 在遇到未知块时调用。

**处理流程：**
1. 首先委托给客户端读取器（如有）
2. 如果客户端返回 false，立即返回 false
3. 检查并处理内部关注的块类型

**支持的块类型：**
- **gmAP**（Gainmap Annotation Parameters）：
  - 包含 Gainmap 参数的元数据
  - 解析为 `SkGainmapInfo` 对象
  - 包括增益映射范围、gamma、基础偏移等

- **gdAT**（Gainmap Data）：
  - 包含 Gainmap 图像的像素数据
  - 存储为 `SkMemoryStream`
  - 后续可被解码为独立图像

- **cLLI**（Content Light Level Information）：
  - HDR 内容光照级别信息
  - 包括最大内容光照级别（MaxCLL）
  - 包括最大帧平均光照级别（MaxFALL）

- **mDCV**（Mastering Display Color Volume）：
  - HDR 显示主色域信息
  - 包括显示原色坐标
  - 包括白点和亮度范围

**返回值：**
- `true`: 块处理成功或已跳过
- `false`: 仅当客户端读取器返回 false 时

### takeGaimapStream

```cpp
std::unique_ptr<SkStream> takeGaimapStream()
```

获取并转移 Gainmap 数据流的所有权。调用后内部流指针被重置。

**返回值：** Gainmap 数据流（可能为 nullptr）

### getGainmapInfo

```cpp
std::optional<SkGainmapInfo> getGainmapInfo() const
```

获取解析的 Gainmap 信息。

**返回值：** 如果成功解析则返回 `SkGainmapInfo`，否则返回空

### getHdrMetadata

```cpp
const skhdr::Metadata& getHdrMetadata() const
```

获取 HDR 元数据的常量引用。

**返回值：** HDR 元数据对象

## 内部实现细节

### 块解析顺序

PNG 文件中块的出现顺序不固定，因此需要处理以下场景：
- gdAT 可能在 gmAP 之前或之后
- cLLI 和 mDCV 可能独立出现
- 同一类型的块可能出现多次（后者覆盖前者）

### Gainmap 数据流管理

使用 `SkMemoryStream::MakeCopy()` 而非 `MakeWithoutCopy()`，原因：
- libpng 提供的 data 指针仅在回调期间有效
- 必须复制数据以保证后续访问安全
- 复制开销是必要的（Gainmap 通常较小）

### 客户端回调优先级

客户端读取器优先处理，设计原因：
1. 允许客户端拦截或修改块处理
2. 客户端可能有特殊的错误处理逻辑
3. 保持向后兼容性

### 空数据处理

```cpp
if (data == nullptr || length == 0) {
    return true;
}
```

空块被视为成功处理，原因：
- PNG 规范允许零长度块
- 可能用于标记或占位
- 不应导致解码失败

### 解析失败处理

当 `SkGainmapInfo::Parse()` 或 HDR 元数据解析失败时：
- **不设置对应的成员变量**（`std::optional` 保持为空）
- **不返回 false**（继续处理其他块）
- **不影响整体解码**（Gainmap 和 HDR 是可选特性）

## 依赖关系

### 直接依赖

- **SkPngChunkReader**: 父类，定义块读取接口
- **SkGainmapInfo**: Gainmap 参数数据结构
- **skhdr::Metadata**: HDR 元数据容器
  - `ContentLightLevelInformation`: cLLI 块数据
  - `MasteringDisplayColorVolume`: mDCV 块数据
- **SkStream**: 数据流接口
- **SkData**: 不可变数据容器

### 间接依赖

- **SkRefCnt**: 引用计数基类
- **SkMemoryStream**: 内存流实现

### 被依赖关系

- **SkPngCodec**: 在创建时传入此读取器
- **SkPngRustCodec**: Rust 实现也使用此读取器

## 设计模式与设计决策

### 装饰器模式

包装客户端的 `SkPngChunkReader`，在不修改其接口的情况下添加新功能。

### 复合模式

组合多个块处理器的功能到单一接口：
- 客户端自定义块
- Gainmap 块
- HDR 元数据块

### 策略模式

根据块类型（tag）选择不同的解析策略。

### 设计决策

1. **单一回调限制的解决方案**：
   - PNG API 限制：一次只能注册一个未知块回调
   - 解决：通过复合类包装，内部分发

2. **内存复制 vs 引用**：
   - 选择：复制 Gainmap 数据
   - 原因：libpng 回调后数据指针失效

3. **失败不传播**：
   - Gainmap 解析失败不影响基础图像解码
   - HDR 元数据失败不影响正常显示
   - 理由：这些是增强特性，非必需

4. **可选特性设计**：
   - 使用 `std::optional<SkGainmapInfo>`
   - 允许查询是否存在 Gainmap
   - 避免默认构造无意义的对象

5. **流所有权转移**：
   - `takeGaimapStream()` 转移所有权
   - 避免重复复制大数据
   - 符合 RAII 原则

## 性能考量

### 优化策略

1. **延迟解析**：
   - 仅在需要时解析 Gainmap 信息
   - HDR 元数据按需使用

2. **单次复制**：
   - Gainmap 数据仅复制一次（从 libpng 回调）
   - 后续通过移动语义转移所有权

3. **字符串比较优化**：
   - 块标签仅 4 字节，`strcmp` 开销可忽略
   - 常见场景下很少遇到这些块

### 性能瓶颈

- **Gainmap 数据复制**：可能较大（取决于原始图像尺寸）
- **串行块处理**：每个块顺序处理，不支持并行

### 内存使用

- **基本开销**：约 200 字节（对象本身）
- **Gainmap 信息**：约 100 字节
- **Gainmap 流**：取决于数据大小（通常 < 原图的 50%）
- **HDR 元数据**：约 200 字节

### 典型场景

| 场景 | 性能影响 |
|------|---------|
| 无 Gainmap 的普通 PNG | 可忽略（仅对象构造） |
| 有 Gainmap 的 HDR PNG | 中等（额外数据复制） |
| 有客户端回调的 PNG | 取决于客户端实现 |
| 多个未知块 | 线性增长（每块串行处理） |

## 相关文件

### 核心文件

- `include/codec/SkPngChunkReader.h`: 父类接口
- `include/private/SkGainmapInfo.h`: Gainmap 参数定义
- `include/private/SkHdrMetadata.h`: HDR 元数据定义

### 使用方

- `src/codec/SkPngCodec.h/cpp`: libpng 解码器
- `src/codec/SkPngRustCodec.h/cpp`: Rust PNG 解码器

### 相关数据结构

- `src/codec/SkGainmapInfo.cpp`: Gainmap 信息实现
- `src/core/SkHdrMetadata.cpp`: HDR 元数据实现

### 测试文件

- `tests/CodecTest.cpp`: 编解码器测试
- `tests/GainmapTest.cpp`: Gainmap 特定测试
- `resources/gainmap/*.png`: 测试用 Gainmap PNG 图像
