# src/effects - Skia 效果子系统

## 概述

`src/effects` 是 Skia 图形库中**效果子系统**的顶层目录，负责实现各种图形效果处理功能。该目录涵盖了三大类效果：**路径效果**（Path Effects）、**遮罩滤镜**（Mask Filters）以及**颜色与混合处理**。这些效果可以在绘制过程中对路径、颜色和像素进行变换和修饰，是 Skia 渲染管线中不可缺少的重要组成部分。

路径效果子系统是本目录的核心功能之一，提供了丰富的路径变换能力。包括沿路径重复放置图案的 `Sk1DPathEffect`、在二维网格上生成路径的 `Sk2DPathEffect`、生成虚线的 `SkDashPathEffect`、圆角路径的 `SkCornerPathEffect`、路径离散化的 `SkDiscretePathEffect`，以及路径裁剪的 `SkTrimPathEffect`。这些路径效果均继承自 `SkPathEffectBase`（位于 `src/core`），通过 `onFilterPath` 虚函数对输入路径进行变换处理。

遮罩滤镜方面，本目录实现了浮雕遮罩滤镜 `SkEmbossMaskFilter`（模拟 3D 浮雕效果）、基于着色器的遮罩滤镜 `SkShaderMaskFilterImpl`，以及表格遮罩滤镜 `SkTableMaskFilter`。这些滤镜通过修改遮罩（Mask）中的 alpha 通道数据来实现各种视觉特效。

此外，本目录还包含 `SkBlenders`（算术混合器实现）、`SkColorMatrix`（颜色矩阵工具类）、`SkColorMatrixFilter`（颜色矩阵滤镜的便捷封装）以及 `SkHighContrastFilter`（高对比度滤镜，用于辅助功能）。这些实用组件为上层应用提供了灵活的颜色和混合操控能力。

`src/effects` 目录还包含两个重要子目录：`colorfilters`（颜色滤镜实现）和 `imagefilters`（图像滤镜实现），分别封装了更加专业化的颜色变换和像素级图像处理功能。

## 架构图

```
                         +----------------------------+
                         |      include/effects/      |
                         |   (公共 API 头文件)          |
                         +-------------+--------------+
                                       |
                    +------------------+------------------+
                    |                  |                  |
         +----------v--------+ +------v------+ +---------v----------+
         |  src/effects/      | | colorfilters| |   imagefilters     |
         |  (路径效果/遮罩/   | |  (颜色滤镜)  | |   (图像滤镜)        |
         |   混合/颜色矩阵)   | |             | |                    |
         +---+----+----+-----+ +------+------+ +--------+-----------+
             |    |    |              |                   |
             v    v    v              v                   v
    +--------+  +-+----+--+  +-------+--------+  +------+---------+
    |SkPath  |  |SkMask   |  |SkColorFilter   |  |SkImageFilter   |
    |Effect  |  |Filter   |  |Base             |  |_Base           |
    |Base    |  |Base     |  |(颜色滤镜基类)    |  |(图像滤镜基类)   |
    |(路径效  |  |(遮罩滤镜 |  +----------------+  +----------------+
    | 果基类) |  | 基类)   |
    +--------+  +---------+
             \      |      /
              \     |     /
               v    v    v
         +-----+----+-----+
         |    src/core/    |
         | (核心渲染管线)   |
         | SkRasterPipeline|
         +--+-----------+--+
            |           |
            v           v
    +-------+---+ +-----+--------+
    | SkFlatten | | SkArenaAlloc |
    |  able     | | (内存分配器)  |
    | (序列化)  | +------+-------+
    +-----------+
```

## 目录结构

