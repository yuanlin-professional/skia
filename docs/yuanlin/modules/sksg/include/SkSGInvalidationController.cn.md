# SkSGInvalidationController

> 源文件: modules/sksg/include/SkSGInvalidationController.h

## 概述

SkSGInvalidationController 是 Skia 场景图系统中负责追踪和管理失效（invalidation）事件的核心组件。它作为失效事件的接收器，收集需要重绘的脏区域（dirty regions），为增量渲染提供支持。

该类采用区域累积策略，记录所有失效的矩形区域，并维护一个总体边界框。这使得渲染系统可以只重绘实际改变的区域，而不是整个画布，显著提升动画和交互场景的性能。

## 架构位置

在 Skia 场景图架构中的位置：

- **角色定位**: 失效事件收集器和管理器
- **协作关系**:
  - 被 Node::revalidate() 调用，报告失效区域
  - 被 Scene 类使用，管理场景级别的失效
  - 与变换矩阵配合，将本地坐标失效区域转换到全局坐标
- **模块位置**: modules/sksg，场景图核心支持模块
- **生命周期**: 通常在渲染循环的开始创建或重置，收集失效后供渲染系统查询

该类不参与场景图的层次结构，而是作为外部工具配合节点系统工作。

## 主要类与结构体

### InvalidationController 类

```cpp
class InvalidationController {
public:
    InvalidationController();
    InvalidationController(const InvalidationController&) = delete;
    InvalidationController& operator=(const InvalidationController&) = delete;

    // 记录失效区域
    void inval(const SkRect&, const SkMatrix& ctm = SkMatrix::I());

    // 查询总边界
    const SkRect& bounds() const { return fBounds; }

    // 迭代器接口
    auto begin() const { return fRects.cbegin(); }
    auto end()   const { return fRects.cend(); }

    // 重置状态
    void reset();

private:
    std::vector<SkRect> fRects;   // 失效矩形列表
    SkRect              fBounds;  // 总边界框
};
```

**关键成员**:
- `fRects`: 存储所有失效矩形区域的向量
- `fBounds`: 所有失效区域的联合边界框

**设计特点**:
- 禁止拷贝构造和赋值（删除的拷贝构造函数）
- 轻量级值类型，通常栈分配
- 提供 STL 风格的迭代器接口

## 公共 API 函数

### 构造函数
```cpp
InvalidationController();
```
默认构造函数，初始化空的失效状态。fRects 为空向量，fBounds 为空矩形。

### inval()
```cpp
void inval(const SkRect& rect, const SkMatrix& ctm = SkMatrix::I());
```
记录一个失效区域。

**参数**:
- `rect`: 失效矩形，通常为节点在本地坐标系的边界
- `ctm`: 当前变换矩阵（Current Transformation Matrix），默认为单位矩阵

**行为**:
1. 将 rect 通过 ctm 变换到全局坐标系
2. 将变换后的矩形添加到 fRects
3. 更新 fBounds 以包含新矩形（通过 SkRect::join()）

**用途**:
- 节点重验证时报告自己的失效区域
- 支持嵌套变换的正确失效追踪
- 累积多个失效事件供后续批量处理

### bounds()
```cpp
const SkRect& bounds() const;
```
返回所有失效区域的联合边界框。

**返回值**: 包含所有失效矩形的最小边界矩形

**用途**:
- 快速判断是否有失效（bounds.isEmpty()）
- 确定需要重绘的总区域
- 优化裁剪和视口计算

### begin() / end()
```cpp
auto begin() const { return fRects.cbegin(); }
auto end()   const { return fRects.cend(); }
```
提供 STL 风格的常量迭代器，遍历所有失效矩形。

**用途**:
- 支持范围 for 循环：`for (const auto& rect : controller) { ... }`
- 精细化失效处理（如瓦片渲染）
- 调试和可视化失效区域

### reset()
```cpp
void reset();
```
清除所有失效记录，重置为初始状态。

**行为**:
- 清空 fRects 向量
- 重置 fBounds 为空矩形

**用途**:
- 在渲染循环开始前重置
- 在处理完失效后准备下一帧
- 避免重复分配，复用控制器对象

## 内部实现细节

### 矩形变换和累积

inval() 方法的典型实现逻辑：
```cpp
void inval(const SkRect& rect, const SkMatrix& ctm) {
    SkRect transformedRect;
    ctm.mapRect(&transformedRect, rect);
    fRects.push_back(transformedRect);
    fBounds.join(transformedRect);
}
```

