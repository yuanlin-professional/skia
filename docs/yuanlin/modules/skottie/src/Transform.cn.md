# Transform - Skottie 变换适配器

> 源文件: [`modules/skottie/src/Transform.h`](../../../modules/skottie/src/Transform.h), [`modules/skottie/src/Transform.cpp`](../../../modules/skottie/src/Transform.cpp)

## 概述

Transform 模块实现了 Skottie 的 2D 和 3D 变换适配器，将 Lottie JSON 中的变换属性（锚点、位置、缩放、旋转、倾斜）映射为 Skia 的 SkMatrix（2D）或 SkM44（3D）变换矩阵。这些适配器是 Skottie 动画系统的核心组件，控制着所有图层和形状的空间变换。

## 架构位置

位于 Skottie 内部实现层：

- **调用者**: AnimationBuilder::attachMatrix2D / attachMatrix3D、LayerBuilder
- **父类/基础**: DiscardableAdapterBase（可丢弃适配器基类）
- **输出**: sksg::Matrix<SkMatrix> 或 sksg::Matrix<SkM44> 场景图节点
- **派生类**: CameraAdaper（覆写 3D 变换以添加透视投影）

## 主要类与结构体

### `TransformAdapter2D` 类
2D 变换适配器，管理锚点、位置、缩放、旋转、倾斜属性。

```cpp
class TransformAdapter2D final : public DiscardableAdapterBase<TransformAdapter2D,
                                                               sksg::Matrix<SkMatrix>> {
    Vec2Value   fAnchorPoint = {0, 0}, fPosition = {0, 0}, fScale = {100, 100};
    ScalarValue fRotation = 0, fSkew = 0, fSkewAxis = 0, fOrientation = 0;
public:
    SkMatrix totalMatrix() const;
    // getter/setter 用于公共属性 API
};
```

### `TransformAdapter3D` 类
3D 变换适配器，管理 3D 空间中的锚点、位置、缩放和三轴旋转。

```cpp
class TransformAdapter3D : public DiscardableAdapterBase<TransformAdapter3D,
                                                          sksg::Matrix<SkM44>> {
    VectorValue fAnchorPoint, fPosition, fOrientation, fScale = {100, 100, 100};
    ScalarValue fRx = 0, fRy = 0, fRz = 0;
public:
    virtual SkM44 totalMatrix() const;
protected:
    SkV3 anchor_point() const;
    SkV3 position() const;
    SkV3 rotation() const;
};
```

## 公共 API 函数

### TransformAdapter2D

| 函数 | 说明 |
|------|------|
| `totalMatrix()` | 返回组合后的 2D 变换矩阵 |
| `getAnchorPoint()` / `setAnchorPoint()` | 锚点存取 |
| `getPosition()` / `setPosition()` | 位置存取 |
| `getScale()` / `setScale()` | 缩放存取 |
| `getRotation()` / `setRotation()` | 旋转存取 |
| `getSkew()` / `setSkew()` | 倾斜存取 |
| `getSkewAxis()` / `setSkewAxis()` | 倾斜轴存取 |

### TransformAdapter3D

| 函数 | 说明 |
|------|------|
| `totalMatrix()` | 返回组合后的 3D 变换矩阵（virtual） |

## 内部实现细节

### 2D 变换矩阵组合
`TransformAdapter2D::totalMatrix()` 按以下顺序组合：
```
T(position) * R(rotation + orientation) * Skew(skew, skewAxis) * S(scale/100) * T(-anchorPoint)
```
倾斜实现模拟 CSS/SVG 的 SkewX，通过旋转到倾斜轴、应用 X 方向倾斜、再旋转回来。倾斜角度被限制在 [-85, 85] 度。

### 3D 变换矩阵组合
`TransformAdapter3D::totalMatrix()` 按以下顺序组合：
```
T(position) * Rx(rotation.x) * Ry(rotation.y) * Rz(rotation.z) * S(scale/100) * T(-anchorPoint)
```
旋转合并了轴向旋转（rx, ry, rz）和方向（orientation）属性。

### 自动朝向（Auto-Orient）
2D 变换支持自动朝向功能，通过 `bindAutoOrientable` 将路径运动方向作为额外旋转分量（fOrientation）叠加到旋转属性上。

### 静态变换优化
- 如果变换是静态的且为恒等矩阵，直接丢弃（返回父变换）
- 如果变换是静态但非恒等，在时间 0 处求值并固定

### 2D 旋转的 3D 伪装
某些 Lottie 文件中 2D 旋转存储在 "rz" 而非 "r" 键下，`attachMatrix2D` 会检查并回退到 "rz"。

## 依赖关系

- `modules/skottie/src/Adapter.h` - DiscardableAdapterBase 基类
- `modules/skottie/src/SkottieValue.h` - Vec2Value、ScalarValue、VectorValue
- `modules/sksg/include/SkSGTransform.h` - 场景图变换节点
- `include/core/SkMatrix.h` - 2D 矩阵
- `include/core/SkM44.h` - 4x4 矩阵

## 设计模式与设计决策

### 适配器模式
TransformAdapter 将 JSON 属性绑定转换为场景图节点更新，隔离了数据源和渲染系统。

### 可丢弃基类
继承 DiscardableAdapterBase 使静态变换在首次求值后可以释放动画器资源。

### 百分比缩放
缩放值以 100 为基准（100 = 100%），与 AE 的 UI 表示一致。

## 性能考量

- 恒等变换完全跳过，不创建节点
- 静态变换仅求值一次
- setter 方法直接触发 onSync，避免延迟刷新

## 相关文件

- `modules/skottie/src/Adapter.h` - 适配器基类
- `modules/skottie/src/Camera.h` - 继承 TransformAdapter3D
- `modules/skottie/src/Layer.h` - 使用变换的图层构建
- `modules/sksg/include/SkSGTransform.h` - 场景图变换节点
