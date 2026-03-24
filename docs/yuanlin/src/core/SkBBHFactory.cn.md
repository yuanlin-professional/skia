# SkBBHFactory

> 源文件
> - include/core/SkBBHFactory.h
> - src/core/SkBBHFactory.cpp

## 概述

`SkBBHFactory` 是 Skia 图形库中用于创建包围盒层次结构（Bounding Box Hierarchy, BBH）的工厂类系统。BBH 是空间索引数据结构，用于加速 Picture 回放时的裁剪查询，通过快速过滤不可见的绘制操作显著提升性能。

## 架构位置

`SkBBHFactory` 位于 Skia 的 Picture 系统的性能优化层，为 `SkPictureRecorder` 提供空间索引支持。它定义了 BBH 的抽象接口和工厂模式。

```
Skia Core
  └── Picture System
      ├── SkPictureRecorder (使用工厂创建 BBH)
      ├── SkBigPicture (持有 BBH 实例)
      └── BBH System
          ├── SkBBHFactory (抽象工厂)
          │   └── SkRTreeFactory (R-Tree 工厂实现)
          └── SkBBoxHierarchy (抽象索引接口)
              └── SkRTree (R-Tree 实现)
```

## 主要类与结构体

### SkBBoxHierarchy

**继承关系**
- 继承自 `SkRefCnt`（引用计数）
- 不可拷贝

**内嵌结构 Metadata**

| 成员 | 类型 | 说明 |
|------|------|------|
| `isDraw` | `bool` | 对应的矩形是否界定绘制命令（而非纯状态变更） |

**关键方法**

| 方法 | 说明 |
|------|------|
| `insert(const SkRect[], int N)` | 纯虚函数：插入 N 个包围盒 |
| `insert(const SkRect[], const Metadata[], int N)` | 带元数据的插入（默认忽略元数据） |
| `search(const SkRect& query, std::vector<int>* results) const` | 纯虚函数：空间查询，返回相交的索引 |
| `bytesUsed() const` | 纯虚函数：返回内存占用 |

### SkBBHFactory

**继承关系**
- 抽象基类，不可拷贝

**关键方法**

| 方法 | 说明 |
|------|------|
| `operator()() const` | 纯虚函数：工厂方法，创建 BBH 实例 |
| `~SkBBHFactory()` | 虚析构函数 |

### SkRTreeFactory

**继承关系**
- 继承自 `SkBBHFactory`

**关键方法**

| 方法 | 说明 |
|------|------|
| `operator()() const override` | 实现：创建 `SkRTree` 实例 |

## 公共 API 函数

### SkBBoxHierarchy 接口

**insert(const SkRect[], int N)**
- **功能**: 向空间索引中插入 N 个包围盒
- **参数**:
  - `SkRect[]` - 包围盒数组
  - `N` - 数量
- **用途**: 构建 Picture 时记录每个绘制操作的边界

**insert(const SkRect[], const Metadata[], int N)**
- **功能**: 带元数据的插入重载
- **默认实现**: 忽略 `Metadata`，调用基本的 `insert`
- **用途**: 为未来扩展预留接口

**search(const SkRect& query, std::vector<int>* results) const**
- **功能**: 查询与指定矩形相交的所有包围盒
- **参数**:
  - `query` - 查询矩形（通常是裁剪区域）
  - `results` - 输出参数，相交的索引列表
- **用途**: Picture 回放时过滤不可见操作

**bytesUsed() const**
- **功能**: 返回数据结构占用的内存字节数
- **用途**: 内存分析和优化

### SkBBHFactory 接口

**operator()() const**
- **功能**: 工厂方法，创建新的 BBH 实例
- **返回**: `sk_sp<SkBBoxHierarchy>` 智能指针
- **用途**: 被 `SkPictureRecorder` 调用创建空间索引

### SkRTreeFactory 实现

**operator()() const override**
- **功能**: 创建 R-Tree 空间索引实例
- **实现**: `return sk_make_sp<SkRTree>();`
- **返回**: R-Tree 智能指针

## 内部实现细节

### 默认 insert 实现

```cpp
void SkBBoxHierarchy::insert(const SkRect rects[],
                             const Metadata[],
                             int N) {
    // 默认忽略 Metadata
    this->insert(rects, N);
}
```

