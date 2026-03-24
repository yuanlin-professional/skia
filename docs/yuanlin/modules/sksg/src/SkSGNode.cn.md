# SkSGNode

> 源文件: modules/sksg/src/SkSGNode.cpp

## 概述

SkSGNode 是 Skia Scene Graph 系统中所有节点的抽象基类实现，提供了场景图的核心基础设施，包括失效传播机制、观察者模式实现、边界缓存和遍历保护。该文件包含 164 行代码，实现了场景图最关键的两个功能：**失效管理**（Invalidation Management）和**增量更新**（Incremental Updates）。

Node 类通过观察者模式实现了父子节点间的依赖关系管理，当节点状态改变时，失效信息会自动向上传播到所有观察者（父节点），触发增量式的重新验证和渲染。这种设计使得场景图能够高效地处理动画和交互，避免全图重绘。

## 架构位置

Node 在 Scene Graph 类层次中的位置：

```
SkRefCnt (Skia 引用计数基类)
    ↓
Node (场景图节点基类) ← 当前文件
    ├── GeometryNode (几何节点抽象)
    │   ├── Rect / Path / Plane
    │   └── ...
    ├── PaintNode (绘制属性节点抽象)
    │   ├── Color / ShaderPaint
    │   └── ...
    └── RenderNode (渲染节点抽象)
        ├── Draw (叶子节点)
        ├── Group (容器节点)
        └── EffectNode (效果节点)
```

在失效传播流程中：

```
叶子节点属性修改
    ↓ invalidate()
观察者节点失效
    ↓ 递归向上传播
根节点失效
    ↓ revalidate()
递归向下验证
    ↓ onRevalidate()
子类重新计算属性和边界
```

## 主要类与结构体

### Node

```cpp
class Node : public SkRefCnt {
public:
    // 验证接口
    const SkRect& revalidate(InvalidationController*, const SkMatrix&);

    // 失效接口
    void invalidate(bool damage = true);

protected:
    // 失效特性
    enum InvalTraits {
        kBubbleDamage_Trait   = 1 << 0,  // 损坏向上冒泡
        kOverrideDamage_Trait = 1 << 1,  // 覆盖后代损坏
    };

    explicit Node(uint32_t invalTraits);
    ~Node() override;

    // 子类接口
    const SkRect& bounds() const;
    bool hasInval() const;
    virtual SkRect onRevalidate(InvalidationController*, const SkMatrix&) = 0;

    // 观察者管理
    void observeInval(const sk_sp<Node>&);
    void unobserveInval(const sk_sp<Node>&);

private:
    // 内部标志
    enum Flags {
        kInvalidated_Flag   = 1 << 0,  // 需要重新验证
        kDamage_Flag        = 1 << 1,  // 产生损坏
        kObserverArray_Flag = 1 << 2,  // 有多个观察者
        kInTraversal_Flag   = 1 << 3,  // 正在遍历（循环检测）
    };

    // 成员变量
    union {
        Node* fInvalObserver;                // 单个观察者
        std::vector<Node*>* fInvalObserverArray;  // 多个观察者
    };
    SkRect fBounds;                    // 缓存的边界框
    const uint32_t fInvalTraits : 2;   // 失效特性
    uint32_t fFlags : 4;               // 内部标志
    uint32_t fNodeFlags : 8;           // 子类可访问标志
};
```

**关键数据结构**：

1. **观察者存储**（Union 优化）：
   ```cpp
   union {
       Node* fInvalObserver;                // 单个观察者（8 字节）
       std::vector<Node*>* fInvalObserverArray;  // 多个观察者指针
   };
   ```
   - 大多数节点只有一个父节点
   - 使用 Union 节省内存（单观察者时无需分配向量）
   - 通过 `kObserverArray_Flag` 标志区分两种状态

2. **位域标志**（内存优化）：
   ```cpp
   const uint32_t fInvalTraits : 2;  // 2 位
   uint32_t fFlags : 4;               // 4 位
   uint32_t fNodeFlags : 8;           // 8 位
   // 剩余 18 位可用于未来扩展
   ```
   - 总共使用 32 位（4 字节）存储所有标志
   - 比使用多个 bool 变量节省空间

