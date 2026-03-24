# SkSGGeometryEffect - 场景图几何效果节点

> 源文件: `modules/sksg/src/SkSGGeometryEffect.cpp`

## 概述

`SkSGGeometryEffect.cpp` 实现了 Skia 场景图 (sksg) 中的一系列几何效果节点，用于对子几何节点的路径进行各种变换和修饰。包括 `GeometryEffect`（基类）、`TrimEffect`（路径裁剪）、`GeometryTransform`（几何变换）、`FillTypeOverride`（填充类型覆盖）、`DashEffect`（虚线效果）、`RoundEffect`（圆角效果）和 `OffsetEffect`（路径偏移/膨胀效果）。这些效果在 Skottie 中广泛用于实现 After Effects 的形状修饰器。

## 架构位置

`GeometryEffect` 及其子类位于 sksg 模块的几何效果层，继承自 `GeometryNode`。它们是场景图中的中间几何节点，装饰单个子几何节点的路径输出。在 Lottie 渲染管线中，这些效果节点对应 After Effects 中的 Trim Paths、Dash、Round Corners、Offset Paths 等形状修饰器。

## 主要类与结构体

### `GeometryEffect`（基类）
```cpp
class GeometryEffect : public GeometryNode {
    sk_sp<GeometryNode> fChild;
    SkPath fPath;  // 缓存的效果处理后的路径
};
```
提供通用的子节点管理、绘制、裁剪和重新验证逻辑。

### `TrimEffect` - 路径裁剪
根据 `fStart`、`fStop` 和 `fMode` 参数裁剪路径的一部分。

### `GeometryTransform` - 几何变换
对子几何路径应用 `Transform` 节点定义的矩阵变换。

### `FillTypeOverride` - 填充类型覆盖
覆盖子路径的填充规则（如 winding/even-odd）。

### `DashEffect` - 虚线效果
将路径转换为虚线模式，支持间隔数组和相位偏移。

### `RoundEffect` - 圆角效果
对路径的角点应用圆角处理。

### `OffsetEffect` - 路径偏移
向外或向内偏移路径边缘，使用描边扩展和路径布尔运算实现。

## 公共 API 函数

### GeometryEffect 基类方法

| 方法 | 说明 |
|------|------|
| `GeometryEffect(sk_sp<GeometryNode>)` | 构造函数，注册子节点失效观察 |
| `~GeometryEffect()` | 析构函数，取消失效观察 |
| `void onClip(SkCanvas*, bool) const` | 使用效果路径裁剪 |
| `void onDraw(SkCanvas*, const SkPaint&) const` | 绘制效果路径 |
| `bool onContains(const SkPoint&) const` | 路径包含测试 |
| `SkPath onAsPath() const` | 返回效果路径 |
| `SkRect onRevalidate(InvalidationController*, const SkMatrix&)` | 重新验证并调用子类效果 |

### 子类效果方法

| 方法 | 说明 |
|------|------|
| `TrimEffect::onRevalidateEffect(child, ctm)` | 应用路径裁剪效果 |
| `GeometryTransform::onRevalidateEffect(child, ctm)` | 应用矩阵变换 |
| `FillTypeOverride::onRevalidateEffect(child, ctm)` | 覆盖填充类型 |
| `DashEffect::onRevalidateEffect(child, ctm)` | 应用虚线效果 |
| `RoundEffect::onRevalidateEffect(child, ctm)` | 应用圆角效果 |
| `OffsetEffect::onRevalidateEffect(child, ctm)` | 应用路径偏移 |

## 内部实现细节

### 基类重新验证流程
```cpp
SkRect GeometryEffect::onRevalidate(InvalidationController* ic, const SkMatrix& ctm) {
    fChild->revalidate(ic, ctm);
    fPath = this->onRevalidateEffect(fChild, ctm);  // 模板方法
    return fPath.computeTightBounds();
}
```

### TrimEffect
使用 `SkTrimPathEffect` 裁剪路径：
```cpp
if (const auto trim = SkTrimPathEffect::Make(fStart, fStop, fMode)) {
    SkStrokeRec rec(SkStrokeRec::kHairline_InitStyle);
    SkPathBuilder builder;
    SkAssertResult(trim->filterPath(&builder, path, &rec, nullptr, SkMatrix::I()));
    return builder.detach();
}
```

### GeometryTransform
通过 `TransformPriv` 提取变换矩阵：
```cpp
fTransform->revalidate(nullptr, SkMatrix::I());
const auto m = TransformPriv::As<SkMatrix>(fTransform);
return child->asPath().makeTransform(m);
```
额外管理 `fTransform` 节点的失效观察。

