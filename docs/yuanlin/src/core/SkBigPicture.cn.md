# SkBigPicture

> 源文件
> - src/core/SkBigPicture.h
> - src/core/SkBigPicture.cpp

## 概述

`SkBigPicture` 是 Skia 图形库中 `SkPicture` 的主要实现类，用于支持任意数量绘制命令的录制和回放。它使用 `SkRecord` 存储绘制指令，配合可选的空间索引结构（BBH）优化裁剪查询，是 Skia 绘图命令序列化和重用的核心机制。

## 架构位置

`SkBigPicture` 位于 Skia 的绘图记录和回放系统的核心，是 `SkPicture` 抽象类的最终实现（final class）。它与 `SkPictureRecorder` 和 `SkRecordDraw` 协作，构成完整的录制-回放流水线。

```
Skia Core
  └── Picture System
      ├── SkPictureRecorder (录制器)
      ├── SkPicture (抽象接口)
      │   └── SkBigPicture (主要实现)
      ├── SkRecord (指令存储)
      └── SkRecordDraw (回放引擎)
```

## 主要类与结构体

### SkBigPicture

**继承关系**
- 继承自 `SkPicture`（final 类，不可再继承）

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fCullRect` | `const SkRect` | 裁剪矩形，定义 Picture 的边界 |
| `fApproxBytesUsedBySubPictures` | `const size_t` | 子 Picture 占用的近似字节数 |
| `fRecord` | `sk_sp<const SkRecord>` | 存储绘制指令的记录对象 |
| `fDrawablePicts` | `std::unique_ptr<const SnapshotArray>` | 引用的 Drawable/Picture 数组 |
| `fBBH` | `sk_sp<const SkBBoxHierarchy>` | 可选的包围盒层次结构（空间索引） |

### SnapshotArray

**继承关系**
- 继承自 `SkNoncopyable`（不可复制）

**功能**
- 管理 Picture 中引用的子 Picture/Drawable 的生命周期
- 数组元素是引用计数的 `SkPicture*` 指针
- 析构时自动释放所有引用

**关键方法**

| 方法 | 说明 |
|------|------|
| `SnapshotArray(const SkPicture* pics[], int count)` | 构造函数，接管指针数组 |
| `~SnapshotArray()` | 析构函数，对所有 Picture 调用 `unref()` |
| `begin() const` | 返回数组起始指针 |
| `count() const` | 返回数组元素数量 |

## 公共 API 函数

### 构造函数

**SkBigPicture(const SkRect& cull, sk_sp<SkRecord>, std::unique_ptr<SnapshotArray>, sk_sp<SkBBoxHierarchy>, size_t approxBytesUsedBySubPictures)**
- **参数**:
  - `cull`: 裁剪矩形
  - `record`: 绘制指令记录
  - `drawablePicts`: 子 Picture/Drawable 数组
  - `bbh`: 可选的空间索引结构
  - `approxBytesUsedBySubPictures`: 子 Picture 内存估算
- **所有权**: 通过智能指针转移所有权

### SkPicture 接口重写

**playback(SkCanvas* canvas, AbortCallback* callback) const**
- **功能**: 将录制的绘制命令回放到画布上
- **优化**: 自动决定是否使用 BBH 加速
  - 如果查询包含整个 Picture，跳过 BBH
  - 否则使用 BBH 进行空间查询优化
- **实现**: 调用 `SkRecordDraw()` 执行实际回放

**cullRect() const**
- **功能**: 返回 Picture 的裁剪矩形
- **返回**: `fCullRect`

**approximateOpCount(bool nested) const**
- **功能**: 估算操作数量
- **参数**: `nested` - 是否递归计算子 Picture
- **非嵌套**: 返回 `fRecord->count()`
- **嵌套**: 遍历所有操作，递归累加 `DrawPicture` 的操作数

**approximateBytesUsed() const**
- **功能**: 估算总内存占用
- **计算**: `sizeof(*this) + fRecord->bytesUsed() + fApproxBytesUsedBySubPictures + fBBH->bytesUsed()`

**asSkBigPicture() const**
- **功能**: 类型转换辅助方法
- **返回**: `this` 指针

### 内部访问方法（供 GrRecordReplaceDraw 使用）

**bbh() const**
- **返回**: 包围盒层次结构指针

**record() const**
- **返回**: 绘制指令记录指针

## 内部实现细节

### NestedApproxOpCounter

嵌套操作计数的访问者模式实现：

```cpp
struct NestedApproxOpCounter {
    int fCount = 0;

    template <typename T> void operator()(const T& op) {
        fCount += 1;  // 普通操作计数 1
    }

