# SkCanvasStack

> 源文件
> - src/utils/SkCanvasStack.h
> - src/utils/SkCanvasStack.cpp

## 概述

`SkCanvasStack` 是一个特殊的 Canvas 管理类，继承自 `SkNWayCanvas`，用于管理多个分层 Canvas 的 Z 轴顺序和裁剪关系。与 `SkNWayCanvas` 不同，它持有子 Canvas 的所有权，并自动处理层级间的遮挡裁剪，确保上层 Canvas 完全遮挡下层对应区域。

## 架构位置

该类位于 Skia 工具层（`src/utils/`），作为 Canvas 系统的高级抽象。它主要服务于：
- 分层绘制场景（如多文档页面、图层管理）
- 需要 Z 轴顺序管理的复合 Canvas 系统
- 图层遮挡和裁剪自动化处理

继承关系：
```
SkCanvas
   ↑
SkNWayCanvas (N-way 转发)
   ↑
SkCanvasStack (所有权 + Z 顺序管理)
```

## 主要类与结构体

### SkCanvasStack 类

继承自 `SkNWayCanvas`，提供带所有权管理的 Canvas 栈功能。

**核心特性：**
1. **所有权管理**：持有子 Canvas 的 `unique_ptr`，析构时自动释放
2. **Z 顺序裁剪**：自动计算层间遮挡关系，裁剪被遮挡区域
3. **坐标偏移**：每个子 Canvas 可以有独立的原点偏移

### CanvasData 结构体

存储每个子 Canvas 的元数据：

```cpp
struct CanvasData {
    SkIPoint origin;                    // Canvas 的原点偏移
    SkRegion requiredClip;              // 该层的必需裁剪区域
    std::unique_ptr<SkCanvas> ownedCanvas;  // 持有的 Canvas 对象
};
```

**Trivially Relocatable 优化：**
通过 `sk_is_trivially_relocatable` 标记，允许编译器优化内存移动操作。

## 公共 API 函数

### 构造与析构
```cpp
SkCanvasStack(int width, int height)
```
创建指定尺寸的 Canvas 栈。

```cpp
~SkCanvasStack() override
```
析构函数，调用 `removeAll()` 释放所有子 Canvas。

### Canvas 管理
```cpp
void pushCanvas(std::unique_ptr<SkCanvas>, const SkIPoint& origin)
```
将新 Canvas 推入栈顶，指定其原点偏移。这是添加子 Canvas 的唯一合法方式。

**处理流程：**
1. 计算新 Canvas 的边界
2. 添加到父类的转发列表
3. 创建 `CanvasData` 并存储
4. 更新所有下层 Canvas 的 `requiredClip`（减去被遮挡区域）

```cpp
void removeAll() override
```
移除所有子 Canvas，先调用父类清理转发列表，再清空 `fCanvasData`。

### 禁用的接口
```cpp
void addCanvas(SkCanvas*) override     // 标记为无效操作
void removeCanvas(SkCanvas*) override  // 标记为无效操作
```
从 `SkNWayCanvas` 继承的接口被禁用，因为 `SkCanvasStack` 要求使用 `pushCanvas` 来管理所有权。

## 内部实现细节

### Z 顺序裁剪机制

**核心思想：**
当新 Canvas 被添加时，它会遮挡下层对应位置的区域，需要从下层的 `requiredClip` 中减去被遮挡部分。

**算法实现（`pushCanvas`）：**
```cpp
for (int i = fList.size() - 1; i > 0; --i) {
    SkIRect localBounds = canvasBounds;
    localBounds.offset(origin - fCanvasData[i-1].origin);  // 坐标转换

    fCanvasData[i-1].requiredClip.op(localBounds, SkRegion::kDifference_Op);  // 差集运算
    fList[i-1]->clipRegion(fCanvasData[i-1].requiredClip);  // 应用裁剪
}
```

**坐标系转换：**
每个 Canvas 有独立的原点，需要将上层 Canvas 的边界转换到下层的本地坐标系。

### 矩阵变换处理

