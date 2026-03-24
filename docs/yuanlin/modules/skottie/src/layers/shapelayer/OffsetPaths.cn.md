# OffsetPaths

> 源文件: modules/skottie/src/layers/shapelayer/OffsetPaths.cpp

## 概述

`OffsetPaths.cpp` 实现了 Skottie 形状层系统中的路径偏移效果。该模块沿法线方向扩展或收缩路径,创建平行路径效果,支持不同的线段连接样式和斜接限制。这是 After Effects Offset Paths 效果在 Skottie 中的实现。

## 架构位置

- **模块**: `modules/skottie/src/layers/shapelayer/`
- **命名空间**: `skottie::internal`
- **角色**: 几何效果,通过 `ShapeBuilder` 附加到形状层

## 主要类与结构体

### OffsetPathsAdapter
```cpp
class OffsetPathsAdapter final : public DiscardableAdapterBase<OffsetPathsAdapter, sksg::OffsetEffect>
```

路径偏移适配器,管理偏移属性的动画和同步。

**成员变量**:
- `fAmount`: 偏移量(默认 0)
- `fMiterLimit`: 斜接限制(默认 0)

**核心方法**:
- `onSync()`: 设置偏移量和斜接限制到底层效果节点

## 公共 API 函数

### AttachOffsetGeometryEffect
```cpp
std::vector<sk_sp<sksg::GeometryNode>> ShapeBuilder::AttachOffsetGeometryEffect(
    const skjson::ObjectValue& jround,
    const AnimationBuilder* abuilder,
    std::vector<sk_sp<sksg::GeometryNode>>&& geos)
```

为每个几何节点附加路径偏移效果。

**JSON 参数**:
- `"a"`: 偏移量(Amount),正值扩展,负值收缩
- `"ml"`: 斜接限制(Miter Limit)
- `"lj"`: 线段连接(Line Join)
  - `1`: Miter(尖角)
  - `2`: Round(圆角)
  - `3`: Bevel(斜角)

## 内部实现细节

### 线段连接映射
```cpp
static constexpr SkPaint::Join gJoinMap[] = {
    SkPaint::kMiter_Join,  // 'lj': 1
    SkPaint::kRound_Join,  // 'lj': 2
    SkPaint::kBevel_Join,  // 'lj': 3
};
```

### 索引安全转换
```cpp
const auto join = ParseDefault<int>(joffset["lj"], 1) - 1;
this->node()->setJoin(gJoinMap[SkTPin<int>(join, 0, std::size(gJoinMap) - 1)]);
```
- 从 1-based JSON 索引转换为 0-based 数组索引
- 使用 `SkTPin` 限制索引范围防止越界

### 批量处理
```cpp
for (auto& g : geos) {
    offsetted.push_back(abuilder->attachDiscardableAdapter<OffsetPathsAdapter>(jround, *abuilder, std::move(g)));
}
```
每个几何节点独立应用偏移效果。

## 依赖关系

- **Skia 核心**: `SkPaint::Join`, `SkTPin`
- **SkSG**: `sksg::OffsetEffect`(路径偏移效果实现)
- **Skottie**: `DiscardableAdapterBase`, `ScalarValue`

## 设计模式与设计决策

### 适配器模式
适配 JSON 动画数据到 SkSG 的 `OffsetEffect` 节点。

### 装饰器模式
偏移效果装饰现有几何,不改变原始接口。

### 策略模式
不同的线段连接样式(Miter/Round/Bevel)实现不同的角落处理策略。

## 性能考量

- **可丢弃优化**: 偏移量为 0 时可优化掉适配器
- **常量查找表**: `gJoinMap` 编译时常量,零运行时开销
- **边界检查**: `SkTPin` 提供安全的数组访问
- **移动语义**: 避免智能指针和向量的深拷贝

## 相关文件

- `modules/sksg/include/SkSGGeometryEffect.h`: `OffsetEffect` 实现
- `modules/skottie/src/layers/shapelayer/RoundCorners.cpp`: 其他几何效果
- `modules/skottie/src/layers/shapelayer/TrimPaths.cpp`: 路径修剪效果
- `include/core/SkPaint.h`: `SkPaint::Join` 枚举定义
