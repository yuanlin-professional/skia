# ShapeLayer

> 源文件
> - `modules/skottie/src/layers/shapelayer/ShapeLayer.h`
> - `modules/skottie/src/layers/shapelayer/ShapeLayer.cpp`

## 概述

`ShapeLayer` 模块是 Skottie 库中专门负责处理 Lottie 动画中形状图层的核心组件。该模块通过 `ShapeBuilder` 类提供了一套完整的形状构建系统,用于将 Lottie JSON 格式的形状数据转换为 Skia 场景图（Scene Graph）节点。它支持多种几何形状、绘制样式、几何效果以及绘制效果的解析和渲染,是实现 Lottie 矢量图形动画的关键模块。

该模块的设计遵循 Lottie 规范,处理从简单的路径、矩形、椭圆到复杂的渐变填充、描边、修剪效果等各种形状元素。它通过分层的架构将 JSON 数据转换为可渲染的场景图结构,同时支持形状的动画属性绑定。

## 架构位置

`ShapeLayer` 位于 Skottie 动画引擎的图层处理层,具体架构位置如下:

```
Skottie 动画引擎
├── Animation (动画管理)
├── AnimationBuilder (构建器)
│   └── attachShapeLayer() ──> ShapeBuilder
├── Layers (图层系统)
│   ├── ImageLayer (图像图层)
│   ├── TextLayer (文本图层)
│   └── ShapeLayer (形状图层) ← 本模块
└── Scene Graph (sksg)
    ├── GeometryNode (几何节点)
    ├── PaintNode (绘制节点)
    └── RenderNode (渲染节点)
```

该模块依赖于:
- **sksg (Scene Graph)**: 提供底层的几何、绘制和渲染节点
- **AnimationBuilder**: 提供动画属性解析和绑定功能
- **skjson**: 提供 JSON 数据访问接口

## 主要类与结构体

### ShapeBuilder

形状构建器的核心类,提供静态方法用于附加各种形状元素:

```cpp
class ShapeBuilder final : SkNoncopyable {
public:
    // 几何形状附加方法
    static sk_sp<sksg::GeometryNode> AttachPathGeometry(
        const skjson::ObjectValue&, const AnimationBuilder*);
    static sk_sp<sksg::GeometryNode> AttachRRectGeometry(
        const skjson::ObjectValue&, const AnimationBuilder*);
    static sk_sp<sksg::GeometryNode> AttachEllipseGeometry(
        const skjson::ObjectValue&, const AnimationBuilder*);
    static sk_sp<sksg::GeometryNode> AttachPolystarGeometry(
        const skjson::ObjectValue&, const AnimationBuilder*);

    // 绘制样式附加方法
    static sk_sp<sksg::PaintNode> AttachColorFill(
        const skjson::ObjectValue&, const AnimationBuilder*);
    static sk_sp<sksg::PaintNode> AttachColorStroke(
        const skjson::ObjectValue&, const AnimationBuilder*);
    static sk_sp<sksg::PaintNode> AttachGradientFill(
        const skjson::ObjectValue&, const AnimationBuilder*);
    static sk_sp<sksg::PaintNode> AttachGradientStroke(
        const skjson::ObjectValue&, const AnimationBuilder*);

    // 几何效果方法
    static std::vector<sk_sp<sksg::GeometryNode>> AttachMergeGeometryEffect(...);
    static std::vector<sk_sp<sksg::GeometryNode>> AttachTrimGeometryEffect(...);
    static std::vector<sk_sp<sksg::GeometryNode>> AttachRoundGeometryEffect(...);
    static std::vector<sk_sp<sksg::GeometryNode>> AttachOffsetGeometryEffect(...);
    static std::vector<sk_sp<sksg::GeometryNode>> AttachPuckerBloatGeometryEffect(...);
};
```

### AttachShapeContext

形状附加上下文结构体,用于在递归处理形状时维护状态:

```cpp
struct AttachShapeContext {
    std::vector<sk_sp<sksg::GeometryNode>>* fGeometryStack;        // 几何体栈
    std::vector<GeometryEffectRec>* fGeometryEffectStack;          // 几何效果栈
    size_t fCommittedAnimators;                                     // 已提交的动画器数量
};
```

### ShapeInfo

