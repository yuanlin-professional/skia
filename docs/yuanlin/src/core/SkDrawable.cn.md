# SkDrawable

> 源文件
> - include/core/SkDrawable.h
> - src/core/SkDrawable.cpp

## 概述

`SkDrawable` 是 Skia 中用于封装可重用绘制内容的抽象基类。它允许将复杂的绘图操作打包为对象，可以在不同的 `SkCanvas` 上重复绘制，同时保持状态一致性和支持缓存优化。该类提供了生成ID机制用于失效检测，支持GPU后端的3D API直接绘制，并且可以序列化为 `SkPicture`。它是Skia渲染系统中实现延迟绘制和跨平台抽象的关键组件。

## 架构位置

`SkDrawable` 位于 Skia 公共API层（`include/core`），是 `SkFlattenable` 系列的一部分，与 `SkPicture` 和 `SkImageFilter` 处于同一抽象层次。它在绘制管线中位于应用逻辑和画布之间，作为可重用绘制命令的容器。GPU后端（如Vulkan）可以通过 `GpuDrawHandler` 机制绕过Skia抽象直接使用底层3D API。

## 主要类与结构体

### SkDrawable (抽象基类)

封装可绘制内容的基类，强制子类实现绘制逻辑和边界计算。

| 类型 | 说明 |
|------|------|
| 继承关系 | 继承自 `SkFlattenable`（支持序列化） |
| 主要用途 | 作为基类定义可绘制对象的接口 |

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fGenerationID` | `int32_t` | 生成ID，用于检测内容变化，延迟初始化为0 |

### GpuDrawHandler (内部类)

用于在GPU后端执行时提供对底层3D API的访问。

| 类型 | 说明 |
|------|------|
| 继承关系 | 无继承，独立接口类 |
| 生命周期 | 每次绘制时创建新实例，命令提交到GPU后析构 |

**关键方法：**

```cpp
virtual void draw(const GrBackendDrawableInfo&)
```
在GPU刷新时调用，允许添加3D API命令到命令流。

## 公共 API 函数

### 绘制方法

```cpp
void draw(SkCanvas* canvas, const SkMatrix* matrix = nullptr)
void draw(SkCanvas* canvas, SkScalar x, SkScalar y)
```
将内容绘制到指定画布。第一个重载接受可选变换矩阵，第二个重载提供简化的平移接口。绘制前后画布状态（保存层级、矩阵、裁剪）保持不变。

### GPU 后端支持

```cpp
std::unique_ptr<GpuDrawHandler> snapGpuDrawHandler(GrBackendApi backendApi,
                                                   const SkMatrix& matrix,
                                                   const SkIRect& clipBounds,
                                                   const SkImageInfo& bufferInfo)
```
捕获当前状态的GPU绘制处理器。接收后端类型（Vulkan等）、变换矩阵、裁剪边界和目标缓冲信息。当前仅Vulkan后端支持。

### 状态查询

```cpp
uint32_t getGenerationID()
```
返回唯一生成ID。首次调用时懒初始化为全局递增的ID。客户端可以缓存基于此ID的计算结果。

```cpp
SkRect getBounds()
```
返回保守的绘制边界。对于可变内容（如动画），必须返回所有可能状态下的外包围盒。

```cpp
size_t approximateBytesUsed()
```
返回对象占用的大致内存量（字节）。基类默认返回0。

### 状态修改

```cpp
void notifyDrawingChanged()
```
使当前生成ID失效，下次调用 `getGenerationID()` 将生成新ID。子类在内部状态变化导致绘制结果不同时必须调用此方法。

### 序列化

```cpp
sk_sp<SkPicture> makePictureSnapshot()
```
生成包含当前绘制内容的 `SkPicture`。默认实现使用 `SkPictureRecorder` 录制 `onDraw()` 的调用。

```cpp
static sk_sp<SkDrawable> Deserialize(const void* data, size_t size,
                                     const SkDeserialProcs* procs = nullptr)
