# GrBezierEffect

> 源文件
> - src/gpu/ganesh/effects/GrBezierEffect.h
> - src/gpu/ganesh/effects/GrBezierEffect.cpp

## 概述

`GrBezierEffect` 模块实现了基于 GPU 的贝塞尔曲线渲染,包含两个几何处理器:`GrConicEffect` (圆锥曲线) 和 `GrQuadEffect` (二次贝塞尔曲线)。这些处理器基于 Loop-Blinn 算法,使用隐式方程在 GPU 上高效渲染反走样的曲线边缘,是 Skia 矢量图形渲染的核心组件。

该模块通过在片段着色器中计算到曲线的距离并生成覆盖率值,实现了细线 (hairline) 风格的曲线渲染,广泛应用于路径描边和形状轮廓绘制。

## 架构位置

`GrBezierEffect` 位于 Ganesh GPU 后端的几何处理器层:

```
skia/
└── src/gpu/ganesh/
    └── effects/
        ├── GrBezierEffect.h    (头文件 - 两个处理器定义)
        └── GrBezierEffect.cpp  (实现文件 - 着色器代码生成)
```

在渲染管线中的位置:
- **输入**: 顶点位置、贝塞尔曲线系数
- **层级**: 几何处理器,负责顶点变换和曲线距离计算
- **输出**: 基于距离的覆盖率值,用于反走样

## 主要类与结构体

### GrConicEffect (圆锥曲线效果)

```cpp
class GrConicEffect : public GrGeometryProcessor {
    SkPMColor4f fColor;          // 曲线颜色
    SkMatrix    fViewMatrix;     // 视图变换矩阵
    SkMatrix    fLocalMatrix;    // 局部坐标变换
    bool        fUsesLocalCoords; // 是否使用局部坐标
    uint8_t     fCoverageScale;  // 覆盖率缩放因子

    static constexpr Attribute kAttributes[] = {
        {"inPosition",    kFloat2, SkSLType::kFloat2},
        {"inConicCoeffs", kFloat4, SkSLType::kHalf4}  // K, L, M 系数
    };
};
```

**核心职责**:
- 渲染圆锥曲线 (椭圆、抛物线、双曲线)
- 使用隐式方程 `K² - LM = 0` 表示曲线
- 一阶泰勒展开近似距离计算
- 生成反走样覆盖率

**顶点属性**:
- `inPosition`: 顶点 2D 位置
- `inConicCoeffs`: 四分量向量 `(K, L, M, unused)`

### GrQuadEffect (二次贝塞尔曲线效果)

```cpp
class GrQuadEffect : public GrGeometryProcessor {
    SkPMColor4f fColor;          // 曲线颜色
    SkMatrix    fViewMatrix;     // 视图变换矩阵
    SkMatrix    fLocalMatrix;    // 局部坐标变换
    bool        fUsesLocalCoords; // 是否使用局部坐标
    uint8_t     fCoverageScale;  // 覆盖率缩放因子

    static constexpr Attribute kAttributes[] = {
        {"inPosition",     kFloat2, SkSLType::kFloat2},
        {"inHairQuadEdge", kFloat4, SkSLType::kHalf4}  // u, v 参数坐标
    };
};
```

**核心职责**:
- 渲染二次贝塞尔曲线
- 使用规范形式 `u² - v = 0` 表示曲线
- 计算距离并生成覆盖率
- 支持透视变换和局部坐标

**顶点属性**:
- `inPosition`: 顶点 2D 位置
- `inHairQuadEdge`: 参数坐标 `(u, v, unused, unused)`
  - 三个控制点处的值: `(0,0)`, `(0.5,0)`, `(1,1)`

## 公共 API 函数

### GrConicEffect::Make

```cpp
static GrGeometryProcessor* Make(
    SkArenaAlloc* arena,
    const SkPMColor4f& color,
    const SkMatrix& viewMatrix,
    const GrCaps& caps,
    const SkMatrix& localMatrix,
    bool usesLocalCoords,
    uint8_t coverage = 0xff);
```

**功能**: 创建圆锥曲线几何处理器

**参数**:
- `color`: 曲线颜色
- `viewMatrix`: 视图变换矩阵
- `caps`: GPU 能力查询 (需要 `fShaderDerivativeSupport`)
- `localMatrix`: 局部坐标变换
- `usesLocalCoords`: 是否需要局部坐标 (与片段处理器结合时)
- `coverage`: 全局覆盖率缩放 (0-255)

**返回值**: 处理器指针,若不支持导数则返回 `nullptr`

**硬件要求**: 必须支持 `dFdx`/`dFdy` 指令

### GrQuadEffect::Make

```cpp
static GrGeometryProcessor* Make(
    SkArenaAlloc* arena,
    const SkPMColor4f& color,
    const SkMatrix& viewMatrix,
    const GrCaps& caps,
    const SkMatrix& localMatrix,
    bool usesLocalCoords,
    uint8_t coverage = 0xff);
```

**功能**: 创建二次贝塞尔曲线几何处理器

**参数**: 与 `GrConicEffect::Make` 相同

