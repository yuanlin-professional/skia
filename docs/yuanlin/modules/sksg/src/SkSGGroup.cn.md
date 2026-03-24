# SkSGGroup

> 源文件: modules/sksg/src/SkSGGroup.cpp

## 概述

SkSGGroup 是 Skia Scene Graph 模块中的容器节点实现，用于将多个渲染节点组合在一起形成层次结构。该文件实现了场景图的核心组合功能，允许开发者构建复杂的渲染树，并自动处理子节点的渲染、边界计算、损坏传播和点击测试。

Group 节点智能检测子节点间的重叠关系，在必要时自动启用图层隔离以确保渲染效果的正确性。该实现包含 119 行代码，是场景图系统中最基础和常用的容器节点。

## 架构位置

SkSGGroup 在 Scene Graph 层次结构中的位置：

```
Scene Graph 模块 (modules/sksg)
    ├── Node (所有节点基类)
    │
    ├── RenderNode (可渲染节点基类)
    │   ├── Draw (叶子节点：几何+绘制)
    │   ├── EffectNode (效果节点)
    │   └── Group (容器节点) ← 当前文件
    │
    └── InvalidationController (失效控制器)
```

在渲染管线中的作用：

```
应用层构建场景图
    ↓
Group 节点组织子节点
    ├── 子节点1 (Draw/Effect/Group)
    ├── 子节点2
    └── 子节点3
    ↓
重叠检测与隔离决策
    ↓
遍历渲染所有子节点
    ↓
Canvas 输出
```

## 主要类与结构体

### Group

```cpp
class Group : public RenderNode {
public:
    // 工厂方法
    static sk_sp<Group> Make();
    static sk_sp<Group> Make(std::vector<sk_sp<RenderNode>> children);

    // 子节点管理
    void addChild(sk_sp<RenderNode>);
    void removeChild(const sk_sp<RenderNode>&);
    void clear();

    // 查询方法
    size_t size() const { return fChildren.size(); }
    bool empty() const { return fChildren.empty(); }

protected:
    Group();
    explicit Group(std::vector<sk_sp<RenderNode>>);
    ~Group() override;

    // RenderNode 接口实现
    void onRender(SkCanvas*, const RenderContext*) const override;
    const RenderNode* onNodeAt(const SkPoint&) const override;
    SkRect onRevalidate(InvalidationController*, const SkMatrix&) override;

private:
    std::vector<sk_sp<RenderNode>> fChildren;   // 子节点列表
    bool fRequiresIsolation = true;             // 是否需要图层隔离
};
```

**成员变量说明**：
- `fChildren`：使用 `std::vector` 存储子节点，保持插入顺序
- `fRequiresIsolation`：标记是否需要图层隔离（当子节点重叠时为 true）

## 公共 API 函数

### Group::Make()

```cpp
static sk_sp<Group> Make();
static sk_sp<Group> Make(std::vector<sk_sp<RenderNode>> children);
```

工厂方法，创建空的或带初始子节点的 Group。

**使用示例**：
```cpp
// 创建空 Group
auto group = Group::Make();

// 创建带初始子节点的 Group
std::vector<sk_sp<RenderNode>> children = {node1, node2, node3};
auto group = Group::Make(std::move(children));
```

### addChild()

```cpp
void addChild(sk_sp<RenderNode> node);
```

添加子节点到 Group。特性：
- 自动注册为子节点的观察者（监听失效事件）
- 检查重复，不添加已存在的节点
- 触发 Group 自身失效

**实现细节**：
```cpp
void Group::addChild(sk_sp<RenderNode> node) {
    // 检查重复
    for (const auto& child : fChildren) {
        if (child == node) {
            return;  // 已存在，直接返回
        }
    }

    this->observeInval(node);  // 注册观察者
    fChildren.push_back(std::move(node));
    this->invalidate();  // 触发重新验证
}
```

### removeChild()

```cpp
void removeChild(const sk_sp<RenderNode>& node);
```

从 Group 中移除指定子节点。特性：
- 自动注销观察者关系
- 断言确保节点存在（调试模式）
- 触发 Group 失效

**实现细节**：
```cpp
void Group::removeChild(const sk_sp<RenderNode>& node) {
    SkDEBUGCODE(const auto origSize = fChildren.size());
    fChildren.erase(std::remove(fChildren.begin(), fChildren.end(), node), fChildren.end());
    SkASSERT(fChildren.size() == origSize - 1);  // 确保恰好移除一个

    this->unobserveInval(node);
    this->invalidate();
}
```

### clear()

```cpp
void clear();
```

清空所有子节点，注销所有观察者关系。

### size() / empty()

```cpp
size_t size() const;
bool empty() const;
```

查询子节点数量和是否为空。

## 内部实现细节

### 构造与析构

