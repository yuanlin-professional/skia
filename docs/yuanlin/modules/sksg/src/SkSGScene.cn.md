# SkSGScene

> 源文件: modules/sksg/src/SkSGScene.cpp

## 概述

SkSGScene 是 Skia Scene Graph 的顶层场景管理类，提供了场景图的入口点和整体协调功能。该文件仅包含 36 行代码，却是整个场景图系统的门面（Facade），封装了渲染、验证和点击测试等核心操作。Scene 类持有场景图的根节点，并提供简洁的 API 供应用层使用。

Scene 类的设计哲学是"简单即美"：将复杂的场景图操作封装为少数几个直观的方法调用，隐藏了内部的验证流程、损坏追踪和遍历细节。

## 架构位置

Scene 在场景图系统中的位置：

```
应用层 (Skottie / Viewer / 用户代码)
    ↓
Scene (场景管理器) ← 当前组件
    ↓
RenderNode 树 (根节点)
    ├── Group (容器)
    ├── Draw (叶子)
    └── EffectNode (效果)
         ↓
Skia Canvas (底层渲染)
```

在使用流程中：

```
1. 构建场景图
   auto root = Group::Make();
   root->addChild(...);

2. 创建 Scene
   auto scene = Scene::Make(root);

3. 每帧循环
   scene->revalidate(&ic);  // 验证更新
   scene->render(canvas);    // 渲染
```

## 主要类与结构体

### Scene

```cpp
class Scene {
public:
    // 工厂方法
    static std::unique_ptr<Scene> Make(sk_sp<RenderNode> root);

    // 场景操作
    void render(SkCanvas* canvas) const;
    void revalidate(InvalidationController* ic = nullptr);
    const RenderNode* nodeAt(const SkPoint& p) const;

    // 析构函数
    ~Scene();

private:
    // 私有构造函数
    explicit Scene(sk_sp<RenderNode> root);

    sk_sp<RenderNode> fRoot;  // 根节点
};
```

**设计特点**：
- 使用 `std::unique_ptr` 管理生命周期（独占所有权）
- 所有方法都很轻量，直接委托给根节点
- 不可复制，不可赋值（隐式禁用）

## 公共 API 函数

### Scene::Make()

```cpp
static std::unique_ptr<Scene> Make(sk_sp<RenderNode> root);
```

创建场景实例的工厂方法。

**参数**：
- `root`：场景图的根节点

**返回值**：
- 成功：指向新 Scene 的 `unique_ptr`
- 失败：`nullptr`（root 为空时）

**使用示例**：
```cpp
// 构建场景图
auto root = Group::Make();
root->addChild(Draw::Make(rect, color));

// 创建场景
auto scene = Scene::Make(root);
if (!scene) {
    // 错误处理
    return;
}
```

**设计决策**：
- 返回 `unique_ptr` 而非 `shared_ptr`：明确独占所有权语义
- 检查空指针：防止创建无效场景

### render()

```cpp
void render(SkCanvas* canvas) const;
```

渲染整个场景图到指定画布。

**实现**：
```cpp
void Scene::render(SkCanvas* canvas) const {
    fRoot->render(canvas);
}
```

**参数**：
- `canvas`：Skia 画布对象，目标渲染表面

**前提条件**：
- 场景必须已通过 `revalidate()` 验证
- 画布状态应该已正确设置（变换、裁剪等）

**使用示例**：
```cpp
// 每帧渲染
void onDraw(SkCanvas* canvas) {
    scene->revalidate(&ic);
    scene->render(canvas);
}
```

**特点**：
- 轻量委托，零额外开销
- 不修改场景状态（const 方法）
- 不创建渲染上下文（传递 nullptr 给根节点）

### revalidate()

```cpp
void revalidate(InvalidationController* ic = nullptr);
```

验证场景图，更新所有失效节点并收集损坏区域。

**实现**：
```cpp
void Scene::revalidate(InvalidationController* ic) {
    fRoot->revalidate(ic, SkMatrix::I());
}
```