**返回值**: 处理器指针,若不支持导数则返回 `nullptr`

## 内部实现细节

### GrConicEffect 着色器实现

**片段着色器核心代码** (简化版):

```glsl
// 1. 计算偏导数 (自动微分)
float3 dklmdx = dFdx(conicCoeffs.xyz);  // K, L, M 的 x 偏导
float3 dklmdy = dFdy(conicCoeffs.xyz);  // K, L, M 的 y 偏导

// 2. 计算隐式函数 f = K² - LM 的偏导
float dfdx = 2.0 * K * dklmdx.x - L * dklmdx.z - M * dklmdx.y;
float dfdy = 2.0 * K * dklmdy.x - L * dklmdy.z - M * dklmdy.y;

// 3. 计算梯度向量的模 (距离的倒数)
float2 gF = float2(dfdx, dfdy);
float gFM = length(gF);

// 4. 计算隐式函数值
float func = K * K - L * M;

// 5. 一阶泰勒近似距离
float edgeAlpha = abs(func) / gFM;

// 6. 生成反走样覆盖率
edgeAlpha = max(1.0 - edgeAlpha, 0.0);

// 7. 输出覆盖率
outputCoverage = half4(edgeAlpha * coverageScale);
```

**数学原理**:
- **隐式方程**: `f(K,L,M) = K² - LM = 0` 定义圆锥曲线
- **距离近似**: `distance ≈ |f(p)| / ||∇f(p)||`
- **泰勒展开**: 一阶近似,平衡精度与性能

### GrQuadEffect 着色器实现

**片段着色器核心代码** (简化版):

```glsl
// 1. 计算参数坐标的偏导数
half2 duvdx = half2(dFdx(uv.xy));
half2 duvdy = half2(dFdy(uv.xy));

// 2. 计算隐式函数 f = u² - v 的梯度
half2 gF = half2(2.0 * u * duvdx.x - duvdx.y,
                 2.0 * u * duvdy.x - duvdy.y);

// 3. 计算隐式函数值
half edgeAlpha = u * u - v;

// 4. 距离归一化
edgeAlpha = sqrt(edgeAlpha * edgeAlpha / dot(gF, gF));

// 5. 生成反走样覆盖率
edgeAlpha = max(1.0 - edgeAlpha, 0.0);

// 6. 输出覆盖率
outputCoverage = half4(edgeAlpha * coverageScale);
```

**数学原理**:
- **规范形式**: `f(u,v) = u² - v = 0` 定义二次贝塞尔曲线
- **参数化**: 控制点在 `(u,v)` 空间中的固定位置
- **距离计算**: 类似圆锥曲线的梯度方法

### 二阶距离近似 (已禁用)

代码注释提到了两种二阶近似方法:

**版本 1** (低估距离):
```glsl
edgeAlpha = (sqrt(gFM*gFM + 4.0*func*gF2M) - gFM) / (2.0*gF2M);
```

**版本 2** (高估距离):
```glsl
edgeAlpha = (gFM - sqrt(gFM*gFM - 4.0*func*gF2M)) / (2.0*gF2M);
```

**弃用原因**:
- 版本 1 增加误差,效果不佳
- 版本 2 过度高估,曲线变细 (ropey)
- 一阶近似性能更好,配合几何细分足够精确

### 覆盖率缩放

支持可选的覆盖率调整:

```cpp
if (fCoverageScale != 0xff) {
    float coverageScale = fCoverageScale / 255.0f;
    outputCoverage = half4(coverageScale * edgeAlpha);
}
```

**用途**: 实现半透明曲线或与其他效果混合

### 键值生成

```cpp
void addToKey(const GrShaderCaps& caps, skgpu::KeyBuilder* b) const override {
    uint32_t key = 0;
    key |= (fCoverageScale == 0xff) ? 0x8  : 0x0;  // 覆盖率标志
    key |= fUsesLocalCoords         ? 0x10 : 0x0;  // 局部坐标标志
    key = ProgramImpl::AddMatrixKeys(caps, key, fViewMatrix, fLocalMatrix);
    b->add32(key);
}
```

**编码信息**:
- 位 3: 是否使用覆盖率缩放
- 位 4: 是否使用局部坐标
- 高位: 矩阵类型 (单位/平移/仿射等)

## 依赖关系

### 内部依赖

- `GrGeometryProcessor`: 基类,定义几何处理器接口
- `GrCaps`/`GrShaderCaps`: 能力查询,检查导数支持
- `SkMatrix`: 矩阵变换
- `SkPMColor4f`: 预乘 alpha 颜色
- `SkArenaAlloc`: 对象池分配器

### 外部依赖

- `skgpu::KeyBuilder`: 着色器缓存键构建
- `GrGLSLFragmentShaderBuilder`: 片段着色器代码生成
- `GrGLSLProgramDataManager`: 统一变量管理
- `GrGLSLUniformHandler`: 统一变量声明
- `GrGLSLVaryingHandler`: Varying 变量管理

### 依赖关系图

