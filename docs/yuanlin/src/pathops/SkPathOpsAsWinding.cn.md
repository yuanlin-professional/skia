# SkPathOpsAsWinding

> 源文件: src/pathops/SkPathOpsAsWinding.cpp

## 概述

`SkPathOpsAsWinding` 模块实现了将 Even-Odd 填充规则的路径转换为 Winding(Non-Zero)填充规则的路径的功能。在图形渲染中,有两种常见的填充规则:
- **Even-Odd**: 从点发出射线,计算与路径边界交点的奇偶性
- **Winding(Non-Zero)**: 从点发出射线,计算边界交叉方向的和

该模块通过分析轮廓的包含关系和方向,自动反转需要反转的轮廓,使得使用 Winding 规则渲染时得到与原 Even-Odd 规则相同的结果。这对于需要统一填充规则的渲染后端特别有用。

## 架构位置

`SkPathOpsAsWinding` 在 PathOps 架构中属于高层操作:

```
公共 API (SkPathOps.h)
    ├─ AsWinding ← 当前模块
    ├─ Op (布尔运算)
    └─ Simplify (路径简化)
    ↓
协调层 (SkPathOpsCommon)
    ↓
数据结构层 (SkOpContour, SkOpSegment)
    ↓
几何计算层 (SkPathOpsCurve, SkPathOpsQuad, SkPathOpsCubic)
```

## 主要类与结构体

### Contour (轮廓)

表示路径中的一个轮廓,存储轮廓的边界、方向和层级关系。

**核心枚举:**
```cpp
enum class Direction {
    kCCW = -1,    // 逆时针
    kNone,        // 未确定
    kCW,          // 顺时针
};
```

**成员变量:**
- `vector<Contour*> fChildren`: 子轮廓列表(被当前轮廓包含的轮廓)
- `const SkRect fBounds`: 轮廓的边界矩形
- `SkPoint fMinXY`: 轮廓最左边的点
- `const int fVerbStart`: 轮廓在路径中的起始 verb 索引
- `const int fVerbEnd`: 轮廓在路径中的结束 verb 索引
- `Direction fDirection`: 轮廓的方向(顺时针/逆时针)
- `bool fContained`: 是否被父轮廓包含
- `bool fReverse`: 是否需要反转

### OpAsWinding (转换执行器)

封装转换操作的核心逻辑,提供轮廓分析和反转功能。

**核心枚举:**
```cpp
enum class Edge {
    kInitial,  // 初始化边(查找最左边的点)
    kCompare,  // 比较边(计算绕组)
};
```

**成员变量:**
- `const SkPath& fPath`: 要转换的输入路径

## 公共 API 函数

### AsWinding
```cpp
std::optional<SkPath> AsWinding(const SkPath& path)
```
将 Even-Odd 填充规则的路径转换为 Winding 填充规则。实现步骤:
1. 检查路径有效性和填充类型
2. 如果已是 Winding 规则,直接返回
3. 计算所有轮廓的边界
4. 构建轮廓包含关系树
5. 确定每个轮廓的方向
6. 标记需要反转的轮廓
7. 反转标记的轮廓并重建路径

**早期退出优化:**
- 路径无效返回空
- 已是 Winding 规则返回原路径
- 空路径或凸路径直接修改填充类型
- 只有一个轮廓直接修改填充类型
- 所有轮廓无嵌套直接修改填充类型

## OpAsWinding 主要方法

### contourBounds
```cpp
void contourBounds(vector<Contour>* containers)
```
遍历路径,计算每个轮廓的边界矩形。每个 Move 命令开始一个新轮廓,收集后续的 Line/Quad/Conic/Cubic 命令的边界。

### getDirection
```cpp
Contour::Direction getDirection(Contour& contour)
```
计算轮廓的方向(顺时针或逆时针)。使用有向面积法:
```
signed_area = Σ (y₀ - y₁)(x₀ + x₁) / 2
```
负值表示逆时针,正值表示顺时针。这是计算平面多边形方向的经典算法。

### nextEdge
```cpp
int nextEdge(Contour& contour, Edge edge)
```
根据边类型执行不同操作:
- **Edge::kInitial**: 查找轮廓最左边的点(`fMinXY`)
- **Edge::kCompare**: 计算从 `fMinXY` 发出的水平射线与轮廓的交点绕组

返回绕组值,用于判断包含关系。

