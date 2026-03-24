# SkSGNode

> 源文件: modules/sksg/include/SkSGNode.h

## 概述

SkSGNode 是 Skia 场景图（Scene Graph）系统的核心基类，定义了所有场景图节点的通用接口和失效机制。该模块实现了场景图的有向无环图（DAG）结构管理，支持节点间的父子关系追踪、增量重验证和脏区域传播。

Node 类提供了场景图的基础设施，包括边界框缓存、失效标记、观察者模式的依赖管理等。它不直接处理渲染或几何逻辑，而是为各种具体节点类型（渲染节点、几何节点、效果节点等）提供统一的框架。

该模块还定义了两个重要的宏 SG_ATTRIBUTE 和 SG_MAPPED_ATTRIBUTE，用于简化子类属性的声明，自动集成失效通知机制。

## 架构位置

SkSGNode 在 Skia 场景图架构中占据基础地位：

- **继承层次**: Node → SkRefCnt，是所有场景图节点的根基类
- **派生类型**:
  - RenderNode: 可渲染节点（如 Group、Image、Draw）
  - GeometryNode: 几何节点（如 Rect、Path、Merge）
  - EffectNode: 效果节点（如 OpacityEffect、MaskEffect）
  - PaintNode: 绘制属性节点（如 Color、ShaderPaint）
  - Transform: 变换节点（如 Matrix、Concat）
- **模块位置**: modules/sksg，场景图核心模块
- **设计模式**: 观察者模式（节点间失效通知）、模板方法模式（onRevalidate 虚函数）

## 主要类与结构体

### Node 类

```cpp
class Node : public SkRefCnt {
public:
    // 重验证接口
    const SkRect& revalidate(InvalidationController*, const SkMatrix&);

    // 失效接口
    void invalidate(bool damage = true);

protected:
    // 失效特性标志
    enum InvalTraits {
        kBubbleDamage_Trait   = 1 << 0,  // 损伤向祖先冒泡
        kOverrideDamage_Trait = 1 << 1,  // 覆盖后代损伤
    };

    explicit Node(uint32_t invalTraits);
    ~Node() override;

    // 获取缓存的边界框
    const SkRect& bounds() const;
    bool hasInval() const;

    // 纯虚函数：子类实现重验证逻辑
    virtual SkRect onRevalidate(InvalidationController*, const SkMatrix& ctm) = 0;

    // 观察者管理
    void observeInval(const sk_sp<Node>&);
    void unobserveInval(const sk_sp<Node>&);

private:
    enum Flags {
        kInvalidated_Flag   = 1 << 0,  // 节点或后代需要重验证
        kDamage_Flag        = 1 << 1,  // 节点在重验证期间贡献损伤
        kObserverArray_Flag = 1 << 2,  // 节点有多个失效观察者
        kInTraversal_Flag   = 1 << 3,  // 节点处于遍历中（循环检测）
    };

    union {
        Node*               fInvalObserver;        // 单个观察者
        std::vector<Node*>* fInvalObserverArray;   // 多个观察者
    };
    SkRect     fBounds;         // 缓存的边界框
    uint32_t   fInvalTraits :  2;
    uint32_t   fFlags       :  4;
    uint32_t   fNodeFlags   :  8;  // 子类可访问的标志位
};
```

### 属性宏

#### SG_ATTRIBUTE 宏
```cpp
#define SG_ATTRIBUTE(attr_name, attr_type, attr_container)
```
自动生成：
- `get##attr_name()`: 获取属性
- `set##attr_name(const attr_type&)`: 设置属性（const 引用版本）
- `set##attr_name(attr_type&&)`: 设置属性（移动语义版本）

设置时会检查值是否改变，若改变则调用 `invalidate()`。

#### SG_MAPPED_ATTRIBUTE 宏
```cpp
#define SG_MAPPED_ATTRIBUTE(attr_name, attr_type, attr_container)
```
用于属性委托场景，通过容器对象的 getter/setter 访问属性。

## 公共 API 函数

### revalidate()
```cpp
const SkRect& revalidate(InvalidationController*, const SkMatrix&);
```
遍历 DAG 并重验证所有失效的依赖节点。返回该 DAG 片段的边界框。

**参数**:
- `InvalidationController*`: 失效控制器，收集损伤区域
- `const SkMatrix&`: 当前变换矩阵（累积的父变换）

**返回**: 节点在父坐标系中的边界框

**流程**:
1. 检查节点是否失效（kInvalidated_Flag）
2. 若失效，调用 `onRevalidate()` 让子类重新计算
3. 清除失效标志，缓存新边界框
4. 将损伤区域报告给 InvalidationController
5. 返回缓存的边界框

### invalidate()
```cpp
void invalidate(bool damage = true);
```
标记节点为失效状态，可选地标记为损伤。

**参数**:
- `damage`: 是否贡献损伤区域（默认 true）

**行为**:
- 设置 kInvalidated_Flag
- 如果 damage 为 true，设置 kDamage_Flag
- 通知所有观察者（父节点）传播失效
- 触发级联失效直到场景图根节点

## 内部实现细节

### 失效特性（InvalTraits）

#### kBubbleDamage_Trait
具有此特性的节点不直接生成损伤，而是将损伤冒泡到祖先。例如：
- Transform 节点：自身不产生视觉内容，损伤来自子节点
- Effect 节点：包装其他节点，损伤通常由被包装节点产生

