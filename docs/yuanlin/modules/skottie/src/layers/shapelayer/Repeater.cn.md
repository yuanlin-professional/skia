# Repeater

> 源文件: modules/skottie/src/layers/shapelayer/Repeater.cpp

## 概述

`Repeater.cpp` 实现了 Skottie 形状层系统中的重复器效果。该模块允许以不同的变换参数(位置、缩放、旋转)和不透明度渐变多次渲染形状内容,创建图案重复和动画效果。这是 After Effects Repeater 效果在 Skottie 中的实现,常用于创建阵列、图案和复杂的几何设计。

## 架构位置

该文件位于 Skottie 形状层绘制效果子系统中:
- **模块**: `modules/skottie/src/layers/shapelayer/`
- **命名空间**: `skottie::internal`
- **依赖关系**: 依赖 SkSG 场景图的自定义渲染节点系统
- **角色**: 作为绘制效果实现,通过 `ShapeBuilder` 附加到形状层

## 主要类与结构体

### RepeaterRenderNode
```cpp
class RepeaterRenderNode final : public sksg::CustomRenderNode
```
重复器渲染节点,执行多次子节点渲染并应用实例变换。

**CompositeMode 枚举**:
```cpp
enum class CompositeMode { kBelow, kAbove };
```
定义合成顺序:
- **kBelow**: 从下到上(先渲染的在底层)
- **kAbove**: 从上到下(先渲染的在顶层)

**成员变量**:
- `fMode`: 合成模式
- `fChildrenBounds`: 缓存的子节点边界
- `fCount`: 重复次数(默认 0)
- `fOffset`: 偏移量(默认 0)
- `fRotation`: 旋转角度(默认 0)
- `fStartOpacity`: 起始不透明度(默认 1)
- `fEndOpacity`: 结束不透明度(默认 1)
- `fAnchorPoint`: 锚点(默认 {0,0})
- `fPosition`: 位置(默认 {0,0})
- `fScale`: 缩放(默认 {1,1})

**属性宏**:
使用 `SG_ATTRIBUTE` 定义所有可设置属性,自动生成 getter/setter。

**核心方法**:

#### instanceTransform
```cpp
SkMatrix instanceTransform(size_t i) const
```
计算第 `i` 个实例的变换矩阵:
```
t = fOffset + i
变换 = 平移(t*位置 + 锚点) * 旋转(t*旋转) * 缩放(缩放^t) * 平移(-锚点)
```
- 位置、旋转线性缩放
- 缩放指数缩放(`std::pow`)

#### onRevalidate
```cpp
SkRect onRevalidate(sksg::InvalidationController* ic, const SkMatrix& ctm) override
```
重新验证并计算总边界:
1. 重新验证所有子节点
2. 计算子节点的联合边界
3. 对每个实例的变换后边界求并集

#### onRender
```cpp
void onRender(SkCanvas* canvas, const RenderContext* ctx) const override
```
渲染所有实例:
1. 计算不透明度增量:`dOpacity = (结束-起始) / 次数`
2. 根据合成模式确定渲染顺序
3. 对每个实例:
   - 跳过不透明度 <= 0 的实例
   - 应用实例变换
   - 调制不透明度
   - 设置隔离(如有多个子节点)
   - 渲染所有子节点

### RepeaterAdapter
```cpp
class RepeaterAdapter final : public DiscardableAdapterBase<RepeaterAdapter, RepeaterRenderNode>
```
重复器适配器类,将 JSON 动画数据绑定到 `RepeaterRenderNode`。

**成员变量**:
- **重复器属性**: `fCount`, `fOffset`
- **变换属性**: `fAnchorPoint`, `fPosition`, `fScale`, `fRotation`, `fStartOpacity`, `fEndOpacity`

**构造函数**:
```cpp
RepeaterAdapter(const skjson::ObjectValue& jrepeater,
                const skjson::ObjectValue& jtransform,
                const AnimationBuilder& abuilder,
                std::vector<sk_sp<sksg::RenderNode>>&& draws)
```
- 创建 `RepeaterRenderNode` 并解析合成模式
- 绑定重复器属性("c", "o")
- 绑定变换属性("a", "p", "s", "r", "so", "eo")