### containerContains
```cpp
bool containerContains(Contour& contour, Contour& test)
```
判断 `contour` 是否包含 `test`。算法:
1. 找到 `test` 的最左边点
2. 从该点发出水平射线
3. 计算射线与 `contour` 边界的交点绕组
4. 绕组非零表示包含

### inParent
```cpp
void inParent(Contour& contour, Contour& parent)
```
递归地将轮廓插入正确的父轮廓中。维护轮廓树的层级结构:
1. 查找 parent 的子轮廓是否包含 contour
2. 如果找到,递归插入到该子轮廓
3. 否则,将 parent 的子轮廓中被 contour 包含的移动到 contour 的子列表
4. 将 contour 添加到 parent 的子列表

### checkContainerChildren
```cpp
bool checkContainerChildren(Contour* parent, Contour* child)
```
递归验证轮廓的包含关系是否正确。确保父轮廓确实包含子轮廓。

### markReverse
```cpp
bool markReverse(Contour* parent, Contour* child)
```
递归标记需要反转的轮廓。规则:
- 如果子轮廓与父轮廓方向相同,则需要反转
- 反转后的轮廓方向取反

这确保了嵌套轮廓的方向交替(外-内-外-内...),满足 Winding 规则。

### reverseMarkedContours
```cpp
SkPath reverseMarkedContours(vector<Contour>& contours, SkPathFillType fillType)
```
根据标记重建路径:
1. 遍历所有轮廓
2. 未标记的轮廓直接添加到结果路径
3. 标记的轮廓先添加到临时路径,然后反转后添加到结果

## 辅助函数

### VerbPtCount
```cpp
static unsigned VerbPtCount(SkPathVerb verb)
```
返回 verb 包含的点数(不含起始点):
- Move: 1, Line: 1, Quad: 2, Conic: 2, Cubic: 3, Close: 0

### VerbPtIndex
```cpp
static int VerbPtIndex(SkPathVerb verb)
```
返回 verb 点数组的起始索引:
- Move: 0, Line: 1, Quad: 1, Conic: 1, Cubic: 1, Close: 0

### to_direction
```cpp
static Contour::Direction to_direction(SkScalar dy)
```
根据 Y 方向分量判断方向:dy > 0 为逆时针,dy < 0 为顺时针。

### contains_edge
```cpp
static int contains_edge(const SkPoint pts[4], SkPathVerb verb,
                         SkScalar weight, const SkPoint& edge)
```
计算从 `edge` 点发出的水平射线与曲线的交点绕组。实现步骤:
1. 快速边界检查(上下左右)
2. 计算曲线与水平线 y=edge.fY 的交点参数
3. 过滤 x > edge.fX 的交点
4. 对于 x = edge.fX 的交点,检查曲线是否在射线左侧
5. 计算每个交点的导数方向(上/下)
6. 累加绕组值

### left_edge
```cpp
static SkPoint left_edge(const SkPoint pts[4], SkPathVerb verb, SkScalar weight)
```
查找曲线最左边的点:
1. 如果曲线在 X 方向单调,返回端点中 X 较小的
2. 否则查找 X 方向的极值点
3. 对于三次曲线,可能有多个极值点,选择 X 最小的

### conic_weight
```cpp
static float conic_weight(const SkPath::IterRec& rec)
```
获取圆锥曲线的权重,非圆锥曲线返回 1。

## 内部实现细节

### 有向面积算法

计算轮廓方向使用的有向面积公式:
```
signed_area = Σ (y₀ - yₙ)(x₀ + xₙ)
```
其中 n 是曲线的最后一个点(Line:1, Quad/Conic:2, Cubic:3)。

这个公式是 Shoelace 公式的简化版,只使用端点,忽略控制点。对于封闭曲线,这个近似足够判断整体方向。

### 射线投射算法

判断点是否在轮廓内使用射线投射(Ray Casting)算法:
1. 从点发出水平射线
2. 计算射线与轮廓边界的交点
3. 统计交点的方向(上/下)
4. 绕组 = Σ(方向),非零表示内部

关键细节:
- 跳过射线右侧的交点
- 处理射线与端点重合的情况
- 使用曲线导数判断交点方向

### 轮廓树构建

通过边界矩形的包含关系构建树:
```
sorted (root)
  ├─ contour1 (外)
  │   └─ contour2 (内)
  │       └─ contour3 (外)
  └─ contour4 (外)
      └─ contour5 (内)
```