```
src/effects/
|-- BUILD.bazel                      # Bazel 构建配置
|-- Sk1DPathEffect.cpp               # 一维路径效果（沿路径放置图案）
|-- Sk2DPathEffect.cpp               # 二维路径效果（二维网格路径生成）
|-- SkBlenders.cpp                   # 算术混合器（Arithmetic Blender）
|-- SkColorMatrix.cpp                # 颜色矩阵工具类实现
|-- SkColorMatrixFilter.cpp          # 颜色矩阵滤镜便捷封装
|-- SkCornerPathEffect.cpp           # 圆角路径效果
|-- SkDashImpl.h                     # 虚线路径效果内部实现头文件
|-- SkDashPathEffect.cpp             # 虚线路径效果
|-- SkDiscretePathEffect.cpp         # 离散路径效果（锯齿/噪声）
|-- SkEmbossMask.cpp                 # 浮雕遮罩生成实现
|-- SkEmbossMask.h                   # 浮雕遮罩内部头文件
|-- SkEmbossMaskFilter.cpp           # 浮雕遮罩滤镜
|-- SkEmbossMaskFilter.h             # 浮雕遮罩滤镜内部头文件
|-- SkHighContrastFilter.cpp         # 高对比度滤镜（辅助功能）
|-- SkShaderMaskFilterImpl.cpp       # 着色器遮罩滤镜实现
|-- SkShaderMaskFilterImpl.h         # 着色器遮罩滤镜内部头文件
|-- SkTableMaskFilter.cpp            # 表格遮罩滤镜
|-- SkTrimPE.h                       # 路径裁剪效果内部头文件
|-- SkTrimPathEffect.cpp             # 路径裁剪效果
|-- colorfilters/                    # 颜色滤镜子目录
|-- imagefilters/                    # 图像滤镜子目录
```

## 关键类与函数

### 路径效果类

| 类名 | 基类 | 功能描述 |
|------|------|----------|
| `Sk1DPathEffect` | `SkPathEffectBase` | 沿路径轮廓重复放置图案的抽象基类 |
| `SkPath1DPathEffectImpl` | `Sk1DPathEffect` | 一维路径效果的具体实现，支持平移、旋转、变形三种放置模式 |
| `Sk2DPathEffect` | `SkPathEffectBase` | 在二维矩阵网格上生成路径的抽象基类 |
| `SkLine2DPathEffectImpl` | `Sk2DPathEffect` | 在二维网格中绘制线段 |
| `SkPath2DPathEffectImpl` | `Sk2DPathEffect` | 在二维网格中放置路径 |
| `SkDashImpl` | `SkPathEffectBase` | 虚线路径效果，根据间隔数组和相位参数生成虚线 |
| `SkCornerPathEffectImpl` | `SkPathEffectBase` | 将路径拐角替换为指定半径的圆弧 |
| `SkTrimPE` | `SkPathEffectBase` | 根据起止参数裁剪路径的一部分 |

### 遮罩滤镜类

| 类名 | 基类 | 功能描述 |
|------|------|----------|
| `SkEmbossMaskFilter` | `SkMaskFilterBase` | 通过指定光源方向和模糊量模拟 3D 浮雕效果 |
| `SkShaderMaskFilterImpl` | `SkMaskFilterBase` | 使用着色器修改遮罩的 alpha 通道 |
| `SkTableMaskFilter` | -- | 通过查找表对遮罩 alpha 值进行映射变换 |

### 工具与辅助类

| 类/函数名 | 功能描述 |
|-----------|----------|
| `SkBlenders::Arithmetic()` | 创建算术混合器，支持 k1*src*dst + k2*src + k3*dst + k4 公式 |
| `SkColorMatrix` | 4x5 颜色变换矩阵，支持缩放、平移、饱和度调整、RGB/YUV 转换 |
| `SkHighContrastFilter::Make()` | 创建高对比度颜色滤镜，支持灰度化、亮度/明度反转和对比度调节 |
| `SkColorMatrixFilter` | `SkColorMatrix` 与 `SkColorFilter` 之间的便捷桥接 |

### 关键函数

- **`onFilterPath()`**：所有路径效果的核心虚函数，接收源路径并输出变换后的路径
- **`filterMask()`**：遮罩滤镜的核心函数，接收源遮罩并输出处理后的遮罩
- **`morphpath()`**：`Sk1DPathEffect` 中的内部函数，将路径沿测量路径进行形态变换
- **`SkDashPath::CalcDashParameters()`**：计算虚线的初始偏移和间隔参数
- **`set_concat()`**：`SkColorMatrix` 中的矩阵级联运算函数

