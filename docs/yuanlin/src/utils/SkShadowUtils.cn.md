# SkShadowUtils

> 源文件: include/utils/SkShadowUtils.h, src/utils/SkShadowUtils.cpp

## 概述

`SkShadowUtils` 是 Skia 图形库中专门用于生成和绘制阴影的工具类。该模块实现了基于物理的阴影渲染系统,支持环境光阴影(ambient shadow)和聚光阴影(spot shadow)的生成,提供了一套完整的阴影计算和渲染方案。通过对光源位置、遮挡物高度、光源半径等参数的精确控制,能够生成逼真的3D阴影效果。

该模块的核心功能包括:根据路径和光照参数绘制阴影、计算阴影边界框、计算色调颜色,以及通过资源缓存机制优化重复绘制的性能。支持点光源和方向光源两种光照模式,并提供透明遮挡物、几何阴影、模糊阴影等多种渲染选项。

## 架构位置

`SkShadowUtils` 位于 Skia 的实用工具层(utils),为上层应用提供高级阴影绘制功能。它依赖于核心图形模块(core)、设备抽象层(device)以及顶点镶嵌器(tessellator)等底层组件:

```
应用层
   ↓
SkShadowUtils (工具层 - include/utils, src/utils)
   ↓
├── SkCanvas (画布抽象)
├── SkDevice (设备层)
├── SkShadowTessellator (阴影镶嵌器)
├── SkResourceCache (资源缓存)
└── 核心图形组件 (SkPath, SkPaint, SkVertices 等)
```

## 主要类与结构体

### SkShadowUtils

主要的阴影工具类,提供静态方法用于阴影绘制和计算。

**继承关系**: 无继承关系,纯静态工具类

**关键成员变量**: 无(所有方法为静态方法)

### SkShadowFlags (枚举)

| 标志 | 值 | 说明 |
|------|-----|------|
| kNone_ShadowFlag | 0x00 | 无特殊标志 |
| kTransparentOccluder_ShadowFlag | 0x01 | 遮挡物不透明,可剔除背后阴影几何 |
| kGeometricOnly_ShadowFlag | 0x02 | 不使用解析阴影,仅使用几何方法 |
| kDirectionalLight_ShadowFlag | 0x04 | 光源位置表示方向,光源半径为高度1处的模糊半径 |
| kConcaveBlurOnly_ShadowFlag | 0x08 | 凹路径仅使用模糊生成阴影 |
| kAll_ShadowFlag | 0x0F | 所有标志的掩码 |

### CachedTessellations (内部类)

管理特定形状的阴影镶嵌结果缓存,包含环境光和聚光阴影的顶点集合。

**关键成员变量**:

| 变量名 | 类型 | 说明 |
|--------|------|------|
| fAmbientSet | Set<AmbientVerticesFactory, 4> | 环境光阴影顶点缓存集合 |
| fSpotSet | Set<SpotVerticesFactory, 4> | 聚光阴影顶点缓存集合 |

### AmbientVerticesFactory (内部结构体)

环境光阴影顶点工厂,存储生成环境光阴影所需的参数。

**关键成员变量**:

| 变量名 | 类型 | 说明 |
|--------|------|------|
| fOccluderHeight | SkScalar | 遮挡物高度 |
| fTransparent | bool | 遮挡物是否透明 |
| fOffset | SkVector | 阴影偏移量 |

### SpotVerticesFactory (内部结构体)

聚光阴影顶点工厂,存储生成聚光阴影所需的参数。

**关键成员变量**:

| 变量名 | 类型 | 说明 |
|--------|------|------|
| fOffset | SkVector | 阴影偏移量 |
| fLocalCenter | SkPoint | 局部中心点 |
| fOccluderHeight | SkScalar | 遮挡物高度 |
| fDevLightPos | SkPoint3 | 设备空间光源位置 |
| fLightRadius | SkScalar | 光源半径 |
| fOccluderType | OccluderType | 遮挡物类型枚举 |

## 公共 API 函数

### DrawShadow

```cpp
static void DrawShadow(SkCanvas* canvas, const SkPath& path,
                      const SkPoint3& zPlaneParams,
                      const SkPoint3& lightPos, SkScalar lightRadius,
                      SkColor ambientColor, SkColor spotColor,
                      uint32_t flags = kNone_ShadowFlag);
```

