# MergePaths

> 源文件: modules/skottie/src/layers/shapelayer/MergePaths.cpp

## 概述

`MergePaths.cpp` 实现了 Skottie 形状层系统中的路径合并功能。该模块提供将多个几何节点通过不同的布尔运算模式(合并、并集、差集、交集、异或)组合成单个几何节点的能力。这是 After Effects 风格路径操作在 Skottie 中的实现。

## 架构位置

该文件位于 Skottie 形状层子系统中:
- **模块**: `modules/skottie/src/layers/shapelayer/`
- **命名空间**: `skottie::internal`
- **依赖关系**: 依赖 SkSG 场景图系统的几何节点和合并节点
- **角色**: 作为 `ShapeBuilder` 的一部分,提供路径合并效果

## 主要类与结构体

该文件主要扩展 `ShapeBuilder` 类,添加两个静态方法,不定义新的类或结构体。

### ShapeBuilder 扩展方法

#### MergeGeometry
```cpp
sk_sp<sksg::Merge> ShapeBuilder::MergeGeometry(
    std::vector<sk_sp<sksg::GeometryNode>>&& geos,
    sksg::Merge::Mode mode)
```
核心合并函数,将多个几何节点按指定模式合并。

#### AttachMergeGeometryEffect
```cpp
std::vector<sk_sp<sksg::GeometryNode>> ShapeBuilder::AttachMergeGeometryEffect(
    const skjson::ObjectValue& jmerge,
    const AnimationBuilder*,
    std::vector<sk_sp<sksg::GeometryNode>>&& geos)
```
从 JSON 数据解析并附加合并几何效果。

## 公共 API 函数

### MergeGeometry
将几何节点向量合并为单个 `sksg::Merge` 节点。

**参数**:
- `geos`: 要合并的几何节点向量(右值引用,移动语义)
- `mode`: 合并模式

**返回值**: `sksg::Merge` 智能指针

**实现细节**:
1. 预留 `merge_recs` 容量以避免重新分配
2. 遍历所有几何节点,构造 `sksg::Merge::Rec` 记录
3. 第一个几何节点使用 `kMerge` 模式,后续节点使用指定的 `mode`
4. 调用 `sksg::Merge::Make` 创建合并节点

**特殊处理**:
第一个几何节点总是使用 `kMerge` 模式作为基础,后续几何节点才应用指定的布尔运算。

### AttachMergeGeometryEffect
从 JSON 对象解析合并参数并应用合并效果。

**参数**:
- `jmerge`: JSON 合并配置对象
- `abuilder`: 动画构建器指针(当前未使用)
- `geos`: 要合并的几何节点向量

**返回值**: 包含单个合并节点的几何节点向量

**JSON 参数映射**:
- `"mm"`: 合并模式(Merge Mode)
  - `1`: `kMerge` - 合并
  - `2`: `kUnion` - 并集
  - `3`: `kDifference` - 差集
  - `4`: `kIntersect` - 交集
  - `5`: `kXOR` - 异或

**实现逻辑**:
1. 从 JSON 的 "mm" 字段解析模式索引(默认为 1)
2. 将索引减 1 转换为数组索引
3. 使用 `std::min` 限制索引范围,防止越界
4. 调用 `MergeGeometry` 执行实际合并
5. 将结果包装成向量返回

## 内部实现细节

### 合并模式映射
使用静态常量数组映射 After Effects 的合并模式:
```cpp
static constexpr sksg::Merge::Mode gModes[] = {
    sksg::Merge::Mode::kMerge,      // "mm": 1
    sksg::Merge::Mode::kUnion,      // "mm": 2
    sksg::Merge::Mode::kDifference, // "mm": 3
    sksg::Merge::Mode::kIntersect,  // "mm": 4
    sksg::Merge::Mode::kXOR,        // "mm": 5
};
```

### 索引安全处理
使用双重保护防止数组越界:
```cpp
const auto mode = gModes[std::min<size_t>(
    ParseDefault<size_t>(jmerge["mm"], 1) - 1,
    std::size(gModes) - 1)];
```
- `ParseDefault` 提供默认值 1
- 减 1 转换为 0-based 索引
- `std::min` 确保不超过数组边界

