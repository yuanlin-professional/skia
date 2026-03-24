# SkScanPriv

> 源文件: src/core/SkScanPriv.h

## 概述

`SkScanPriv.h` 是 Skia 扫描转换模块的内部私有头文件,提供了扫描转换算法共享的工具函数和数据结构。该文件包含边缘链表操作模板、裁剪辅助工具和超采样配置,支撑了 `SkScan` 系列算法的实现。

该文件约 79 行代码,虽然代码量较小,但提供了扫描转换的核心基础设施,被多个扫描转换实现文件共享使用。

## 架构位置

```
Skia 扫描转换模块
├── src/core/SkScan.h (公共接口)
├── src/core/SkScanPriv.h (内部工具) ← 当前模块
├── 扫描转换实现
│   ├── SkScan.cpp
│   ├── SkScan_AAAPath.cpp
│   ├── SkScan_Hairline.cpp
│   ├── SkScan_Path.cpp
│   └── SkScan_PathAAClip.cpp
└── 边缘数据结构
    ├── SkEdge.h
    ├── SkAnalyticEdge.h
    └── SkEdgeBuilder.h
```

`SkScanPriv` 位于扫描转换模块的内部工具层,为各种扫描算法提供共享的基础设施。

## 主要类与结构体

### SkScanClipper 类

**继承关系**: 无继承

**关键成员变量**

| 成员 | 类型 | 说明 |
|------|------|------|
| fRectBlitter | SkRectClipBlitter | 矩形裁剪 Blitter |
| fRgnBlitter | SkRgnClipBlitter | 区域裁剪 Blitter |
| fRectClipCheckBlitter | SkRectClipCheckBlitter | Debug 模式裁剪检查 (仅 SK_DEBUG) |
| fBlitter | SkBlitter* | 当前使用的 Blitter 指针 |
| fClipRect | const SkIRect* | 裁剪矩形指针 |

### 宏定义

```cpp
#define SK_SUPERSAMPLE_SHIFT 2
```

**说明**: 定义了超采样的位移量,用于传统扫描转换算法。

- 值为 2 表示 2² = 4 倍超采样
- 在 Y 方向上每像素使用 4 条扫描线
- 扫描线位置: y = 1/8 + n/4 (n = 0, 1, 2, ...)

## 公共 API 函数

### SkScanClipper 构造函数

```cpp
SkScanClipper(
    SkBlitter* blitter,          // 目标 Blitter
    const SkRegion* clip,        // 裁剪区域 (可为 nullptr)
    const SkIRect& bounds,       // 绘制边界
    bool skipRejectTest = false, // 跳过完全拒绝测试
    bool boundsPreClipped = false // 边界已预裁剪
);
```

**功能**: 根据裁剪区域类型创建合适的裁剪 Blitter 包装器。

**裁剪策略**:
- 无裁剪: 直接使用原始 Blitter
- 矩形裁剪: 使用 `SkRectClipBlitter`
- 复杂裁剪: 使用 `SkRgnClipBlitter`

### SkScanClipper 访问器

```cpp
SkBlitter* getBlitter() const;      // 获取当前 Blitter
const SkIRect* getClipRect() const; // 获取裁剪矩形
```

### 区域 Blit 函数

```cpp
void sk_blit_above(SkBlitter* blitter, const SkIRect& avoid, const SkRegion& clip);
void sk_blit_below(SkBlitter* blitter, const SkIRect& avoid, const SkRegion& clip);
```

**功能**: 渲染裁剪区域中避开特定矩形的上方和下方区域。

**应用场景**: 反向填充 (inverse fill) 时需要填充路径外部区域。

## 内部实现细节

### 边缘链表操作模板

#### remove_edge 模板

```cpp
template<class EdgeType>
static inline void remove_edge(EdgeType* edge) {
    edge->fPrev->fNext = edge->fNext;
    edge->fNext->fPrev = edge->fPrev;
}
```

**功能**: 从双向链表中移除边缘节点

**复杂度**: O(1)

**前置条件**:
- `edge->fPrev` 和 `edge->fNext` 必须非空
- 边缘必须在链表中

#### insert_edge_after 模板

```cpp
template<class EdgeType>
static inline void insert_edge_after(EdgeType* edge, EdgeType* afterMe) {
    edge->fPrev = afterMe;
    edge->fNext = afterMe->fNext;
    afterMe->fNext->fPrev = edge;
    afterMe->fNext = edge;
}
```

**功能**: 在指定节点后插入新边缘

**复杂度**: O(1)

**操作顺序**:
1. 设置新边缘的前驱
2. 设置新边缘的后继
3. 更新后继节点的前驱
4. 更新前驱节点的后继

#### backward_insert_edge_based_on_x 模板

```cpp
template<class EdgeType>
void backward_insert_edge_based_on_x(EdgeType* edge) {
    SkFixed x = edge->fX;
    EdgeType* prev = edge->fPrev;
    while (prev->fPrev && prev->fX > x) {
        prev = prev->fPrev;
    }
    if (prev->fNext != edge) {
        remove_edge(edge);
        insert_edge_after(edge, prev);
    }
}
```

**功能**: 将边缘向左移动到按 X 坐标排序的正确位置

**算法**: 向后线性搜索插入点

**应用场景**: 当边缘 X 坐标更新后需要重新排序

**时间复杂度**: O(n),其中 n 为向左移动的边缘数量

#### backward_insert_start 模板

```cpp
template<class EdgeType>
EdgeType* backward_insert_start(EdgeType* prev, SkFixed x) {
    while (prev->fPrev && prev->fX > x) {
        prev = prev->fPrev;
    }
    return prev;
}
```