## 依赖关系

### 向上依赖（被以下模块使用）

- `include/effects/` - 公共 API 头文件，定义了各效果的工厂方法
- `src/core/SkPaint` - 绘制时通过 Paint 引用路径效果和遮罩滤镜
- `src/core/SkDraw` - 绘制流程中调用路径效果进行路径变换
- `src/gpu/` - GPU 后端在渲染时使用各类效果

### 向下依赖（依赖以下模块）

- `src/core/SkPathEffectBase` - 路径效果的基类
- `src/core/SkMaskFilterBase` - 遮罩滤镜的基类
- `src/core/SkRasterPipeline` - 光栅化管线，颜色操作的执行引擎
- `src/core/SkArenaAlloc` - 高效的竞技场内存分配器
- `src/core/SkReadBuffer` / `SkWriteBuffer` - 序列化与反序列化支持
- `src/core/SkKnownRuntimeEffects` - 预编译的运行时效果（SkSL 程序）
- `include/core/SkFlattenable` - 可平坦化接口，用于持久化和网络传输
- `include/core/SkPathMeasure` - 路径测量，供一维路径效果使用
- `modules/skcms/` - 颜色管理系统模块

## 设计模式分析

### 工厂方法模式（Factory Method）

所有效果类都通过静态工厂方法创建实例，而非直接暴露构造函数。例如：
- `SkPath1DPathEffect::Make(path, advance, phase, style)` - 创建一维路径效果
- `SkDashPathEffect::Make(intervals, count, phase)` - 创建虚线效果
- `SkEmbossMaskFilter::Make(blurSigma, light)` - 创建浮雕遮罩滤镜
- `SkHighContrastFilter::Make(config)` - 创建高对比度滤镜

工厂方法中会进行参数有效性验证，不合法参数返回 `nullptr`。

### 模板方法模式（Template Method）

路径效果的基类定义了算法骨架，子类实现具体步骤：
- `Sk1DPathEffect::onFilterPath()` 定义了沿路径迭代的整体流程，子类通过 `begin()` 和 `next()` 提供具体行为
- `Sk2DPathEffect::onFilterPath()` 定义了二维网格遍历流程，子类通过 `begin()`、`next()`、`nextSpan()`、`end()` 实现具体的路径生成

### 策略模式（Strategy Pattern）

`SkPath1DPathEffectImpl` 中的 `Style` 枚举（`kTranslate`、`kRotate`、`kMorph`）体现了策略模式，相同的路径放置迭代框架配合不同的变换策略，在 `next()` 函数中根据策略选择不同的变换方式。

### Flattenable 序列化框架

所有效果类都实现了 `SkFlattenable` 接口，通过 `flatten()` 和 `CreateProc()` 实现序列化与反序列化。使用 `SK_FLATTENABLE_HOOKS` 宏和 `SK_REGISTER_FLATTENABLE` 宏简化了注册流程，支持旧名称的兼容反序列化。

### 运行时效果委托

`SkHighContrastFilter` 和 `SkBlenders::Arithmetic()` 展示了一种委托模式：它们并不直接实现像素处理逻辑，而是将参数打包后委托给预编译的 SkSL 运行时效果（通过 `SkKnownRuntimeEffects` 获取），利用 `SkRuntimeEffect` 的跨后端执行能力。

## 数据流

### 路径效果数据流

```
输入路径(SkPath)
    |
    v
SkPathEffect::filterPath()
    |
    v
onFilterPath(SkPathBuilder*, SkPath&, SkStrokeRec*)
    |
    +-- Sk1DPathEffect: SkPathMeasure 沿路径迭代
    |       |
    |       +-- begin() -> 获取初始偏移
    |       +-- next()  -> 在每个位置生成/变换子路径
    |       |     +-- kTranslate: addPath(平移)
    |       |     +-- kRotate: addPath(矩阵旋转)
    |       |     +-- kMorph: morphpath(形态变换)
    |       +-- 累加 delta 直到轮廓结束
    |
    +-- Sk2DPathEffect: SkMatrix 反变换 + SkRegion 遍历
    |       |
    |       +-- begin() -> 初始化
    |       +-- nextSpan() -> 逐行遍历网格点
    |       +-- end() -> 完成
    |
    +-- SkDashImpl: SkDashPath::InternalFilter 虚线逻辑
    |
    +-- SkTrimPE: SkPathMeasure 截取 [startT, stopT] 段
    |
    v
输出路径(SkPathBuilder -> SkPath)
```

