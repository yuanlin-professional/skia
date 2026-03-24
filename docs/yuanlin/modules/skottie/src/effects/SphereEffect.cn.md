# SphereEffect - Skottie CC Sphere 球体效果

> 源文件: `modules/skottie/src/effects/SphereEffect.cpp`

## 概述

SphereEffect 实现了 After Effects 中的"CC Sphere"效果。该效果将图层纹理映射到一个三维球体上，支持可配置的旋转、光照模型（环境光、漫射光、镜面高光）以及正面/背面渲染选项。实现基于 SkRuntimeEffect 运行时着色器，通过光线投射（ray casting）计算球面交点，然后进行 UV 映射和 Phong 光照计算。

## 架构位置

该文件位于 Skottie 效果子系统中（`skottie::internal` 命名空间），采用三层架构：SkSL 着色器实现核心渲染算法，自定义渲染节点管理着色器构建和渲染，适配器处理 AE 属性到渲染参数的转换。

```
AnimationBuilder
  └── EffectBuilder::attachSphereEffect()
        └── SphereAdapter (DiscardableAdapterBase)
              └── SphereNode (CustomRenderNode)
                    ├── gSphereSkSL + gBasicLightSkSL (环境光模式)
                    └── gSphereSkSL + gFancyLightSkSL (完整光照模式)
```

## 主要类与结构体

### `SphereNode`
- 继承自 `sksg::CustomRenderNode`
- 枚举 `RenderSide`：`kFull`（双面）、`kOutside`（外表面）、`kInside`（内表面）
- 10 个 `SG_ATTRIBUTE` 属性：Center、Radius、Rotation、Side、LightVec、LightColor、AmbientLight、DiffuseLight、SpecularLight、SpecularExp
- 缓存两个着色器：`fSphereShader`（当前帧）和 `fContentShader`（纹理）

### `SphereAdapter`
- 继承自 `DiscardableAdapterBase<SphereAdapter, SphereNode>`
- 绑定 15 个效果属性（旋转 XYZ、旋转顺序、半径、偏移、渲染面、光照强度/颜色/高度/方向、环境光/漫射/镜面/粗糙度）

## 公共 API 函数

### `EffectBuilder::attachSphereEffect()`
```cpp
sk_sp<sksg::RenderNode> EffectBuilder::attachSphereEffect(
    const skjson::ArrayValue& jprops, sk_sp<sksg::RenderNode> layer) const;
```

## 内部实现细节

### SkSL 球体着色器 (gSphereSkSL)

着色器通过 `%s` 格式化字符串注入光照模型代码，实现以下渲染管线：

1. **光线投射**：从眼睛位置 `(0, 0, -5.5)` 向像素位置 `(x, y, 0)` 投射光线
2. **球面求交**：在单位球上求解二次方程 `at^2 + bt + c = 0`，`side_select` 控制取前交点还是后交点
3. **法线计算**：球面交点即为法线方向（单位球的特性）
4. **法线旋转**：通过 `rot_matrix`（3x3 旋转矩阵）旋转法线
5. **UV 映射**：使用球面坐标映射 `(atan2, asin)` 将旋转后的法线转换为 UV 坐标
6. **纹理采样**：在 UV 坐标处采样子着色器，按 `child_scale` 缩放
7. **光照计算**：调用 `apply_light()` 应用光照模型

### 光照模型

**基础光照 (gBasicLightSkSL)**：仅环境光，`c.rgb *= l_coeff_ambient`

**完整光照 (gFancyLightSkSL)**：Phong 模型
```
颜色 = (ambient + diffuse * light_color) * texture_color + specular * light_color * alpha
```
- 漫射分量：`max(dot(l_vec, N), 0)`
- 镜面分量：`pow(max(dot(eye, reflect(-l_vec, N)), 0), specular_exp)`

### 双面渲染

`onRevalidate` 中处理三种渲染面模式：
- **Outside**：`side_select = -1`（后交点）
- **Inside**：`side_select = 1`（前交点）
- **Full**：构建两个着色器，通过 `SkShaders::Blend(SkBlendMode::kSrcOver)` 混合

### 旋转顺序

支持 6 种欧拉角旋转顺序（XYZ、XZY、YXZ、YZX、ZXY、ZYX），通过 `SkM44::Rotate` 矩阵乘法组合。注意 Z 轴旋转取负值以匹配 AE 的约定。

### 光照向量计算

从球面坐标（height, direction）转换为笛卡尔坐标：
```cpp
z = sin(height * PI/2);
r = sqrt(1 - z*z);
x = cos(direction) * r;
y = sin(direction) * r;
```

