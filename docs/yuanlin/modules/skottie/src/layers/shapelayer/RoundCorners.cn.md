# RoundCorners

> 源文件: modules/skottie/src/layers/shapelayer/RoundCorners.cpp

## 概述

`RoundCorners.cpp` 实现了 Skottie 形状层系统中的圆角效果。该模块为几何路径添加圆角处理,通过动画化的半径参数平滑路径的尖锐拐角。这是 After Effects 圆角效果在 Skottie 中的实现,支持参数动画。

## 架构位置

该文件位于 Skottie 形状层几何效果子系统中:
- **模块**: `modules/skottie/src/layers/shapelayer/`
- **命名空间**: `skottie::internal`
- **依赖关系**: 依赖 SkSG 场景图的几何效果系统和 Skottie 适配器框架
- **角色**: 作为几何效果实现,通过 `ShapeBuilder` 附加到形状层

## 主要类与结构体

### RoundCornersAdapter
```cpp
class RoundCornersAdapter final : public DiscardableAdapterBase<RoundCornersAdapter, sksg::RoundEffect>
```
圆角适配器类,将 JSON 动画数据绑定到 SkSG 的 `RoundEffect` 节点。

**继承关系**:
- 继承自 `DiscardableAdapterBase` 模板基类
- 模板参数: `RoundCornersAdapter`(CRTP), `sksg::RoundEffect`(目标节点类型)

**成员变量**:
- `fRadius`: 圆角半径标量值(类型 `ScalarValue`)

**构造函数**:
```cpp
RoundCornersAdapter(const skjson::ObjectValue& jround,
                    const AnimationBuilder& abuilder,
                    sk_sp<sksg::GeometryNode> child)
```
- **参数**:
  - `jround`: JSON 圆角配置对象
  - `abuilder`: 动画构建器引用
  - `child`: 子几何节点智能指针
- **初始化**: 创建 `sksg::RoundEffect` 并将 JSON 的 `"r"` 字段绑定到 `fRadius`

**核心方法**:
- `onSync()`: 同步回调,将 `fRadius` 设置到底层 `RoundEffect` 节点

**设计特点**:
- 使用 CRTP(奇异递归模板模式)实现类型安全的基类功能
- 支持自动丢弃优化(通过 `DiscardableAdapterBase`)
- 继承了属性动画绑定能力

## 公共 API 函数

### AttachRoundGeometryEffect
```cpp
std::vector<sk_sp<sksg::GeometryNode>> ShapeBuilder::AttachRoundGeometryEffect(
    const skjson::ObjectValue& jround,
    const AnimationBuilder* abuilder,
    std::vector<sk_sp<sksg::GeometryNode>>&& geos)
```
为每个输入几何节点附加圆角效果。

**参数**:
- `jround`: JSON 圆角配置对象
- `abuilder`: 动画构建器指针
- `geos`: 要应用圆角的几何节点向量(右值引用)

**返回值**: 包含应用圆角效果后的几何节点向量

**JSON 参数映射**:
- `"r"`: 圆角半径(Radius),支持动画

**实现逻辑**:
1. 创建输出向量 `rounded` 并预留容量
2. 遍历所有输入几何节点
3. 对每个节点通过 `attachDiscardableAdapter` 创建 `RoundCornersAdapter`
4. 将包装后的节点添加到输出向量
5. 返回处理后的几何节点向量

**特点**:
- 支持批量处理多个几何节点
- 每个节点独立应用圆角效果
- 使用移动语义避免不必要的复制

## 内部实现细节

### 适配器绑定机制
```cpp
this->bind(abuilder, jround["r"], fRadius);
```
- 调用基类 `bind` 方法将 JSON 字段绑定到成员变量
- 支持静态值和关键帧动画
- 自动处理动画器的创建和管理

### 同步机制
```cpp
void onSync() override {
    this->node()->setRadius(fRadius);
}
```
- 每次动画 seek 后调用
- 将当前 `fRadius` 值同步到底层 `sksg::RoundEffect`
- 保持动画状态和渲染状态一致

### 可丢弃适配器
使用 `attachDiscardableAdapter` 而非普通的 `attachAdapter`:
```cpp
abuilder->attachDiscardableAdapter<RoundCornersAdapter>(jround, *abuilder, std::move(g))
```
- 如果圆角半径为 0 或效果不可见,适配器可以被优化掉
- 减少不必要的场景图节点
- 提高渲染性能

