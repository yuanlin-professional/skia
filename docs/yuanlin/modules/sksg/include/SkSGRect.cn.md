# SkSGRect -- 矩形与圆角矩形几何节点

> 源文件: `modules/sksg/include/SkSGRect.h`

## 概述

`SkSGRect.h` 定义了 Skia Scene Graph 中的两个基础几何节点：`Rect`（矩形）和 `RRect`（圆角矩形）。这两个节点分别封装了 Skia 的 `SkRect` 和 `SkRRect` 类型，是场景图中最常用的几何构建块。它们支持设置边界坐标/圆角参数、路径方向和起始点索引，适用于 SVG 和 Lottie 动画中的矩形和圆角矩形绘制。

## 架构位置

```
Node
└── GeometryNode
    ├── Rect   ← 矩形几何体
    ├── RRect  ← 圆角矩形几何体
    ├── Path (通用路径)
    ├── Plane (无限平面)
    └── Text (文本)
```

`Rect` 和 `RRect` 是 `GeometryNode` 的具体实现，作为叶几何节点使用。它们可以直接与 `PaintNode` 组合通过 `Draw` 节点渲染，也可以作为 `GeometryEffect` 链的输入，或作为 `ClipEffect` 的裁剪区域。

## 主要类与结构体

### `Rect`
```cpp
class Rect final : public GeometryNode {
public:
    static sk_sp<Rect> Make();
    static sk_sp<Rect> Make(const SkRect& r);

    SG_ATTRIBUTE(L, SkScalar, fRect.fLeft)
    SG_ATTRIBUTE(T, SkScalar, fRect.fTop)
    SG_ATTRIBUTE(R, SkScalar, fRect.fRight)
    SG_ATTRIBUTE(B, SkScalar, fRect.fBottom)

    SG_MAPPED_ATTRIBUTE(Direction,         SkPathDirection, fAttrContaier)
    SG_MAPPED_ATTRIBUTE(InitialPointIndex, uint8_t,         fAttrContaier)
private:
    SkRect fRect;
    struct AttrContainer { /* 位字段: fDirection, fInitialPointIndex */ };
    AttrContainer fAttrContaier;
};
```

矩形节点，通过 L/T/R/B 四个属性独立控制四条边的位置。

### `RRect`
```cpp
class RRect final : public GeometryNode {
public:
    static sk_sp<RRect> Make();
    static sk_sp<RRect> Make(const SkRRect& rr);

    SG_ATTRIBUTE(RRect, SkRRect, fRRect)

    SG_MAPPED_ATTRIBUTE(Direction,         SkPathDirection, fAttrContaier)
    SG_MAPPED_ATTRIBUTE(InitialPointIndex, uint8_t,         fAttrContaier)
private:
    SkRRect fRRect;
    struct AttrContainer { /* 与 Rect 相同的位字段 */ };
    AttrContainer fAttrContaier;
};
```

圆角矩形节点，通过 `SkRRect` 封装完整的圆角矩形数据（包括矩形边界和四个角的圆角半径）。

### `AttrContainer` (内部结构)
```cpp
struct AttrContainer {
    uint8_t fDirection         : 1;  // 路径方向 (CW/CCW)
    uint8_t fInitialPointIndex : 2;  // 起始点索引 (0-3)
};
```
使用位字段紧凑存储路径方向和起始点索引。两个类共享相同的 AttrContainer 定义。

## 公共 API 函数

### Rect 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| L | SkScalar | 左边界 |
| T | SkScalar | 上边界 |
| R | SkScalar | 右边界 |
| B | SkScalar | 下边界 |
| Direction | SkPathDirection | 路径方向（CW 顺时针 / CCW 逆时针） |
| InitialPointIndex | uint8_t | 路径起始点索引（0-3，对应四个角） |

### RRect 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| RRect | SkRRect | 完整的圆角矩形数据 |
| Direction | SkPathDirection | 路径方向 |
| InitialPointIndex | uint8_t | 路径起始点索引 |