根据给定路径绘制偏移的聚光阴影和环境光阴影。阴影可能被缓存,具体取决于路径类型和画布矩阵。

**参数说明**:
- `canvas`: 绘制阴影的画布
- `path`: 用于生成阴影的遮挡物路径
- `zPlaneParams`: 平面函数参数,返回遮挡物相对画布的Z偏移
- `lightPos`: 光源的3D位置(相对画布平面),或方向光的方向向量
- `lightRadius`: 光盘半径,或方向光在Z=1处的模糊量
- `ambientColor`: 环境光阴影颜色
- `spotColor`: 聚光阴影颜色
- `flags`: 控制优化和光源位置的标志

### GetLocalBounds

```cpp
static bool GetLocalBounds(const SkMatrix& ctm, const SkPath& path,
                          const SkPoint3& zPlaneParams,
                          const SkPoint3& lightPos,
                          SkScalar lightRadius, uint32_t flags,
                          SkRect* bounds);
```

生成相对于路径的阴影边界框,包括环境光和聚光阴影的边界。

**返回值**: 成功返回 true,否则返回 false

### ComputeTonalColors

```cpp
static void ComputeTonalColors(SkColor inAmbientColor, SkColor inSpotColor,
                               SkColor* outAmbientColor,
                               SkColor* outSpotColor);
```

计算单遍色调 alpha 的颜色值。根据输入的环境光和聚光颜色计算修改后的色调颜色。该函数实现了基于亮度的颜色 alpha 调整算法,确保阴影颜色与 UX 示例匹配。

## 内部实现细节

### 阴影镶嵌与缓存机制

模块采用顶点镶嵌技术生成阴影几何体,通过 `SkShadowTessellator` 将阴影转换为可渲染的顶点网格。为优化性能,实现了基于 `SkResourceCache` 的多级缓存策略:

1. **CachedTessellationsRec**: 存储特定路径的镶嵌结果
2. **Set 结构**: 每种阴影类型(环境光/聚光)最多缓存4个不同配置的顶点集
3. **随机替换策略**: 缓存满时随机替换旧条目

缓存键基于路径的几何特征(`GrStyledShape`)生成,通过 `ShadowInvalidator` 监听路径变化自动失效缓存。

### 阴影绘制流程

`SkDevice::drawShadow` 实现了完整的阴影绘制管线:

1. **参数验证**: 检查光源位置、Z平面参数的有效性
2. **矩阵转换**: 将光源位置从世界空间转换到设备空间
3. **环境光阴影绘制**:
   - 尝试从缓存获取顶点
   - 缓存未命中则调用镶嵌器生成
   - 应用高斯滤镜和颜色调制
   - 失败时降级到模糊路径方式
4. **聚光阴影绘制**:
   - 计算遮挡物类型(透明/不透明/部分本影等)
   - 根据类型选择合适的镶嵌策略
   - 应用颜色滤镜并绘制
   - 失败时使用阴影变换矩阵+模糊

### 色调颜色计算

`ComputeTonalColors` 实现了复杂的色调颜色算法:

- **环境光**: 转换为灰度(仅保留 alpha)
- **聚光**: 基于亮度计算色彩 alpha 和灰度 alpha
  - 亮度范围 [0,1] 映射到不同的 alpha 值
  - 使用多项式函数确保特定亮度点的 alpha 值匹配 UX 规范
  - 最终颜色 = 预乘后的色彩分量 + alpha 组合

### 遮挡物类型分类

聚光阴影根据遮挡物特性和投影情况分为5种类型:

- **kPointTransparent**: 透明遮挡物,无法剔除本影
- **kPointOpaquePartialUmbra**: 不透明遮挡物,部分本影可见
- **kPointOpaqueNoUmbra**: 不透明遮挡物,本影完全被遮挡
- **kDirectional**: 方向光源
- **kDirectionalTransparent**: 方向光源下的透明遮挡物

