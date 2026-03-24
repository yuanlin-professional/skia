# PuckerBloat

> 源文件: modules/skottie/src/layers/shapelayer/PuckerBloat.cpp

## 概述

`PuckerBloat.cpp` 实现了 Skottie 形状层系统中的收缩/膨胀(Pucker/Bloat)效果。该模块通过将路径顶点向中心拉动或推离中心来变形几何形状,同时反向处理控制点以保持曲线的平滑性。这是 After Effects Pucker & Bloat 效果在 Skottie 中的实现,常用于创建星形、波浪等有机形状动画。

## 架构位置

该文件位于 Skottie 形状层几何效果子系统中:
- **模块**: `modules/skottie/src/layers/shapelayer/`
- **命名空间**: `skottie::internal`
- **依赖关系**: 依赖 SkSG 场景图的几何效果系统和 Skia 的路径操作
- **角色**: 作为几何效果实现,通过 `ShapeBuilder` 附加到形状层

## 主要类与结构体

### PuckerBloatEffect
```cpp
class PuckerBloatEffect final : public sksg::GeometryEffect
```
收缩/膨胀效果的核心实现类,对路径进行立方曲线级别的变形。

**继承关系**:
- 继承自 `sksg::GeometryEffect`
- 作为几何效果链的一部分

**成员变量**:
- `fAmount`: 效果强度,0 表示无效果,1 表示完全收缩到中心

**属性**:
```cpp
SG_ATTRIBUTE(Amount, float, fAmount)
```
使用 SkSG 属性宏定义可设置的 `Amount` 属性。

**核心方法**:
```cpp
SkPath onRevalidateEffect(const sk_sp<GeometryNode>& geo, const SkMatrix&) override
```
重新验证并计算效果后的路径:
1. 获取输入路径
2. 如果 `fAmount` 接近 0,直接返回原路径
3. 计算路径的紧密边界矩形中心
4. 将所有路径动词归一化为三次贝塞尔曲线
5. 对每个轮廓应用收缩/膨胀变换
6. 返回变形后的路径

### PuckerBloatAdapter
```cpp
class PuckerBloatAdapter final : public DiscardableAdapterBase<PuckerBloatAdapter, PuckerBloatEffect>
```
收缩/膨胀适配器类,将 JSON 动画数据绑定到 `PuckerBloatEffect`。

**继承关系**:
- 继承自 `DiscardableAdapterBase` 模板基类
- 模板参数: `PuckerBloatAdapter`(CRTP), `PuckerBloatEffect`(目标节点类型)

**成员变量**:
- `fAmount`: 效果强度百分比(AE 语义)

**构造函数**:
```cpp
PuckerBloatAdapter(const skjson::ObjectValue& joffset,
                   const AnimationBuilder& abuilder,
                   sk_sp<sksg::GeometryNode> child)
```
- 创建 `PuckerBloatEffect` 并绑定 JSON 的 "a" 字段到 `fAmount`

**核心方法**:
```cpp
void onSync() override
```
- 将 AE 的百分比值转换为归一化值:`fAmount / 100`
- 设置到底层效果节点

### CubicInfo 结构体
```cpp
struct CubicInfo {
    SkPoint ctrl0, ctrl1, pt;
};
```
存储三次贝塞尔曲线段信息,对应 `SkPath::cubicTo()` 的三个参数。

## 公共 API 函数

### AttachPuckerBloatGeometryEffect
```cpp
std::vector<sk_sp<sksg::GeometryNode>> ShapeBuilder::AttachPuckerBloatGeometryEffect(
    const skjson::ObjectValue& jround,
    const AnimationBuilder* abuilder,
    std::vector<sk_sp<sksg::GeometryNode>>&& geos)
```
为每个输入几何节点附加收缩/膨胀效果。

**参数**:
- `jround`: JSON 效果配置对象
- `abuilder`: 动画构建器指针
- `geos`: 要应用效果的几何节点向量(右值引用)