### DashEffect 与 `make_dash` 辅助函数
```cpp
static sk_sp<SkPathEffect> make_dash(const std::vector<float>& intervals, float phase) {
    // 奇数间隔数时翻倍（SkDashPathEffect 要求偶数）
    if (intervals_count & 1) {
        intervals_count *= 2;
        storage.resize(intervals_count);
        std::copy(intervals.begin(), intervals.end(), storage.begin());
        std::copy(intervals.begin(), intervals.end(), storage.begin() + intervals.size());
    }
    return SkDashPathEffect::Make({intervals_ptr, intervals_count}, phase);
}
```
处理了 `SkDashPathEffect` 要求偶数个间隔值的约束。

### OffsetEffect
使用描边扩展 + 路径布尔运算实现偏移：
```cpp
SkPaint paint;
paint.setStyle(SkPaint::kStroke_Style);
paint.setStrokeWidth(abs_offset * 2);
paint.setStrokeMiter(fMiterLimit);
paint.setStrokeJoin(fJoin);
SkPath fill_path = skpathutils::FillPathWithPaint(path, paint);
SkPathOp op = fOffset > 0 ? kUnion_SkPathOp : kDifference_SkPathOp;
if (auto result = Op(path, fill_path, op)) { path = *result; }
```

关键细节：
- 正偏移使用 Union（并集），负偏移使用 Difference（差集）
- 设备空间偏移量被钳制到 `kMaxDevOffset = 100000` 以防止 pathops 溢出
- 支持 `fMiterLimit` 和 `fJoin` 参数控制偏移形状

## 依赖关系

- **直接依赖**: `SkSGGeometryEffect.h`、`SkSGGeometryNode.h`、`SkCanvas.h`、`SkPath.h`、`SkPathBuilder.h`、`SkPathEffect.h`、`SkStrokeRec.h`
- **路径效果**: `SkTrimPathEffect.h`、`SkDashPathEffect.h`、`SkCornerPathEffect.h`
- **路径操作**: `SkPathOps.h`（用于 OffsetEffect）
- **内部依赖**: `SkSGTransformPriv.h`（用于 GeometryTransform）
- **被使用**: Skottie 形状修饰器

## 设计模式与设计决策

- **模板方法模式**: `GeometryEffect` 基类在 `onRevalidate` 中定义算法骨架（子节点重新验证 -> 效果应用 -> 边界计算），子类通过 `onRevalidateEffect` 提供具体效果
- **装饰器模式**: 每个效果类装饰一个子几何节点，效果可以链式叠加
- **路径效果适配**: `TrimEffect`、`DashEffect`、`RoundEffect` 将 Skia 的 `SkPathEffect` API 适配为场景图节点，支持动画属性
- **描边到路径转换**: `OffsetEffect` 创新性地使用描边宽度扩展 + 布尔运算来实现路径偏移，而非直接的数学偏移
- **设备空间钳制**: `OffsetEffect` 将偏移量在设备空间中钳制，防止极端缩放导致的计算溢出

## 性能考量

- **路径缓存**: 效果路径 `fPath` 缓存在成员变量中，仅在失效时重新计算
- **紧凑边界**: 使用 `computeTightBounds()` 获取精确边界
- **pathops 开销**: `OffsetEffect` 使用路径布尔运算，计算复杂度较高。代码中钳制偏移量到 `kMaxDevOffset` 以防止极端情况下的性能问题
- **SkPathEffect::needsCTM()**: 对于 `TrimEffect` 和 `DashEffect`，断言路径效果不需要 CTM，这允许在世界空间下操作，避免重复变换
- **STArray 栈优化**: `make_dash` 使用 `STArray<32, float, true>` 在栈上分配小型间隔数组，避免堆分配
- **Simplify 注释**: `OffsetEffect` 中有注释说明 `Simplify()` 可能导致路径组合问题（winding 不匹配），因此被注释掉

## 相关文件

- `modules/sksg/include/SkSGGeometryEffect.h` — 所有效果类的声明和属性定义
- `modules/sksg/include/SkSGGeometryNode.h` — 几何节点基类
- `modules/sksg/src/SkSGTransformPriv.h` — 变换节点私有访问
- `include/effects/SkTrimPathEffect.h` — 路径裁剪效果
- `include/effects/SkDashPathEffect.h` — 虚线效果
- `include/effects/SkCornerPathEffect.h` — 圆角效果
- `include/pathops/SkPathOps.h` — 路径布尔运算
- `modules/sksg/src/SkSGMerge.cpp` — 另一个使用 pathops 的几何节点