类型判定考虑透明度、偏移量、路径凸性等因素,影响镶嵌器的剔除策略。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkCanvas | 画布接口,用于绘制阴影 |
| SkPath | 路径表示,定义遮挡物形状 |
| SkPaint | 绘制属性,设置颜色滤镜和混合模式 |
| SkVertices | 顶点数据表示 |
| SkShadowTessellator | 阴影镶嵌器,生成阴影几何体 |
| SkResourceCache | 资源缓存系统 |
| SkDevice | 设备抽象层 |
| SkBlurMask | 模糊蒙版,用于降级路径 |
| SkColorFilter | 颜色滤镜,实现高斯滤镜和色彩调制 |
| SkDrawShadowMetrics | 阴影度量计算 |

### 被依赖的模块

作为高级工具类,`SkShadowUtils` 主要被以下模块使用:

| 模块 | 使用方式 |
|------|----------|
| 应用程序代码 | 直接调用 DrawShadow 绘制阴影 |
| UI 框架 | Material Design 风格阴影效果 |
| SkCanvas | 内部调用 private_draw_shadow_rec |
| SkDevice | 设备层调用 drawShadow 方法 |

## 设计模式与设计决策

### 工厂模式

`AmbientVerticesFactory` 和 `SpotVerticesFactory` 采用工厂模式,封装了不同阴影类型的顶点生成逻辑:

- `makeVertices`: 根据参数生成顶点数据
- `isCompatible`: 判断是否可复用现有顶点

这种设计允许缓存系统统一处理不同类型的阴影,同时保持各自生成策略的灵活性。

### 资源缓存模式

基于 `SkResourceCache` 实现的缓存策略遵循以下原则:

- **不可变记录**: `CachedTessellationsRec` 不可修改,更新时创建新记录
- **访问者模式**: `FindVisitor` 用于查找和验证缓存条目
- **监听器模式**: `ShadowInvalidator` 监听路径变化自动失效缓存

### 降级策略

采用多级降级机制确保在各种情况下都能绘制阴影:

1. **优先级1**: 使用缓存的镶嵌顶点(最快)
2. **优先级2**: 实时镶嵌生成顶点(快速)
3. **降级方式**: 使用路径描边+模糊滤镜(兼容性最好)

特定条件触发降级:
- 透视变换
- 易变路径(volatile)
- 倾斜的Z平面
- 凹路径且设置了 `kConcaveBlurOnly_ShadowFlag`

### 条件编译优化

通过 `SK_ENABLE_OPTIMIZE_SIZE` 宏控制代码大小优化:

- 定义时:禁用镶嵌器和缓存,仅使用模糊方式
- 未定义时:启用完整的镶嵌+缓存系统

## 性能考量

### 缓存策略

- **Set 大小限制**: 每种阴影类型最多缓存4个变体,平衡内存占用和命中率
- **随机替换**: 避免固定模式导致的最坏情况
- **矩阵兼容性**: 非透视矩阵只比较缩放和倾斜,提高缓存命中率

### 顶点生成优化

- **规范位置**: 对于非透视矩阵,在规范位置(平移归零)生成顶点,提高可复用性
- **跳过颜色转换**: 阴影顶点颜色为黑色或透明,绘制时设置 `skipColorXform=true`
- **透视检测**: 透视矩阵下的阴影不缓存,直接生成并绘制

### 模糊计算优化

环境光模糊路径使用预计算的 `AmbientBlurRadius` 和 `AmbientRecipAlpha`:

- 避免每次绘制时重复计算模糊参数
- 描边宽度和模糊半径基于 Z 高度插值计算
- 公式优化:通过比例关系快速得到最终参数

### 降级路径优化

- 预变换路径到设备空间,避免变换描边
- 路径标记为易变,提示跳过缓存
- 模糊滤镜设置 `respectCTM=false`,减少变换计算

## 相关文件

| 文件路径 | 说明 |
|----------|------|
| include/utils/SkShadowUtils.h | 公共 API 头文件 |
| src/utils/SkShadowUtils.cpp | 实现文件 |
| src/utils/SkShadowTessellator.h | 阴影镶嵌器头文件 |
| src/core/SkDevice.h | 设备抽象层 |
| src/core/SkDrawShadowInfo.h | 阴影绘制信息结构 |
| src/core/SkResourceCache.h | 资源缓存系统 |
| src/core/SkBlurMask.h | 模糊蒙版 |
| src/core/SkColorFilterPriv.h | 颜色滤镜私有接口 |
| src/gpu/ganesh/GrStyledShape.h | Ganesh GPU 形状样式 |
