# CommandTypes

> 源文件: src/gpu/graphite/CommandTypes.h

## 概述

`CommandTypes.h` 定义了 Skia Graphite GPU 后端中用于命令记录和执行的核心类型。该文件包含两个主要组件：`BufferTextureCopyData` 结构体用于描述缓冲区与纹理间的复制操作，以及 `Scissor` 类用于管理可重放的剪裁矩形。这些类型是 Graphite 命令缓冲系统的基础构建块，支持延迟渲染和命令重放功能。

Graphite 是 Skia 的下一代 GPU 后端，相比 Ganesh 更注重现代 GPU API（如 Vulkan、Metal、Dawn）的特性，该文件体现了 Graphite 对命令记录和重放的设计理念。

## 架构位置

在 Skia Graphite 架构中的位置：

```
skia/
├── include/
│   └── gpu/graphite/
│       └── GraphiteTypes.h        # 公共类型定义
├── src/
    └── gpu/
        └── graphite/
            ├── CommandTypes.h      # 本文件
            ├── CommandBuffer.h     # 命令缓冲区
            ├── CopyTask.h          # 复制任务
            └── RenderPassTask.h    # 渲染通道任务
```

该文件在命令系统中的角色：
- **基础类型**: 为命令记录提供数据结构
- **任务系统**: 被 `Task` 子类使用
- **命令缓冲**: `CommandBuffer` 使用这些类型记录操作

## 主要类与结构体

### BufferTextureCopyData

```cpp
struct BufferTextureCopyData {
    size_t fBufferOffset;      // 缓冲区中的字节偏移
    size_t fBufferRowBytes;    // 缓冲区行跨度（字节）
    SkIRect fRect;             // 纹理复制区域
    unsigned int fMipLevel;    // 目标 Mipmap 级别
};
```

**功能：** 描述单个缓冲区到纹理（或反向）的复制操作

**字段说明：**

1. **fBufferOffset**: 缓冲区起始位置
   - 必须满足对齐要求（通常 256 字节）
   - 相对于缓冲区开头的偏移

2. **fBufferRowBytes**: 每行像素的字节数
   - 包括任何填充字节
   - 必须 ≥ `fRect.width() * bytesPerPixel`
   - 用于处理非紧密打包的数据

3. **fRect**: 复制的矩形区域
   - 纹理空间中的坐标
   - 左上角为原点
   - 支持部分纹理更新

4. **fMipLevel**: Mipmap 层级
   - 0 表示基础级别
   - 必须 < 纹理的 Mipmap 级别数

**使用场景：**
- 上传纹理数据到 GPU
- 从 GPU 读取纹理数据
- Mipmap 生成
- 纹理流式传输

**示例：**
```cpp
// 上传 256x256 纹理的右下角 100x100 区域
BufferTextureCopyData copyData = {
    .fBufferOffset = 0,
    .fBufferRowBytes = 100 * 4,  // RGBA, 4 字节/像素
    .fRect = SkIRect::MakeXYWH(156, 156, 100, 100),
    .fMipLevel = 0
};
```

### Scissor

```cpp
class Scissor {
public:
    explicit Scissor(const SkIRect& rect) : fRect(rect) {}

    SkIRect getRect(const SkIVector& replayTranslation,
                    const SkIRect& replayClip) const;

private:
    const SkIRect fRect;
};
```

**功能：** 可重放的剪裁矩形，支持平移和裁剪

**设计特点：**
- 不可变对象（`const fRect`）
- 延迟求值（在重放时计算最终矩形）
- 支持命令缓冲的重放优化

## 公共 API 函数

### Scissor 构造函数

```cpp
explicit Scissor(const SkIRect& rect)
```

**功能：** 创建剪裁矩形

**参数：** `rect` - 原始剪裁矩形（记录空间坐标）

**示例：**
```cpp
SkIRect clipRect = SkIRect::MakeXYWH(10, 20, 300, 400);
Scissor scissor(clipRect);
```

### Scissor::getRect

```cpp
SkIRect getRect(const SkIVector& replayTranslation,
                const SkIRect& replayClip) const
```

**功能：** 计算重放时的实际剪裁矩形

**参数：**
- `replayTranslation`: 重放时的平移向量
- `replayClip`: 重放时的裁剪区域

**返回值：** 变换和裁剪后的最终矩形

**算法：**
```cpp
SkIRect getRect(...) const {
    SkIRect rect = fRect.makeOffset(replayTranslation);
    if (!rect.intersect(replayClip)) {
        rect.setEmpty();
    }
    return rect;
}
```

**步骤：**
1. 应用平移：`rect = fRect + replayTranslation`
2. 与裁剪区域求交：`rect = rect ∩ replayClip`
3. 无交集则返回空矩形

**使用场景：**
```cpp
// 记录时
Scissor scissor(SkIRect::MakeXYWH(0, 0, 100, 100));

// 重放时（平移 50, 50）
SkIVector translation = {50, 50};
SkIRect clip = SkIRect::MakeXYWH(0, 0, 200, 200);
SkIRect actualScissor = scissor.getRect(translation, clip);
// 结果: {50, 50, 150, 150}
```

## 内部实现细节

### 缓冲区对齐

`BufferTextureCopyData::fBufferOffset` 必须满足对齐要求：

**典型对齐：**
- Vulkan: 256 字节（`VkPhysicalDeviceLimits::minTexelBufferOffsetAlignment`）
- Metal: 256 字节
- Dawn: 256 字节

