# SkSGInvalidationController

> 源文件: modules/sksg/src/SkSGInvalidationController.cpp

## 概述

SkSGInvalidationController 是 Skia Scene Graph 中的失效控制器实现，负责收集和管理场景图节点失效（invalidation）产生的脏区（dirty regions）。该文件仅包含 32 行代码，却是场景图优化渲染的核心机制，通过精确跟踪变化区域，实现增量渲染和局部重绘。

失效控制器在场景图验证（revalidation）过程中收集所有需要重新绘制的矩形区域，使得渲染系统可以只更新发生变化的部分，而非每帧全屏重绘，极大提升了动画和交互的性能。

## 架构位置

InvalidationController 在场景图系统中的位置：

```
Scene Graph 更新流程
    ↓
节点属性修改
    ↓
节点失效标记
    ↓
场景图验证 (revalidate)
    ├── 递归验证所有失效节点
    └── 收集失效区域 → InvalidationController ← 当前组件
         ↓
渲染系统
    ├── 检查失效边界
    ├── 优化绘制区域
    └── 执行增量渲染
```

在模块依赖中：

```
modules/sksg (Scene Graph 模块)
    ├── Node (节点基类)
    │   └── revalidate(InvalidationController*, ...) ← 使用失效控制器
    ├── InvalidationController (失效控制器) ← 当前文件
    └── Scene (场景管理)
        └── revalidate() → 创建并使用失效控制器
```

## 主要类与结构体

### InvalidationController

```cpp
class InvalidationController {
public:
    InvalidationController();

    // 记录失效区域
    void inval(const SkRect& r, const SkMatrix& ctm);

    // 重置状态
    void reset();

    // 查询失效信息
    const SkRect& bounds() const { return fBounds; }
    const std::vector<SkRect>& rects() const { return fRects; }

private:
    std::vector<SkRect> fRects;  // 失效矩形列表
    SkRect fBounds;              // 所有失效区域的并集
};
```

**成员变量说明**：

1. **fRects**：
   - 存储所有失效矩形的向量
   - 按失效发生的顺序记录
   - 用于精细化的失效分析和调试

2. **fBounds**：
   - 所有失效矩形的并集（包围框）
   - 快速访问的总失效区域
   - 用于粗粒度的渲染优化

## 公共 API 函数

### 构造函数

```cpp
InvalidationController::InvalidationController()
    : fBounds(SkRect::MakeEmpty()) {}
```

初始化失效边界为空矩形，表示无失效区域。

### inval()

```cpp
void InvalidationController::inval(const SkRect& r, const SkMatrix& ctm);
```

记录一个失效区域。

**参数**：
- `r`：节点的局部坐标系中的失效矩形
- `ctm`：当前变换矩阵（Current Transformation Matrix），用于将局部坐标转换为设备坐标

**使用示例**：
```cpp
InvalidationController ic;

// 节点1在原点处失效（50x50 矩形）
SkRect local_bounds = SkRect::MakeWH(50, 50);
SkMatrix identity = SkMatrix::I();
ic.inval(local_bounds, identity);

// 节点2在 (100, 100) 处失效，带有缩放
SkRect local_bounds2 = SkRect::MakeWH(25, 25);
SkMatrix transform = SkMatrix::Translate(100, 100);
transform.postScale(2, 2);
ic.inval(local_bounds2, transform);  // 失效区域: {100, 100, 150, 150}
```

### reset()

```cpp
void InvalidationController::reset();
```

清空所有失效记录，重置为初始状态。通常在帧开始时调用。

**使用场景**：
```cpp
// 每帧渲染循环
while (running) {
    ic.reset();  // 清空上一帧的失效记录

    // 场景更新（可能产生新的失效）
    scene->revalidate(&ic, SkMatrix::I());

    // 检查是否有失效
    if (!ic.bounds().isEmpty()) {
        // 渲染失效区域
        canvas->clipRect(ic.bounds());
        scene->render(canvas);
    }
}
```

### bounds()

```cpp
const SkRect& bounds() const { return fBounds; }
```

获取所有失效区域的并集。这是最常用的接口，用于快速判断是否需要重绘以及重绘范围。

**返回值**：
- 空矩形 `isEmpty() == true`：无失效，无需重绘
- 非空矩形：需要重绘的最小包围框

### rects()