### 内容着色器缓存

`contentShader()` 方法检查 `hasChildrenInval()` 以决定是否需要重新渲染子节点为 SkPicture 并创建着色器，避免不必要的重复渲染。

## 依赖关系

- **Skia 核心**：`SkCanvas`、`SkPaint`、`SkPicture`、`SkShader`、`SkM44`、`SkMatrix`
- **Skia 效果**：`SkRuntimeEffect`（运行时着色器）
- **Skottie 内部**：`Adapter.h`、`Effects.h`、`SkottiePriv.h`、`SkottieValue.h`
- **SkSG**：`CustomRenderNode`

## 设计模式与设计决策

1. **着色器组合**：通过 `SkStringPrintf` 将光照代码注入球体着色器模板，实现编译期的着色器组合。

2. **双单例模式**：`sphere_fancylight_effect()` 和 `sphere_basiclight_effect()` 分别缓存两种着色器变体，根据光照参数动态选择。

3. **条件着色器选择**：当漫射和镜面分量为零时自动切换到更简单的基础光照着色器，减少 GPU 计算量。

4. **SkPicture 纹理化**：将子节点渲染为 SkPicture 再转换为着色器，支持 `kRepeat` 平铺模式，模拟球面的纹理环绕。

5. **几何简化**：将球体固定在原点、半径为 1，通过着色器局部矩阵实现平移和缩放，简化了光线投射方程。

## 性能考量

- 基础/完整光照着色器的动态选择避免了不使用光照时的额外 GPU 计算
- 内容着色器缓存（`fContentShader`）避免了子节点无变化时的重复 SkPicture 录制
- 球体着色器编译为单例，仅初始化一次
- 双面渲染需要两次着色器构建和混合，比单面渲染更昂贵
- `drawCircle` 仅在球体投影圆内执行着色器，自然裁剪了无效像素
- 当半径 <= 0 时 `onRender` 提前返回

## 补充说明

### 光线投射方程推导

对于单位球（r=1，中心在原点），眼睛在 `(0, 0, eye_z)`，观察点在 `(x, y, 0)`：
- 光线方程：`P = Eye + t * (Target - Eye)`，其中 Target = (x, y, 0)，Eye = (0, 0, eye_z)
- 球面方程：`|P|^2 = 1`
- 展开得到：`a*t^2 + b*t + c = 0`
  - `a = dot(Eye, Eye)`
  - `b = -2 * eye_z^2`
  - `c = eye_z^2 - 1`
- `side_select = +1` 选择前交点（外表面），`-1` 选择后交点（内表面）

eye_z = -5.5 的值是经过调试选择的，以匹配 AE CC Sphere 的视觉透视效果。

### UV 球面坐标映射

旋转后的法线 `RN` 被映射为纹理坐标：
```
U = 0.5 + (1/2pi) * atan2(RN.x, RN.z)  -> [0, 1] 水平环绕
V = 0.5 + (1/pi) * asin(RN.y)            -> [0, 1] 垂直跨度
```
这是标准的等距圆柱投影（equirectangular projection），与地理学中的经纬度映射一致。

### 旋转顺序枚举

6 种欧拉角旋转顺序对应不同的轴组合优先级：
1. XYZ  2. XZY  3. YXZ  4. YZX  5. ZXY  6. ZYX

不同的旋转顺序在给定相同角度时会产生不同的最终方向，这是欧拉角的固有特性（万向节锁问题的来源之一）。

### 光照参数归一化

AE 的光照参数均为百分比制（0-100），在适配器中转换为 Skia 友好的范围：
- 环境光：`ambient * 0.01`，范围 [0, 2]（允许过曝）
- 漫射/镜面光：乘以 `intensity * 0.01` 后限制在 [0, 1]
- 光照高度：`height * 0.01`，范围 [-1, 1]（-1 为下方，1 为上方）
- 粗糙度：取倒数作为镜面指数 `1/roughness`，范围 [2, 1000]

## 相关文件

- `modules/skottie/src/effects/Effects.h` - EffectBuilder 定义
- `modules/skottie/src/Adapter.h` - DiscardableAdapterBase 基类
- `modules/sksg/include/SkSGRenderNode.h` - CustomRenderNode 基类
- `include/effects/SkRuntimeEffect.h` - SkRuntimeEffect API
- `modules/skottie/src/effects/DisplacementMapEffect.cpp` - 另一个使用 SkRuntimeEffect 的效果