```cpp
Group::Group() = default;

Group::Group(std::vector<sk_sp<RenderNode>> children)
    : fChildren(std::move(children)) {
    for (const auto& child : fChildren) {
        this->observeInval(child);  // 批量注册观察者
    }
}

Group::~Group() {
    for (const auto& child : fChildren) {
        this->unobserveInval(child);  // 清理观察者关系
    }
}
```

**设计要点**：
- 构造函数使用 `std::move` 避免复制向量
- 析构函数确保所有观察者关系正确清理，防止悬空指针

### 渲染实现

```cpp
void Group::onRender(SkCanvas* canvas, const RenderContext* ctx) const {
    const auto local_ctx = ScopedRenderContext(canvas, ctx)
        .setIsolation(this->bounds(), canvas->getTotalMatrix(), fRequiresIsolation);

    for (const auto& child : fChildren) {
        child->render(canvas, local_ctx);
    }
}
```

**渲染流程**：
1. 创建局部渲染上下文 `local_ctx`
2. 根据 `fRequiresIsolation` 决定是否创建图层隔离
3. 按顺序渲染所有子节点（绘制顺序即添加顺序）

**图层隔离条件**：
- 当 `fRequiresIsolation == true` 时，`setIsolation()` 会调用 `canvas->saveLayer()`
- 隔离确保后面的子节点不会与前面的子节点产生非预期的混合效果

### 点击测试

```cpp
const RenderNode* Group::onNodeAt(const SkPoint& p) const {
    for (auto it = fChildren.crbegin(); it != fChildren.crend(); ++it) {
        if (const auto* node = (*it)->nodeAt(p)) {
            return node;
        }
    }
    return nullptr;
}
```

**实现特点**：
- 使用**反向迭代器** `crbegin()` 从后向前遍历
- 理由：后添加的节点在视觉上位于上层，应优先响应点击
- 返回第一个包含点 `p` 的子节点
- 如果所有子节点都不包含，返回 `nullptr`

**交互逻辑**：
```
用户点击 (x, y)
    ↓
Group 从上层到下层检查子节点
    ├── 子节点3 → 包含点 (返回)
    ├── 子节点2 → 不包含 (跳过)
    └── 子节点1 → 不检查
```

### 边界验证与重叠检测

```cpp
SkRect Group::onRevalidate(InvalidationController* ic, const SkMatrix& ctm) {
    SkASSERT(this->hasInval());

    SkRect bounds = SkRect::MakeEmpty();
    fRequiresIsolation = false;

    for (size_t i = 0; i < fChildren.size(); ++i) {
        const auto child_bounds = fChildren[i]->revalidate(ic, ctm);

        // 检测重叠
        if (!fRequiresIsolation && i > 0 && child_bounds.intersects(bounds)) {
            fRequiresIsolation = true;
        }

        bounds.join(child_bounds);  // 合并边界
    }

    return bounds;
}
```

**关键逻辑**：

1. **初始化**：边界为空，假设不需要隔离
2. **遍历子节点**：依次验证每个子节点
3. **重叠检测**：
   ```cpp
   if (!fRequiresIsolation && i > 0 && child_bounds.intersects(bounds)) {
       fRequiresIsolation = true;
   }
   ```
   - 从第二个子节点开始检查
   - 判断当前子节点是否与之前所有子节点的并集重叠
   - 一旦发现重叠，标记需要隔离

4. **边界合并**：使用 `join()` 将子节点边界并入总边界

**保守策略**：
```cpp
#if 1
    // 与所有前置节点并集测试（当前实现）
    if (child_bounds.intersects(bounds)) {
        fRequiresIsolation = true;
    }
#else
    // 精确测试（注释掉的代码）
    for (size_t j = 0; j < i; ++j) {
        if (child_bounds.intersects(fChildren[j]->bounds())) {
            fRequiresIsolation = true;
            break;
        }
    }
#endif
```

**设计决策**：
- 当前使用保守策略：与并集测试（O(n) 复杂度）
- 精确策略需要 O(n²) 复杂度
- 注释说明：实践中精确策略并未显著提高图层优化率

**为什么需要隔离**：
```cpp
// 无隔离场景
Group {
    Rect1 (bounds: 0,0-50,50, opacity: 0.5)
    Rect2 (bounds: 25,25-75,75, opacity: 0.5)
}
// 结果：重叠区域会有非预期的混合效果

// 有隔离场景
Group {
    saveLayer();  // 创建离屏缓冲
    Rect1 (opacity: 0.5)
    Rect2 (opacity: 0.5)
    restoreLayer();  // 整体合成到画布
}
// 结果：Group 整体作为一个单元应用效果
```

## 依赖关系

### 头文件依赖

```cpp
#include "modules/sksg/include/SkSGGroup.h"  // 公共头文件
#include "include/core/SkCanvas.h"           // 画布渲染
#include "include/private/base/SkAssert.h"   // 断言宏
#include "include/private/base/SkDebug.h"    // 调试宏
#include "modules/sksg/include/SkSGNode.h"   // 节点基类

#include <algorithm>  // std::remove
```