```
从序列化数据反序列化 `SkDrawable`（通过 `SkFlattenable` 机制）。

## 内部实现细节

### 生成ID机制

**原子递增：** 使用 `std::atomic<int32_t>` 确保多线程下ID唯一：
```cpp
static std::atomic<int32_t> nextID{1};
int32_t id;
do {
    id = nextID.fetch_add(1, std::memory_order_relaxed);
} while (id == 0);  // 跳过0（作为未初始化标记）
```

**懒初始化：** `fGenerationID` 初始为0，首次调用 `getGenerationID()` 时才分配。这避免了从不调用此方法的对象浪费ID空间。

### 画布状态保护

`draw()` 方法使用 `SkAutoCanvasRestore` 自动恢复画布状态：
```cpp
SkAutoCanvasRestore acr(canvas, true);
if (matrix) {
    canvas->concat(*matrix);
}
this->onDraw(canvas);
```
即使 `onDraw()` 抛出异常，析构函数也会恢复画布状态。

### Picture 快照生成

默认实现：
1. 创建 `SkPictureRecorder`
2. 获取边界并开始录制
3. 调用 `draw()` 将内容录制到Picture中
4. 完成录制并返回 `sk_sp<SkPicture>`

子类可以覆盖 `onMakePictureSnapshot()` 提供更高效的实现（例如直接返回已有的Picture）。

### GPU 绘制处理器生命周期

1. 调用 `snapGpuDrawHandler()` 时，子类创建包含当前状态快照的 `GpuDrawHandler`
2. GPU后端将handler排队
3. 刷新时调用 `handler->draw(info)`，此时可以安全访问GPU上下文
4. 命令提交后，handler被析构，触发子类的资源清理逻辑（如插入GPU fence）

### 调试支持

在调试模式下，`draw()` 可以选择性绘制边界框（代码中被注释为 `if ((false))`）：
```cpp
if ((false)) {
    draw_bbox(canvas, this->getBounds());
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkFlattenable` | 序列化框架基类 |
| `SkCanvas` | 绘制目标接口 |
| `SkPictureRecorder` | Picture生成 |
| `SkMatrix` | 变换矩阵 |
| `GrBackendDrawableInfo` | GPU后端上下文信息 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| `SkCanvas::drawDrawable()` | 画布直接支持绘制SkDrawable |
| `SkPicture` | 可以包含drawable对象 |
| Ganesh / Graphite GPU后端 | 通过GpuDrawHandler执行GPU绘制 |

## 设计模式与设计决策

**模板方法模式：** 公共方法 `draw()` 定义算法骨架（保存/恢复状态），调用虚函数 `onDraw()` 让子类实现具体绘制逻辑。

**非可侵入式扩展（Non-Invasive Extension）：** GPU后端支持通过可选的 `snapGpuDrawHandler()` 实现，不强制所有子类支持GPU。默认返回 `nullptr` 表示回退到CPU路径。

**生成式版本控制：** 使用生成ID而非传统的版本号，避免了溢出问题（32位ID在实践中不会耗尽）。

**延迟初始化：** 生成ID在首次需要时才分配，减少不使用缓存功能的drawable的开销。

**资源管理设计：** `GpuDrawHandler` 的析构函数作为资源释放信号，是一种RAII（Resource Acquisition Is Initialization）的应用。子类可以在析构时插入fence等待GPU完成。

**Flattenable集成：** 覆盖 `getFactory()` 和 `getTypeName()` 返回 `nullptr`，表明基类不直接支持序列化（子类必须实现）。这避免了意外序列化抽象对象。

## 性能考量

**状态保存开销：** 每次调用 `draw()` 都会保存/恢复画布状态，有一定开销。但这确保了安全性，对于复杂drawable（内部有多层变换）是必要的。

**ID比较vs内容比较：** 生成ID机制使得相等性检查变为O(1)的整数比较，避免了昂贵的深度比较。缓存系统可以高效判断内容是否变化。

**懒初始化优化：** 不调用 `getGenerationID()` 的drawable（如一次性绘制的临时对象）不会分配ID，节省内存和原子操作开销。

**边界计算缓存：** `getBounds()` 调用虚函数，子类应当缓存计算结果以避免重复计算（Skia本身不提供自动缓存）。

**GPU直接访问：** `GpuDrawHandler` 机制允许完全绕过Skia抽象，直接使用Vulkan/Metal等API，对于需要高性能GPU特性（如compute shader）的特殊drawable至关重要。

**Picture快照：** 默认的picture快照实现需要重新执行绘制逻辑，对于复杂drawable开销较大。建议子类覆盖 `onMakePictureSnapshot()` 提供优化版本。

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `include/core/SkCanvas.h` | 提供 `drawDrawable()` 方法 |
| `include/core/SkPicture.h` | Picture可以包含drawable |
| `include/core/SkFlattenable.h` | 序列化基类 |
| `include/core/SkPictureRecorder.h` | Picture生成工具 |
| `include/gpu/GrBackendDrawableInfo.h` | GPU后端信息 |
| `src/gpu/ganesh/GrRenderTargetContext.cpp` | Ganesh中执行GpuDrawHandler |