    void operator()(const SkRecords::DrawPicture& op) {
        fCount += op.picture->approximateOpCount(true);  // 递归计数
    }
};
```

### BBH 使用决策

```cpp
const bool useBBH = !canvas->getLocalClipBounds().contains(this->cullRect());
```

**逻辑**:
- 如果画布裁剪区域完全包含 Picture，不使用 BBH
- 否则使用 BBH 过滤不可见的绘制操作

**原因**:
- BBH 查询有开销（树遍历）
- 全量绘制时直接遍历更快
- 部分绘制时 BBH 能跳过大量操作

### 内存管理策略

1. **智能指针**: `fRecord` 和 `fBBH` 使用 `sk_sp` 自动管理
2. **unique_ptr**: `fDrawablePicts` 独占所有权
3. **const 语义**: 所有成员都是 const，确保不可变性
4. **延迟计算**: `approximateBytesUsed()` 每次调用时计算

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `include/core/SkPicture.h` | 基类定义 |
| `include/core/SkBBHFactory.h` | 空间索引接口 |
| `include/core/SkCanvas.h` | 回放目标画布 |
| `src/core/SkRecord.h` | 绘制指令存储 |
| `src/core/SkRecordDraw.h` | 回放引擎 |
| `src/core/SkRecords.h` | 具体的绘制指令类型 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| `SkPictureRecorder` | 创建 SkBigPicture 实例 |
| `SkCanvas::drawPicture` | 回放 Picture |
| `GrRecordReplaceDraw` | GPU 路径的替换绘制 |
| `SkMultiPictureDraw` | 批量绘制多个 Picture |
| 序列化系统 | 保存/加载 Picture |

## 设计模式与设计决策

### 不可变对象模式（Immutable Object）
- **特性**: 所有成员变量都是 const
- **优势**:
  - 线程安全（可在多线程中共享）
  - 缓存友好（状态不变）
  - 语义清晰（创建后不可修改）

### 访问者模式（Visitor Pattern）
- **应用**: `NestedApproxOpCounter` 遍历 Record
- **优势**:
  - 对不同操作类型执行不同逻辑
  - 避免 if-else 或 switch 级联

### 策略模式（Strategy Pattern）
- **体现**: BBH 作为可选的空间索引策略
- **灵活性**: 可使用 RTree、Grid 或不使用

### Final 类设计
- **决策**: 将 SkBigPicture 声明为 final
- **原因**:
  - 不再需要继承（过去有 "mini" 版本，已废弃）
  - 优化虚函数调用（编译器可去虚化）

### 延迟决策优化
- **体现**: `playback()` 运行时决定是否使用 BBH
- **优势**: 根据实际绘制场景自适应

## 性能考量

### 优化点

1. **智能 BBH 使用**
   - 全量绘制：跳过 BBH，减少树遍历开销
   - 部分绘制：使用 BBH，跳过不可见操作
   - 典型加速：2-10x（取决于可见比例）

2. **零拷贝回放**
   - `fRecord` 和 `fBBH` 通过智能指针共享
   - 多次回放无额外内存分配
   - 支持多个画布并发回放（只读）

3. **子 Picture 管理**
   - `SnapshotArray` 避免重复引用计数操作
   - 批量析构子 Picture

4. **内存局部性**
   - `SkRecord` 使用内存池连续存储指令
   - 顺序回放缓存友好

### 性能特征

| 操作 | 时间复杂度 | 说明 |
|------|-----------|------|
| 构造 | O(1) | 只是传递指针 |
| playback（全量） | O(n) | n 为指令数量 |
| playback（裁剪） | O(log n + k) | BBH 查询 + k 个可见操作 |
| approximateOpCount | O(n) 或 O(total) | 取决于是否嵌套计算 |
| approximateBytesUsed | O(1) | 已预计算子 Picture 大小 |

### 内存占用

| 组件 | 占用 | 说明 |
|------|------|------|
| SkBigPicture 对象 | ~64 字节 | 固定开销 |
| SkRecord | ~24 + 数据 | 指令数据 |
| BBH (RTree) | ~16 * 节点数 | 可选 |
| SnapshotArray | ~16 + 8 * 子 Picture 数 | 可选 |

### 典型使用场景性能

| 场景 | 性能 | 说明 |
|------|------|------|
| 静态 UI 缓存 | 优秀 | 录制一次，多次回放 |
| 动画部分更新 | 良好 | BBH 加速裁剪 |
| 大场景滚动 | 优秀 | BBH 显著减少绘制操作 |
| 小 Picture 全量绘制 | 良好 | 跳过 BBH 开销 |

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/core/SkPicture.h` | 基类 | Picture 抽象接口 |
| `src/core/SkPictureRecorder.h` | 创建者 | 录制并创建 SkBigPicture |
| `src/core/SkRecord.h` | 成员 | 绘制指令存储 |
| `src/core/SkRecordDraw.h` | 协作者 | 回放引擎 |
| `include/core/SkBBHFactory.h` | 依赖 | BBH 工厂接口 |
| `src/core/SkRTree.h` | 依赖 | RTree 空间索引实现 |
| `src/gpu/ganesh/GrRecordReplaceDraw.h` | 使用者 | GPU 路径替换绘制 |