```cpp
const std::vector<SkRect>& rects() const { return fRects; }
```

获取所有失效矩形的列表。主要用于：
- 调试和可视化失效区域
- 实现更复杂的失效合并策略
- 分析性能瓶颈

## 内部实现细节

### inval() 实现

```cpp
void InvalidationController::inval(const SkRect& r, const SkMatrix& ctm) {
    // 1. 早期退出优化
    if (r.isEmpty()) {
        return;
    }

    // 2. 变换矩形到设备坐标
    SkRect rect = ctm.mapRect(r);

    // 3. 记录失效矩形
    fRects.push_back(rect);

    // 4. 更新总边界
    fBounds.join(rect);
}
```

**关键实现细节**：

1. **空矩形检查**：
   ```cpp
   if (r.isEmpty()) {
       return;
   }
   ```
   - 避免记录无效的失效区域
   - 减少向量增长和边界更新的开销

2. **坐标变换**：
   ```cpp
   SkRect rect = ctm.mapRect(r);
   ```
   - 将节点的局部坐标转换为设备坐标（或画布坐标）
   - `mapRect()` 返回能包含变换后矩形的轴对齐边界框
   - 考虑旋转、缩放、平移等所有变换

   **变换示例**：
   ```cpp
   // 局部矩形
   SkRect local = SkRect::MakeWH(10, 10);

   // 平移变换
   SkMatrix translate = SkMatrix::Translate(50, 50);
   translate.mapRect(local);  // → {50, 50, 60, 60}

   // 旋转变换（45度）
   SkMatrix rotate = SkMatrix::RotateDeg(45);
   rotate.mapRect(local);  // → {-7.07, 0, 7.07, 14.14} (近似)
   ```

3. **记录失效矩形**：
   ```cpp
   fRects.push_back(rect);
   ```
   - 按顺序记录所有失效矩形
   - 不进行合并或去重（保留完整信息）
   - `std::vector` 提供高效的追加操作

4. **更新并集**：
   ```cpp
   fBounds.join(rect);
   ```
   - `join()` 扩展 `fBounds` 以包含新矩形
   - 等价于 `fBounds = union(fBounds, rect)`
   - O(1) 操作，无需遍历现有矩形

### reset() 实现

```cpp
void InvalidationController::reset() {
    fRects.clear();
    fBounds.setEmpty();
}
```

**实现要点**：
- `clear()` 清空向量，但保留已分配的容量（避免重新分配）
- `setEmpty()` 将边界重置为空矩形

**性能特性**：
- 时间复杂度：O(1)（向量容量保留）
- 空间复杂度：O(1)（不释放已分配内存）

## 依赖关系

### 头文件依赖

```cpp
#include "modules/sksg/include/SkSGInvalidationController.h"  // 公共头文件
#include "include/core/SkRect.h"  // 矩形类型
```

**最小依赖设计**：
- 仅依赖 `SkRect`，无其他 Skia 或场景图依赖
- 可以独立测试和使用

### 使用者

- **Node::revalidate()**：所有节点的验证方法接受失效控制器参数
- **Scene::revalidate()**：创建失效控制器并传递给根节点
- **渲染系统**：检查失效边界以优化绘制

### 调用流程示例

```cpp
// 1. 创建失效控制器
InvalidationController ic;

// 2. 验证场景图（收集失效）
scene->revalidate(&ic, SkMatrix::I());

// 3. 节点内部调用 inval()
void SomeNode::onRevalidate(InvalidationController* ic, const SkMatrix& ctm) {
    // ... 计算节点边界 ...
    if (ic && this->hasInval()) {
        ic->inval(this->bounds(), ctm);
    }
    // ... 验证子节点 ...
}

// 4. 检查失效边界
if (!ic.bounds().isEmpty()) {
    // 有失效，执行渲染
}
```

## 设计模式与设计决策

### 收集器模式 (Collector Pattern)

InvalidationController 是一个收集器，遍历过程中收集信息：

```cpp
// 遍历器（节点树）
void traverse(Node* node, Collector* collector) {
    node->process(collector);  // 节点向收集器报告信息
    for (auto child : node->children) {
        traverse(child, collector);
    }
}

// 收集器（失效控制器）
class Collector {
    void collect(Data data) { ... }
    Results getResults() { ... }
};
```

### 值对象模式 (Value Object)

