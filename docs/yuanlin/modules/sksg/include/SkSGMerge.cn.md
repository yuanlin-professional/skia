# SkSGMerge

> 源文件: modules/sksg/include/SkSGMerge.h

## 概述

SkSGMerge 是 Skia 场景图中的几何组合节点，用于将多个几何节点（GeometryNode）通过不同的模式合并成单一几何形状。它支持简单的路径追加以及基于 SkPathOp 的布尔运算（并集、交集、差集等）。

Merge 节点是场景图中实现复杂形状的关键工具，允许通过组合基本几何图形创建复杂的矢量图形，类似于矢量图形编辑器中的路径操作功能。

## 架构位置

在 Skia 场景图架构中的位置：

- **继承关系**: Merge → GeometryNode → Node
- **功能定位**: 几何组合器，产生复合几何形状
- **输入**: 多个 GeometryNode（矩形、路径、椭圆等）
- **输出**: 单一合并后的几何形状
- **使用场景**: 与 Draw 节点配合，绘制复杂形状

Merge 使得场景图能够表达复杂的矢量图形层次结构，支持动态修改几何组合方式。

## 主要类与结构体

### Merge 类

```cpp
class Merge final : public GeometryNode {
public:
    enum class Mode {
        kMerge,              // 路径追加模式
        kUnion,              // 并集
        kIntersect,          // 交集
        kDifference,         // 差集
        kReverseDifference,  // 反向差集
        kXOR,                // 异或
    };

    struct Rec {
        sk_sp<GeometryNode> fGeo;
        Mode                fMode;
    };

    static sk_sp<Merge> Make(std::vector<Rec>&& recs);
    ~Merge() override;

protected:
    void onClip(SkCanvas*, bool antiAlias) const override;
    void onDraw(SkCanvas*, const SkPaint&) const override;
    bool onContains(const SkPoint&) const override;
    SkRect onRevalidate(InvalidationController*, const SkMatrix&) override;
    SkPath onAsPath() const override;

private:
    explicit Merge(std::vector<Rec>&& recs);

    const std::vector<Rec> fRecs;
    SkPath                 fMerged;

    using INHERITED = GeometryNode;
};
```

### Mode 枚举

**kMerge**: 简单追加路径，不进行布尔运算。各几何形状按顺序添加到结果路径。

**kUnion**: 并集操作，合并所有重叠区域。结果包含所有输入几何的覆盖区域。

**kIntersect**: 交集操作，保留重叠部分。结果仅包含所有输入共同覆盖的区域。

**kDifference**: 差集操作，从第一个几何中减去后续几何。

**kReverseDifference**: 反向差集，从后续几何中减去第一个几何。

**kXOR**: 异或操作，保留非重叠部分。结果为仅被一个几何覆盖的区域。

### Rec 结构体

```cpp
struct Rec {
    sk_sp<GeometryNode> fGeo;  // 几何节点
    Mode                fMode;  // 合并模式
};
```

每个 Rec 表示一个参与合并的几何节点及其应用的模式。

## 公共 API 函数

### Make()
```cpp
static sk_sp<Merge> Make(std::vector<Rec>&& recs);
```
静态工厂方法，创建 Merge 节点。

**参数**: 几何节点和模式的记录向量，使用移动语义

**使用示例**:
```cpp
auto merge = sksg::Merge::Make({
    {circle1, Merge::Mode::kMerge},
    {circle2, Merge::Mode::kUnion},
    {rect, Merge::Mode::kDifference}
});
```

## 内部实现细节

### 路径合并 (onAsPath)

`onAsPath()` 执行实际的几何合并：
1. 初始化空的 SkPath
2. 遍历 fRecs 中的每个记录
3. 获取每个几何节点的路径（调用 asPath()）
4. 根据 Mode 应用相应操作：
   - kMerge: 使用 SkPath::addPath()
   - 其他: 使用 SkPathOp 库函数
5. 存储结果到 fMerged
6. 返回 fMerged

### 重验证 (onRevalidate)

重验证时：
1. 调用 onAsPath() 更新 fMerged
2. 计算 fMerged 的边界框
3. 重验证所有子几何节点（触发依赖更新）
4. 返回计算的边界