形状信息结构体,定义了各种 Lottie 形状类型的元数据:

```cpp
struct ShapeInfo {
    const char* fTypeString;      // 类型字符串标识
    ShapeType fShapeType;         // 形状类型枚举
    uint16_t fAttacherIndex;      // 附加器索引
    uint16_t fFlags;              // 标志位
};
```

### ShapeRec

形状记录结构体,用于在两遍处理过程中缓存形状信息:

```cpp
struct ShapeRec {
    const skjson::ObjectValue& fJson;   // JSON 对象引用
    const ShapeInfo& fInfo;             // 形状信息引用
    bool fSuppressed;                   // 是否被抑制绘制
};
```

## 公共 API 函数

### 几何形状附加接口

**AttachPathGeometry**
```cpp
static sk_sp<sksg::GeometryNode> AttachPathGeometry(
    const skjson::ObjectValue& jpath,
    const AnimationBuilder* abuilder);
```
解析并附加自定义路径几何体,支持贝塞尔曲线路径。

**AttachRRectGeometry**
```cpp
static sk_sp<sksg::GeometryNode> AttachRRectGeometry(
    const skjson::ObjectValue&,
    const AnimationBuilder*);
```
附加圆角矩形几何体,支持尺寸和圆角半径动画。

**AttachEllipseGeometry**
```cpp
static sk_sp<sksg::GeometryNode> AttachEllipseGeometry(
    const skjson::ObjectValue&,
    const AnimationBuilder*);
```
附加椭圆几何体,支持尺寸和位置动画。

**AttachPolystarGeometry**
```cpp
static sk_sp<sksg::GeometryNode> AttachPolystarGeometry(
    const skjson::ObjectValue&,
    const AnimationBuilder*);
```
附加多边形和星形几何体,支持点数、旋转等参数动画。

### 绘制样式附加接口

**AttachColorFill / AttachColorStroke**
```cpp
static sk_sp<sksg::PaintNode> AttachColorFill(
    const skjson::ObjectValue&,
    const AnimationBuilder*);
```
附加纯色填充或描边,支持颜色和不透明度动画。

**AttachGradientFill / AttachGradientStroke**
```cpp
static sk_sp<sksg::PaintNode> AttachGradientFill(
    const skjson::ObjectValue&,
    const AnimationBuilder*);
```
附加渐变填充或描边,支持线性和径向渐变,支持渐变颜色和位置动画。

### 几何效果接口

**AttachMergeGeometryEffect**
```cpp
static std::vector<sk_sp<sksg::GeometryNode>> AttachMergeGeometryEffect(
    const skjson::ObjectValue&,
    const AnimationBuilder*,
    std::vector<sk_sp<sksg::GeometryNode>>&&);
```
合并多个几何体,支持联合、相交、差集等布尔运算模式。

**AttachTrimGeometryEffect**
```cpp
static std::vector<sk_sp<sksg::GeometryNode>> AttachTrimGeometryEffect(
    const skjson::ObjectValue&,
    const AnimationBuilder*,
    std::vector<sk_sp<sksg::GeometryNode>>&&);
```
修剪路径效果,支持起始点、结束点和偏移量动画。

**AttachRoundGeometryEffect**
```cpp
static std::vector<sk_sp<sksg::GeometryNode>> AttachRoundGeometryEffect(
    const skjson::ObjectValue&,
    const AnimationBuilder*,
    std::vector<sk_sp<sksg::GeometryNode>>&&);
```
圆角效果,为路径的尖角添加圆角。

### 形状图层附加接口

**attachShapeLayer**
```cpp
sk_sp<sksg::RenderNode> AnimationBuilder::attachShapeLayer(
    const skjson::ObjectValue& layer,
    LayerInfo*) const;
```
附加完整的形状图层,是形状图层处理的入口函数。

**attachShape**
```cpp
sk_sp<sksg::RenderNode> AnimationBuilder::attachShape(
    const skjson::ArrayValue* jshape,
    AttachShapeContext* ctx,
    bool suppress_draws) const;
```
递归处理形状数组,构建渲染节点树。

## 内部实现细节

### 两遍处理算法

`attachShape` 函数使用两遍处理算法来正确构建形状层次结构:

