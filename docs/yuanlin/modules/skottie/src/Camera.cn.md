# Camera - Skottie 相机系统

> 源文件: [`modules/skottie/src/Camera.h`](../../../modules/skottie/src/Camera.h), [`modules/skottie/src/Camera.cpp`](../../../modules/skottie/src/Camera.cpp)

## 概述

Camera 模块实现了 Skottie 的 3D 相机系统，对应 After Effects 中的相机层。它支持两种 AE 相机类型（单节点和双节点），实现了透视投影和视图变换，将 3D 场景映射到 2D 画布上。

## 架构位置

位于 Skottie 内部实现层：

- **调用者**: AnimationBuilder（在解析相机层时调用 attachCamera）
- **父类**: TransformAdapter3D（3D 变换适配器基类）
- **输出**: sksg::Transform 节点（场景图变换）

## 主要类与结构体

### `CameraAdaper` 类
继承自 TransformAdapter3D，实现 AE 相机的变换计算。

```cpp
class CameraAdaper final : public TransformAdapter3D {
public:
    CameraAdaper(const ObjectValue& jlayer, const ObjectValue& jtransform,
                 const AnimationBuilder& abuilder, const SkSize& viewport_size);
    static sk_sp<sksg::Transform> DefaultCameraTransform(const SkSize& viewport_size);
    SkM44 totalMatrix() const override;
private:
    enum class CameraType { kOneNode, kTwoNode };
};
```

### `CameraType` 枚举
- `kOneNode`: 隐式面向前方（z 递减方向），不自动朝向
- `kTwoNode`: 显式面向兴趣点（锚点），自动朝向

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `totalMatrix()` | 返回完整的相机变换矩阵（视图 + 透视） |
| `DefaultCameraTransform(viewport_size)` | 无显式相机时的默认变换 |

## 内部实现细节

### ComputeCameraMatrix 函数
计算完整的相机矩阵，包含三个阶段：

1. **相机变换 (cam_t)**:
   - 应用旋转（ZYX 欧拉角）
   - 使用 LookAt 矩阵面向兴趣点
   - Z 轴翻转（AE 使用右手坐标系）

2. **透视投影 (persp_t)**:
   - 视野大小 = max(width, height)
   - 视距 = zoom 属性（对应 AE 的 "pe" 属性）
   - 视角 = atan(view_size / 2 / view_distance)
   - 使用 SkM44::Perspective 构建透视矩阵

3. **视口居中**: 平移到视口中心

### 相机类型判断
通过检查 JSON 变换中是否存在锚点属性 "a" 来区分单节点和双节点相机。NullValue 表示单节点。

### 兴趣点 (POI)
- 单节点: POI 固定在相机正前方 `(pos.x, pos.y, -pos.z - 1)`
- 双节点: POI 来自锚点属性，Z 坐标取反

### 默认相机
当动画没有显式相机层时，使用默认参数：位置在视口中心上方，zoom = 879.13（AE 默认值），面向正前方。

## 依赖关系

- `modules/skottie/src/Transform.h` - TransformAdapter3D 基类
- `modules/skottie/src/SkottiePriv.h` - AnimationBuilder
- `modules/sksg/include/SkSGTransform.h` - 场景图变换节点
- `include/core/SkM44.h` - 4x4 矩阵

## 设计模式与设计决策

### 适配器模式
CameraAdaper 继承 TransformAdapter3D，复用 3D 变换的位置、旋转、锚点绑定逻辑，仅覆写 totalMatrix() 添加透视投影。

### 静态相机优化
如果相机参数不动画（isStatic），直接在时间 0 求值并跳过动画调度。

## 性能考量

- 矩阵计算在每帧中仅在属性变化时重新计算
- SkM44 操作使用 SIMD 加速

## 相关文件

- `modules/skottie/src/Transform.h` - TransformAdapter3D 基类
- `modules/skottie/src/Layer.h` - 图层解析
- `modules/sksg/include/SkSGTransform.h` - 场景图变换