### 绘制 (onDraw)

绘制合并后的路径：
```cpp
canvas->drawPath(fMerged, paint);
```
直接使用 SkCanvas 的路径绘制 API。

### 裁剪 (onClip)

使用合并后的路径作为裁剪区域：
```cpp
canvas->clipPath(fMerged, antiAlias);
```

### 包含测试 (onContains)

检查点是否在合并后的路径内：
```cpp
return fMerged.contains(point.x(), point.y());
```

## 依赖关系

### 核心依赖
- **include/core/SkPath.h**: 路径定义和操作
- **include/core/SkRect.h**: 边界框
- **modules/sksg/include/SkSGGeometryNode.h**: 几何节点基类

### 路径操作依赖
- **include/pathops/SkPathOps.h**: 布尔路径操作（隐式依赖）

### 渲染依赖
- **SkCanvas**: 绘制和裁剪
- **SkPaint**: 绘制属性
- **SkPoint**: 点坐标

### 标准库
- **<utility>**: std::move
- **<vector>**: 记录存储

## 设计模式与设计决策

### 1. 不可变几何集合
fRecs 声明为 const，构造后不可修改：
- 简化失效逻辑
- 防止意外修改
- 需要修改时创建新 Merge 节点

### 2. 延迟计算与缓存
fMerged 路径在重验证时计算并缓存：
- 避免重复计算
- 只在几何失效时重新合并
- 渲染时直接使用缓存路径

### 3. 终态类设计
声明为 final，不可继承：
- 合并逻辑相对固定
- 简化虚函数调用
- 明确使用意图

### 4. 记录模式
使用 Rec 结构体而非分离的向量：
- 几何和模式配对清晰
- 避免索引不同步
- 类型安全

### 5. 移动语义优化
构造函数接受右值引用：
- 避免拷贝 vector
- 减少引用计数操作
- 高效转移所有权

## 性能考量

### 1. 路径操作开销
布尔路径操作（非 kMerge 模式）计算密集：
- 涉及复杂的几何算法
- 时间复杂度依赖路径复杂度
- 可能产生大量顶点

### 2. 缓存有效性
fMerged 缓存避免重复计算：
- 只在重验证时更新
- 渲染和命中测试复用
- 对静态几何效率高

### 3. 内存占用
存储原始几何和合并结果：
- fRecs 保留所有输入几何引用
- fMerged 存储完整合并路径
- 对于简单几何可能冗余

### 4. 几何节点重验证
Merge 依赖所有子几何节点：
- 任一子节点失效触发 Merge 重验证
- 可能级联触发整个路径重新计算
- 频繁变化的几何成本高

### 5. 模式选择影响
- kMerge: 最快，简单路径追加
- kUnion: 中等，合并重叠区域
- kIntersect/kDifference: 较慢，复杂计算
- 选择合适模式平衡质量和性能

## 相关文件

### 头文件
- **modules/sksg/include/SkSGGeometryNode.h**: 几何节点基类
- **include/core/SkPath.h**: 路径 API
- **include/pathops/SkPathOps.h**: 布尔操作

### 实现文件
- **modules/sksg/src/SkSGMerge.cpp**: Merge 类实现

### 相关几何节点
- **SkSGRect.h**: 矩形几何（可作为 Merge 输入）
- **SkSGPath.h**: 路径几何
- **SkSGRRect.h**: 圆角矩形（可能存在）

### 使用场景
- **modules/skottie**: Lottie 动画中的路径合并
- 矢量图形编辑器中的形状组合
- 复杂图标和 Logo 的构建
- 动态形状变化和过渡

### 示例用法
```cpp
// 创建甜甜圈形状（外圆减内圆）
auto outer = sksg::Circle::Make(center, 50);
auto inner = sksg::Circle::Make(center, 30);
auto donut = sksg::Merge::Make({
    {outer, Merge::Mode::kMerge},
    {inner, Merge::Mode::kDifference}
});

// 与绘制节点组合
auto paint = sksg::Color::Make(SK_ColorBLUE);
auto draw = sksg::Draw::Make(donut, paint);
```