**参数**：
- `ic`：失效控制器指针（可选）
  - 传递 `nullptr`：仅验证，不收集损坏区域
  - 传递有效指针：验证并收集损坏信息（用于增量渲染）

**操作流程**：
1. 从根节点开始递归遍历
2. 验证所有标记为失效的节点
3. 重新计算边界框
4. 将损坏区域报告给失效控制器

**使用示例**：
```cpp
// 完整渲染（无增量优化）
scene->revalidate();  // ic == nullptr
scene->render(canvas);

// 增量渲染
InvalidationController ic;
scene->revalidate(&ic);
if (!ic.bounds().isEmpty()) {
    canvas->save();
    canvas->clipRect(ic.bounds());
    scene->render(canvas);
    canvas->restore();
}
```

**性能考量**：
- 传递 `SkMatrix::I()`（单位矩阵）作为初始变换
- 节点内部会累积变换矩阵
- 仅失效节点被重新验证（惰性更新）

### nodeAt()

```cpp
const RenderNode* nodeAt(const SkPoint& p) const;
```

点击测试：查找包含指定点的最上层节点。

**实现**：
```cpp
const RenderNode* Scene::nodeAt(const SkPoint& p) const {
    return fRoot->nodeAt(p);
}
```

**参数**：
- `p`：测试点的坐标（场景坐标系）

**返回值**：
- 包含该点的最上层节点指针
- `nullptr` 表示没有节点包含该点

**使用示例**：
```cpp
// 鼠标点击处理
void onMouseClick(float x, float y) {
    SkPoint click_pos = SkPoint::Make(x, y);
    const RenderNode* hit_node = scene->nodeAt(click_pos);

    if (hit_node) {
        // 处理点击事件
        handleNodeClick(hit_node);
    }
}
```

**遍历顺序**：
- 从上到下（Z 顺序）
- Group 节点从后向前遍历子节点
- 返回第一个命中的节点

## 内部实现细节

### 构造与析构

```cpp
Scene::Scene(sk_sp<RenderNode> root) : fRoot(std::move(root)) {}

Scene::~Scene() = default;
```

**构造函数**：
- 私有构造，强制使用工厂方法
- 使用 `std::move` 避免引用计数操作
- 单一成员变量初始化

**析构函数**：
- 编译器生成的默认析构函数
- 自动释放 `fRoot`（智能指针管理）
- 无需手动清理资源

### 委托模式实现

所有方法都是简单的委托：

```cpp
// 渲染委托
void Scene::render(SkCanvas* canvas) const {
    fRoot->render(canvas);
}

// 验证委托
void Scene::revalidate(InvalidationController* ic) {
    fRoot->revalidate(ic, SkMatrix::I());
}

// 点击测试委托
const RenderNode* Scene::nodeAt(const SkPoint& p) const {
    return fRoot->nodeAt(p);
}
```

**优点**：
- Scene 类保持简洁（单一职责）
- 所有复杂逻辑由节点实现
- 零性能开销（内联优化）

## 依赖关系

### 头文件依赖

```cpp
#include "include/core/SkMatrix.h"                  // 变换矩阵
#include "modules/sksg/include/SkSGRenderNode.h"    // 渲染节点
#include "modules/sksg/include/SkSGScene.h"         // 公共头文件

#include <utility>  // std::move
```

**最小化依赖**：
- 仅依赖必要的头文件
- 不依赖具体节点类型（如 Group、Draw）
- 保持编译时间最优

### 模块关系

```
应用层
    ↓ 创建和使用
Scene (门面)
    ↓ 持有
RenderNode (根节点)
    ↓ 包含
子节点树（Group, Draw, Effect 等）
    ↓ 使用
InvalidationController (可选)
```

## 设计模式与设计决策

### 门面模式 (Facade Pattern)

Scene 是场景图系统的门面：

```cpp
// 复杂子系统
RenderNode::render()
    ├── Group::onRender()
    │   ├── child1->render()
    │   └── child2->render()
    ├── Draw::onRender()
    └── EffectNode::onRender()

// 简单门面
Scene::render() → fRoot->render()
```