`SkRect` 是值类型，复制成本低：
- 传递 `const SkRect&` 避免复制
- 存储 `SkRect` 值而非指针，简化内存管理

### 缓存友好设计

```cpp
std::vector<SkRect> fRects;  // 连续内存
SkRect fBounds;              // 局部变量
```

- 向量元素连续存储，遍历时缓存友好
- `fBounds` 作为缓存，避免重复计算并集

### 惰性合并策略

不在 `inval()` 时合并矩形，而是记录所有失效：

**优势**：
- `inval()` 操作 O(1)，性能可预测
- 保留完整信息，支持后续优化

**可选优化**（未实现）：
```cpp
// 可能的合并策略
void inval(const SkRect& r, const SkMatrix& ctm) {
    SkRect rect = ctm.mapRect(r);

    // 尝试与最近的矩形合并
    if (!fRects.empty() && fRects.back().intersects(rect)) {
        fRects.back().join(rect);
    } else {
        fRects.push_back(rect);
    }

    fBounds.join(rect);
}
```

当前实现选择简单性而非最优合并。

## 性能考量

### 内存使用

**最坏情况**：
- 每个节点产生一个失效矩形
- 1000 节点场景：`1000 * sizeof(SkRect) ≈ 32 KB`

**典型情况**：
- 仅修改的节点失效（< 10%）
- 100 节点失效：`100 * sizeof(SkRect) ≈ 3.2 KB`

**优化**：
- 向量容量保留，避免频繁重新分配
- `reset()` 不释放内存，适合循环使用

### 时间复杂度

| 操作 | 复杂度 | 说明 |
|------|--------|------|
| `inval()` | O(1) | 追加操作 + 矩形并集 |
| `reset()` | O(1) | 清空向量（不释放内存） |
| `bounds()` | O(1) | 返回缓存值 |
| `rects()` | O(1) | 返回引用 |

### 坐标变换开销

```cpp
SkRect rect = ctm.mapRect(r);
```

**开销**：
- 4 次矩阵-点乘法（4 个角点）
- 计算变换后的边界框
- 约 20-30 条指令

**优化机会**：
- 对于单位矩阵，可以跳过变换
- 对于平移矩阵，使用快速路径

**潜在优化**：
```cpp
void inval(const SkRect& r, const SkMatrix& ctm) {
    if (r.isEmpty()) return;

    SkRect rect;
    if (ctm.isIdentity()) {
        rect = r;  // 快速路径
    } else if (ctm.isTranslate()) {
        rect = r;
        rect.offset(ctm.getTranslateX(), ctm.getTranslateY());
    } else {
        rect = ctm.mapRect(r);  // 完整变换
    }

    fRects.push_back(rect);
    fBounds.join(rect);
}
```

## 相关文件

### 头文件

- **modules/sksg/include/SkSGInvalidationController.h** - 失效控制器的公共接口
- **include/core/SkRect.h** - Skia 矩形类型

### 使用者

- **modules/sksg/include/SkSGNode.h** - 节点基类定义 `revalidate()` 接口
- **modules/sksg/src/SkSGScene.cpp** - 场景类使用失效控制器
- **modules/sksg/src/SkSGRenderNode.cpp** - 渲染节点报告失效

### 测试文件

- **tests/SkSGTest.cpp** - Scene Graph 单元测试

### 使用示例

```cpp
// 完整的增量渲染示例
class AnimationLoop {
    Scene* scene;
    SkCanvas* canvas;
    InvalidationController ic;

    void onFrame() {
        // 1. 重置失效控制器
        ic.reset();

        // 2. 更新动画（修改节点属性）
        animateProperties();

        // 3. 验证场景（收集失效）
        scene->revalidate(&ic, SkMatrix::I());

        // 4. 检查失效边界
        const SkRect& dirty = ic.bounds();
        if (dirty.isEmpty()) {
            // 无变化，跳过渲染
            return;
        }

        // 5. 增量渲染
        canvas->save();
        canvas->clipRect(dirty);  // 仅绘制失效区域
        canvas->clear(SK_ColorWHITE);
        scene->render(canvas);
        canvas->restore();

        // 6. 调试可视化（可选）
        for (const auto& rect : ic.rects()) {
            canvas->drawRect(rect, debug_paint);  // 显示失效矩形
        }
    }
};
```
