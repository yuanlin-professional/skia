# SkPictureRecord

> 源文件
> - src/core/SkPictureRecord.h
> - src/core/SkPictureRecord.cpp

## 概述

`SkPictureRecord` 是 Skia 图形库中负责记录绘图命令的核心类。它继承自 `SkCanvas`，通过虚函数机制拦截所有绘图操作，并将这些操作序列化为二进制格式存储在内部缓冲区中。这个类是 `SkPicture` 记录阶段的关键实现，负责将用户的绘图调用转换为可以重播的操作流。

`SkPictureRecord` 不直接执行绘图操作，而是将它们编码为紧凑的二进制格式，包括操作类型（DrawType）、参数数据以及对资源（如图像、路径、画笔等）的索引引用。它还维护了裁剪和变换状态的栈结构，支持延迟优化。

## 架构位置

`SkPictureRecord` 位于 Skia 的核心图形层，是 Picture 子系统的重要组成部分：

- 继承自 `SkCanvasVirtualEnforcer<SkCanvas>`，是 Canvas 层次结构的一部分
- 被 `SkPictureRecorder` 使用来执行实际的绘图命令记录
- 与 `SkPictureData` 协作，后者负责存储和序列化记录的数据
- 生成的数据由 `SkPicturePlayback` 用于回放操作

## 主要类与结构体

### SkPictureRecord

**继承关系**
- 继承自：`SkCanvasVirtualEnforcer<SkCanvas>`
- 友元类：`SkPictureData`

**关键成员变量**

| 成员变量 | 类型 | 描述 |
|---------|------|------|
| fWriter | SkWriter32 | 二进制写入器，存储操作码和参数 |
| fPaints | TArray<SkPaint> | 去重后的画笔数组 |
| fPaths | THashMap<SkPath, int, PathHash> | 路径到索引的映射表 |
| fImages | TArray<sk_sp<const SkImage>> | 图像引用数组 |
| fPictures | TArray<sk_sp<const SkPicture>> | 子图片数组 |
| fDrawables | TArray<sk_sp<SkDrawable>> | 可绘制对象数组 |
| fTextBlobs | TArray<sk_sp<const SkTextBlob>> | 文本块数组 |
| fVertices | TArray<sk_sp<const SkVertices>> | 顶点数组 |
| fSlugs | TArray<sk_sp<const sktext::gpu::Slug>> | GPU文本块数组 |
| fRestoreOffsetStack | SkTDArray<int32_t> | 恢复偏移栈，用于优化裁剪跳转 |
| fRecordFlags | uint32_t | 记录标志 |
| fInitialSaveCount | int | 初始保存计数 |

## 公共 API 函数

### 构造与初始化

```cpp
// 使用尺寸和标志构造
SkPictureRecord(const SkISize& dimensions, uint32_t recordFlags);
SkPictureRecord(const SkIRect& dimensions, uint32_t recordFlags);

// 开始和结束记录
void beginRecording();
void endRecording();
```

### 数据访问

```cpp
// 获取记录的操作数据
sk_sp<SkData> opData() const;

// 获取资源数组
const TArray<sk_sp<const SkPicture>>& getPictures() const;
const TArray<sk_sp<SkDrawable>>& getDrawables() const;
const TArray<sk_sp<const SkTextBlob>>& getTextBlobs() const;
const TArray<sk_sp<const sktext::gpu::Slug>>& getSlugs() const;
const TArray<sk_sp<const SkVertices>>& getVertices() const;
const TArray<sk_sp<const SkImage>>& getImages() const;

// 获取写入流
const SkWriter32& writeStream() const;

// 设置标志
void setFlags(uint32_t recordFlags);
```

## 内部实现细节

### 操作记录机制

`SkPictureRecord` 使用 `addDraw()` 方法记录每个绘图操作：

```cpp
size_t addDraw(DrawType drawType, size_t* size)
```

每个操作以紧凑格式存储：
- 前32位包含操作类型（8位）和大小（24位）
- 如果大小超过24位，则使用额外的32位存储完整大小
- 后续是操作特定的参数数据

### 资源去重

为减少内存占用，`SkPictureRecord` 对各类资源进行去重：

1. **画笔（Paint）**：存储在数组中，通过索引引用（1-based）
2. **路径（Path）**：使用哈希表映射，基于 GenerationID 去重
3. **图像/纹理**：使用 uniqueID 进行去重
4. **其他对象**：使用 `find_or_append()` 模板函数实现去重逻辑

