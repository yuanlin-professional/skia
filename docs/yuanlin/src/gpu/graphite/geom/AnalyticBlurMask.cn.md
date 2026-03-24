# AnalyticBlurMask -- 解析模糊遮罩

> 源文件:
> - `src/gpu/graphite/geom/AnalyticBlurMask.h`
> - `src/gpu/graphite/geom/AnalyticBlurMask.cpp`

## 概述

AnalyticBlurMask 封装了对矩形、圆角矩形和圆形进行解析高斯模糊所需的着色器输入数据。与通用模糊滤镜不同,解析模糊利用形状的数学特性在着色器中直接计算模糊结果,配合预计算的积分/轮廓纹理实现高效渲染。该类是 Graphite 模糊遮罩滤镜渲染步骤的核心数据载体。

## 架构位置

```
SkMaskFilter (模糊滤镜)
  -> AnalyticBlurRenderStep (渲染步骤)
    -> AnalyticBlurMask (着色器数据)  <-- 本模块
       -> ProxyCache (纹理缓存)
       -> TextureProxy (积分/轮廓纹理)
```

## 主要类与结构体

### ShapeType 枚举

```cpp
enum class ShapeType { kRect = 0, kRRect = 1, kCircle = 2 };
```
枚举值被着色器代码直接引用,不可随意更改。

### AnalyticBlurMask

```cpp
class AnalyticBlurMask {
    Rect fDrawBounds;           // 局部空间绘制边界
    SkM44 fDevToScaledShape;    // 设备空间到缩放形状空间的变换
    Rect fShapeData;            // 形状数据（含义因类型而异）
    SkV2 fBlurData;             // 模糊参数（含义因类型而异）
    ShapeType fShapeType;       // 形状类型
    sk_sp<TextureProxy> fProxy; // 积分/轮廓纹理代理
};
```

### 字段含义（按形状类型）

| 字段 | 矩形 | 圆形 | 圆角矩形 |
|------|-------|------|----------|
| `fShapeData` | 内缩矩形边界 | (cx, cy, 1/texRadius, solidOffset) | 外扩 devRRect 边界 |
| `fBlurData.x` | isFast (bool) | 未使用 | edgeSize |
| `fBlurData.y` | 1/(6*sigma) | 未使用 | 未使用 |
| `fProxy` | 积分表纹理 | 圆形轮廓纹理 | 九宫格模糊纹理 |

## 公共 API 函数

### Make -- 统一入口

```cpp
static std::optional<AnalyticBlurMask> Make(Recorder*,
                                            const Transform& localToDevice,
                                            float deviceSigma,
                                            const SkRRect& srcRRect);
```
根据输入的圆角矩形和变换自动选择最优处理路径:
1. **矩形**: `isRect()` 且保持直角 -> `MakeRect`
2. **圆形**: 变换后为圆形 -> `MakeCircle`（含旋转矩阵下的圆形检测）
3. **简单圆角矩形**: 变换后为简单圆角 + 缩放平移变换 -> `MakeRRect`
4. 不满足任何条件返回 `nullopt`

### 访问器

```cpp
const Rect& drawBounds() const;
const SkM44& deviceToScaledShape() const;
const Rect& shapeData() const;
ShapeType shapeType() const;
const SkV2& blurData() const;
sk_sp<TextureProxy> refProxy() const;
```

## 内部实现细节

### MakeRect -- 矩形模糊

1. **变换处理**: 如果矩形在设备空间仍为矩形则直接工作于设备空间;否则分解缩放和旋转,在缩放空间中操作
2. **精度保护**: 非 32 位浮点设备上,坐标超过 16000 时退出
3. **积分表**: 通过 `ProxyCache::findOrCreateCachedProxy` 查找或创建宽度为 `tableWidth` 的 1D 积分表纹理
4. **快速路径**: 当矩形在两个维度上都大于 6*sigma 时,可以使用简化的查找

### MakeCircle -- 圆形模糊

1. **参数量化**: 将半径和 sigma 量化到最近的 1/32 像素以提高缓存命中率
2. **半平面近似**: 当 sigma/radius < 0.1 时使用半平面近似（更快但限制条件）
3. **轮廓纹理**: 创建 512 像素宽的 1D 轮廓纹理
4. **着色器优化**: 预计算 `1/textureRadius` 和偏移量避免着色器中的大数值溢出

### MakeRRect -- 圆角矩形模糊

1. **九宫格检查**: 验证圆角矩形可进行九宫格切分（边缘区域不重叠）
2. **GPU 渲染**: 使用 `Surface::MakeScratch` 在 GPU 上创建临时表面,通过 `SkImageFilters::Blur` 绘制模糊结果
3. **缓存**: 结果通过 `ProxyCache` 缓存,使用 SkRRect 数据和 sigma 作为缓存键
4. **edgeSize**: 计算模糊边缘大小 `2*blurRadius + cornerRadius + 0.5`,供着色器九宫格采样

### outset_bounds -- 绘制边界计算

将源矩形向外扩展 3*sigma 的距离,考虑变换的缩放因子。对于非缩放平移矩阵,使用 `decomposeScale` 提取缩放。

## 依赖关系

### 上游依赖
- `ProxyCache` -- 纹理缓存(积分表、轮廓、九宫格)
- `TextureProxy` -- 纹理代理
- `BlurUtils` (`ComputeIntegralTableWidth`, `CreateIntegralTable`, `CreateCircleProfile`) -- 模糊工具函数
- `SkRRectPriv` -- 圆角矩形内部工具
- `Transform` -- Graphite 变换封装

### 下游被依赖
- `AnalyticBlurRenderStep` -- 使用本类的数据驱动着色器渲染

## 设计模式与设计决策

1. **不可变值类型**: 构造函数为 private,仅通过静态工厂方法创建,使用 `std::optional` 表示可能的失败。删除默认构造函数确保始终处于有效状态。

2. **多态数据复用**: `fShapeData` 和 `fBlurData` 根据 `fShapeType` 有不同含义,避免了使用 `std::variant` 或继承层次,保持内存布局紧凑。

3. **纹理缓存策略**:
   - 矩形积分表以 `tableWidth` 为键
   - 圆形轮廓以量化后的 (sigma, radius) 为键
   - 圆角矩形以完整几何参数为键

4. **渐进退化**: 如果解析方法不适用(如任意仿射变换下的圆角矩形),返回 `nullopt` 让调用方回退到通用模糊路径。

## 性能考量

- **量化缓存键**: 圆形参数量化到 1/32 像素精度,增加了缓存命中率而不影响视觉质量。
- **快速路径**: 矩形模糊的 "fast" 路径在大矩形上将着色器操作减半。
- **着色器预计算**: 在 CPU 端预计算如 `1/textureRadius` 等值,避免着色器中的除法。
- **GPU 渲染九宫格**: 圆角矩形的模糊纹理在 GPU 上渲染,避免大型 CPU 端卷积。
- **纹理复用**: 所有积分/轮廓纹理通过 `ProxyCache` 缓存和复用,避免重复创建。

## 相关文件

- `src/gpu/graphite/geom/Rect.h` -- Graphite 矩形类
- `src/gpu/graphite/geom/Transform.h` -- 变换封装
- `src/gpu/graphite/ProxyCache.h` -- 纹理代理缓存
- `src/gpu/BlurUtils.h` -- 模糊积分表和轮廓生成
- `src/gpu/graphite/render/AnalyticBlurRenderStep.h` -- 模糊渲染步骤
