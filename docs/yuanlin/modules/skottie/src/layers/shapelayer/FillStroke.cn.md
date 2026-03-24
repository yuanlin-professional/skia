# FillStroke

> 源文件: modules/skottie/src/layers/shapelayer/FillStroke.cpp

## 概述

`FillStroke.cpp` 实现了 Skottie 形状层系统中的填充和描边绘制功能。该模块处理形状的视觉渲染属性,包括纯色/渐变填充、描边样式(宽度、端点、连接)、不透明度和虚线效果。这是 After Effects 形状层绘制系统在 Skottie 中的核心实现。

## 架构位置

该文件位于 Skottie 形状层绘制子系统中:
- **模块**: `modules/skottie/src/layers/shapelayer/`
- **命名空间**: `skottie::internal`
- **依赖关系**: 依赖 SkSG 场景图的绘制节点和几何效果系统
- **角色**: 作为 `ShapeBuilder` 的一部分,提供填充和描边绘制能力

## 主要类与结构体

### FillStrokeAdapter
```cpp
class FillStrokeAdapter final : public DiscardableAdapterBase<FillStrokeAdapter, sksg::PaintNode>
```
填充/描边适配器类,管理绘制属性的动画和同步。

**Type 枚举**:
```cpp
enum class Type { kFill, kStroke };
```
区分填充和描边两种模式。

**成员变量**:
- `fShaderType`: 着色器类型(颜色或渐变)
- `fColor`: 颜色值(仅颜色着色器使用)
- `fOpacity`: 不透明度(默认 100)
- `fStrokeWidth`: 描边宽度(默认 1,仅描边使用)

**构造函数参数**:
- `jpaint`: JSON 绘制配置对象
- `abuilder`: 动画构建器引用
- `paint_node`: 绘制节点智能指针
- `gradient_adapter`: 渐变适配器(可选,null 表示纯色)
- `type`: 填充或描边类型

**构造逻辑**:
1. 附加渐变适配器(如果存在)
2. 绑定不透明度 "o" 属性
3. 启用抗锯齿
4. **描边特有配置**:
   - 绑定描边宽度 "w"
   - 设置描边样式
   - 配置斜接限制 "ml"(默认 4.0)
   - 配置线段连接 "lj"(Miter/Round/Bevel)
   - 配置线段端点 "lc"(Butt/Round/Square)
5. 绑定颜色 "c"(仅纯色)

**核心方法**:
```cpp
void onSync() override
```
同步绘制属性:
- 设置不透明度(转换为 0-1 范围)
- 设置描边宽度
- 如果是颜色着色器,设置颜色

### DashAdapter
```cpp
class DashAdapter final : public DiscardableAdapterBase<DashAdapter, sksg::DashEffect>
```
虚线适配器类,实现虚线/点线描边效果。

**成员变量**:
- `fIntervals`: 间隔数组(交替的实线/空白长度)
- `fOffset`: 虚线偏移/相位(默认 0)

**构造函数**:
```cpp
DashAdapter(const skjson::ArrayValue& jdash,
            const AnimationBuilder& abuilder,
            sk_sp<sksg::GeometryNode> geo)
```
- JSON 数组编码任意数量的间隔值 + 单个尾随偏移
- 最后一个值是偏移,其余是间隔
- 每个值可独立动画

**核心方法**:
```cpp
void onSync() override
```
- 设置虚线相位(偏移)
- 设置间隔数组

## 公共 API 函数

### AttachFill
```cpp
sk_sp<sksg::PaintNode> ShapeBuilder::AttachFill(
    const skjson::ObjectValue& jpaint,
    const AnimationBuilder* abuilder,
    sk_sp<sksg::PaintNode> paint_node,
    sk_sp<AnimatablePropertyContainer> gradient)
```
附加填充适配器到绘制节点。

**参数**:
- `jpaint`: JSON 填充配置
- `abuilder`: 动画构建器
- `paint_node`: 基础绘制节点(颜色或渐变)
- `gradient`: 渐变适配器(可选)

**返回值**: 配置好的绘制节点

