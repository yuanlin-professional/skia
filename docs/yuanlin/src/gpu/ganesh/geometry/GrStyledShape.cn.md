# GrStyledShape

> 源文件: src/gpu/ganesh/geometry/GrStyledShape.h, src/gpu/ganesh/geometry/GrStyledShape.cpp

## 概述

`GrStyledShape` 是 Ganesh GPU 后端中表示带样式几何形状的核心类。它将几何信息(`GrShape`)与渲染样式(`GrStyle`)封装在一起,支持路径效果、描边和填充的应用。该类能够将样式信息烘焙到几何中,生成新的几何表示,这是 GPU 路径渲染的关键优化技术。

核心功能:
- 封装几何形状和渲染样式
- 应用路径效果和描边到几何
- 几何简化和样式转换
- 生成几何的键值(用于缓存)
- 支持反填充和路径监听器

## 架构位置

`GrStyledShape` 位于 Ganesh 几何层的顶层,连接几何和样式系统:

```
src/gpu/ganesh/
  ├── GrStyle.h/cpp                # 渲染样式
  └── geometry/
      ├── GrShape.h/cpp            # 底层几何
      ├── GrStyledShape.h/cpp      # 带样式的几何(本模块)
      └── ops/
          └── PathRenderer implementations  # 使用者
```

它是路径渲染器和绘制操作之间的桥梁。

## 主要类与结构体

### GrStyledShape 类

**继承关系**: 无基类

**用途**: 表示一个几何形状及其关联的渲染样式,支持样式应用和几何简化。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fShape` | `GrShape` | 底层几何形状 |
| `fStyle` | `GrStyle` | 渲染样式(描边、路径效果等) |
| `fGenID` | `int32_t` | 原始路径的生成 ID(用于缓存) |
| `fClosed` | `bool` | 几何是否闭合 |
| `fSimplified` | `bool` | 是否已简化 |
| `fInheritedKey` | `AutoSTArray<8, uint32_t>` | 继承的键值(应用样式后) |
| `fInheritedPathForListeners` | `optional<SkPath>` | 用于监听器的原始路径 |

### DoSimplify 枚举

```cpp
enum class DoSimplify : bool { kNo = false, kYes = true };
```

控制构造时是否自动调用 `simplify()`。

### FillInversion 枚举

```cpp
enum class FillInversion {
    kPreserve,           // 保持原始反填充状态
    kFlip,              // 翻转反填充状态
    kForceNoninverted,  // 强制非反填充
    kForceInverted      // 强制反填充
};
```

用于 `MakeFilled()` 控制填充反转行为。

## 公共 API 函数

### 构造函数

```cpp
// 从路径构造
explicit GrStyledShape(const SkPath& path, DoSimplify = DoSimplify::kYes);
GrStyledShape(const SkPath& path, const GrStyle& style, DoSimplify = DoSimplify::kYes);

// 从矩形构造
explicit GrStyledShape(const SkRect& rect, DoSimplify = DoSimplify::kYes);
GrStyledShape(const SkRect& rect, const GrStyle& style, DoSimplify = DoSimplify::kYes);

// 从圆角矩形构造
explicit GrStyledShape(const SkRRect& rrect, DoSimplify = DoSimplify::kYes);
GrStyledShape(const SkRRect& rrect, SkPathDirection dir, unsigned start,
              bool inverted, const GrStyle& style, DoSimplify = DoSimplify::kYes);
```

### 静态工厂方法

```cpp
static GrStyledShape MakeFilled(const GrStyledShape& original,
                                FillInversion = FillInversion::kPreserve);
```

创建原始形状的填充版本(移除描边/路径效果)。

```cpp
static GrStyledShape MakeArc(const SkArc& arc, const GrStyle& style,
                             DoSimplify = DoSimplify::kYes);