**功能**: 找到批量插入新边缘的起始位置

**优化点**:
- 从右侧开始向左搜索
- 避免每次插入都从左端开始
- 为批量插入提供更好的起点

**注释说明**:
- 当前实现: 从右向左线性搜索
- 潜在优化: 从上次插入位置开始,或使用二分搜索

### 模板设计原理

使用模板而非虚函数的原因:

1. **零开销抽象**: 编译时多态,无虚表开销
2. **内联优化**: 编译器可完全内联模板函数
3. **类型安全**: 编译时类型检查
4. **代码复用**: 支持 `SkEdge`、`SkAnalyticEdge` 等多种边缘类型

**类型要求** (Duck Typing):

边缘类型必须提供以下成员:
```cpp
class EdgeType {
    EdgeType* fPrev;  // 前驱指针
    EdgeType* fNext;  // 后继指针
    SkFixed fX;       // X 坐标 (用于排序)
};
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 | 头文件 |
|------|------|--------|
| SkBlitter | Blitter 基类 | src/core/SkBlitter.h |
| SkScan | 扫描转换接口 | src/core/SkScan.h |
| SkPath | 路径数据 | include/core/SkPath.h |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| SkScan_AAAPath.cpp | 使用边缘操作模板和 `SkScanClipper` |
| SkScan_Path.cpp | 使用边缘操作模板和超采样宏 |
| SkScan_Hairline.cpp | 使用 `SkScanClipper` 进行裁剪 |
| SkScan_PathAAClip.cpp | 使用 `sk_blit_above`/`sk_blit_below` |

## 设计模式与设计决策

### 1. 模板编程 (Template Metaprogramming)

**设计决策**: 使用模板函数而非虚函数实现边缘操作

**优点**:
- 编译时多态,无运行时开销
- 支持多种边缘类型 (SkEdge, SkAnalyticEdge, SkAnalyticQuadraticEdge, SkAnalyticCubicEdge)
- 编译器可完全内联

**缺点**:
- 代码膨胀 (每种类型生成一份实例)
- 编译时间增加

### 2. 适配器模式

`SkScanClipper` 作为适配器,根据裁剪类型包装不同的 Blitter:

```
SkBlitter (原始)
    ↓
SkScanClipper (适配器)
    ↓
SkRectClipBlitter / SkRgnClipBlitter (具体裁剪)
```

### 3. 策略模式

裁剪策略根据 `SkRegion` 的复杂度动态选择:
- **简单矩形**: `SkRectClipBlitter` (快速路径)
- **复杂区域**: `SkRgnClipBlitter` (通用路径)

### 4. RAII 模式

`SkScanClipper` 通过对象生命周期管理裁剪 Blitter 的创建和销毁:

```cpp
{
    SkScanClipper clipper(blitter, clip, bounds);
    // 使用 clipper.getBlitter() 进行渲染
    // 离开作用域自动清理
}
```

### 5. 内联优化

所有模板函数和辅助函数都声明为 `static inline`,确保编译器内联优化热点路径。

## 性能考量

### 1. 模板内联

边缘链表操作是扫描转换的热点路径,使用模板 + inline 确保零开销:

```cpp
// 编译后等价于直接代码,无函数调用开销
remove_edge(edge);
// ↓
edge->fPrev->fNext = edge->fNext;
edge->fNext->fPrev = edge->fPrev;
```

### 2. 超采样精度权衡

`SK_SUPERSAMPLE_SHIFT = 2` 的选择:

| Shift | 倍数 | 质量 | 性能 |
|-------|------|------|------|
| 1 | 2x | 低 | 快 |
| 2 | 4x | 中 | 中 |
| 3 | 8x | 高 | 慢 |
| 4 | 16x | 极高 | 极慢 |

选择 4x 平衡质量和性能。

### 3. 裁剪 Blitter 选择

`SkScanClipper` 根据裁剪复杂度选择实现:

| 裁剪类型 | Blitter | 开销 |
|----------|---------|------|
| 无裁剪 | 原始 Blitter | 零开销 |
| 矩形裁剪 | SkRectClipBlitter | 低开销 (边界检查) |
| 复杂裁剪 | SkRgnClipBlitter | 高开销 (区域查询) |

### 4. 边缘插入优化

`backward_insert_start` 的优化策略:

**当前实现** (从右向左):
- 适合新边缘 X 坐标接近当前最大 X 的场景
- 扫描转换常见模式 (边缘按 Y 坐标批量插入)

**潜在优化** (注释建议):
- 缓存上次插入位置
- 对大量边缘使用二分搜索

### 5. 避免虚函数调用

在性能关键的边缘操作中使用模板而非虚函数,避免虚表查找开销 (约 5-10 个 CPU 周期)。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| src/core/SkScan.h | 配对公共接口 | 扫描转换公共 API |
| src/core/SkScan.cpp | 使用者 | 基础扫描转换实现 |
| src/core/SkScan_AAAPath.cpp | 使用者 | 解析式抗锯齿实现 |
| src/core/SkScan_Path.cpp | 使用者 | 传统路径扫描实现 |
| src/core/SkScan_Hairline.cpp | 使用者 | 线条渲染实现 |
| src/core/SkBlitter.h | 依赖 | Blitter 基类定义 |
| src/core/SkEdge.h | 配合使用 | 传统边缘数据结构 |
| src/core/SkAnalyticEdge.h | 配合使用 | 解析式边缘数据结构 |
| src/core/SkRectClipBlitter.h | 内部使用 | 矩形裁剪 Blitter |
| src/core/SkRgnClipBlitter.h | 内部使用 | 区域裁剪 Blitter |