#### kOverrideDamage_Trait
具有此特性的节点会覆盖后代的损伤，总是使用自己的边界作为损伤区域。例如：
- 缓存层节点：整个缓存区域都需要重绘
- 某些复合效果：无法精确追踪内部损伤

### 观察者模式优化

Node 使用联合体（union）优化内存：
```cpp
union {
    Node*               fInvalObserver;
    std::vector<Node*>* fInvalObserverArray;
};
```
- 如果只有一个观察者，直接存储指针（常见情况）
- 如果有多个观察者，分配 vector（罕见但支持）
- 通过 kObserverArray_Flag 区分两种状态

这种设计在典型场景（单父节点）下节省内存，同时支持 DAG 的共享节点。

### 循环检测

kInTraversal_Flag 用于检测 DAG 中的循环引用：
- 进入节点时设置标志
- 遍历子节点时检查标志
- 若发现已设置，表示存在循环
- 退出节点时清除标志

### 位域优化

使用位域紧凑存储标志位：
```cpp
uint32_t fInvalTraits :  2;  // 失效特性（2位够用）
uint32_t fFlags       :  4;  // 内部标志（4位）
uint32_t fNodeFlags   :  8;  // 子类标志（8位，RenderNode 使用）
// 剩余 18 位未使用
```
总共 32 位（一个 uint32_t），内存高效。

## 依赖关系

### 核心依赖
- **include/core/SkRect.h**: 边界框类型
- **include/core/SkRefCnt.h**: 引用计数基类
- **include/private/base/SkAssert.h**: 断言宏

### 前向声明
- **SkMatrix**: 变换矩阵（在 onRevalidate 中使用）
- **InvalidationController**: 失效控制器（定义在同模块）

### 标准库
- **<cstdint>**: 固定宽度整数类型
- **<vector>**: 动态数组（多观察者场景）

### 被依赖关系
几乎所有场景图节点都依赖此头文件：
- RenderNode, GeometryNode, EffectNode（直接派生）
- 所有具体节点类型（间接派生）
- InvalidationController（协作关系）

## 设计模式与设计决策

### 1. 观察者模式
节点间通过 observeInval/unobserveInval 建立依赖关系：
- 子节点失效时自动通知父节点
- 支持增量更新，避免全局重绘
- 实现了反向边管理（子到父）

### 2. 模板方法模式
revalidate() 定义框架流程，onRevalidate() 由子类实现：
- 统一处理失效检查和边界缓存
- 子类专注于边界计算逻辑
- 分离变与不变部分

### 3. 延迟计算
边界框只在需要时（重验证）计算，计算后缓存：
- 减少冗余计算
- 配合失效机制实现增量更新
- 查询边界时直接返回缓存值

### 4. 内存优化策略
- 联合体优化观察者存储
- 位域紧凑存储标志位
- 缓存边界框避免重复计算

### 5. 引用计数管理
继承自 SkRefCnt，使用 sk_sp 智能指针：
- 自动生命周期管理
- 支持 DAG 共享节点
- 防止内存泄漏和悬空指针

### 6. 宏驱动属性系统
SG_ATTRIBUTE 宏统一属性模式：
- 减少样板代码
- 自动集成失效通知
- 一致的 API 风格

## 性能考量

### 1. 增量更新
失效机制支持增量重验证：
- 只重新计算失效的节点
- 避免遍历整个场景图
- 对动态场景效率显著提升

### 2. 边界缓存
缓存边界框避免重复计算：
- bounds() 访问为 O(1)
- 只在失效时重新计算
- 对频繁查询边界的场景有利

### 3. 观察者模式开销
- 单观察者场景：零额外开销（直接指针）
- 多观察者场景：vector 分配和遍历开销
- 通常场景图树结构，多观察者情况罕见

### 4. 虚函数调用
onRevalidate() 虚函数调用有一定开销，但：
- 只在失效时调用（不是每帧）
- 提供的灵活性值得这个代价
- 现代 CPU 分支预测减轻影响

### 5. 位域访问
位域操作可能略慢于整字段访问，但：
- 节省的内存提升缓存局部性
- 现代编译器优化减少差异
- 总体利大于弊

### 6. 引用计数开销
sk_sp 的引用计数操作有原子性开销：
- 对象创建/销毁时增减引用
- 通常不在热路径（渲染循环）
- 简化内存管理的价值更大

## 相关文件

### 核心头文件
- **modules/sksg/include/SkSGInvalidationController.h**: 失效控制器定义
- **modules/sksg/src/SkSGNodePriv.h**: 节点私有辅助工具
- **include/core/SkMatrix.h**: 变换矩阵

### 实现文件
- **modules/sksg/src/SkSGNode.cpp**: Node 类实现

### 派生节点
- **SkSGRenderNode.h**: 渲染节点基类
- **SkSGGeometryNode.h**: 几何节点基类
- **SkSGEffectNode.h**: 效果节点基类（未在此文件中，但是派生类）
- **SkSGPaintNode.h**: 绘制节点基类
- **SkSGTransform.h**: 变换节点

### 友元类
- **NodePriv**: 提供私有成员访问
- **RenderNode**: 访问 fNodeFlags

### 使用示例
- **modules/skottie**: Lottie 动画场景图构建
- **modules/sksg/src/SkSGScene.cpp**: 场景管理