**核心方法**:
```cpp
void onSync() override
```
同步所有属性:
- 限制次数到 [0, 1024] 并四舍五入
- 转换缩放(百分比 → 比例)
- 转换不透明度(百分比 → [0,1])

## 公共 API 函数

### AttachRepeaterDrawEffect
```cpp
std::vector<sk_sp<sksg::RenderNode>> ShapeBuilder::AttachRepeaterDrawEffect(
    const skjson::ObjectValue& jrepeater,
    const AnimationBuilder* abuilder,
    std::vector<sk_sp<sksg::RenderNode>>&& draws)
```
为绘制节点附加重复器效果。

**参数**:
- `jrepeater`: JSON 重复器配置对象
- `abuilder`: 动画构建器指针
- `draws`: 要重复的绘制节点向量(右值引用)

**返回值**: 包含重复器节点的绘制节点向量

**JSON 参数映射**:
- **重复器参数**:
  - `"c"`: 次数(Count)
  - `"o"`: 偏移(Offset)
  - `"m"`: 合成模式(Mode)
    - `1`: Below(从下到上)
    - `其他`: Above(从上到下)
  - `"tr"`: 变换对象

- **变换参数** (在 "tr" 对象中):
  - `"a"`: 锚点(Anchor)
  - `"p"`: 位置(Position)
  - `"s"`: 缩放(Scale)
  - `"r"`: 旋转(Rotation)
  - `"so"`: 起始不透明度(Start Opacity)
  - `"eo"`: 结束不透明度(End Opacity)

**实现逻辑**:
1. 检查是否存在变换对象 "tr"
2. 如果存在:
   - 反转绘制顺序(输入是上→下,需要转为绘制顺序)
   - 创建 `RepeaterAdapter`
   - 返回包含单个重复器节点的向量
3. 如果不存在:
   - 直接返回原始绘制节点(无重复)

## 内部实现细节

### 实例变换计算
```cpp
const auto t = fOffset + i;
SkMatrix::Translate(t * fPosition.x + fAnchorPoint.x, t * fPosition.y + fAnchorPoint.y)
  * SkMatrix::RotateDeg(t * fRotation)
  * SkMatrix::Scale(std::pow(fScale.x, t), std::pow(fScale.y, t))
  * SkMatrix::Translate(-fAnchorPoint.x, -fAnchorPoint.y);
```

**变换顺序**:
1. 平移到锚点相对的实例位置
2. 应用旋转(随索引线性增长)
3. 应用缩放(随索引指数增长)
4. 平移回原点(移除锚点偏移)

### 不透明度渐变
```cpp
const auto dOpacity = fCount > 1 ? (fEndOpacity - fStartOpacity) / fCount : 0.0f;
const auto opacity = fStartOpacity + dOpacity * render_index;
```

**注释说明**:
```cpp
// To cover the full opacity range, the denominator below should be (fCount - 1).
// Interstingly, that's not what AE does. Off-by-one bug?
```
使用 `fCount` 而非 `fCount - 1` 作为分母,匹配 AE 的行为(可能是 AE 的 bug)。

### 渲染顺序
```cpp
const auto render_index = fMode == CompositeMode::kAbove ? i : fCount - i - 1;
```
- **kAbove**: 正序渲染(0, 1, 2, ...)
- **kBelow**: 反序渲染(n-1, n-2, ..., 0)

### 不透明度优化
```cpp
if (opacity <= 0) {
    continue;
}
```
跳过完全透明的实例,避免不必要的渲染。

### 隔离层条件
```cpp
.setIsolation(fChildrenBounds, canvas->getTotalMatrix(), children.size() > 1)
```
仅当有多个子节点时设置隔离,单子节点无需额外层。

