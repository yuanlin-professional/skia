# SkPathBuilder

> 源文件
> - include/core/SkPathBuilder.h
> - src/core/SkPathBuilder.cpp

## 概述

`SkPathBuilder` 是 Skia 路径构建系统的核心类,提供了高效、灵活的路径构造接口。该类支持链式调用、增量构建、变换操作等功能,是创建复杂路径的首选工具。

相比直接操作 `SkPath`,`SkPathBuilder` 提供了更好的性能(避免中间状态缓存失效)和更清晰的语义(可变构建器 vs 不可变路径)。构建完成后可通过 `detach()` 或 `snapshot()` 生成最终的 `SkPath` 对象。

## 架构位置

`SkPathBuilder` 位于 Skia 路径系统的构建层:

```
include/core/
├── SkPath (不可变路径)
├── SkPathBuilder (可变构建器) ← 当前组件
├── SkPathTypes (类型定义)
└── SkMatrix (变换矩阵)

src/core/
├── SkPathBuilder.cpp (实现)
├── SkPathData.h (数据容器)
└── SkPathPriv.h (私有辅助)
```

构建流程:
```
SkPathBuilder (构建)
    ↓
  snapshot() / detach()
    ↓
SkPathData (数据)
    ↓
SkPath (路径)
```

## 主要类与结构体

### SkPathBuilder 类

**继承关系**: 无(独立类)

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fPts | PointsArray | 点数组(动态) |
| fVerbs | VerbsArray | 动词数组(动态) |
| fConicWeights | ConicWeightsArray | 圆锥权重数组(动态) |
| fFillType | SkPathFillType | 填充类型 |
| fIsVolatile | bool | 是否易变 |
| fConvexity | SkPathConvexity | 凸性 |
| fSegmentMask | unsigned | 分段掩码 |
| fLastMoveIndex | int | 最后 Move 动词索引 |
| fType | SkPathIsAType | 特殊形状类型 |
| fIsA | SkPathIsAData | 形状元数据 |

**类型定义**:

```cpp
using PointsArray = skia_private::STArray<4, SkPoint>;
using VerbsArray = skia_private::STArray<4, SkPathVerb>;
using ConicWeightsArray = skia_private::STArray<2, float>;
```

**枚举类型**:

```cpp
enum class ArcSize {
    kSmall_ArcSize,  // 小弧
    kLarge_ArcSize,  // 大弧
};

enum class Reserve {
    kExact,  // 精确预留
    kGrow,   // 允许增长
};

enum class DumpFormat {
    kDecimal,  // 十进制
    kHex,      // 十六进制
};
```

## 公共 API 函数

### 构造和配置

```cpp
// 默认构造(空路径)
SkPathBuilder();

// 指定填充类型
explicit SkPathBuilder(SkPathFillType fillType);

// 从现有路径构造
explicit SkPathBuilder(const SkPath& path);

// 拷贝和移动
SkPathBuilder(const SkPathBuilder&);
SkPathBuilder& operator=(const SkPathBuilder&);
SkPathBuilder(SkPathBuilder&&);
SkPathBuilder& operator=(SkPathBuilder&&);

// 从路径赋值
SkPathBuilder& operator=(const SkPath&);
```

### 属性设置

```cpp
// 设置填充类型
SkPathBuilder& setFillType(SkPathFillType ft);

// 设置易变标志
SkPathBuilder& setIsVolatile(bool isVolatile);

// 重置为空
SkPathBuilder& reset();
```

### 基本路径操作

```cpp
// 移动到点
SkPathBuilder& moveTo(SkPoint point);
SkPathBuilder& moveTo(SkScalar x, SkScalar y);

// 直线
SkPathBuilder& lineTo(SkPoint pt);
SkPathBuilder& lineTo(SkScalar x, SkScalar y);

// 二次贝塞尔
SkPathBuilder& quadTo(SkPoint pt1, SkPoint pt2);
SkPathBuilder& quadTo(SkScalar x1, SkScalar y1,
                      SkScalar x2, SkScalar y2);

// 圆锥曲线
SkPathBuilder& conicTo(SkPoint pt1, SkPoint pt2,
                       SkScalar w);
SkPathBuilder& conicTo(SkScalar x1, SkScalar y1,
                       SkScalar x2, SkScalar y2,
                       SkScalar w);

// 三次贝塞尔
SkPathBuilder& cubicTo(SkPoint pt1, SkPoint pt2, SkPoint pt3);
SkPathBuilder& cubicTo(SkScalar x1, SkScalar y1,
                       SkScalar x2, SkScalar y2,
                       SkScalar x3, SkScalar y3);

// 闭合轮廓
SkPathBuilder& close();
```