**返回值**: 包含应用效果后的几何节点向量

**JSON 参数映射**:
- `"a"`: Amount(强度),百分比值,支持动画

**实现逻辑**:
1. 创建输出向量 `bloated` 并预留容量
2. 遍历所有输入几何节点
3. 对每个节点通过 `attachDiscardableAdapter` 创建 `PuckerBloatAdapter`
4. 将包装后的节点添加到输出向量
5. 返回处理后的几何节点向量

## 内部实现细节

### 插值辅助函数
```cpp
static SkPoint lerp(const SkPoint& p0, const SkPoint& p1, SkScalar t) {
    return p0 + (p1 - p0) * t;
}
```
线性插值点坐标,用于计算收缩/膨胀后的位置。

### 中心点计算
```cpp
const auto input_bounds = input.computeTightBounds();
const SkPoint center{input_bounds.centerX(), input_bounds.centerY()};
```
使用紧密边界矩形的中心作为收缩/膨胀的基准点。

### 路径归一化为三次曲线
效果将所有路径动词转换为三次贝塞尔曲线:

**直线 (kLine)**:
```cpp
static constexpr float kCtrlPosFraction = 1.f / 100;
cubics.push_back({
    lerp(line_start, line_end, kCtrlPosFraction),
    lerp(line_start, line_end, 1 - kCtrlPosFraction),
    line_end
});
```
控制点放置在距离端点 1/100 长度处(经验值)。

**二次曲线 (kQuad)**:
```cpp
SkPoint quad[4];
SkConvertQuadToCubic(pts.data(), quad);
cubics.push_back({quad[1], quad[2], quad[3]});
```
使用 Skia 的标准转换函数。

**圆锥曲线 (kConic)**:
```cpp
static constexpr float kCubicCircleCoeff = 1 - 0.551915024494f;
cubics.push_back({
    lerp(pts[1], conic_start, kCubicCircleCoeff),
    lerp(pts[1], conic_end, kCubicCircleCoeff),
    conic_end
});
```
圆锥曲线(主要来自圆/椭圆)转换为三次曲线,使用魔法常数 `0.551915024494`(圆的三次贝塞尔近似系数)。

**三次曲线 (kCubic)**:
直接使用,无需转换。

### 变形应用
```cpp
builder.moveTo(lerp(contour_start, center, fAmount));
for (const auto& c : cubics) {
    builder.cubicTo(lerp(c.ctrl0, center, -fAmount),  // 控制点反向
                    lerp(c.ctrl1, center, -fAmount),  // 控制点反向
                    lerp(c.pt, center, fAmount));     // 顶点正向
}
```

**关键特性**:
- **顶点**: 使用正 `fAmount`,向中心拉动(收缩)或推离(膨胀,负值)
- **控制点**: 使用负 `-fAmount`,反向移动以保持曲线平滑度
- 允许负值和超范围值,提供更丰富的效果

### 轮廓提交机制
```cpp
auto commit_contour = [&]() {
    builder.moveTo(lerp(contour_start, center, fAmount));
    for (const auto& c : cubics) {
        builder.cubicTo(...);
    }
    builder.close();
    cubics.clear();
};
```
Lambda 函数处理轮廓的提交:
- 在遇到新的 `kMove` 或 `kClose` 时调用
- 清空 `cubics` 向量准备下一个轮廓

### 路径迭代器
```cpp
SkPath::Iter iter(input, true);  // true = 强制闭合
while (auto rec = iter.next()) {
    SkSpan<const SkPoint> pts = rec->fPoints;
    switch (rec->fVerb) {
        // ...
    }
}
```
遍历输入路径的所有动词和点。

## 依赖关系

### 外部依赖
- **Skia 核心**:
  - `SkPath`: 路径表示
  - `SkPathBuilder`: 路径构建器
  - `SkPoint`: 点坐标
  - `SkRect`: 矩形
  - `SkScalar`: 标量类型
  - `SkMatrix`: 变换矩阵
  - `SkGeometry`: 几何转换(如 `SkConvertQuadToCubic`)