树的层级对应嵌套深度。

### 方向反转规则

Even-Odd 规则不关心方向,Winding 规则关心方向:
- Even-Odd: 奇数层填充,偶数层不填充
- Winding: 通过方向控制填充

转换规则:
- 第 0 层(外轮廓):保持原方向
- 第 1 层(孔):反转方向(如果与父同向)
- 第 2 层(岛):保持原方向(如果与祖父同向)
- ...

### 边界快速剔除

在 `contains_edge` 中使用多级边界检查:
```cpp
if (bounds.fTop > edge.fY) return 0;      // 边在曲线下方
if (bounds.fBottom <= edge.fY) return 0;  // 边在曲线上方或端点
if (bounds.fLeft >= edge.fX) return 0;    // 曲线完全在边右侧
```

这避免了昂贵的曲线求交计算。

## 依赖关系

### 头文件依赖
- `include/core/SkPath.h`: 路径类
- `include/core/SkPathBuilder.h`: 路径构建器
- `include/pathops/SkPathOps.h`: 公共 API
- `src/pathops/SkPathOpsCubic.h`: 三次曲线
- `src/pathops/SkPathOpsQuad.h`: 二次曲线
- `src/pathops/SkPathOpsConic.h`: 圆锥曲线
- `src/pathops/SkPathOpsCurve.h`: 曲线工具
- `src/core/SkPathPriv.h`: 路径私有工具

### 算法依赖
- **CurveIntercept**: 曲线与水平线交点函数表
- **CurvePointAtT**: 曲线参数求值函数表
- **CurveSlopeAtT**: 曲线导数函数表
- **SkPathPriv::Iterate**: 路径迭代器
- **SkPathPriv::ReverseAddPath**: 反向添加路径

## 设计模式与设计决策

### 树形层级结构

使用树而非平面列表管理轮廓:
- 自然表达嵌套关系
- 简化包含判断
- 支持递归遍历

### 早期退出优化

多级检查避免不必要的计算:
1. 路径有效性
2. 填充类型
3. 凸性
4. 轮廓数量
5. 嵌套关系

### 两阶段处理

分离分析和构建阶段:
1. 分析阶段:构建轮廓树,标记反转
2. 构建阶段:重建路径

这使得逻辑更清晰,便于调试。

### 函数表设计

使用函数指针表处理不同曲线类型:
```cpp
CurveIntercept[(int)verb * 2]
CurvePointAtT[(int)verb]
CurveSlopeAtT[(int)verb]
```

避免了大量的 switch 语句,代码更简洁。

### 边界矩形缓存

预计算并缓存轮廓边界:
- 避免重复计算
- 加速包含判断
- 支持快速剔除

## 性能考量

### 快速剔除

多级快速剔除策略:
1. 边界矩形检查(最快)
2. 水平射线检查
3. 精确交点计算(最慢)

### 缓存最左点

缓存 `fMinXY` 避免重复查找:
- 每个轮廓只计算一次
- 后续包含判断直接使用

### 避免精确交点

使用近似的有向面积判断方向:
- 只使用端点,忽略控制点
- 足够准确且计算快速

### 向量预分配

使用 `vector` 的 `emplace_back`:
- 就地构造,避免拷贝
- 动态增长,无需预知大小

### 引用传递

大部分方法使用引用传递:
```cpp
void inParent(Contour& contour, Contour& parent)
```
避免了对象拷贝。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/pathops/SkPathOps.h` | 被依赖 | 公共 API 声明 |
| `src/pathops/SkPathOpsCubic.h/cpp` | 依赖 | 三次曲线极值查找 |
| `src/pathops/SkPathOpsQuad.h/cpp` | 依赖 | 二次曲线极值查找 |
| `src/pathops/SkPathOpsConic.h/cpp` | 依赖 | 圆锥曲线极值查找 |
| `src/pathops/SkPathOpsCurve.h/cpp` | 依赖 | 曲线函数表 |
| `src/pathops/SkPathOpsPoint.h` | 依赖 | 点类型 |
| `src/pathops/SkPathOpsTypes.h` | 依赖 | 类型定义 |
| `include/core/SkPath.h` | 依赖 | 路径类 |
| `include/core/SkPathBuilder.h` | 依赖 | 路径构建 |
| `src/core/SkPathPriv.h` | 依赖 | 路径私有工具 |