**特殊性：**
`setMatrix` 是覆盖操作（非预串联），需要特殊处理原点偏移。

**实现（`didSetM44`）：**
```cpp
for (int i = 0; i < fList.size(); ++i) {
    fList[i]->setMatrix(
        SkM44::Translate(-origin.x(), -origin.y()) * mx
    );
}
```

为每个子 Canvas 预先应用其原点的负偏移，确保坐标系正确对齐。

### 裁剪操作处理

**四种几何裁剪：**
- `onClipRect` - 矩形裁剪
- `onClipRRect` - 圆角矩形裁剪
- `onClipPath` - 路径裁剪
- `onClipRegion` - 区域裁剪

**统一流程：**
1. 调用父类方法转发裁剪到所有子 Canvas
2. 调用 `clipToZOrderedBounds()` 重新应用 Z 顺序裁剪

**特殊情况（着色器裁剪）：**
`onClipShader` 不改变裁剪边界，无需更新 Z 顺序裁剪。

### 区域裁剪的坐标转换

`onClipRegion` 需要手动处理坐标转换：
```cpp
for (int i = 0; i < fList.size(); ++i) {
    SkRegion tempRegion;
    deviceRgn.translate(-origin.x(), -origin.y(), &tempRegion);  // 转换到本地坐标
    tempRegion.op(requiredClip, SkRegion::kIntersect_Op);        // 与必需裁剪求交
    fList[i]->clipRegion(tempRegion, op);
}
```

## 依赖关系

**直接依赖：**
- `include/utils/SkNWayCanvas.h` - 父类，提供多 Canvas 转发机制
- `include/core/SkCanvas.h` - Canvas 基类
- `include/core/SkRegion.h` - 区域裁剪计算
- `include/private/base/SkTArray.h` - 动态数组容器

**间接依赖：**
- 裁剪栈系统
- 矩阵变换系统
- 区域运算库

## 设计模式与设计决策

### 所有权语义
通过 `std::unique_ptr` 明确表达所有权转移，避免悬垂指针和内存泄漏。这与 `SkNWayCanvas` 的非所有权语义形成对比。

### 模板方法模式
重写 `onClip*` 系列虚函数，在父类转发基础上增加 Z 顺序裁剪逻辑。

### 惰性裁剪更新
裁剪操作后立即调用 `clipToZOrderedBounds()` 更新所有层，保证状态一致性。

### 不变式维护
代码中多处使用 `SkASSERT(fList.size() == fCanvasData.size())`，确保转发列表和元数据数组始终同步。

### 接口限制
禁用 `addCanvas` 和 `removeCanvas`，强制使用 `pushCanvas`，避免所有权混乱。

## 性能考量

### 时间复杂度
- **pushCanvas**: O(n * m)，其中 n 是现有 Canvas 数量，m 是区域运算复杂度
- **裁剪操作**: O(n)，需要遍历所有子 Canvas
- **矩阵设置**: O(n)，需要更新所有子 Canvas

### 空间复杂度
- O(n)，存储 n 个 Canvas 及其元数据
- 每个 `CanvasData` 包含一个 `SkRegion`（可能较大）

### 性能瓶颈
1. **区域运算开销**：差集和交集运算在复杂区域上成本较高
2. **裁剪栈状态同步**：每次裁剪操作触发全局更新
3. **坐标转换**：频繁的原点偏移计算

### 优化策略
1. **Trivially Relocatable 优化**：允许高效的数组重新分配
2. **惰性计算**：只在需要时计算裁剪区域
3. **避免小对象分配**：使用 `TArray` 而非 `vector`

### 适用场景
- 层数较少（< 10 层）的场景
- 需要精确 Z 顺序遮挡的图层系统
- 文档生成等非实时场景

## 相关文件

**核心依赖：**
- `include/utils/SkNWayCanvas.h` - 父类
- `include/core/SkRegion.h` - 区域运算
- `include/core/SkCanvas.h` - Canvas 基类

**可能使用此类的场景：**
- 多页文档渲染
- 图层管理系统
- 复合绘制场景
- 测试和调试工具