### 相对路径操作

```cpp
// 相对移动
SkPathBuilder& rMoveTo(SkVector pt);
SkPathBuilder& rMoveTo(SkScalar dx, SkScalar dy);

// 相对直线
SkPathBuilder& rLineTo(SkVector pt);
SkPathBuilder& rLineTo(SkScalar dx, SkScalar dy);

// 相对二次曲线
SkPathBuilder& rQuadTo(SkVector pt1, SkVector pt2);
SkPathBuilder& rQuadTo(SkScalar dx1, SkScalar dy1,
                       SkScalar dx2, SkScalar dy2);

// 相对圆锥曲线
SkPathBuilder& rConicTo(SkVector p1, SkVector p2,
                        SkScalar w);

// 相对三次曲线
SkPathBuilder& rCubicTo(SkVector pt1, SkVector pt2,
                        SkVector pt3);
```

### 弧线操作

```cpp
// 椭圆弧(起止角度)
SkPathBuilder& arcTo(const SkRect& oval,
                     SkScalar startAngleDeg,
                     SkScalar sweepAngleDeg,
                     bool forceMoveTo);

// 相对椭圆弧(SVG 风格)
SkPathBuilder& arcTo(SkPoint r, SkScalar xAxisRotate,
                     ArcSize largeArc,
                     SkPathDirection sweep,
                     SkPoint xy);

SkPathBuilder& rArcTo(SkPoint r, SkScalar xAxisRotate,
                      ArcSize largeArc,
                      SkPathDirection sweep,
                      SkVector dxdy);

// 圆角(PostScript 风格)
SkPathBuilder& arcTo(SkPoint p1, SkPoint p2,
                     SkScalar radius);

// 添加完整弧
SkPathBuilder& addArc(const SkRect& oval,
                      SkScalar startAngleDeg,
                      SkScalar sweepAngleDeg);
```

### 标准形状

```cpp
// 矩形
SkPathBuilder& addRect(const SkRect&,
                       SkPathDirection,
                       unsigned startIndex);
SkPathBuilder& addRect(const SkRect& rect,
                       SkPathDirection dir = SkPathDirection::kDefault);

// 椭圆
SkPathBuilder& addOval(const SkRect&,
                       SkPathDirection,
                       unsigned startIndex);
SkPathBuilder& addOval(const SkRect& oval,
                       SkPathDirection dir = SkPathDirection::kDefault);

// 圆角矩形
SkPathBuilder& addRRect(const SkRRect& rrect,
                        SkPathDirection,
                        unsigned start);
SkPathBuilder& addRRect(const SkRRect& rrect,
                        SkPathDirection dir = SkPathDirection::kDefault);

// 圆
SkPathBuilder& addCircle(SkPoint center, float radius,
                         SkPathDirection dir = SkPathDirection::kDefault);
SkPathBuilder& addCircle(float x, float y, float radius,
                         SkPathDirection dir = SkPathDirection::kDefault);

// 多边形
SkPathBuilder& addPolygon(SkSpan<const SkPoint> pts,
                          bool close);

// 直线
SkPathBuilder& addLine(SkPoint a, SkPoint b);

// 折线
SkPathBuilder& polylineTo(SkSpan<const SkPoint> pts);
```

### 路径合并

```cpp
// 添加路径(带偏移)
SkPathBuilder& addPath(const SkPath& src,
                       SkScalar dx, SkScalar dy,
                       SkPath::AddPathMode mode = SkPath::kAppend_AddPathMode);

// 添加路径(带变换)
SkPathBuilder& addPath(const SkPath& src,
                       const SkMatrix& matrix,
                       SkPath::AddPathMode mode = SkPath::kAppend_AddPathMode);

// 添加路径
SkPathBuilder& addPath(const SkPath& src,
                       SkPath::AddPathMode mode = SkPath::kAppend_AddPathMode);
```

### 变换和修改

```cpp
// 偏移
SkPathBuilder& offset(SkScalar dx, SkScalar dy);

// 变换
SkPathBuilder& transform(const SkMatrix& matrix);

// 反转填充类型
SkPathBuilder& toggleInverseFillType();
```

### 查询和访问