### ScopedFlag

```cpp
class Node::ScopedFlag {
public:
    ScopedFlag(Node* node, uint32_t flag);
    ~ScopedFlag();
    bool wasSet() const { return fWasSet; }

private:
    Node* fNode;
    uint32_t fFlag;
    bool fWasSet;
};
```

RAII 辅助类，用于临时设置和恢复标志位，主要用于循环检测。

## 公共 API 函数

### revalidate()

```cpp
const SkRect& revalidate(InvalidationController* ic, const SkMatrix& ctm);
```

遍历 DAG 并重新验证所有失效的依赖节点。

**参数**：
- `ic`：失效控制器指针（可选），用于收集损坏区域
- `ctm`：当前变换矩阵（Current Transformation Matrix）

**返回值**：
- DAG 片段的边界框

**使用示例**：
```cpp
InvalidationController ic;
SkMatrix identity = SkMatrix::I();
const SkRect& bounds = node->revalidate(&ic, identity);

// 检查损坏区域
if (!ic.bounds().isEmpty()) {
    // 有变化，需要重绘
}
```

### invalidate()

```cpp
void invalidate(bool damage = true);
```

标记节点为失效状态，触发重新验证。

**参数**：
- `damage`：是否产生损坏（默认 true）
  - `true`：节点变化影响渲染，需要记录损坏区域
  - `false`：仅标记失效，不产生可见变化（如内部状态更新）

**使用示例**：
```cpp
// 修改节点属性后调用
rect->setRect(new_bounds);  // 内部调用 invalidate(true)

// 仅更新内部缓存
node->invalidate(false);
```

## 内部实现细节

### 构造与析构

```cpp
Node::Node(uint32_t invalTraits)
    : fInvalObserver(nullptr)
    , fBounds(SkRectPriv::MakeLargeS32())  // 初始为无限大
    , fInvalTraits(invalTraits)
    , fFlags(kInvalidated_Flag)            // 初始标记为失效
    , fNodeFlags(0) {}
```

**初始化策略**：
- 观察者列表为空
- 边界初始化为无限大（尚未验证）
- 标记为失效（需要首次验证）

```cpp
Node::~Node() {
    if (fFlags & kObserverArray_Flag) {
        SkASSERT(fInvalObserverArray->empty());  // 应该已清理所有观察者
        delete fInvalObserverArray;
    } else {
        SkASSERT(!fInvalObserver);  // 应该已清理单个观察者
    }
}
```

**析构检查**：
- 断言确保所有观察者关系已清理
- 防止悬空指针和内存泄漏

### 观察者管理实现

#### observeInval() - 注册观察者

```cpp
void Node::observeInval(const sk_sp<Node>& node) {
    SkASSERT(node);

    // 情况1：节点还没有观察者
    if (!(node->fFlags & kObserverArray_Flag)) {
        if (!node->fInvalObserver) {
            node->fInvalObserver = this;  // 设置单个观察者
            return;
        }

        // 情况2：从单观察者升级到多观察者
        auto observers = new std::vector<Node*>();
        observers->reserve(2);
        observers->push_back(node->fInvalObserver);  // 保留原观察者

        node->fInvalObserverArray = observers;
        node->fFlags |= kObserverArray_Flag;  // 设置多观察者标志
    }

    // 情况3：添加到观察者数组
    SkASSERT(std::find(node->fInvalObserverArray->begin(),
                       node->fInvalObserverArray->end(), this)
             == node->fInvalObserverArray->end());  // 防止重复
    node->fInvalObserverArray->push_back(this);
}
```

**三级存储策略**：
1. **0 个观察者**：`fInvalObserver == nullptr`
2. **1 个观察者**：`fInvalObserver` 指向该观察者
3. **2+ 观察者**：`fInvalObserverArray` 指向动态数组

**优化理由**：
- 绝大多数节点只有一个父节点（树形结构）
- 避免为常见情况分配动态内存

#### unobserveInval() - 注销观察者

