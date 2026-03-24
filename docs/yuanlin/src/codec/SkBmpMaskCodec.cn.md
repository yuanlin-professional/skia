# SkBmpMaskCodec

> 源文件: src/codec/SkBmpMaskCodec.h, src/codec/SkBmpMaskCodec.cpp

## 概述

`SkBmpMaskCodec` 是 Skia 图像编解码框架中用于处理位掩码格式 BMP 图像的专用解码器。它继承自 `SkBmpBaseCodec`，专门处理那些使用颜色掩码来定义像素格式的 BMP 图像，例如 16 位和 32 位的 BMP 文件。这类格式通过位掩码来指定红、绿、蓝和可选的 alpha 通道在像素值中的位置，提供了比标准调色板格式更灵活的颜色表示方式。

该类的核心职责是解析位掩码信息，并使用 `SkMaskSwizzler` 将原始像素数据按照掩码规则转换为 Skia 内部使用的标准像素格式。它支持自上而下和自下而上两种扫描线顺序，并能够处理颜色空间转换。

## 架构位置

`SkBmpMaskCodec` 位于 Skia 的编解码器子系统中，具体层次结构如下：

```
SkCodec (抽象基类)
  └── SkBmpBaseCodec (BMP 格式基类)
        └── SkBmpMaskCodec (位掩码 BMP 专用解码器)
```

在 BMP 解码的执行流程中，`SkBmpCodec::MakeFromStream` 会根据 BMP 文件的压缩类型和颜色深度创建相应的解码器实例。当检测到使用位掩码格式时（如 BI_BITFIELDS 压缩类型），会实例化 `SkBmpMaskCodec` 来处理解码任务。

该类与以下组件紧密协作：
- **SkMasks**: 存储和管理颜色掩码信息
- **SkMaskSwizzler**: 执行实际的像素格式转换
- **SkColorSpaceXform**: 处理颜色空间转换（可选）

## 主要类与结构体

### SkBmpMaskCodec

主解码器类，提供位掩码 BMP 图像的完整解码功能。

**关键成员变量：**
- `std::unique_ptr<SkMasks> fMasks`: 存储颜色掩码信息，包含 RGB 和 alpha 通道的位位置和掩码值
- `std::unique_ptr<SkMaskSwizzler> fMaskSwizzler`: 像素格式转换器，根据掩码规则转换像素数据

**核心方法：**
- `SkBmpMaskCodec()`: 构造函数，接收编码信息、输入流、每像素比特数、掩码对象和扫描线顺序
- `onGetPixels()`: 执行完整图像解码的主入口
- `onPrepareToDecode()`: 解码前的准备工作，初始化 swizzler 和颜色转换器
- `decodeRows()`: 逐行解码图像数据
- `getSampler()`: 返回 swizzler 用于采样操作

## 公共 API 函数

### 构造函数

```cpp
SkBmpMaskCodec(SkEncodedInfo&& info,
               std::unique_ptr<SkStream> stream,
               uint16_t bitsPerPixel,
               SkMasks* masks,
               SkCodec::SkScanlineOrder rowOrder)
```

创建位掩码 BMP 解码器实例。虽然标记为 public，但仅由 `SkBmpCodec::MakeFromStream` 调用。

**参数：**
- `info`: 包含图像尺寸、颜色类型等编码信息
- `stream`: 图像数据输入流
- `bitsPerPixel`: 每像素比特数（通常为 16 或 32）
- `masks`: 颜色掩码对象指针，定义各颜色通道的位布局
- `rowOrder`: 扫描线顺序（`kTopDown` 或 `kBottomUp`）

## 内部实现细节

### 解码流程

1. **初始化阶段** (`onPrepareToDecode`)：
   - 检查是否需要颜色空间转换，如需要则分配转换缓冲区
   - 根据目标格式和颜色转换需求调整 swizzler 的工作格式
   - 创建 `SkMaskSwizzler` 实例，传递掩码信息和不透明度信息
   - 处理预乘 alpha 和非预乘 alpha 的转换需求

2. **解码阶段** (`decodeRows`)：
   - 逐行从输入流读取原始像素数据到源缓冲区
   - 使用 `getDstRow()` 计算目标行索引（处理上下翻转）
   - 根据是否有颜色转换选择不同路径：
     - **有颜色转换**：先用 swizzler 转换到中间格式，再应用颜色空间转换
     - **无颜色转换**：直接用 swizzler 转换到目标格式
   - 处理不完整输入的情况，返回已解码的行数