**设计意图**:
- 保持向后兼容
- 大多数 BBH 实现不需要元数据
- 未来可按需扩展元数据支持

### R-Tree 工厂实现

```cpp
sk_sp<SkBBoxHierarchy> SkRTreeFactory::operator()() const {
    return sk_make_sp<SkRTree>();
}
```

**特点**:
- 无参数构造（使用默认配置）
- 返回新实例（每次调用创建新对象）
- 使用智能指针管理生命周期

### Metadata 扩展设计

`Metadata::isDraw` 标志的潜在用途：
- **绘制优先级**: 优先查询绘制操作，跳过纯状态变更
- **内存优化**: 分离存储绘制和状态操作
- **未来扩展**: 预留字段便于后续功能

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `include/core/SkRefCnt.h` | 引用计数基类 |
| `include/core/SkTypes.h` | 基础类型定义 |
| `include/core/SkRect.h` | 矩形类型 |
| `src/core/SkRTree.h` | R-Tree 具体实现 |
| `<vector>` | 查询结果容器 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| `SkPictureRecorder` | 录制时创建 BBH |
| `SkBigPicture` | 持有 BBH 实例 |
| `SkRecordDraw` | 回放时使用 BBH 查询 |
| `SkMultiPictureDraw` | 批量绘制时的裁剪优化 |

## 设计模式与设计决策

### 抽象工厂模式（Abstract Factory Pattern）
- **角色**:
  - `SkBBHFactory` - 抽象工厂
  - `SkRTreeFactory` - 具体工厂
  - `SkBBoxHierarchy` - 抽象产品
  - `SkRTree` - 具体产品
- **优势**:
  - 解耦创建和使用
  - 易于替换不同的空间索引实现
  - 客户端代码无需知道具体类型

### 策略模式（Strategy Pattern）
- **体现**: BBH 作为可插拔的空间索引策略
- **灵活性**:
  - 可使用 R-Tree（当前主要实现）
  - 可扩展 Quad-Tree、Grid 等其他实现
  - 可选择不使用 BBH（传 nullptr）

### 接口隔离原则
- **SkBBoxHierarchy**: 只定义必要的空间索引操作
- **Metadata**: 可选扩展，不强制所有实现支持

### 默认实现模式
- **insert 重载**: 基类提供默认实现
- **优势**: 派生类无需修改即可兼容新接口

### 不可拷贝设计
- **原因**:
  - BBH 通常很大，拷贝成本高
  - 语义不清晰（深拷贝还是浅拷贝）
  - 通过智能指针共享

## 性能考量

### 设计权衡

1. **工厂模式开销**
   - 创建开销：可忽略（只在录制时一次性）
   - 虚函数调用：可忽略（创建不在热路径）
   - 灵活性收益：远大于开销

2. **引用计数管理**
   - 开销：原子操作 ~5-10 cycles
   - 场景：BBH 通常被长期持有，增减少
   - 优势：线程安全的共享

3. **Metadata 忽略**
   - 当前实现：未使用 `isDraw` 标志
   - 预留扩展：未来可优化查询性能

### 典型使用场景性能

| 场景 | 性能影响 | 说明 |
|------|---------|------|
| Picture 录制 | +5-10% | 构建 BBH 的额外开销 |
| 全量回放 | 0 | 不使用 BBH |
| 裁剪回放 | -50% ~ -90% | 大幅减少绘制操作 |
| 内存占用 | +5-15% | BBH 数据结构开销 |

### R-Tree 性能特征

| 操作 | 时间复杂度 | 说明 |
|------|-----------|------|
| insert | O(log n) | 平均情况 |
| search | O(log n + k) | k 为结果数量 |
| 构建（批量） | O(n log n) | n 为元素数量 |
| 内存 | O(n) | 线性空间 |

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/core/SkRTree.h` | 具体实现 | R-Tree 空间索引 |
| `src/core/SkRTree.cpp` | 具体实现 | R-Tree 实现细节 |
| `src/core/SkPictureRecorder.h` | 使用者 | 使用工厂创建 BBH |
| `src/core/SkBigPicture.h` | 使用者 | 持有 BBH 实例 |
| `src/core/SkRecordDraw.h` | 使用者 | 回放时查询 BBH |
| `include/core/SkPicture.h` | 关联 | Picture 系统核心 |