```cpp
void Node::unobserveInval(const sk_sp<Node>& node) {
    SkASSERT(node);

    // 单观察者情况
    if (!(node->fFlags & kObserverArray_Flag)) {
        SkASSERT(node->fInvalObserver == this);
        node->fInvalObserver = nullptr;
        return;
    }

    // 多观察者情况
    SkDEBUGCODE(const auto origSize = node->fInvalObserverArray->size());
    node->fInvalObserverArray->erase(
        std::remove(node->fInvalObserverArray->begin(),
                   node->fInvalObserverArray->end(), this),
        node->fInvalObserverArray->end());
    SkASSERT(node->fInvalObserverArray->size() == origSize - 1);
}
```

**注意**：不会从多观察者降级回单观察者（避免复杂逻辑）。

#### forEachInvalObserver() - 遍历观察者

```cpp
template <typename Func>
void Node::forEachInvalObserver(Func&& func) const {
    if (fFlags & kObserverArray_Flag) {
        for (const auto& parent : *fInvalObserverArray) {
            func(parent);  // 调用每个观察者
        }
        return;
    }

    if (fInvalObserver) {
        func(fInvalObserver);  // 调用单个观察者
    }
}
```

模板函数，接受任意可调用对象（lambda、函数指针等）。

### 失效传播实现

```cpp
void Node::invalidate(bool damageBubbling) {
    TRAVERSAL_GUARD;  // 防止循环

    // 早期退出：已失效且损坏标志已设置
    if (this->hasInval() && (!damageBubbling || (fFlags & kDamage_Flag))) {
        return;
    }

    // 损坏传播逻辑
    if (damageBubbling && !(fInvalTraits & kBubbleDamage_Trait)) {
        fFlags |= kDamage_Flag;  // 此节点产生损坏
        damageBubbling = false;  // 停止向上冒泡
    }

    fFlags |= kInvalidated_Flag;  // 标记失效

    // 递归通知观察者
    forEachInvalObserver([&](Node* observer) {
        observer->invalidate(damageBubbling);
    });
}
```

**TRAVERSAL_GUARD 宏**：

```cpp
#define TRAVERSAL_GUARD \
    ScopedFlag traversal_guard(this, kInTraversal_Flag); \
    if (traversal_guard.wasSet()) \
        return
```

防止循环遍历（虽然场景图应该是 DAG，但防御性编程）。

**损坏冒泡机制**：

```
叶子节点 (kBubbleDamage_Trait)
    ↓ invalidate(true)
    损坏继续冒泡
    ↓
容器节点 (无 kBubbleDamage_Trait)
    ↓ 设置 kDamage_Flag
    停止冒泡
    ↓ invalidate(false)
祖先节点仅标记失效
```

**设计意图**：
- Paint/Geometry 节点不产生损坏（由 Draw 节点聚合）
- Draw/Group 节点产生损坏（实际影响像素）

### 验证实现

```cpp
const SkRect& Node::revalidate(InvalidationController* ic, const SkMatrix& ctm) {
    TRAVERSAL_GUARD fBounds;  // 循环检测

    // 早期退出：已验证
    if (!this->hasInval()) {
        return fBounds;
    }

    // 判断是否生成损坏
    const auto generate_damage =
            ic && ((fFlags & kDamage_Flag) || (fInvalTraits & kOverrideDamage_Trait));

    if (!generate_damage) {
        // 简单验证：无损坏
        fBounds = this->onRevalidate(ic, ctm);
    } else {
        // 验证并生成损坏
        const auto prev_bounds = fBounds;  // 保存旧边界

        // 覆盖损坏特性：不传递失效控制器给子节点
        auto* ic_override = (fInvalTraits & kOverrideDamage_Trait) ? nullptr : ic;
        fBounds = this->onRevalidate(ic_override, ctm);

        // 记录旧边界的损坏
        ic->inval(prev_bounds, ctm);

        // 边界改变时记录新边界的损坏
        if (fBounds != prev_bounds) {
            ic->inval(fBounds, ctm);
        }
    }

    // 清除失效和损坏标志
    fFlags &= ~(kInvalidated_Flag | kDamage_Flag);

    return fBounds;
}
```

**损坏生成策略**：

1. **无损坏**（`kBubbleDamage_Trait` 节点）：
   - 直接调用 `onRevalidate()`
   - 不记录损坏区域