### 工厂方法
- `Rect::Make()` / `Rect::Make(rect)` -- 创建空或指定矩形
- `RRect::Make()` / `RRect::Make(rrect)` -- 创建空或指定圆角矩形

## 内部实现细节

- **SG_ATTRIBUTE 直接访问成员字段**：Rect 的 L/T/R/B 属性直接映射到 `fRect.fLeft` 等成员，允许独立动画化每条边。

- **SG_MAPPED_ATTRIBUTE**：Direction 和 InitialPointIndex 通过 AttrContainer 的 getter/setter 间接访问，AttrContainer 使用位字段压缩存储。

- **路径方向和起始点**：这些属性控制 `onAsPath` 生成路径时顶点的遍历方向和起始位置，对于 SVG/Lottie 中的 TrimPath 效果至关重要（裁剪范围依赖于路径的参数化方向）。

- **位字段拼写注意**：成员变量名为 `fAttrContaier`（缺少 'n'），这是代码中的一个小拼写错误，但由于已在公开头文件中使用，更改会破坏 ABI。

- **默认值**：Direction 默认为 `kCW`（顺时针），InitialPointIndex 默认为 0。

## 依赖关系

- `include/core/SkRect.h` -- SkRect 类型
- `include/core/SkRRect.h` -- SkRRect 类型
- `include/core/SkPath.h` -- onAsPath 返回类型
- `include/core/SkPathTypes.h` -- SkPathDirection / SkPathFillType
- `include/private/base/SkTo.h` -- 安全类型转换
- `modules/sksg/include/SkSGGeometryNode.h` -- 基类

## 设计模式与设计决策

1. **独立边属性（Rect）**：将矩形的四条边作为独立属性暴露，便于动画系统独立驱动每条边的位置，满足 Lottie 中矩形大小和位置动画的需求。

2. **完整对象属性（RRect）**：由于 SkRRect 内部结构复杂（矩形 + 4 个角的 X/Y 半径），使用单一属性直接设置完整的 SkRRect，而非拆分为多个独立属性。

3. **位字段压缩**：Direction（1 bit）和 InitialPointIndex（2 bits）使用位字段压缩到一个 uint8_t 中，节省内存。

4. **共享 AttrContainer 设计**：Rect 和 RRect 使用结构相同的 AttrContainer，保持一致的 Direction/InitialPointIndex 接口。

5. **路径参数化控制**：Direction 和 InitialPointIndex 控制路径的参数化方向，这对于路径裁剪（TrimEffect）效果的视觉结果至关重要。

## 性能考量

- Rect 和 RRect 是极轻量的节点，只存储基本几何数据和 3 个位字段。Rect 的内存占用约为 SkRect（16 字节）+ AttrContainer（1 字节）+ Node 基类开销。
- Canvas 对矩形和圆角矩形有专门的优化绘制路径（`drawRect`/`drawRRect`），比通用路径 `drawPath` 更高效。GPU 后端可以直接使用专用的矩形着色器而无需进行路径光栅化。
- `onRevalidate` 直接返回矩形边界，几乎零计算开销。对于 RRect，边界为外接矩形。
- SkRRect 的 `operator==` 比较比 SkPath 快得多（固定大小的结构体比较 vs 可变长度的路径点比较）。
- SG_ATTRIBUTE 生成的 setter 方法在新值与旧值相等时直接返回，避免不必要的失效传播和后续的 revalidation 开销。
- 独立的 L/T/R/B 属性允许只更新变化的边，但由于 SkScalar 的相等比较是精确的浮点比较，微小的浮点差异也会触发失效。

## 相关文件

- `modules/sksg/src/SkSGRect.cpp` -- Rect 和 RRect 的实现
- `modules/sksg/include/SkSGGeometryNode.h` -- GeometryNode 基类
- `modules/sksg/include/SkSGPath.h` -- 通用路径几何节点
- `modules/sksg/include/SkSGDraw.h` -- 绘制节点
- `modules/sksg/include/SkSGGeometryEffect.h` -- 几何效果（TrimEffect 等）