**第一遍（自底向上）**:
1. 识别并记录所有形状元素
2. 提取组变换信息
3. 将几何效果压入栈中
4. 检查并处理隐藏标志
5. 处理效果的绘制抑制标志

**第二遍（自顶向下）**:
1. 处理几何形状,添加到几何栈
2. 应用几何效果并从栈中弹出
3. 递归处理形状组
4. 为绘制样式创建绘制节点
5. 应用绘制效果

### 形状类型查找表

使用二分搜索优化形状类型查找:

```cpp
const ShapeInfo* FindShapeInfo(const skjson::ObjectValue& jshape) {
    static constexpr ShapeInfo gShapeInfo[] = {
        { "el", ShapeType::kGeometry, 2, kNone },          // ellipse
        { "fl", ShapeType::kPaint, 0, kNone },             // fill
        { "gf", ShapeType::kPaint, 2, kNone },             // gradient fill
        { "gr", ShapeType::kGroup, 0, kNone },             // group
        { "gs", ShapeType::kPaint, 3, kNone },             // gradient stroke
        { "mm", ShapeType::kGeometryEffect, 0, kSuppressDraws }, // merge
        // ... 更多类型
    };
    // 使用 bsearch 进行快速查找
}
```

### 填充规则调整

Lottie 在绘制节点上指定填充规则,而 Skia 在几何节点上指定,需要转换:

```cpp
sk_sp<sksg::GeometryNode> AdjustGeometryFillRule(
    sk_sp<sksg::GeometryNode> geo,
    const skjson::ObjectValue& jpaint) {
    static constexpr SkPathFillType gFillTypes[] = {
        SkPathFillType::kWinding,  // "r": 1
        SkPathFillType::kEvenOdd,  // "r": 2
    };
    const SkPathFillType ft = gFillTypes[...];
    return sksg::FillTypeOverride::Make(std::move(geo), ft);
}
```

### 几何效果栈机制

几何效果使用栈结构延迟应用,确保效果按正确顺序应用到几何体:

1. 第一遍将效果压栈
2. 遇到绘制时,从栈顶到栈底依次应用所有效果
3. 处理效果节点时弹出对应的栈项

### 动画器提交机制

使用 `fCommittedAnimators` 跟踪已提交的动画器,避免未使用的几何体保持动画器引用:

```cpp
ctx->fCommittedAnimators = fCurrentAnimatorScope->size();
// 处理完成后裁剪未提交的动画器
fCurrentAnimatorScope->resize(shapeCtx.fCommittedAnimators);
```

### 变换和不透明度处理

形状组的变换和不透明度需要特殊处理,确保动画器正确插入:

```cpp
AutoScope ascope(this);
if ((shape_transform = this->attachMatrix2D(*jtransform, nullptr))) {
    shape_wrapper = sksg::TransformEffect::Make(std::move(shape_wrapper), shape_transform);
}
shape_wrapper = this->attachOpacity(*jtransform, std::move(shape_wrapper));

// 将本地作用域的动画器插入到已提交位置
auto local_scope = ascope.release();
fCurrentAnimatorScope->insert(fCurrentAnimatorScope->begin() + ctx->fCommittedAnimators,
                              std::make_move_iterator(local_scope.begin()),
                              std::make_move_iterator(local_scope.end()));
```

## 依赖关系

### 对外依赖

- **sksg (Scene Graph)**: 提供 `GeometryNode`、`PaintNode`、`RenderNode` 等基础图形节点
- **AnimationBuilder**: 提供 `attachPath`、`attachMatrix2D`、`attachOpacity` 等动画属性绑定功能
- **skjson**: 提供 `ObjectValue`、`ArrayValue`、`StringValue` 等 JSON 访问接口
- **Skia Core**: 提供 `SkPathFillType`、`SkRefCnt` 等基础类型

### 内部依赖

- **Animator**: 动画器系统,用于绑定属性动画
- **SkottiePriv**: 提供 `ParseDefault`、`AutoPropertyTracker` 等工具函数
- **Logger**: 日志系统,用于报告解析错误

### 被依赖情况

- **AnimationBuilder**: 在构建形状图层时调用 `attachShapeLayer`
- **Skottie**: 通过 `AnimationBuilder` 间接使用该模块解析形状图层

## 设计模式与设计决策

### 静态工厂模式