```

从圆弧创建带样式的形状。

### 样式应用

```cpp
GrStyledShape applyStyle(GrStyle::Apply apply, SkScalar scale) const;
```

应用样式到几何,生成新的形状:
- `GrStyle::Apply::kPathEffectOnly`: 仅应用路径效果
- `GrStyle::Apply::kPathEffectAndStrokeRec`: 应用路径效果和描边

**参数**:
- `apply`: 应用模式
- `scale`: 缩放因子(用于近似输出几何)

**返回值**: 应用样式后的新形状

### 几何查询

```cpp
bool isRect() const;                                   // 是否为矩形
bool asRRect(SkRRect* rrect, bool* inverted) const;   // 转换为圆角矩形
bool asLine(SkPoint pts[2], bool* inverted) const;    // 转换为线段
bool asNestedRects(SkRect rects[2]) const;             // 转换为嵌套矩形
SkPath asPath() const;                                 // 转换为路径
bool isEmpty() const;                                  // 是否为空
SkRect bounds() const;                                 // 几何边界
SkRect styledBounds() const;                           // 应用样式后的边界
```

### 拓扑查询

```cpp
bool knownToBeConvex() const;         // 是否为凸形
bool knownDirection() const;          // 是否有明确的绕向
bool inverseFilled() const;           // 是否为反填充
bool mayBeInverseFilledAfterStyling() const;  // 应用样式后可能反填充
bool knownToBeClosed() const;         // 是否闭合(无开放端点)
uint32_t segmentMask() const;         // 路径段类型掩码
```

### 键值生成

```cpp
int unstyledKeySize() const;                      // 未样式化键的大小
bool hasUnstyledKey() const;                      // 是否有键值
void writeUnstyledKey(uint32_t* key) const;       // 写入键值
```

用于几何缓存的唯一标识。

### 路径监听器

```cpp
void addGenIDChangeListener(sk_sp<SkIDChangeListener>) const;
```

添加监听器,当原始路径改变时通知。

### 简化

```cpp
void simplify();
```

简化几何和样式,可能:
- 将复杂几何简化为简单形状(如路径→矩形)
- 将样式烘焙到几何中(如描边→填充)
- 移除无效的样式属性

## 内部实现细节

### 样式应用流程

应用样式的核心算法:

1. **路径效果应用**:
```cpp
if (pe) {
    SkStrokeRec strokeRec = parentStyle.strokeRec();
    parentStyle.applyPathEffectToPath(&newPath, &strokeRec, srcPath, scale);
}
```

2. **描边应用**(如果需要):
```cpp
if (apply == GrStyle::Apply::kPathEffectAndStrokeRec && strokeRec.needToApply()) {
    parentStyle.applyToPath(&newPath, &fillOrHairline, srcPath, scale);
}
```

3. **键值继承**:
```cpp
setInheritedKey(parentShape, apply, scale);
```

### 简化策略

`simplify()` 执行多层简化:

1. **几何简化**:
```cpp
unsigned simplifyFlags = 0;
if (fStyle.isSimpleFill()) {
    simplifyFlags = GrShape::kAll_Flags;  // 激进简化
} else if (!fStyle.hasPathEffect()) {
    simplifyFlags |= GrShape::kIgnoreWinding_Flag;  // 忽略绕向
    simplifyFlags |= GrShape::kMakeCanonical_Flag;  // 规范化
}
fClosed = fShape.simplify(simplifyFlags);
```

2. **样式简化**(点和线):
```cpp
void simplifyStroke() {
    if (fShape.isPoint()) {
        // 点的描边变为填充的圆或矩形
        if (fStyle.strokeRec().getCap() == SkPaint::kRound_Cap) {
            fShape.setRRect(SkRRect::MakeOval(rect));
        } else {
            fShape.setRect(rect);
        }
        fStyle = GrStyle::SimpleFill();
    }
    // 类似处理线段...
}
```

### 键值生成算法

键值编码格式:

```
[ 几何类型 | 几何数据 | 路径效果键 | 描边键 ]
```

- **小路径**: 直接编码顶点和控制点
- **大路径**: 使用生成 ID
- **继承键**: 父形状的键 + 样式键

```cpp
void setInheritedKey(const GrStyledShape& parent, GrStyle::Apply apply, SkScalar scale) {
    int parentCnt = parent.unstyledKeySize();
    int styleCnt = GrStyle::KeySize(parent.fStyle, apply, styleKeyFlags);
    fInheritedKey.reset(parentCnt + styleCnt);
    parent.writeUnstyledKey(fInheritedKey.get());
    GrStyle::WriteKey(fInheritedKey.get() + parentCnt, parent.fStyle, apply, scale, ...);
}
```

### 嵌套矩形检测

检测双层矩形(用于描边矩形的优化):

```cpp
bool asNestedRects(SkRect rects[2]) const {
    SkPathDirection dirs[2];
    if (!SkPathPriv::IsNestedFillRects(fShape.path(), rects, dirs)) {
        return false;
    }
    // 检查绕向和边距一致性
    if (dirs[0] == dirs[1]) return false;  // 需要相反绕向
    // 检查边距是否一致...
}
```

### 反填充处理

反填充(inverse fill)的特殊处理:

```cpp
class AutoRestoreInverseness {
    AutoRestoreInverseness(GrShape* shape, const GrStyle& style)
            : fShape(shape), fInverted(!style.isDashed() && fShape->inverted()) {}
    ~AutoRestoreInverseness() {
        fShape->setInverted(fInverted);  // 恢复反填充状态
    }
};
```

虚线会忽略反填充,因此需要特殊处理。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrShape` | 底层几何表示 |
| `GrStyle` | 渲染样式定义 |
| `SkPath` | 路径数据结构 |
| `SkStrokeRec` | 描边记录 |
| `SkPathEffect` | 路径效果 |
| `SkIDChangeListener` | 路径变更监听 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| `GrPathRenderer` 层次结构 | 各种路径渲染器 |
| `GrDrawPathOp` | 路径绘制操作 |
| `GrStencilAndCoverPathRenderer` | 模板覆盖渲染 |
| `GrAAConvexPathRenderer` | 凸路径抗锯齿渲染 |