### AttachStroke
```cpp
sk_sp<sksg::PaintNode> ShapeBuilder::AttachStroke(
    const skjson::ObjectValue& jpaint,
    const AnimationBuilder* abuilder,
    sk_sp<sksg::PaintNode> paint_node,
    sk_sp<AnimatablePropertyContainer> gradient)
```
附加描边适配器到绘制节点(类似 `AttachFill`,但类型为 `kStroke`)。

### AttachColorFill
```cpp
sk_sp<sksg::PaintNode> ShapeBuilder::AttachColorFill(
    const skjson::ObjectValue& jpaint,
    const AnimationBuilder* abuilder)
```
创建并配置纯色填充。

**实现**:
1. 创建黑色 `sksg::Color` 节点
2. 调用 `AttachFill` 配置
3. 分发颜色属性(用于属性观察)
4. 返回填充绘制节点

### AttachColorStroke
```cpp
sk_sp<sksg::PaintNode> ShapeBuilder::AttachColorStroke(
    const skjson::ObjectValue& jpaint,
    const AnimationBuilder* abuilder)
```
创建并配置纯色描边(类似 `AttachColorFill`,但为描边)。

### AdjustStrokeGeometry
```cpp
std::vector<sk_sp<sksg::GeometryNode>> ShapeBuilder::AdjustStrokeGeometry(
    const skjson::ObjectValue& jstroke,
    const AnimationBuilder* abuilder,
    std::vector<sk_sp<sksg::GeometryNode>>&& geos)
```
为描边几何节点应用虚线效果。

**参数**:
- `jstroke`: JSON 描边配置(可能包含虚线数组 "d")
- `abuilder`: 动画构建器
- `geos`: 几何节点向量

**返回值**: 应用虚线效果后的几何节点向量

**实现**:
- 检查 "d" 字段是否存在且长度 > 1
- 如果存在,为每个几何节点附加 `DashAdapter`
- 返回调整后的几何

## 内部实现细节

### JSON 参数映射

**通用参数**:
- `"o"`: 不透明度(Opacity),0-100

**纯色参数**:
- `"c"`: 颜色(Color),RGB 数组

**描边专有参数**:
- `"w"`: 宽度(Width)
- `"ml"`: 斜接限制(Miter Limit),默认 4.0
- `"lj"`: 线段连接(Line Join)
  - `1`: Miter(尖角)
  - `2`: Round(圆角)
  - `3`: Bevel(斜角)
- `"lc"`: 线段端点(Line Cap)
  - `1`: Butt(平头)
  - `2`: Round(圆头)
  - `3`: Square(方头)
- `"d"`: 虚线数组(Dash Array)

### 线段连接和端点映射
```cpp
static constexpr SkPaint::Join gJoins[] = {
    SkPaint::kMiter_Join,
    SkPaint::kRound_Join,
    SkPaint::kBevel_Join,
};

static constexpr SkPaint::Cap gCaps[] = {
    SkPaint::kButt_Cap,
    SkPaint::kRound_Cap,
    SkPaint::kSquare_Cap,
};
```
使用静态常量数组映射 JSON 索引(1-based)到 Skia 枚举(0-based)。

### 着色器类型检测
```cpp
fShaderType(gradient_adapter ? ShaderType::kGradient : ShaderType::kColor)
```
根据是否存在渐变适配器决定着色器类型。

### 条件绑定
```cpp
if (fShaderType == ShaderType::kColor) {
    this->bind(abuilder, jpaint["c"], fColor);
}
```
仅在纯色模式下绑定颜色属性,渐变模式下颜色由渐变适配器管理。

### 虚线编码
虚线数组结构:
```
[interval0, interval1, ..., intervalN, offset]
```
- 前 N 个值: 交替的实线/空白长度
- 最后一个值: 虚线相位偏移

### 类型向下转换
```cpp
auto* color_node = static_cast<sksg::Color*>(this->node().get());
color_node->setColor(fColor);
```
在 `onSync()` 中,对于颜色着色器,安全地向下转换为 `sksg::Color*` 以设置颜色。

### 可丢弃适配器优化
两个适配器都继承 `DiscardableAdapterBase`:
- `FillStrokeAdapter`: 不透明度为 0 时可优化
- `DashAdapter`: 间隔为空或无效时可优化

## 依赖关系