```
GrBezierEffect (模块)
    ├── GrConicEffect (圆锥曲线)
    │   ├── GrGeometryProcessor (基类)
    │   ├── SkMatrix (变换)
    │   └── glsl/GrGLSLFragmentShaderBuilder (着色器生成)
    └── GrQuadEffect (二次曲线)
        ├── GrGeometryProcessor (基类)
        ├── SkMatrix (变换)
        └── glsl/GrGLSLFragmentShaderBuilder (着色器生成)
```

## 设计模式与设计决策

### 1. Loop-Blinn 算法

采用隐式方程表示曲线:
- **优点**: GPU 友好,易于并行计算
- **实现**: 顶点属性传递方程系数
- **参考**: "Resolution Independent Curve Rendering using Programmable Graphics Hardware" (Loop & Blinn, 2005)

### 2. 一阶泰勒近似

使用一阶导数估计距离:
- **优点**: 计算简单,性能高
- **权衡**: 精度略低于二阶,但配合几何细分足够
- **决策**: 实验表明一阶近似性价比最高

### 3. 导数硬件加速

利用 GPU 的 `dFdx`/`dFdy` 指令:
- **优点**: 硬件自动计算偏导,无需显式传递
- **要求**: 需要硬件支持 (大多数现代 GPU 支持)
- **替代**: 不支持时回退到其他渲染方法

### 4. 覆盖率驱动的反走样

使用 `max(1 - distance, 0)` 生成覆盖率:
- **优点**: 平滑的亚像素级反走样
- **实现**: 单指令,无分支
- **效果**: 细线边缘平滑过渡

### 5. 可选的平滑曲线

注释中包含三次平滑函数 (已禁用):
```glsl
// edgeAlpha = edgeAlpha*edgeAlpha*(3.0-2.0*edgeAlpha);  // Smoothstep
```
- **效果**: 更平滑的过渡,类似 smoothstep
- **弃用原因**: 额外计算开销,视觉改善有限

### 6. 矩阵优化

使用 `AddMatrixKeys` 识别矩阵类型:
- **优点**: 单位矩阵跳过变换,平移矩阵简化计算
- **实现**: 编译期优化,生成不同的着色器变体

## 性能考量

### 1. 顶点数据效率

**GrConicEffect**:
- 位置: 8 字节 (2 × float)
- 系数: 16 字节 (4 × float)
- 总计: 24 字节/顶点

**GrQuadEffect**:
- 位置: 8 字节
- 参数坐标: 16 字节
- 总计: 24 字节/顶点

### 2. 片段着色器开销

**GrConicEffect**:
- 4 次 `dFdx`/`dFdy` (硬件加速)
- ~15 次算术运算
- 1 次 `sqrt` 和 `length`
- 总计: ~25-30 GPU 指令

**GrQuadEffect**:
- 2 次 `dFdx`/`dFdy`
- ~10 次算术运算
- 1 次 `sqrt`
- 总计: ~15-20 GPU 指令

### 3. 硬件要求

**必需特性**:
- 着色器导数支持 (GL_OES_standard_derivatives)
- 浮点纹理 (用于中间计算)

**可选优化**:
- Half 精度运算 (移动设备)
- 快速数学模式

### 4. 几何细分策略

**一阶近似的限制**:
- 高曲率区域误差较大
- 需要将曲线细分为多段

**细分准则**:
- 曲率半径 < 像素阈值时细分
- 通常每条曲线 2-8 段

### 5. 批处理优化

- **无状态**: 所有曲线可批量渲染
- **实例化**: 支持 GPU 实例化绘制
- **顶点缓冲**: 共享缓冲区,减少绑定操作

### 6. 实际性能指标

典型曲线渲染场景:
- **顶点数**: 4-8 顶点/曲线段
- **片段数**: 20-100 片段/曲线段
- **渲染时间**: <0.05ms/曲线 (现代 GPU)

## 相关文件

### 同目录文件
- `GrConvexPolyEffect`: 凸多边形裁剪效果
- `GrDistanceFieldGeoProc`: 距离场渲染 (SDF)
- `GrTextureEffect`: 通用纹理采样

### 依赖的核心文件
- `src/gpu/ganesh/GrGeometryProcessor.h`: 几何处理器基类
- `src/gpu/ganesh/GrCaps.h`: GPU 能力查询
- `src/gpu/ganesh/glsl/GrGLSLFragmentShaderBuilder.h`: 片段着色器构建

### 使用此文件的上层模块
- `GrDefaultPathRenderer`: 默认路径渲染器
- `GrTessellatingPathRenderer`: 曲面细分路径渲染器
- `GrStrokeHardwareTessellator`: 描边曲面细分

### 理论参考
- Loop & Blinn, "Resolution Independent Curve Rendering using Programmable Graphics Hardware", SIGGRAPH 2005
- Taubin, "Distance Approximations for Rasterizing Implicit Curves", ACM TOG

### 测试文件
- `tests/ProcessorTest.cpp`: 几何处理器单元测试
- `tests/PathTest.cpp`: 路径渲染测试
- `tests/AAHairlineTest.cpp`: 反走样细线测试