### 次数限制
```cpp
static constexpr SkScalar kMaxCount = 1024;
this->node()->setCount(static_cast<size_t>(SkTPin(fCount, 0.0f, kMaxCount) + 0.5f));
```
- 限制最大次数为 1024(防止性能问题)
- 四舍五入到最接近的整数

### 绘制顺序反转
```cpp
std::reverse(draws.begin(), draws.end());
```
输入绘制节点是从上到下(逻辑顺序),需要反转为从下到上(绘制顺序)。

## 依赖关系

### 外部依赖
- **Skia 核心**:
  - `SkCanvas`: 画布 API
  - `SkMatrix`: 变换矩阵
  - `SkM44`: 4x4 矩阵(未直接使用)
  - `SkRect`: 矩形
  - `SkScalar`: 标量类型
  - `SkTPin`: 值限制函数

- **SkSG 场景图**:
  - `sksg::CustomRenderNode`: 自定义渲染节点基类
  - `sksg::RenderNode`: 渲染节点基类
  - `sksg::InvalidationController`: 失效控制器

- **Skottie 框架**:
  - `AnimationBuilder`: 动画构建器
  - `DiscardableAdapterBase`: 可丢弃适配器基类
  - `ScalarValue`, `Vec2Value`: 值类型
  - `ShapeBuilder`: 形状构建器
  - `ScopedRenderContext`: 作用域渲染上下文

### 内部依赖
- `modules/skottie/src/Adapter.h`: 适配器基类
- `modules/skottie/src/SkottiePriv.h`: AnimationBuilder 和渲染上下文
- `modules/skottie/src/SkottieValue.h`: 值类型定义
- `modules/skottie/src/layers/shapelayer/ShapeLayer.h`: ShapeBuilder 定义
- `modules/sksg/include/SkSGRenderNode.h`: 渲染节点接口

## 设计模式与设计决策

### 适配器模式
`RepeaterAdapter` 适配 JSON 动画数据到自定义的 `RepeaterRenderNode`。

### 模板方法模式
`CustomRenderNode` 定义渲染生命周期,子类实现特定逻辑。

### 组合模式
重复器包含多个子渲染节点,递归渲染。

### 策略模式
`CompositeMode` 实现不同的渲染顺序策略。

### 迭代器模式变体
循环渲染实例,每次应用不同的变换和不透明度。

## 性能考量

### 次数限制
```cpp
static constexpr SkScalar kMaxCount = 1024;
```
防止过大的重复次数导致性能崩溃。

### 不透明度早期退出
```cpp
if (opacity <= 0) {
    continue;
}
```
跳过不可见实例,节省渲染开销。

### 边界缓存
```cpp
SkRect fChildrenBounds = SkRect::MakeEmpty(); // cached
```
缓存子节点边界,避免重复计算。

### 条件隔离
```cpp
children.size() > 1
```
单子节点不创建隔离层,减少图层开销。

### 变换矩阵计算
使用 Skia 的矩阵链乘优化:
```cpp
SkMatrix::Translate(...) * SkMatrix::RotateDeg(...) * SkMatrix::Scale(...)
```
编译器可能优化为单次矩阵构建。

### 移动语义
```cpp
std::move(draws)    // 移动绘制节点向量
std::move(children) // 移动到父类
```
避免向量和智能指针的深拷贝。

### 内存预留
```cpp
repeater_draws.reserve(1);
```
仅预留单个元素(重复器总是产生单个节点)。

## 相关文件

- `modules/sksg/include/SkSGRenderNode.h`: `CustomRenderNode` 基类
- `modules/skottie/src/Adapter.h`: `DiscardableAdapterBase` 定义
- `modules/skottie/src/layers/shapelayer/ShapeLayer.h`: `ShapeBuilder` 定义
- `modules/skottie/src/SkottiePriv.h`: `ScopedRenderContext` 和渲染上下文
- `modules/skottie/src/SkottieValue.h`: `Vec2Value`, `ScalarValue` 定义
- `include/core/SkCanvas.h`: Skia 画布 API
- `include/core/SkMatrix.h`: 变换矩阵 API
- `include/private/base/SkTPin.h`: 值限制函数