### 裁剪优化

`SkPictureRecord` 实现了智能裁剪优化：

- 维护 `fRestoreOffsetStack` 栈，跟踪保存/恢复操作
- 裁剪操作记录 `restoreOffset` 占位符
- 当裁剪区域为空时，可以跳过到下一个恢复点
- 这避免了记录和回放不可见的绘图操作

### 变换记录

对于简单的变换操作，使用优化的记录格式：

```cpp
// 平移：操作码 + dx + dy
void recordTranslate(const SkMatrix& m);

// 缩放：操作码 + sx + sy
void recordScale(const SkMatrix& m);

// 通用矩阵：操作码 + 完整矩阵数据
void recordConcat(const SkMatrix& matrix);
```

### Canvas 虚函数重写

`SkPictureRecord` 重写所有关键的 Canvas 虚函数来拦截绘图操作：

- **绘制操作**：`onDrawRect()`, `onDrawPath()`, `onDrawImage2()` 等
- **状态管理**：`willSave()`, `willRestore()`, `getSaveLayerStrategy()` 等
- **变换操作**：`didConcat44()`, `didSetM44()`, `didScale()`, `didTranslate()` 等
- **裁剪操作**：`onClipRect()`, `onClipPath()`, `onClipRRect()` 等

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| SkCanvas | 基类，提供绘图接口 |
| SkWriter32 | 二进制序列化写入器 |
| SkPictureFlat | 操作码定义和序列化辅助 |
| SkTHash | 哈希表实现，用于路径去重 |
| SkPaint, SkPath, SkImage 等 | 绘图资源类型 |
| SkMatrix, SkM44 | 变换矩阵 |

### 被依赖的模块

| 模块 | 关系 |
|-----|------|
| SkPictureRecorder | 使用 SkPictureRecord 记录绘图命令 |
| SkPictureData | 从 SkPictureRecord 获取数据进行序列化 |
| SkBigPicture | 间接使用记录的数据 |

## 设计模式与设计决策

### 命令模式（Command Pattern）

`SkPictureRecord` 是命令模式的实现：
- 每个绘图操作被编码为命令（操作码 + 参数）
- 命令存储在缓冲区中，可以延迟执行
- 支持回放（通过 `SkPicturePlayback`）

### 享元模式（Flyweight Pattern）

通过资源去重实现享元模式：
- 相同的画笔、路径、图像只存储一次
- 使用索引引用共享资源
- 显著减少内存占用

### 延迟优化

采用延迟优化策略：
- 记录时尽量简单快速
- 复杂优化（如裁剪跳转优化）在完成记录后执行
- 平衡记录性能和回放性能

### 策略模式

`getSaveLayerStrategy()` 返回 `kNoLayer_SaveLayerStrategy`：
- 记录阶段不创建实际的图层
- 避免不必要的内存分配
- 回放时才创建真实图层

## 性能考量

### 内存优化

1. **资源去重**：避免重复存储相同资源
2. **紧凑编码**：使用24位大小字段，常见操作只需4-8字节
3. **索引引用**：使用小整数索引代替指针

### 记录性能

1. **快速路径**：简单操作（如平移、缩放）使用优化路径
2. **延迟计算**：边界计算等推迟到需要时
3. **避免分配**：大多数操作直接写入预分配缓冲区

### 回放优化

1. **裁剪跳转**：空裁剪区域可以跳过整个绘图区块
2. **状态缓存**：记录状态变化而非完整状态
3. **资源共享**：通过索引避免重复加载资源

## 相关文件

| 文件路径 | 描述 |
|---------|------|
| src/core/SkPictureData.h/cpp | 存储和序列化记录的数据 |
| src/core/SkPicturePlayback.h/cpp | 回放记录的操作 |
| src/core/SkPictureRecorder.h/cpp | 高层记录器接口 |
| src/core/SkPictureFlat.h/cpp | 操作码和序列化辅助定义 |
| src/core/SkWriter32.h | 二进制写入器 |
| src/core/SkBigPicture.h/cpp | Picture 的主要实现类 |
| include/core/SkCanvas.h | Canvas 基类 |
| include/core/SkPicture.h | Picture 公共接口 |