### 遮罩滤镜数据流

```
输入遮罩(SkMask)
    |
    v
SkMaskFilter::filterMask()
    |
    +-- SkEmbossMaskFilter:
    |       | 1. 模糊源遮罩
    |       | 2. 计算法线方向
    |       | 3. 根据光源方向计算漫反射和镜面反射
    |       | 4. 生成带有 3D 浮雕效果的 3D 格式遮罩
    |       v
    |   输出遮罩(SkMask, kThreeD_Format)
    |
    +-- SkShaderMaskFilterImpl:
    |       | 1. 对遮罩区域使用着色器渲染到临时位图
    |       | 2. 将着色器 alpha 与源遮罩 alpha 合并
    |       v
    |   输出遮罩(SkMask, kA8_Format)
    |
    v
用于最终光栅化合成
```

### 颜色与混合数据流

```
SkHighContrastFilter::Make(config)
    |
    v
构建 uniform 参数 (grayscale, invertStyle, contrast)
    |
    v
GetKnownRuntimeEffect(StableKey::kHighContrast) -> SkRuntimeEffect
    |
    v
SkColorFilterPriv::WithWorkingFormat(runtimeFilter, linearTF, gamut, unpremul)
    |
    v
SkWorkingFormatColorFilter 包装 -> 在线性色彩空间中执行处理
```

## 相关文档与参考

### 相关头文件

| 公共头文件 | 描述 |
|-----------|------|
| `include/effects/Sk1DPathEffect.h` | 一维路径效果公共 API |
| `include/effects/Sk2DPathEffect.h` | 二维路径效果公共 API |
| `include/effects/SkDashPathEffect.h` | 虚线路径效果公共 API |
| `include/effects/SkCornerPathEffect.h` | 圆角路径效果公共 API |
| `include/effects/SkDiscretePathEffect.h` | 离散路径效果公共 API |
| `include/effects/SkTrimPathEffect.h` | 路径裁剪效果公共 API |
| `include/effects/SkShaderMaskFilter.h` | 着色器遮罩滤镜公共 API |
| `include/effects/SkTableMaskFilter.h` | 表格遮罩滤镜公共 API |
| `include/effects/SkBlenders.h` | 算术混合器公共 API |
| `include/effects/SkColorMatrix.h` | 颜色矩阵工具类公共 API |
| `include/effects/SkHighContrastFilter.h` | 高对比度滤镜公共 API |
| `include/effects/SkRuntimeEffect.h` | 运行时效果框架公共 API |

### 相关子目录

- `src/effects/colorfilters/` - 颜色滤镜实现，包含 8 种颜色滤镜类型
- `src/effects/imagefilters/` - 图像滤镜实现，包含 17 种图像处理效果
- `src/core/` - 核心模块，包含基类 `SkPathEffectBase`、`SkMaskFilterBase` 以及光栅化管线

### 核心依赖模块

- `src/core/SkRasterPipeline` - 光栅化管线，效果处理的底层执行引擎
- `src/core/SkKnownRuntimeEffects` - 预编译 SkSL 运行时效果集合
- `src/utils/SkDashPathPriv` - 虚线路径的辅助计算工具
- `modules/skcms/` - 颜色管理系统，用于色彩空间转换

### 构建系统

- `BUILD.bazel` - Bazel 构建文件，将效果文件打包为 `effects_srcs` 和 `effects_hdrs`
- 颜色滤镜通过 `//src/effects/colorfilters:colorfilter_srcs` 引入
- 图像滤镜通过 `//src/effects/imagefilters:srcs` 引入
- 所有内部头文件通过 `core_priv_hdrs` 导出给 `src/core` 使用