**好处**：
- 隐藏内部复杂性
- 提供统一的入口点
- 简化客户端代码

### 工厂方法模式 (Factory Method)

```cpp
static std::unique_ptr<Scene> Make(sk_sp<RenderNode> root) {
    return root ? std::unique_ptr<Scene>(new Scene(std::move(root))) : nullptr;
}
```

**优点**：
- 控制对象创建
- 验证输入（空指针检查）
- 强制使用智能指针

### 单一职责原则 (SRP)

Scene 的唯一职责是协调场景图操作：
- **不负责**：节点创建、渲染细节、失效管理
- **只负责**：持有根节点、委托操作

### 委托模式 (Delegation)

所有操作委托给根节点：

```cpp
// Scene 不实现渲染逻辑
void render(...) { fRoot->render(...); }

// Scene 不实现验证逻辑
void revalidate(...) { fRoot->revalidate(...); }
```

这使得 Scene 保持稳定，所有变化由节点层处理。

### 独占所有权

使用 `std::unique_ptr` 而非 `std::shared_ptr`：

```cpp
static std::unique_ptr<Scene> Make(...);
```

**理由**：
- 场景通常由单一管理器拥有
- 避免循环引用和所有权混乱
- 明确的生命周期语义

## 性能考量

### 零开销抽象

Scene 的所有方法都是轻量委托：
- 编译器很可能内联这些调用
- 运行时性能等同于直接调用根节点
- 无虚函数开销（Scene 本身不是多态）

### 单位矩阵优化

```cpp
fRoot->revalidate(ic, SkMatrix::I());
```

传递单位矩阵避免不必要的变换计算。Skia 对单位矩阵有优化路径：
- `isIdentity()` 检查 → O(1)
- 跳过矩阵乘法 → 节省约 20 条指令

### 智能指针开销

```cpp
sk_sp<RenderNode> fRoot;
```

使用 Skia 的智能指针（引用计数）：
- **开销**：原子操作（约 10-20 纳秒）
- **收益**：自动内存管理，避免泄漏
- **权衡**：可接受的开销换取安全性

### 内联潜力

所有方法都很短，适合内联：

```cpp
// 内联前
scene->render(canvas);  // 调用开销 + 委托开销

// 内联后（优化编译器）
root->render(canvas);   // 直接调用，无额外开销
```

## 相关文件

### 头文件

- **modules/sksg/include/SkSGScene.h** - Scene 类的公共接口
- **modules/sksg/include/SkSGRenderNode.h** - 渲染节点基类
- **modules/sksg/include/SkSGInvalidationController.h** - 失效控制器

### 实现文件

- **modules/sksg/src/SkSGNode.cpp** - 节点基类实现
- **modules/sksg/src/SkSGRenderNode.cpp** - 渲染节点实现
- **modules/sksg/src/SkSGGroup.cpp** - Group 容器节点

### 使用者

- **modules/skottie/src/Skottie.cpp** - Lottie 动画系统
- **tools/viewer/SkottieSlide.cpp** - Viewer 工具
- **tests/SkSGTest.cpp** - 单元测试

### 使用示例

```cpp
// 完整的场景图应用
class MyApp {
    std::unique_ptr<Scene> scene;
    InvalidationController ic;

    void setup() {
        // 构建场景图
        auto root = Group::Make();
        root->addChild(createBackground());
        root->addChild(createContent());

        // 创建场景
        scene = Scene::Make(root);
    }

    void onFrame(SkCanvas* canvas) {
        // 更新动画属性
        updateAnimation();

        // 验证并渲染
        ic.reset();
        scene->revalidate(&ic);

        if (!ic.bounds().isEmpty()) {
            canvas->save();
            canvas->clipRect(ic.bounds());
            canvas->clear(SK_ColorWHITE);
            scene->render(canvas);
            canvas->restore();
        }
    }

    void onMouseClick(float x, float y) {
        SkPoint p = SkPoint::Make(x, y);
        const RenderNode* hit = scene->nodeAt(p);

        if (hit) {
            // 处理交互
        }
    }
};
```