关键点：
- 使用 SkMatrix::mapRect() 进行矩形变换
- 变换后的矩形可能变大（旋转、倾斜）
- join() 操作扩展 fBounds 以包含新矩形

### 空矩形处理

通常会跳过空矩形的记录：
```cpp
if (rect.isEmpty()) return;
```
这避免了无效的失效通知和额外的存储开销。

### 迭代器类型推导

begin() 和 end() 使用 auto 返回类型，实际为：
```cpp
std::vector<SkRect>::const_iterator
```
这提供了灵活性，vector 实现改变时无需修改接口。

## 依赖关系

### 核心依赖
- **include/core/SkMatrix.h**: 变换矩阵
- **include/core/SkRect.h**: 矩形定义
- **include/core/SkTypes.h**: Skia 基础类型

### 标准库
- **<vector>**: 动态数组存储失效矩形

### 被使用场景
- **Node::revalidate()**: 节点重验证时报告失效
- **Scene**: 场景管理失效和渲染触发
- **Animator**: 动画更新后记录失效
- **自定义渲染循环**: 增量渲染优化

## 设计模式与设计决策

### 1. 不可拷贝设计
删除拷贝构造函数和赋值运算符，因为：
- 控制器通常作为单例或栈对象使用
- 拷贝 vector 可能开销较大且无意义
- 防止意外拷贝导致的失效丢失

### 2. 值语义和栈分配
设计为值类型而非引用计数对象：
- 生命周期明确（通常在单次渲染循环内）
- 避免堆分配和引用计数开销
- 简化使用模式

### 3. 累积策略而非合并
存储所有失效矩形而非合并成单一区域：
- 支持精细化渲染（瓦片渲染、部分更新）
- 避免过度失效（合并可能产生大量空白区域）
- 提供更多信息供高级渲染优化

同时提供 bounds() 简化常见场景的使用。

### 4. STL 风格接口
提供 begin()/end() 而非自定义迭代器：
- 与标准库算法兼容
- 支持现代 C++ 范围 for 循环
- 降低学习成本

### 5. 变换集成
inval() 接受变换矩阵参数：
- 支持嵌套变换的场景图
- 自动处理坐标系转换
- 简化调用者逻辑

## 性能考量

### 1. 动态内存分配
vector 可能触发多次重新分配：
- 初始容量为 0，按需增长
- 可考虑在构造时 reserve() 预分配
- 典型场景失效数量不多，影响有限

### 2. 矩形变换开销
每次 inval() 调用都进行矩阵变换：
- 矩阵乘法计算相对便宜
- 通常失效数量远小于渲染开销
- 正确性优先于微优化

### 3. 边界框更新
join() 操作为 O(1) 简单比较：
- 每次 inval 更新一次
- 相比存储/渲染开销可忽略

### 4. 迭代器性能
常量迭代器无拷贝开销：
- 遍历为 O(n)，n 为失效矩形数量
- 缓存友好（连续内存）

### 5. 重置开销
reset() 清空 vector 但不释放内存：
- 复用已分配的容量
- 对于重复渲染循环效率高
- 避免频繁分配/释放

### 6. 优化机会
可能的优化策略：
- 相邻矩形合并减少数量
- 过小矩形阈值过滤
- 基于瓦片的失效跟踪
- 当前实现保持简单，适合大多数场景

## 相关文件

### 头文件
- **include/core/SkMatrix.h**: 变换矩阵定义
- **include/core/SkRect.h**: 矩形操作 API

### 实现文件
- **modules/sksg/src/SkSGInvalidationController.cpp**: 类实现

### 使用场景
- **modules/sksg/include/SkSGNode.h**: Node::revalidate() 接收控制器参数
- **modules/sksg/include/SkSGScene.h**: Scene 管理失效和渲染
- **modules/skottie**: Lottie 动画增量更新

### 相关概念
- **脏矩形（Dirty Rectangle）**: 图形系统中的经典增量渲染技术
- **失效区域（Invalidation Region）**: UI 框架中的重绘优化
- **瓦片渲染（Tile-based Rendering）**: 基于区域的渲染优化

### 示例用法
```cpp
sksg::InvalidationController ic;

// 场景图重验证
scene_root->revalidate(&ic, SkMatrix::I());

// 检查是否有失效
if (!ic.bounds().isEmpty()) {
    // 只重绘失效区域
    canvas->clipRect(ic.bounds());
    scene_root->render(canvas);
}

// 下一帧重置
ic.reset();
```