2. **有损坏**（`kDamage_Flag` 节点）：
   - 记录旧边界的损坏
   - 重新验证
   - 记录新边界的损坏（如果改变）

3. **覆盖损坏**（`kOverrideDamage_Trait` 节点）：
   - 传递 `nullptr` 给子节点（阻止子节点生成损坏）
   - 自己生成完整的损坏信息
   - 用于 ImageFilter 等完全改变渲染结果的效果

## 依赖关系

### 头文件依赖

```cpp
#include "modules/sksg/include/SkSGNode.h"                // 公共头文件
#include "include/private/base/SkDebug.h"                 // 调试宏
#include "modules/sksg/include/SkSGInvalidationController.h"  // 失效控制器
#include "src/core/SkRectPriv.h"                          // 私有矩形工具

#include <algorithm>  // std::find, std::remove
```

### 使用者

- **所有 Scene Graph 节点类**：继承自 Node
- **Scene**：调用根节点的 `revalidate()`
- **容器节点**：使用 `observeInval()` 管理子节点

## 设计模式与设计决策

### 观察者模式 (Observer Pattern)

节点观察子节点的失效事件：

```cpp
// Draw 节点观察几何和绘制属性
Draw::Draw(sk_sp<GeometryNode> geo, sk_sp<PaintNode> paint) {
    this->observeInval(geo);
    this->observeInval(paint);
}

// 当 geo 失效时，Draw 自动失效
geo->invalidate();  // → Draw::invalidate() 被调用
```

### 模板方法模式 (Template Method)

基类定义验证流程，子类实现具体逻辑：

```cpp
// 基类
const SkRect& Node::revalidate(...) {
    // 前处理
    const auto prev_bounds = fBounds;

    // 调用子类钩子
    fBounds = this->onRevalidate(ic, ctm);

    // 后处理
    ic->inval(prev_bounds, ctm);
    return fBounds;
}

// 子类实现
SkRect Rect::onRevalidate(...) override {
    return fRect;  // 具体逻辑
}
```

### RAII 模式

`ScopedFlag` 使用 RAII 管理标志位：

```cpp
{
    ScopedFlag guard(this, kInTraversal_Flag);
    // flag 被设置
    // ...
}  // flag 自动恢复
```

### 内存优化策略

1. **Union 节省内存**：
   - 单观察者：8 字节
   - 多观察者：8 字节（指针）
   - 无需总是分配向量

2. **位域压缩标志**：
   - 14 位标志存储在 4 字节中
   - 节省 10+ 字节相比使用独立 bool

3. **懒惰分配**：
   - 仅在需要时分配观察者数组
   - 延迟到第二个观察者添加时

## 性能考量

### 失效传播开销

- **最坏情况**：O(n)，n 为节点总数（全图失效）
- **典型情况**：O(log n)，仅失效路径上的节点
- **最优情况**：O(1)，早期退出（已失效）

### 观察者遍历

- **单观察者**：O(1)，直接调用
- **多观察者**：O(k)，k 为观察者数量（通常 < 5）

### 内存占用

每个 Node 实例约 40-50 字节：
- vtable 指针：8 字节
- 引用计数：4 字节
- 观察者：8 字节
- 边界：16 字节
- 标志：4 字节
- 总计：~40 字节

### 循环检测

`TRAVERSAL_GUARD` 的开销：
- 创建 `ScopedFlag`：~10 纳秒
- 标志位检查：~1 纳秒
- 总开销可忽略

## 相关文件

### 头文件

- **modules/sksg/include/SkSGNode.h** - Node 类公共接口
- **modules/sksg/include/SkSGInvalidationController.h** - 失效控制器

### 子类实现

- **modules/sksg/src/SkSGRenderNode.cpp** - 渲染节点基类
- **modules/sksg/src/SkSGGeometryNode.cpp** - 几何节点基类
- **modules/sksg/src/SkSGPaint.cpp** - 绘制属性节点

### 使用者

- **modules/sksg/src/SkSGScene.cpp** - 场景管理器
- **所有具体节点类** - 继承并实现 `onRevalidate()`

### 宏定义

- **SG_ATTRIBUTE** - 自动生成 getter/setter
- **SG_MAPPED_ATTRIBUTE** - 委托给子对象的 getter/setter