### CRTP 模式应用
```cpp
class RoundCornersAdapter final : public DiscardableAdapterBase<RoundCornersAdapter, sksg::RoundEffect>
```
- 基类通过模板参数获知派生类类型
- 实现编译时多态,避免虚函数开销
- 类型安全的静态调度

### 几何效果链
圆角效果是几何效果链的一部分:
```
原始几何 -> RoundEffect -> 其他效果 -> 最终几何
```
每个效果包装前一个几何节点,形成效果栈。

## 依赖关系

### 外部依赖
- **SkSG 场景图**:
  - `sksg::GeometryNode`: 几何节点基类
  - `sksg::RoundEffect`: 圆角效果实现
  - `sksg::GeometryEffect`: 几何效果基类

- **Skottie 框架**:
  - `AnimationBuilder`: 动画构建器
  - `DiscardableAdapterBase`: 可丢弃适配器基类
  - `ScalarValue`: 标量值类型
  - `ShapeBuilder`: 形状构建器

- **JSON 解析**:
  - `skjson::ObjectValue`: JSON 对象

### 内部依赖
- `modules/skottie/src/Adapter.h`: 适配器基类
- `modules/skottie/src/SkottiePriv.h`: AnimationBuilder 定义
- `modules/skottie/src/SkottieValue.h`: ScalarValue 定义
- `modules/skottie/src/layers/shapelayer/ShapeLayer.h`: ShapeBuilder 定义
- `modules/sksg/include/SkSGGeometryEffect.h`: 几何效果基类
- `modules/sksg/include/SkSGGeometryNode.h`: 几何节点接口

## 设计模式与设计决策

### 适配器模式
`RoundCornersAdapter` 适配两个接口:
- **源接口**: JSON 动画数据和 Skottie 动画系统
- **目标接口**: SkSG 的 `RoundEffect` 节点 API
- **作用**: 将声明式 JSON 动画转换为命令式场景图操作

### CRTP(奇异递归模板模式)
```cpp
DiscardableAdapterBase<RoundCornersAdapter, sksg::RoundEffect>
```
- 编译时多态,零运行时开销
- 基类可以调用派生类的静态已知方法
- 比虚函数更高效

### 装饰器模式
圆角效果装饰现有几何:
- `RoundEffect` 包装子几何节点
- 透明地添加圆角功能
- 不改变原始几何的接口

### 工厂方法
使用 `attachDiscardableAdapter` 创建适配器:
- 抽象适配器创建逻辑
- 支持生命周期管理
- 允许优化(可丢弃)

## 性能考量

### 内存预留
```cpp
rounded.reserve(geos.size());
```
预先分配向量容量,避免增长时的重新分配和复制。

### 移动语义
```cpp
std::move(child)  // 移动子节点
std::move(g)      // 移动几何节点
```
避免智能指针引用计数的原子操作。

### 可丢弃优化
使用 `DiscardableAdapterBase`:
- 半径为 0 时可跳过圆角处理
- 减少场景图节点数量
- 降低重新验证和渲染开销

### 直接同步
`onSync()` 直接设置半径:
```cpp
this->node()->setRadius(fRadius);
```
- 避免中间层和间接调用
- 单次函数调用,高效同步

### 批量处理
`AttachRoundGeometryEffect` 一次处理多个几何节点:
- 减少函数调用开销
- 利用空间局部性
- 向量化友好

### 编译时优化
`final` 关键字:
```cpp
class RoundCornersAdapter final
```
- 告知编译器不会有派生类
- 允许去虚拟化优化
- 可能内联虚函数调用

## 相关文件

- `modules/sksg/include/SkSGGeometryEffect.h`: `RoundEffect` 实现
- `modules/sksg/include/SkSGGeometryNode.h`: 几何节点基类
- `modules/skottie/src/Adapter.h`: `DiscardableAdapterBase` 定义
- `modules/skottie/src/layers/shapelayer/ShapeLayer.h`: `ShapeBuilder` 和形状层系统
- `modules/skottie/src/SkottiePriv.h`: `AnimationBuilder` 和内部工具
- `modules/skottie/src/SkottieValue.h`: `ScalarValue` 类型定义
- `modules/skottie/src/layers/shapelayer/TrimPaths.cpp`: 其他几何效果实现
- `modules/skottie/src/layers/shapelayer/OffsetPaths.cpp`: 路径偏移效果