```cpp
// 填充类型
SkPathFillType fillType() const;

// 边界计算
std::optional<SkRect> computeFiniteBounds() const;
std::optional<SkRect> computeTightBounds() const;
SkRect computeBounds() const;  // DEPRECATED

// 判断
bool isEmpty() const;
bool isInverseFillType() const;
bool isFinite() const;
bool contains(SkPoint) const;

// 点访问
SkSpan<const SkPoint> points() const;
SkSpan<const SkPathVerb> verbs() const;
SkSpan<const float> conicWeights() const;
int countPoints() const;

std::optional<SkPoint> getLastPt() const;
void setPoint(size_t index, SkPoint p);
void setLastPoint(SkPoint p);
```

### 生成路径

```cpp
// 快照(保留构建器)
SkPath snapshot(const SkMatrix* mx = nullptr) const;
sk_sp<SkPathData> snapshotData() const;

// 分离(重置构建器)
SkPath detach(const SkMatrix* mx = nullptr);
sk_sp<SkPathData> detachData();
```

### 预留空间

```cpp
// 预留空间(提升性能)
void incReserve(int extraPtCount,
                int extraVerbCount,
                int extraConicCount);
void incReserve(int extraPtCount);
```

### 调试和工具

```cpp
// 迭代器
SkPathIter iter() const;

// 字符串转储
SkString dumpToString(DumpFormat = DumpFormat::kDecimal) const;
void dump(DumpFormat) const;
void dump() const;

// 比较
bool operator==(const SkPathBuilder&) const;
bool operator!=(const SkPathBuilder&) const;
```

### 内部接口

```cpp
// 添加原始数据(内部使用)
SkPathBuilder& addRaw(const SkPathRaw&, Reserve);
```

## 内部实现细节

### moveTo 实现

```cpp
SkPathBuilder& SkPathBuilder::moveTo(SkPoint pt) {
    if (!fVerbs.empty() && fVerbs.back() == SkPathVerb::kMove) {
        // 替换前一个 Move 点
        fPts.back() = pt;
        fLastMoveIndex = fPts.size() - 1;
    } else {
        // 添加新 Move
        fLastMoveIndex = fPts.size();
        fPts.push_back(pt);
        fVerbs.push_back(SkPathVerb::kMove);

        // 清除特殊形状标记
        if (fType == SkPathIsAType::kOval || fType == SkPathIsAType::kRRect) {
            fType = SkPathIsAType::kGeneral;
        }
        fConvexity = SkPathConvexity::kUnknown;
    }
    return *this;
}
```

### ensureMove 辅助

```cpp
void ensureMove() {
    fType = SkPathIsAType::kGeneral;
    if (fVerbs.empty()) {
        this->moveTo({0, 0});
    } else if (fVerbs.back() == SkPathVerb::kClose) {
        this->moveTo(fPts[fLastMoveIndex]);
    }
}
```

在添加非 Move 动词前自动插入 Move。

### 弧线转换

椭圆弧使用圆锥曲线近似:

```cpp
SkConic conics[SkConic::kMaxConicsForArc];
int count = build_arc_conics(oval, startV, stopV, dir, conics, &singlePt);

for (int i = 0; i < count; ++i) {
    this->conicTo(conics[i].fPts[1], conics[i].fPts[2], conics[i].fW);
}
```

### SVG 弧线实现

复杂的 SVG 椭圆弧转换逻辑:

```cpp
SkPathBuilder& SkPathBuilder::arcTo(SkPoint rad, SkScalar angle,
                                    ArcSize arcLarge,
                                    SkPathDirection arcSweep,
                                    SkPoint endPt) {
    // 1. 将端点变换到单位圆
    // 2. 计算弧参数
    // 3. 分割为多个圆锥段
    // 4. 变换回原椭圆
    // ... (约100行代码)
}
```

### snapshot 实现

```cpp
SkPath SkPathBuilder::snapshot(const SkMatrix* mx) const {
    if (!mx) mx = &SkMatrix::I();

    sk_sp<SkPathData> pdata;
    if (auto raw = SkPathPriv::Raw(*this, SkResolveConvexity::kNo)) {
        pdata = SkPathData::MakeTransform(*raw, *mx);
    }

    if (pdata && fType != SkPathIsAType::kGeneral) {
        pdata->setupIsA(fType, fIsA.fDirection, fIsA.fStartIndex);
    }

    return SkPath::MakeNullCheck(std::move(pdata), fFillType, fIsVolatile);
}
```