### 类依赖关系图

```
Node (基类)
    ↓
RenderNode (渲染节点基类)
    ↓
Group (容器节点)
    ├── 持有 RenderNode* (子节点)
    ├── 使用 InvalidationController (失效管理)
    └── 使用 ScopedRenderContext (渲染上下文)
```

### 被使用者

- **Skottie 动画系统**：使用 Group 组织图层
- **Scene Graph 测试**：验证容器逻辑
- **EffectNode**：许多效果节点内部使用 Group 管理子节点

## 设计模式与设计决策

### 组合模式 (Composite Pattern)

Group 是组合模式的经典实现：

```cpp
// 统一接口
class RenderNode {
public:
    virtual void render(...) = 0;
};

// 叶子节点
class Draw : public RenderNode { ... };

// 容器节点
class Group : public RenderNode {
    std::vector<sk_sp<RenderNode>> fChildren;
    void render(...) override {
        for (auto& child : fChildren) {
            child->render(...);  // 递归调用
        }
    }
};
```

**优势**：
- 客户端无需区分叶子节点和容器节点
- 可以构建任意深度的树形结构
- 简化了遍历和操作逻辑

### 观察者模式 (Observer Pattern)

Group 观察子节点的失效事件：

```cpp
// 注册
this->observeInval(child);

// 当 child 失效时，Group 自动收到通知并失效自身
```

**好处**：
- 自动传播变化，无需手动管理依赖
- 解耦子节点和父节点

### 惰性求值 (Lazy Evaluation)

隔离标志 `fRequiresIsolation` 只在验证阶段计算：

```cpp
SkRect onRevalidate(...) {
    fRequiresIsolation = false;  // 每次验证时重新计算
    // ... 检测重叠 ...
}
```

**优势**：
- 子节点变化时，隔离需求可能改变
- 避免维护复杂的增量更新逻辑
- 验证开销较小（O(n)）

### Scoped Context 模式

```cpp
const auto local_ctx = ScopedRenderContext(canvas, ctx)
    .setIsolation(this->bounds(), canvas->getTotalMatrix(), fRequiresIsolation);
```

使用 RAII 确保 `saveLayer/restoreLayer` 配对。

### 防御性编程

```cpp
// 防止重复添加
for (const auto& child : fChildren) {
    if (child == node) {
        return;
    }
}

// 断言验证移除成功
SkASSERT(fChildren.size() == origSize - 1);
```

## 性能考量

### 子节点存储

使用 `std::vector<sk_sp<RenderNode>>`：
- **优点**：缓存友好，顺序遍历快
- **缺点**：中间插入/删除较慢（O(n)）
- **权衡**：场景图构建后结构相对稳定，遍历远多于修改

### 重复检测

```cpp
for (const auto& child : fChildren) {
    if (child == node) {
        return;
    }
}
```

- O(n) 复杂度的线性搜索
- 实践中子节点数量通常较小（< 100）
- 可能的优化：使用 `std::unordered_set` 辅助查重（增加内存开销）

### 重叠检测策略

保守的并集测试 vs 精确的两两测试：

```
保守策略：O(n)
    ├── 每个子节点只测试一次
    └── 可能过度估计重叠（误报）

精确策略：O(n²)
    ├── 每对子节点都测试
    └── 准确识别重叠

实践结论：O(n) 已足够，O(n²) 无显著收益
```

### saveLayer 开销

当 `fRequiresIsolation == true` 时：
- 创建离屏纹理
- 额外的像素填充和合成操作
- GPU 上下文切换

**优化目标**：尽可能避免不必要的隔离。

### 边界计算缓存

```cpp
bounds.join(child_bounds);  // O(1) 操作
```

子节点的边界已在 `revalidate()` 中缓存，无需重复计算。

## 相关文件

### 头文件

- **modules/sksg/include/SkSGGroup.h** - Group 节点的公共接口
- **modules/sksg/include/SkSGRenderNode.h** - 渲染节点基类
- **modules/sksg/include/SkSGNode.h** - 所有节点的基类

### 实现文件

- **modules/sksg/src/SkSGRenderNode.cpp** - 渲染节点基类实现
- **modules/sksg/src/SkSGDraw.cpp** - 叶子渲染节点
- **modules/sksg/src/SkSGEffectNode.cpp** - 效果节点基类

### 测试文件

- **tests/SkSGTest.cpp** - Scene Graph 单元测试

### 使用示例

```cpp
// 构建场景图
auto background = Draw::Make(Plane::Make(), Color::Make(SK_ColorWHITE));
auto content1 = Draw::Make(rect1, paint1);
auto content2 = Draw::Make(rect2, paint2);

auto group = Group::Make();
group->addChild(background);
group->addChild(content1);
group->addChild(content2);

// 渲染
InvalidationController ic;
group->revalidate(&ic, SkMatrix::I());
group->render(canvas, nullptr);
```
