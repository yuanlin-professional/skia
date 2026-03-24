# SkDrawShadowInfo

> 源文件
> - src/core/SkDrawShadowInfo.h
> - src/core/SkDrawShadowInfo.cpp

## 概述

`SkDrawShadowInfo` 是 Skia 中用于计算和管理阴影绘制参数的核心模块。它提供了一组用于计算环境阴影（ambient shadow）和聚光阴影（spot shadow）的工具函数，这些函数基于光源位置、遮挡物高度和半径等参数计算阴影的模糊半径、缩放比例和偏移量。该模块是实现 Material Design 阴影效果的基础，支持方向光和点光源两种光照模型。

## 架构位置

该模块位于 Skia 核心渲染层（`src/core`）中，属于绘制系统的一部分。它为更高层次的阴影渲染 API（如 `SkShadowUtils`）提供底层计算支持，是阴影渲染管线中的数学计算核心。该模块不直接参与图形绘制，而是负责阴影参数的预计算和变换矩阵生成。

## 主要类与结构体

### SkDrawShadowRec

用于封装阴影绘制所需的所有参数。

| 类型 | 说明 |
|------|------|
| 继承关系 | 无继承，独立结构体 |
| 主要用途 | 作为参数传递结构，聚合阴影绘制的所有输入信息 |

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fZPlaneParams` | `SkPoint3` | Z平面参数，定义遮挡物所在平面的方程（ax + by + c） |
| `fLightPos` | `SkPoint3` | 光源的三维位置坐标 |
| `fLightRadius` | `SkScalar` | 光源半径，影响阴影的柔和程度 |
| `fAmbientColor` | `SkColor` | 环境阴影颜色 |
| `fSpotColor` | `SkColor` | 聚光阴影颜色 |
| `fFlags` | `uint32_t` | 标志位，如是否使用方向光 |

### SkDrawShadowMetrics 命名空间

包含阴影计算的所有核心算法。

**关键常量：**

| 常量 | 值 | 说明 |
|------|-----|------|
| `kAmbientHeightFactor` | 1.0f / 128.0f | 环境阴影高度因子 |
| `kAmbientGeomFactor` | 64.0f | 环境阴影几何因子 |
| `kMaxAmbientRadius` | 300 * kAmbientHeightFactor * kAmbientGeomFactor | 最大环境阴影半径（约1200） |

## 公共 API 函数

### 内联工具函数

```cpp
inline SkScalar AmbientBlurRadius(SkScalar height)
```
根据遮挡物高度计算环境阴影的模糊半径。返回值被限制在 `kMaxAmbientRadius` 以内。

```cpp
inline SkScalar AmbientRecipAlpha(SkScalar height)
```
计算环境阴影的alpha倒数，用于根据高度调整透明度。

```cpp
inline SkScalar SpotBlurRadius(SkScalar occluderZ, SkScalar lightZ, SkScalar lightRadius)
```
计算聚光阴影的模糊半径，基于遮挡物Z值、光源Z值和光源半径。

```cpp
inline void GetSpotParams(SkScalar occluderZ, SkScalar lightX, SkScalar lightY,
                          SkScalar lightZ, SkScalar lightRadius,
                          SkScalar* blurRadius, SkScalar* scale, SkVector* translate)
```
获取聚光阴影的完整参数集：模糊半径、缩放比例和平移向量。

```cpp
inline void GetDirectionalParams(SkScalar occluderZ, SkScalar lightX, SkScalar lightY,
                                 SkScalar lightZ, SkScalar lightRadius,
                                 SkScalar* blurRadius, SkScalar* scale, SkVector* translate)
```
获取方向光阴影的参数集。与聚光阴影不同，方向光的缩放始终为1。

### 高级函数

```cpp
bool GetSpotShadowTransform(const SkPoint3& lightPos, SkScalar lightRadius,
                            const SkMatrix& ctm, const SkPoint3& zPlaneParams,
                            const SkRect& pathBounds, bool directional,
                            SkMatrix* shadowTransform, SkScalar* radius)
```
创建聚光阴影的变换矩阵。该函数处理透视投影和非透视两种情况，计算从路径到阴影的完整变换。

```cpp
void GetLocalBounds(const SkPath& path, const SkDrawShadowRec& rec,
                    const SkMatrix& ctm, SkRect* bounds)
