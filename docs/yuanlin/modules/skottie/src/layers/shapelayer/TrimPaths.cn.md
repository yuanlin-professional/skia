# TrimPaths

> 源文件: modules/skottie/src/layers/shapelayer/TrimPaths.cpp

## 概述

`TrimPaths.cpp` 实现了 Skottie 形状层系统中的路径修剪效果。该模块允许通过起始点、结束点和偏移参数动画化地显示路径的部分段,支持并行和串行两种修剪模式。这是 After Effects Trim Paths 效果在 Skottie 中的实现,常用于创建绘制动画和加载动画。

## 架构位置

该文件位于 Skottie 形状层几何效果子系统中:
- **模块**: `modules/skottie/src/layers/shapelayer/`
- **命名空间**: `skottie::internal`
- **依赖关系**: 依赖 SkSG 场景图的几何效果系统和 Skia 的 `SkTrimPathEffect`
- **角色**: 作为几何效果实现,通过 `ShapeBuilder` 附加到形状层

## 主要类与结构体

### TrimEffectAdapter
```cpp
class TrimEffectAdapter final : public DiscardableAdapterBase<TrimEffectAdapter, sksg::TrimEffect>
```
路径修剪适配器类,将 JSON 动画数据绑定到 SkSG 的 `TrimEffect` 节点。

**继承关系**:
- 继承自 `DiscardableAdapterBase` 模板基类
- 模板参数: `TrimEffectAdapter`(CRTP), `sksg::TrimEffect`(目标节点类型)

**成员变量**:
- `fStart`: 起始百分比(默认 0)
- `fEnd`: 结束百分比(默认 100)
- `fOffset`: 偏移角度(默认 0)

**构造函数**:
```cpp
TrimEffectAdapter(const skjson::ObjectValue& jtrim,
                  const AnimationBuilder& abuilder,
                  sk_sp<sksg::GeometryNode> child)
```
- 创建 `sksg::TrimEffect` 并绑定 JSON 的 "s"(start), "e"(end), "o"(offset) 字段

**核心方法**:
```cpp
void onSync() override
```
复杂的同步逻辑:
1. 将百分比转换为 0-1 范围:`start/100`, `end/100`
2. 将偏移从角度转换为比例:`offset/360`
3. 计算实际的 `startT` 和 `stopT`(考虑偏移)
4. 处理跨周期情况(当 `stopT - startT >= 1` 时显示完整路径)
5. 归一化到 [0,1] 范围并处理反转模式
6. 设置到底层 `TrimEffect` 节点

### Mode 枚举
```cpp
enum class Mode {
    kParallel, // "m": 1 (Trim Multiple Shapes: Simultaneously)
    kSerial,   // "m": 2 (Trim Multiple Shapes: Individually)
}
```
定义修剪模式:
- **kParallel**: 并行修剪,每个形状独立应用修剪效果
- **kSerial**: 串行修剪,先合并所有形状再修剪

## 公共 API 函数

### AttachTrimGeometryEffect
```cpp
std::vector<sk_sp<sksg::GeometryNode>> ShapeBuilder::AttachTrimGeometryEffect(
    const skjson::ObjectValue& jtrim,
    const AnimationBuilder* abuilder,
    std::vector<sk_sp<sksg::GeometryNode>>&& geos)
```
为几何节点附加路径修剪效果。

**参数**:
- `jtrim`: JSON 修剪配置对象
- `abuilder`: 动画构建器指针
- `geos`: 要修剪的几何节点向量(右值引用)

**返回值**: 包含应用修剪效果后的几何节点向量

**JSON 参数映射**:
- `"s"`: 起始百分比(Start),0-100
- `"e"`: 结束百分比(End),0-100
- `"o"`: 偏移角度(Offset),以度为单位
- `"m"`: 修剪模式(Mode)
  - `1`: 并行(Simultaneously)
  - `2`: 串行(Individually)

**实现逻辑**:
1. 解析修剪模式,默认为并行(1)
2. **串行模式**: 先将所有几何节点通过 `MergeGeometry` 合并为单个节点
3. **并行模式**: 直接使用输入几何节点
4. 对每个输入节点创建 `TrimEffectAdapter`
5. 返回修剪后的几何节点向量

## 内部实现细节

### BM 语义转换
After Effects/Bodymovin 使用特殊的参数单位:
```cpp
// BM semantics: start/end are percentages, offset is "degrees" (?!).
const auto  start = fStart  / 100,    // 百分比转比例
              end = fEnd    / 100,    // 百分比转比例
           offset = fOffset / 360;    // 角度转比例
```

### 修剪范围计算
```cpp
auto startT = std::min(start, end) + offset,
      stopT = std::max(start, end) + offset;
```
- 确保 `startT <= stopT`(通过 min/max)
- 应用偏移到起始和结束点

### 跨周期处理
```cpp
if (stopT - startT < 1) {
    // 部分路径显示,需要归一化
    startT -= SkScalarFloorToScalar(startT);
    stopT  -= SkScalarFloorToScalar(stopT);

    if (startT > stopT) {
        using std::swap;
        swap(startT, stopT);
        mode = SkTrimPathEffect::Mode::kInverted;
    }
} else {
    // 显示完整路径
    startT = 0;
    stopT  = 1;
}
```