3. **像素格式转换**：
   - `SkMaskSwizzler` 使用位掩码从原始数据中提取各颜色分量
   - 将提取的分量重新组合成标准 RGBA 或 BGRA 格式
   - 处理 alpha 通道的存在与否

### 错误处理

- **不支持子区域解码**：返回 `kUnimplemented`
- **不支持缩放**：检查目标尺寸必须与源尺寸一致，否则返回 `kInvalidScale`
- **输入流不完整**：返回 `kIncompleteInput` 并通过 `rowsDecoded` 参数报告已解码的行数
- **断言检查**：使用 `SkASSERT` 确保 swizzler 已正确初始化

### 颜色空间转换

当目标颜色空间与源颜色空间不同时：
- 使用 `kXformSrcColorType` 作为 swizzler 的输出格式
- 将预乘 alpha 转换为非预乘 alpha（颜色转换前）
- 调用 `applyColorXform()` 执行实际的颜色空间转换
- 使用 `xformBuffer()` 作为中间缓冲区

## 依赖关系

### 直接依赖

- **SkBmpBaseCodec**: 父类，提供 BMP 解码的通用功能
- **SkMasks**: 管理颜色掩码的数据结构
- **SkMaskSwizzler**: 执行位掩码像素转换的核心组件
- **SkCodec**: 编解码器框架的抽象基类
- **SkStream**: 输入流接口

### 间接依赖

- **SkColorSpaceXform**: 颜色空间转换（通过基类）
- **SkEncodedInfo**: 编码信息容器
- **SkImageInfo**: 图像元数据描述

### 被依赖关系

- **SkBmpCodec**: 工厂类，根据 BMP 格式选择创建此解码器

## 设计模式与设计决策

### 模板方法模式

`SkBmpMaskCodec` 实现了父类定义的虚函数接口，形成模板方法模式：
- `onGetPixels()`: 完整图像解码的入口
- `onPrepareToDecode()`: 解码前的初始化
- `decodeRows()`: 具体的行解码实现
- `getSampler()`: 返回采样器

### 策略模式

通过 `SkMaskSwizzler` 封装不同的像素转换策略，使解码器无需关心具体的位操作细节。

### 资源管理

- 使用 `std::unique_ptr` 管理 `SkMasks` 和 `SkMaskSwizzler` 的生命周期
- 避免手动内存管理，确保异常安全

### 设计决策

1. **不支持子区域解码**：位掩码格式的 BMP 通常不大，不需要复杂的局部解码支持
2. **不支持缩放**：解码阶段只进行像素格式转换，缩放由上层处理
3. **延迟创建 swizzler**：在 `onPrepareToDecode()` 中创建，避免不必要的初始化开销
4. **支持颜色空间转换**：适应现代颜色管理需求，但作为可选功能

## 性能考量

### 优化策略

1. **逐行处理**：避免将整个图像加载到内存，适合处理大图
2. **直接像素转换**：当无需颜色空间转换时，直接写入目标缓冲区
3. **缓冲区复用**：使用基类提供的源缓冲区和转换缓冲区，减少内存分配

### 性能瓶颈

- **位操作开销**：提取和组合颜色分量需要多次位运算
- **流读取**：逐行读取可能导致频繁的 I/O 操作
- **颜色空间转换**：增加额外的计算开销

### 内存使用

- 源缓冲区大小：`srcRowBytes` × 1 行
- 转换缓冲区（可选）：`width` × `kXformSrcColorType` 的大小
- 掩码对象：固定大小，存储 4 个通道的掩码信息

## 相关文件

### 核心文件

- `src/codec/SkBmpBaseCodec.h/cpp`: 父类实现
- `src/codec/SkBmpCodec.h/cpp`: BMP 解码器工厂
- `src/codec/SkMaskSwizzler.h/cpp`: 像素格式转换器
- `src/core/SkMasks.h/cpp`: 颜色掩码管理

### 相关解码器

- `src/codec/SkBmpRLECodec.h/cpp`: RLE 压缩 BMP 解码器
- `src/codec/SkBmpStandardCodec.h/cpp`: 标准调色板 BMP 解码器

### 框架文件

- `include/codec/SkCodec.h`: 编解码器基类
- `src/codec/SkCodecPriv.h`: 编解码器内部工具
- `include/private/SkEncodedInfo.h`: 编码信息定义

### 测试文件

- `tests/CodecTest.cpp`: 编解码器单元测试
- `resources/`: 包含测试用的 BMP 图像样本