### 移动语义优化
两个函数都使用右值引用 `&&` 接收几何节点向量:
```cpp
std::vector<sk_sp<sksg::GeometryNode>>&& geos
```
这避免了不必要的向量复制,提高性能。

### Merge::Rec 结构
合并记录结构包含:
```cpp
{std::move(geo), mode}
```
- 第一个元素: 几何节点(移动)
- 第二个元素: 应用的合并模式

### 第一个节点特殊处理
```cpp
merge_recs.empty() ? sksg::Merge::Mode::kMerge : mode
```
第一个节点总是使用 `kMerge` 作为基础,建立合并的起点。

## 依赖关系

### 外部依赖
- **SkSG 场景图**:
  - `sksg::GeometryNode`: 几何节点基类
  - `sksg::Merge`: 合并节点实现
  - `sksg::Merge::Mode`: 合并模式枚举
  - `sksg::Merge::Rec`: 合并记录结构

- **Skottie 框架**:
  - `ShapeBuilder`: 形状构建器(本类扩展)
  - `AnimationBuilder`: 动画构建器

- **JSON 解析**:
  - `skjson::ObjectValue`: JSON 对象
  - `SkJSONReader`: JSON 读取器

### 内部依赖
- `modules/skottie/src/layers/shapelayer/ShapeLayer.h`: 形状层定义
- `modules/skottie/src/SkottieJson.h`: JSON 工具(如 `ParseDefault`)
- `modules/sksg/include/SkSGGeometryNode.h`: 几何节点接口
- `modules/sksg/include/SkSGMerge.h`: 合并节点实现

## 设计模式与设计决策

### 工厂方法模式
`MergeGeometry` 函数作为工厂方法,根据模式参数创建 `sksg::Merge` 对象:
```cpp
return sksg::Merge::Make(std::move(merge_recs));
```

### 策略模式
合并模式数组 `gModes` 实现了策略模式:
- 每个模式代表不同的布尔运算策略
- 通过索引选择具体策略
- 策略在 `sksg::Merge` 中执行

### 构建器模式
作为 `ShapeBuilder` 的一部分,这些方法遵循构建器模式:
- 逐步构建复杂的形状层结构
- 支持链式调用(通过返回几何节点向量)
- 分离构建逻辑和表示

### 面向数据设计
使用 `Merge::Rec` 记录向量而非复杂对象图:
```cpp
std::vector<sksg::Merge::Rec> merge_recs;
```
这种设计更易于序列化、调试和优化。

## 性能考量

### 内存预留
```cpp
merge_recs.reserve(geos.size());
```
预先分配足够空间,避免向量扩容导致的多次内存重新分配。

### 移动语义
全面使用移动语义:
```cpp
std::move(geo)           // 移动几何节点
std::move(geos)          // 移动输入向量
std::move(merge_recs)    // 移动记录向量
```
避免智能指针的引用计数增减和向量的深拷贝。

### 常量查找表
使用 `static constexpr` 数组存储模式映射:
```cpp
static constexpr sksg::Merge::Mode gModes[] = {...};
```
编译时常量,零运行时开销。

### 边界检查优化
使用 `std::min` 而非分支判断:
```cpp
std::min<size_t>(index, std::size(gModes) - 1)
```
避免分支预测失败,在现代 CPU 上更高效。

### 单次合并
将多个几何节点一次性合并为单个节点:
- 减少场景图深度
- 降低遍历和重新验证开销
- 简化渲染流水线

## 相关文件

- `modules/sksg/include/SkSGMerge.h`: 合并节点实现
- `modules/sksg/include/SkSGGeometryNode.h`: 几何节点基类
- `modules/skottie/src/layers/shapelayer/ShapeLayer.h`: 形状层和 ShapeBuilder
- `modules/skottie/src/SkottieJson.h`: JSON 解析工具
- `modules/skottie/src/layers/shapelayer/`: 其他形状效果(如 TrimPaths, RoundCorners)
- `modules/sksg/include/SkSGNode.h`: 场景图节点基类