`ShapeBuilder` 使用纯静态方法,不需要实例化,所有附加方法都是静态工厂方法,返回智能指针管理的对象。这种设计避免了状态管理的复杂性,所有上下文通过参数传递。

### 函数指针表模式

使用函数指针表实现类型分发,避免冗长的 switch-case 语句:

```cpp
static constexpr GeometryAttacherT gGeometryAttachers[] = {
    ShapeBuilder::AttachPathGeometry,
    ShapeBuilder::AttachRRectGeometry,
    ShapeBuilder::AttachEllipseGeometry,
    ShapeBuilder::AttachPolystarGeometry,
};
```

### 栈式处理模式

几何效果和几何体都使用栈结构进行管理,支持正确的层级关系和延迟应用。这确保了效果按照 Lottie 规范的顺序应用。

### 两遍扫描模式

第一遍收集信息和构建栈,第二遍实际构建场景图,这种分离使得代码逻辑清晰,易于处理复杂的依赖关系。

### 智能指针所有权管理

使用 `sk_sp` 智能指针管理所有场景图节点的生命周期,通过 `std::move` 语义明确所有权转移,避免内存泄漏和重复释放。

### 延迟效果应用

几何效果在第一遍被记录,但在第二遍遇到绘制时才应用,这允许效果影响多个后续的绘制操作。

### 绘制抑制机制

某些效果（如 merge）会抑制其上方的所有绘制操作,使用 `suppress_draws` 标志实现这一行为。

## 性能考量

### 二分搜索优化

`FindShapeInfo` 使用 `bsearch` 进行形状类型查找,时间复杂度为 O(log n),适合频繁调用场景。

### 内存预分配

使用 `std::vector` 存储几何体和绘制节点,利用其动态增长特性,同时调用 `shrink_to_fit` 减少内存浪费:

```cpp
std::reverse(draws.begin(), draws.end());
draws.shrink_to_fit();
```

### 引用传递

大量使用常量引用传递 JSON 对象,避免不必要的复制:

```cpp
const skjson::ObjectValue& jshape
```

### 延迟构建

只有在需要时才构建场景图节点,隐藏的形状直接跳过处理:

```cpp
if (ParseDefault<bool>((*shape)["hd"], false)) {
    continue;  // 忽略隐藏形状
}
```

### 智能指针优化

使用 `std::move` 避免不必要的引用计数操作,提高性能:

```cpp
draws.push_back(std::move(draw));
```

### 单绘制优化

当只有一个绘制节点时,避免创建 Group 节点:

```cpp
if (draws.size() == 1) {
    shape_wrapper = std::move(draws.front());
} else if (!draws.empty()) {
    shape_wrapper = sksg::Group::Make(std::move(draws));
}
```

### 动画器裁剪

及时裁剪未提交的动画器,避免保留对未使用几何体的引用:

```cpp
fCurrentAnimatorScope->resize(shapeCtx.fCommittedAnimators);
```

## 相关文件

**头文件依赖**:
- `include/core/SkRefCnt.h` - 智能指针基础设施
- `include/core/SkPathTypes.h` - 路径填充类型定义
- `include/private/base/SkNoncopyable.h` - 不可复制基类
- `modules/sksg/include/SkSGMerge.h` - 几何合并节点
- `modules/sksg/include/SkSGGeometryNode.h` - 几何节点基类
- `modules/sksg/include/SkSGPaintNode.h` - 绘制节点基类
- `modules/sksg/include/SkSGRenderNode.h` - 渲染节点基类

**实现文件依赖**:
- `modules/skottie/src/SkottieJson.h` - JSON 解析工具
- `modules/skottie/src/SkottiePriv.h` - 私有工具函数
- `modules/skottie/src/animator/Animator.h` - 动画器基类
- `modules/sksg/include/SkSGDraw.h` - 绘制节点实现
- `modules/sksg/include/SkSGGeometryEffect.h` - 几何效果节点
- `modules/sksg/include/SkSGGroup.h` - 组节点
- `modules/sksg/include/SkSGTransform.h` - 变换节点

**相关模块**:
- `modules/skottie/src/animator/` - 动画器实现
- `modules/skottie/src/effects/` - 效果处理
- `modules/skottie/src/text/` - 文本处理
- `modules/sksg/` - 场景图系统