- **SkSG 场景图**:
  - `sksg::GeometryNode`: 几何节点基类
  - `sksg::GeometryEffect`: 几何效果基类
  - `sksg::Node`: 场景图节点基类

- **Skottie 框架**:
  - `AnimationBuilder`: 动画构建器
  - `DiscardableAdapterBase`: 可丢弃适配器基类
  - `ScalarValue`: 标量值类型
  - `ShapeBuilder`: 形状构建器

### 内部依赖
- `modules/skottie/src/Adapter.h`: 适配器基类
- `modules/skottie/src/SkottiePriv.h`: AnimationBuilder 定义
- `modules/skottie/src/SkottieValue.h`: ScalarValue 定义
- `modules/skottie/src/layers/shapelayer/ShapeLayer.h`: ShapeBuilder 定义
- `modules/sksg/include/SkSGGeometryEffect.h`: 几何效果基类
- `src/core/SkGeometry.h`: 几何转换函数

## 设计模式与设计决策

### 适配器模式
`PuckerBloatAdapter` 适配 JSON 动画数据到自定义的 `PuckerBloatEffect`:
- 转换 AE 百分比语义到归一化值
- 管理属性绑定和同步

### 模板方法模式
`GeometryEffect` 定义效果生命周期:
- `onRevalidateEffect` 由子类实现具体变形逻辑
- 基类处理缓存、失效和依赖管理

### 策略模式
路径归一化使用不同转换策略:
- 直线 → 控制点策略
- 二次曲线 → 标准转换策略
- 圆锥曲线 → 圆形近似策略
- 三次曲线 → 直接使用策略

### 访问者模式
路径迭代器变体:
- 遍历路径动词
- 根据动词类型执行不同操作
- 累积结果到新路径

## 性能考量

### 早期退出优化
```cpp
if (SkScalarNearlyZero(fAmount)) {
    return input;
}
```
无效果时直接返回原路径,避免不必要的计算。

### 向量预留
```cpp
std::vector<CubicInfo> cubics;
// 在循环中动态增长,但通常轮廓较小
```
未预留容量,因为轮廓大小事先未知,但通常较小。

### 紧密边界计算
```cpp
input.computeTightBounds()
```
使用紧密边界而非常规边界,提供更准确的中心点,但计算成本稍高。

### Lambda 函数内联
```cpp
auto commit_contour = [&]() { ... };
```
Lambda 函数可被编译器内联,避免函数调用开销。

### 移动语义
```cpp
std::move(child)  // 移动子节点
std::move(g)      // 移动几何节点
```
避免智能指针引用计数的原子操作。

### 路径构建器
```cpp
SkPathBuilder builder;
```
使用 `SkPathBuilder` 而非直接操作 `SkPath`,更高效(批量操作,延迟验证)。

### 三次曲线统一表示
归一化到三次曲线:
- 简化变形逻辑(单一代码路径)
- 更好的缓存局部性
- 向量化友好

### 可丢弃适配器
使用 `DiscardableAdapterBase`:
- `fAmount` 为 0 时可优化掉适配器
- 减少场景图节点数量

## 相关文件

- `modules/sksg/include/SkSGGeometryEffect.h`: `GeometryEffect` 基类
- `modules/sksg/include/SkSGGeometryNode.h`: 几何节点基类
- `modules/skottie/src/Adapter.h`: `DiscardableAdapterBase` 定义
- `modules/skottie/src/layers/shapelayer/ShapeLayer.h`: `ShapeBuilder` 定义
- `src/core/SkGeometry.h`: `SkConvertQuadToCubic` 等几何转换
- `include/core/SkPath.h`: Skia 路径 API
- `include/core/SkPathBuilder.h`: 路径构建器 API
- `modules/skottie/src/layers/shapelayer/RoundCorners.cpp`: 其他几何效果示例