## 设计模式与设计决策

### 值语义 vs 引用语义

`GrStyledShape` 使用值语义,但内部路径通过引用计数:

```cpp
GrStyledShape(const GrStyledShape&);  // 拷贝构造
GrStyledShape& operator=(const GrStyledShape&);  // 赋值
```

这在拷贝时共享路径数据,直到需要修改时才复制(写时拷贝)。

### 延迟简化选项

允许禁用自动简化:

```cpp
GrStyledShape(const SkPath& path, DoSimplify::kNo);
```

用于:
- 延迟到更合适的时机简化
- 避免重复简化
- 调试和测试

### 样式烘焙模式

将样式转换为几何是关键优化:

**好处**:
- GPU 只需处理填充(更简单的渲染路径)
- 可以缓存烘焙后的几何
- 多次绘制同一形状时避免重复计算

**代价**:
- 增加几何复杂度(顶点数量)
- 内存占用增加

决策: 对于静态内容和重复绘制场景,烘焙是值得的。

### 继承键机制

样式应用链通过键继承保持一致性:

```
Shape1 --[PathEffect]--> Shape2 --[Stroke]--> Shape3
  |                         |                     |
 Key1                  Key1+PE               Key1+PE+Stroke
```

这确保相同的样式链总是产生相同的键值。

## 性能考量

### 小路径内联

路径顶点少于 `kMaxKeyFromDataVerbCnt = 10` 时直接编码到键中:

```cpp
static int path_key_from_data_size(const SkPath& path) {
    if (path.countVerbs() > GrStyledShape::kMaxKeyFromDataVerbCnt) {
        return -1;  // 使用生成 ID
    }
    // 计算内联键大小
    return 1 + (SkAlign4(verbCnt) >> 2) + 2 * pointCnt + conicWeightCnt;
}
```

避免小路径的哈希查找开销。

### 缓存友好的键值

键值布局:

```cpp
uint32_t key[] = {
    stateFlags,      // 4 字节
    // 几何数据
    // 样式数据
};
```

连续内存,便于快速比较和哈希计算。

### 懒惰路径创建

`asPath()` 仅在需要时创建路径:

```cpp
SkPath asPath() const {
    return fShape.asPath(fStyle.isSimpleFill());
}
```

对于非路径几何(矩形、圆角矩形),避免不必要的路径构建。

### 简化的性能权衡

`simplify()` 可能执行昂贵的计算,但换来:
- 更快的渲染(简单几何渲染更快)
- 更小的缓存键
- 更少的 GPU 状态切换

测量显示,对于重复绘制的形状,简化开销可以忽略。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/geometry/GrShape.h` | 依赖 | 底层几何抽象 |
| `src/gpu/ganesh/GrStyle.h` | 依赖 | 渲染样式定义 |
| `src/gpu/ganesh/GrPathRenderer.h` | 被使用 | 路径渲染器基类 |
| `src/gpu/ganesh/ops/GrDrawPathOp.cpp` | 被使用 | 路径绘制操作 |
| `include/private/SkIDChangeListener.h` | 依赖 | 路径变更监听 |
| `tests/GrStyledShapeTest.cpp` | 测试 | 单元测试 |