### 外部依赖
- **Skia 核心**:
  - `SkPaint`: 绘制属性容器
  - `SkColor`: 颜色类型
  - `SkScalar`: 标量类型
  - `SkPaint::Join`: 线段连接枚举
  - `SkPaint::Cap`: 线段端点枚举

- **SkSG 场景图**:
  - `sksg::PaintNode`: 绘制节点基类
  - `sksg::Color`: 纯色绘制节点
  - `sksg::DashEffect`: 虚线效果
  - `sksg::GeometryNode`: 几何节点
  - `sksg::GeometryEffect`: 几何效果基类

- **Skottie 框架**:
  - `AnimationBuilder`: 动画构建器
  - `DiscardableAdapterBase`: 可丢弃适配器基类
  - `AnimatablePropertyContainer`: 可动画属性容器
  - `ColorValue`, `ScalarValue`: 值类型
  - `ShapeBuilder`: 形状构建器

### 内部依赖
- `modules/skottie/src/Adapter.h`: 适配器基类
- `modules/skottie/src/SkottiePriv.h`: AnimationBuilder 定义
- `modules/skottie/src/SkottieValue.h`: 值类型定义
- `modules/skottie/src/layers/shapelayer/ShapeLayer.h`: ShapeBuilder 定义
- `modules/sksg/include/SkSGPaint.h`: 绘制节点接口
- `modules/sksg/include/SkSGGeometryEffect.h`: 虚线效果实现

## 设计模式与设计决策

### 适配器模式
两个适配器类适配不同接口:
- `FillStrokeAdapter`: JSON 动画数据 → SkSG 绘制节点
- `DashAdapter`: JSON 虚线数组 → SkSG 虚线效果

### 策略模式
`FillStrokeAdapter` 根据类型使用不同策略:
- **Type::kFill**: 填充策略(无描边属性)
- **Type::kStroke**: 描边策略(额外的宽度、连接、端点配置)

### 工厂方法模式
提供多个工厂方法创建不同配置:
- `AttachFill` / `AttachStroke`: 通用工厂
- `AttachColorFill` / `AttachColorStroke`: 纯色专用工厂

### 组合模式
绘制和效果组合成渲染树:
```
几何节点 → [DashEffect] → 绘制节点 → 渲染
```

### 模板方法模式
`DiscardableAdapterBase` 定义适配器生命周期,子类实现 `onSync()`。

## 性能考量

### 常量查找表
```cpp
static constexpr SkPaint::Join gJoins[] = {...};
static constexpr SkPaint::Cap gCaps[] = {...};
```
编译时常量,零运行时开销。

### 条件属性绑定
```cpp
if (type == Type::kStroke) {
    this->bind(abuilder, jpaint["w"], fStrokeWidth);
    // ...
}
```
仅绑定相关属性,避免不必要的动画器创建。

### 边界检查
```cpp
std::min<size_t>(ParseDefault<size_t>(jpaint["lj"], 1) - 1, std::size(gJoins) - 1)
```
安全的数组访问,防止越界。

### 移动语义
```cpp
std::move(paint_node)
std::move(gradient)
std::move(geos[i])
```
避免智能指针的引用计数开销。

### 抗锯齿默认启用
```cpp
this->node()->setAntiAlias(true);
```
提供更好的视觉质量,对性能影响较小(现代 GPU 优化)。

### 虚线条件应用
```cpp
if (jdash && jdash->size() > 1) {
    // 附加虚线效果
}
```
仅在实际需要虚线时创建效果节点。

### 属性分发优化
```cpp
abuilder->dispatchColorProperty(color_node);
```
仅对新创建的颜色节点分发属性,不重复分发。

## 相关文件

- `modules/sksg/include/SkSGPaint.h`: `PaintNode`, `Color` 定义
- `modules/sksg/include/SkSGGeometryEffect.h`: `DashEffect` 实现
- `modules/skottie/src/Adapter.h`: `DiscardableAdapterBase` 定义
- `modules/skottie/src/layers/shapelayer/ShapeLayer.h`: `ShapeBuilder` 定义
- `modules/skottie/src/layers/shapelayer/Gradient.cpp`: 渐变填充/描边实现
- `modules/skottie/src/SkottieValue.h`: `ColorValue`, `ScalarValue` 定义
- `include/core/SkPaint.h`: Skia 绘制属性 API