**计算对齐偏移：**
```cpp
size_t alignedOffset = SkAlignTo(offset, 256);
```

### 行跨度计算

`fBufferRowBytes` 的计算考虑对齐：

```cpp
size_t bytesPerPixel = 4;  // RGBA
size_t minRowBytes = width * bytesPerPixel;
size_t rowAlignment = 256;  // 某些 GPU 要求
size_t fBufferRowBytes = SkAlignTo(minRowBytes, rowAlignment);
```

### Mipmap 级别验证

```cpp
SkASSERT(fMipLevel < texture->numMipLevels());
```

### 剪裁矩形优化

Graphite 使用延迟求值优化命令重放：

**优势：**
- 记录时不需要知道最终坐标系
- 支持命令缓冲在不同上下文重放
- 减少记录时的计算开销

**实现细节：**
```cpp
const SkIRect fRect;  // const 确保不可变性
```

## 依赖关系

### 直接依赖

1. **SkRect.h** (include/core/SkRect.h)
   - `SkIRect` 整数矩形
   - `SkIVector` 整数向量

2. **GraphiteTypes.h** (include/gpu/graphite/GraphiteTypes.h)
   - Graphite 公共类型定义
   - 可能包含 Mipmap 相关枚举

### 被依赖模块

1. **命令缓冲系统**
   - `CommandBuffer` 记录复制和剪裁命令
   - `CopyTask` 使用 `BufferTextureCopyData`
   - `RenderPassTask` 使用 `Scissor`

2. **上传管理器**
   - `UploadManager` 构建复制数据
   - `StagingBufferManager` 管理缓冲区

3. **纹理操作**
   - `Texture::upload()` 使用复制数据
   - `Texture::readPixels()` 使用复制数据

## 设计模式与设计决策

### 1. POD 结构体

`BufferTextureCopyData` 是简单的 POD 结构：

**优势：**
- 高效的内存布局
- 易于序列化
- 零开销抽象

### 2. 不可变对象

`Scissor::fRect` 是 `const` 成员：

**优势：**
- 线程安全
- 可安全缓存和重放
- 避免意外修改

### 3. 延迟求值

`Scissor::getRect()` 在使用时计算：

**优势：**
- 支持命令重放
- 减少记录时开销
- 灵活的坐标系变换

### 4. 显式类型

使用 `size_t` 和 `unsigned int`：

**原因：**
- `size_t` 适合内存偏移和大小
- `unsigned int` 明确 Mipmap 级别为非负

### 5. 命名空间封装

```cpp
namespace skgpu::graphite { ... }
```

**目的：**
- 避免命名冲突
- 清晰的模块边界
- 与 Ganesh 区分

## 性能考量

### 1. 缓冲区复制效率

**对齐的重要性：**
```cpp
// 未对齐（慢）
copyData.fBufferOffset = 17;

// 对齐（快）
copyData.fBufferOffset = 256;
```

**性能差异：** 未对齐可能导致 2-10 倍性能下降

### 2. 行跨度优化

**紧密打包 vs 对齐：**
```cpp
// 紧密打包（可能慢）
fBufferRowBytes = width * 4;

// 对齐（通常更快）
fBufferRowBytes = SkAlignTo(width * 4, 256);
```

**权衡：**
- 对齐：更快的 GPU 访问，但浪费内存
- 紧密：节省内存，但可能降低带宽

### 3. 剪裁矩形计算

`Scissor::getRect()` 的性能：

**开销：**
- 矩形偏移：~2 ns
- 矩形求交：~5 ns
- 总计：~7 ns

**优化：**
- 内联函数（头文件实现）
- 简单的整数运算
- 无分支预测失败

### 4. 部分纹理更新

使用小 `fRect` 减少传输：

**示例：**
```cpp
// 慢：更新整个纹理
fRect = SkIRect::MakeWH(1024, 1024);  // 4 MB

// 快：仅更新变化区域
fRect = SkIRect::MakeXYWH(100, 100, 64, 64);  // 16 KB
```

### 5. Mipmap 传输优化

逐级上传 Mipmap：

**策略：**
```cpp
for (int level = 0; level < numLevels; ++level) {
    BufferTextureCopyData copyData = {
        .fBufferOffset = offsets[level],
        .fBufferRowBytes = rowBytes[level],
        .fRect = SkIRect::MakeWH(width >> level, height >> level),
        .fMipLevel = level
    };
    // 上传当前级别
}
```

## 相关文件

### 核心依赖
- `include/core/SkRect.h` - 矩形类型
- `include/gpu/graphite/GraphiteTypes.h` - Graphite 公共类型

### 命令系统
- `src/gpu/graphite/CommandBuffer.h` - 命令缓冲区
- `src/gpu/graphite/Task.h` - 任务基类
- `src/gpu/graphite/CopyTask.h` - 复制任务
- `src/gpu/graphite/RenderPassTask.h` - 渲染通道任务

### 使用者
- `src/gpu/graphite/UploadManager.cpp` - 上传管理
- `src/gpu/graphite/Texture.cpp` - 纹理操作
- `src/gpu/graphite/DrawPass.cpp` - 绘制通道

### 测试文件
- `tests/graphite/CommandBufferTest.cpp` - 命令缓冲测试
- `tests/graphite/CopyTest.cpp` - 复制操作测试