**归一化逻辑**:
- `SkScalarFloorToScalar` 移除整数部分,将值映射到 [0,1)
- 如果归一化后 `startT > stopT`,说明跨越了周期边界
- 交换两者并使用反转模式(`kInverted`)

### 串行 vs 并行模式
**串行模式**(m=2):
```cpp
inputs.push_back(ShapeBuilder::MergeGeometry(std::move(geos), sksg::Merge::Mode::kMerge));
```
- 先合并所有几何为单个节点
- 作为整体应用修剪
- 修剪沿整个合并路径的长度计算

**并行模式**(m=1):
```cpp
inputs = std::move(geos);
```
- 每个几何节点独立修剪
- 修剪百分比相对于各自路径长度

### 可丢弃适配器优化
使用 `attachDiscardableAdapter`:
```cpp
abuilder->attachDiscardableAdapter<TrimEffectAdapter>(jtrim, *abuilder, i)
```
- 如果起始=0且结束=100(无修剪),适配器可被优化掉
- 减少场景图复杂度

## 依赖关系

### 外部依赖
- **Skia 核心**:
  - `SkScalar`: 标量类型
  - `SkTrimPathEffect`: 路径修剪效果基础实现
  - `SkScalarFloorToScalar`: 浮点数取整

- **SkSG 场景图**:
  - `sksg::GeometryNode`: 几何节点基类
  - `sksg::TrimEffect`: 修剪效果实现
  - `sksg::GeometryEffect`: 几何效果基类
  - `sksg::Merge`: 合并节点

- **Skottie 框架**:
  - `AnimationBuilder`: 动画构建器
  - `DiscardableAdapterBase`: 可丢弃适配器基类
  - `ScalarValue`: 标量值类型
  - `ShapeBuilder`: 形状构建器

### 内部依赖
- `modules/skottie/src/Adapter.h`: 适配器基类
- `modules/skottie/src/SkottiePriv.h`: AnimationBuilder 定义
- `modules/skottie/src/SkottieValue.h`: ScalarValue 定义
- `modules/skottie/src/layers/shapelayer/ShapeLayer.h`: ShapeBuilder 和 MergeGeometry
- `modules/sksg/include/SkSGGeometryEffect.h`: 几何效果基类
- `include/effects/SkTrimPathEffect.h`: Skia 路径修剪效果

## 设计模式与设计决策

### 适配器模式
`TrimEffectAdapter` 适配 JSON 动画数据到 SkSG 场景图:
- 转换 After Effects 语义到 Skia 语义
- 处理单位转换(百分比、角度)
- 管理复杂的边界条件

### 策略模式
两种修剪模式实现不同策略:
- **串行策略**: 合并后修剪(整体路径)
- **并行策略**: 独立修剪(相对路径)

### 模板方法模式
`DiscardableAdapterBase` 定义适配器生命周期:
- 构造时绑定属性
- `onSync()` 由子类实现同步逻辑
- 基类处理丢弃优化

### 组合模式
修剪效果组合到几何树:
```
原始几何 -> TrimEffect -> 其他效果 -> 最终几何
```

## 性能考量

### 内存预留
```cpp
trimmed.reserve(inputs.size());
```
避免向量增长时的重新分配。

### 移动语义
```cpp
std::move(geos)  // 移动输入向量
std::move(child) // 移动子节点
```
避免智能指针引用计数的原子操作开销。

### 快速路径优化
```cpp
if (stopT - startT >= 1) {
    startT = 0;
    stopT  = 1;
}
```
检测完整路径显示情况,跳过复杂的归一化逻辑。

### 条件合并
仅在串行模式下执行合并:
```cpp
if (mode == Mode::kSerial) {
    inputs.push_back(ShapeBuilder::MergeGeometry(...));
}
```
并行模式避免不必要的合并开销。

### 可丢弃优化
使用 `DiscardableAdapterBase`:
- 无效果时(start=0, end=100, offset=0)可优化掉适配器
- 减少场景图遍历成本
- 降低内存占用

### 浮点数处理
使用 `SkScalarFloorToScalar` 而非 `std::floor`:
- Skia 优化的浮点运算
- 可能使用平台特定的快速实现
- 与 Skia 的浮点语义一致

## 相关文件

- `include/effects/SkTrimPathEffect.h`: Skia 路径修剪效果
- `modules/sksg/include/SkSGGeometryEffect.h`: `TrimEffect` 实现
- `modules/sksg/include/SkSGGeometryNode.h`: 几何节点基类
- `modules/skottie/src/Adapter.h`: `DiscardableAdapterBase` 定义
- `modules/skottie/src/layers/shapelayer/ShapeLayer.h`: `ShapeBuilder` 和 `MergeGeometry`
- `modules/skottie/src/layers/shapelayer/RoundCorners.cpp`: 其他几何效果示例
- `modules/sksg/include/SkSGMerge.h`: 合并节点实现