```
计算阴影的本地边界框，合并环境阴影和聚光阴影的边界。

## 内部实现细节

### 阴影计算模型

**环境阴影：**
- 基于高度的线性模型：`blur = height * kAmbientHeightFactor * kAmbientGeomFactor`
- 透明度随高度增加：`alpha_recip = 1.0 + max(height * kAmbientHeightFactor, 0)`
- 环境阴影不受光源位置影响，模拟全向散射光

**聚光阴影：**
- 基于透视投影的模型：`zRatio = occluderZ / (lightZ - occluderZ)`
- 模糊半径：`blur = lightRadius * zRatio`（限制在0.95以内防止过大）
- 缩放比例：`scale = lightZ / (lightZ - occluderZ)`（限制在1.95以内）
- 平移偏移：`translate = -zRatio * (lightX, lightY)`

### 透视投影处理

对于透视变换的情况，`GetSpotShadowTransform` 执行以下步骤：

1. 将路径边界的四个角点映射到3D空间
2. 计算每个角点的Z值（基于 `zPlaneParams`）
3. 从光源位置投影这些点到Z=0平面
4. 使用交叉点方法构建从单位正方形到投影四边形的齐次变换矩阵
5. 预连接从路径边界到单位正方形的变换

### 安全边界处理

- 使用 `divide_and_pin` 函数确保所有除法运算安全且结果在合理范围内
- 检测并拒绝退化情况（如零高度路径、光源在遮挡物下方等）
- 对浮点误差进行补偿（边界外扩1像素）

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkMatrix` | 变换矩阵操作 |
| `SkPath` | 路径边界获取 |
| `SkPoint3` | 三维点运算 |
| `SkShadowUtils` | 阴影标志位定义 |
| `SkFloatingPoint` | 安全浮点除法 |

### 被依赖的模块

该模块主要被以下组件使用：
- `SkShadowUtils`：高层阴影绘制接口
- GPU 后端：Graphite 和 Ganesh 中的阴影渲染器
- `SkDraw`：CPU 光栅化路径中的阴影绘制

## 设计模式与设计决策

**命名空间封装模式：** 使用 `SkDrawShadowMetrics` 命名空间而非类，提供纯函数式接口，所有函数都是无状态的。这种设计使得阴影计算可以高效内联，并且易于在不同上下文中复用。

**参数对象模式：** `SkDrawShadowRec` 结构体封装所有阴影参数，减少函数参数数量，便于参数传递和扩展。

**防御式编程：**
- 大量使用 `divide_and_pin` 进行安全除法，防止除零和无穷大
- 检测数值范围，确保结果在物理上合理（如 zRatio < 0.95）
- 对退化情况提前返回，避免后续计算错误

**Material Design 对齐：** 常量值（如 `kAmbientHeightFactor`）的选择与 Material Design 规范一致，确保视觉效果符合设计语言。

## 性能考量

**内联优化：** 所有核心计算函数都声明为 `inline`，减少函数调用开销。在典型场景下，环境阴影和聚光阴影的参数计算会被完全内联到调用者中。

**早期退出：** 在 `GetSpotShadowTransform` 中尽早检测退化情况（如零面积边界、非可逆矩阵），避免不必要的复杂计算。

**条件分支优化：** 根据是否有透视、是否为方向光等条件，选择不同的代码路径。非透视情况使用简化的仿射变换，避免昂贵的齐次坐标计算。

**数值稳定性：** 使用 `sk_ieee_float_divide` 而非直接除法，确保特殊值（NaN、Inf）得到正确处理，减少分支预测失败。

**缓存友好：** `SkDrawShadowRec` 结构体紧凑（约40字节），可以高效地在栈上传递，避免堆分配。

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `include/utils/SkShadowUtils.h` | 公共阴影API，使用本模块进行计算 |
| `src/core/SkDraw.cpp` | CPU路径绘制中调用阴影计算 |
| `src/gpu/ganesh/ops/ShadowRRectOp.cpp` | GPU阴影渲染操作 |
| `include/core/SkPoint3.h` | 三维点类型定义 |
| `src/core/SkFDot6.h` | 定点数运算支持 |