### detach 实现

```cpp
SkPath SkPathBuilder::detach(const SkMatrix* mx) {
    auto path = this->snapshot(mx);
    this->reset();  // 重置构建器
    return path;
}
```

### 标准形状优化

```cpp
SkPathBuilder& SkPathBuilder::addRect(const SkRect& rect,
                                      SkPathDirection dir,
                                      unsigned index) {
    const bool wasEmpty = (fSegmentMask == 0);
    this->addRaw(SkPathRawShapes::Rect(rect, dir, index), Reserve::kGrow);

    if (wasEmpty) {
        // 空路径添加矩形后仍是矩形
        fConvexity = SkPathDirection_ToConvexity(dir);
    }
    return *this;
}
```

### addPath 变换处理

```cpp
SkPathBuilder& SkPathBuilder::addPath(const SkPath& src,
                                      const SkMatrix& matrix,
                                      SkPath::AddPathMode mode) {
    if (matrix.hasPerspective()) {
        // 透视变换需要特殊处理
        for (auto [verb, pts, w] : SkPathPriv::Iterate(src)) {
            switch (verb) {
                case SkPathVerb::kQuad:
                    // 提升为圆锥曲线
                    this->conicTo(pts[1], pts[2],
                                  SkConic::TransformW(pts, SK_Scalar1, matrix));
                    break;
                case SkPathVerb::kCubic:
                    // 细分三次曲线
                    subdivide_cubic_to(this, pts);
                    break;
                // ... 其他动词
            }
        }
    } else {
        // 非透视:直接映射点
        auto [newPts, newWeights] = this->growForVerbsInPath(src);
        matrix.mapPoints({newPts, count}, src.points());
        // 拷贝动词和权重
    }
    return *this;
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkPath | 输入和输出 |
| SkPathData | 数据容器 |
| SkPathPriv | 私有辅助 |
| SkMatrix | 变换操作 |
| SkRRect | 圆角矩形 |
| SkGeometry | 曲线几何 |
| SkConic | 圆锥曲线 |
| STArray | 动态数组 |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| SkPath | 路径构建 |
| SkPathEffect | 效果处理 |
| SkCanvas | 绘制接口 |
| 路径编辑工具 | 交互式编辑 |
| 测试代码 | 路径生成 |

## 设计模式与设计决策

### 构建器模式

提供流式接口构建复杂对象:
```cpp
SkPathBuilder()
    .moveTo(0, 0)
    .lineTo(100, 0)
    .lineTo(100, 100)
    .close()
    .detach();
```

### 命令模式

每个操作追加到动词队列:
- 支持回放
- 便于优化
- 可序列化

### 写时拷贝

`snapshot()` 共享数据:
```cpp
auto path1 = builder.snapshot();  // 共享
auto path2 = builder.snapshot();  // 仍共享
builder.lineTo(...);              // 创建新数据
```

### 懒惰求值

凸性等属性延迟计算:
```cpp
SkPathConvexity fConvexity = SkPathConvexity::kUnknown;
// 仅在 snapshot() 时可能解析
```

### RAII

`detach()` 自动重置:
```cpp
SkPath path = builder.detach();  // 自动调用 reset()
```

## 性能考量

### 预分配优化

`STArray<4, ...>` 栈上预留4个元素:
- 小路径无堆分配
- 大路径自动扩展

### incReserve 接口

允许预留空间:
```cpp
builder.incReserve(100, 100, 10);  // 避免多次重分配
```

### 标准形状快速路径

`addRect/addOval` 使用优化构造:
```cpp
this->addRaw(SkPathRawShapes::Rect(...), Reserve::kGrow);
```

### 变换优化

非透视变换直接映射点:
```cpp
matrix.mapPoints({newPts, count}, src.points());
```

### 移动语义

支持高效传递:
```cpp
SkPath path = std::move(builder).detach();
```

## 相关文件

| 文件 | 关系 | 说明 |
|------|------|------|
| include/core/SkPath.h | 配合 | 不可变路径 |
| src/core/SkPathData.h | 使用 | 数据容器 |
| src/core/SkPathPriv.h | 使用 | 私有辅助 |
| include/core/SkMatrix.h | 依赖 | 变换矩阵 |
| include/core/SkRRect.h | 依赖 | 圆角矩形 |
| src/core/SkGeometry.h | 依赖 | 曲线几何 |
| include/private/base/SkTArray.h | 依赖 | 动态数组 |
