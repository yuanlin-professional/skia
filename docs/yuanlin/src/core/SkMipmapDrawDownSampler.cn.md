# SkMipmapDrawDownSampler

> 源文件: src/core/SkMipmapDrawDownSampler.cpp

## 概述

`SkMipmapDrawDownSampler` 是 Skia 中基于绘制系统（Drawing System）实现的 mipmap 下采样器。与传统的像素级下采样算法不同，该实现利用 Skia 的 2D 绘制能力和高质量重采样过滤器（如 Catmull-Rom 三次插值）来生成 mipmap 层级。

该下采样器仅在定义了 `SK_USE_DRAWING_MIPMAP_DOWNSAMPLER` 宏时编译，提供更高质量的 mipmap 生成，尤其适合非 2x2 整数倍缩放的情况。它将每个 mipmap 层级的生成视为一次图像绘制操作，充分利用 Skia 的成熟渲染管道。

## 架构位置

`SkMipmapDrawDownSampler` 位于 Skia 的 mipmap 生成子系统中，作为 `SkMipmapDownSampler` 接口的一个实现：

- **接口层**：实现 `SkMipmapDownSampler` 抽象接口
- **同级实现**：与 `SkMipmapHQDownSampler`（高质量像素级下采样器）并列
- **依赖层**：使用 `SkDraw`、`SkRasterClip`、`SkMatrix` 等绘制系统组件

在 mipmap 构建流程中，`SkMipmap::MakeDownSampler()` 根据编译配置选择该实现或其他实现，为 `SkMipmap::Build()` 提供层级生成能力。

## 主要类与结构体

### DrawDownSampler

| **特性** | **说明** |
|---------|---------|
| **继承关系** | 继承自 `SkMipmapDownSampler` |
| **类型** | 下采样策略实现 |
| **作用域** | 匿名命名空间内部，外部不可见 |

**关键成员变量：**

| **成员变量** | **类型** | **说明** |
|------------|---------|---------|
| `fPaint` | `SkPaint` | 绘制配置，设置为 `kSrc` 混合模式以避免额外混合 |

### 关键方法

```cpp
void buildLevel(const SkPixmap& dst, const SkPixmap& src) override;
```

从源层级生成目标层级的像素数据。

## 公共 API 函数

### 工厂方法

```cpp
std::unique_ptr<SkMipmapDownSampler> SkMipmap::MakeDownSampler(const SkPixmap& root);
```

当 `SK_USE_DRAWING_MIPMAP_DOWNSAMPLER` 宏定义时，该函数返回 `DrawDownSampler` 实例：

```cpp
return std::make_unique<DrawDownSampler>();
```

### buildLevel 实现

```cpp
void DrawDownSampler::buildLevel(const SkPixmap& dst, const SkPixmap& src);
```

执行单个 mipmap 层级的生成：

1. 设置光栅裁剪区域为目标区域
2. 计算从源到目标的缩放矩阵
3. 根据缩放比例选择采样选项
4. 使用 `SkDraw` 将源图像绘制到目标

## 内部实现细节

### 采样选项选择

辅助函数 `choose_options()` 根据缩放比例选择最优采样方式：

```cpp
static SkSamplingOptions choose_options(const SkPixmap& dst, const SkPixmap& src) {
    // 完美 2x2 下采样：使用双线性过滤
    if (dst.width() * 2 == src.width() && dst.height() * 2 == src.height()) {
        return SkSamplingOptions(SkFilterMode::kLinear, SkMipmapMode::kNone);
    }
    // 一般情况：使用 Catmull-Rom 三次插值
    const auto cubic = SkCubicResampler::CatmullRom();
    return SkSamplingOptions(cubic);
}
```

**设计考量**：

- **2x2 整数倍缩放**：双线性过滤速度快且质量足够
- **非整数倍或各向异性缩放**：Catmull-Rom 三次插值提供更高质量

### 绘制流程

`buildLevel()` 的核心实现：

```cpp
void DrawDownSampler::buildLevel(const SkPixmap& dst, const SkPixmap& src) {
    const SkRasterClip rclip(dst.bounds());
    const SkMatrix mx = SkMatrix::Scale(
        SkIntToScalar(dst.width()) / src.width(),
        SkIntToScalar(dst.height()) / src.height());
    const auto sampling = choose_options(dst, src);

    SkDraw draw;
    draw.fDst = dst;
    draw.fCTM = &mx;
    draw.fRC = &rclip;

    SkBitmap bitmap;
    bitmap.installPixels(src.info(), const_cast<void*>(src.addr()), src.rowBytes());

    draw.drawBitmap(bitmap, SkMatrix::I(), nullptr, sampling, fPaint);
}
```

**步骤分解**：

1. **裁剪区域**：`SkRasterClip` 限制绘制范围为目标区域
2. **变换矩阵**：计算从单位矩形到目标尺寸的缩放
3. **绘制上下文**：`SkDraw` 封装目标、变换、裁剪信息
4. **源图像包装**：使用 `SkBitmap::installPixels()` 零拷贝包装源数据
5. **执行绘制**：调用 `drawBitmap()` 执行重采样和绘制

### 混合模式优化

构造函数设置 `kSrc` 混合模式：

```cpp
DrawDownSampler() {
    fPaint.setBlendMode(SkBlendMode::kSrc);
}
```

**原因**：

- mipmap 生成不需要混合（目标像素无预存内容）
- `kSrc` 模式直接覆盖目标像素，避免额外的混合计算
- 提升性能，减少不必要的操作

## 依赖关系

### 依赖的模块

| **模块** | **用途** |
|---------|---------|
| `SkDraw` | 核心绘制引擎，执行像素级渲染 |
| `SkRasterClip` | 光栅裁剪，定义绘制边界 |
| `SkMatrix` | 几何变换，计算缩放矩阵 |
| `SkPaint` | 绘制属性，设置混合模式 |
| `SkBitmap` | 图像容器，包装源像素数据 |
| `SkPixmap` | 像素数据访问接口 |
| `SkSamplingOptions` | 采样配置，包括过滤模式和三次插值参数 |

### 被依赖的模块

| **模块** | **关系** |
|---------|---------|
| `SkMipmap` | 通过 `MakeDownSampler()` 工厂方法创建实例 |
| 编译配置系统 | 由 `SK_USE_DRAWING_MIPMAP_DOWNSAMPLER` 宏控制 |

## 设计模式与设计决策

### 策略模式

`DrawDownSampler` 作为 `SkMipmapDownSampler` 接口的具体策略：

- 与 `HQDownSampler` 提供不同的实现方式
- 运行时通过工厂方法选择（但当前是编译时配置）
- 易于扩展和替换

### 编译时配置

通过宏 `SK_USE_DRAWING_MIPMAP_DOWNSAMPLER` 控制：

```cpp
#ifdef SK_USE_DRAWING_MIPMAP_DOWNSAMPLER
// 实现代码
#endif
```

**优势**：

- 避免运行时开销和代码膨胀
- 允许针对不同平台优化
- 条件编译减少不必要的依赖

### 复用现有基础设施

充分利用 Skia 的绘制系统：

- 无需重新实现重采样算法
- 自动支持各种像素格式
- 受益于绘制系统的优化（SIMD、缓存友好等）

### 零拷贝数据传递

使用 `SkBitmap::installPixels()` 而非 `allocPixels()`：

- 避免不必要的内存分配和拷贝
- 直接操作源 `SkPixmap` 的数据
- 提高性能和内存效率

## 性能考量

### 质量 vs 速度权衡

**优势**：

- **高质量重采样**：Catmull-Rom 三次插值优于简单的盒式或双线性过滤
- **自动优化**：绘制系统内部已针对各种路径优化
- **格式灵活性**：自动处理各种像素格式，无需针对每种格式编写代码

**劣势**：

- **额外开销**：完整的绘制管道比专用像素级算法更重
- **缓存效率**：可能不如手写的缓存友好循环
- **代码路径复杂**：经过多层抽象，调试和优化困难

### 适用场景

- **质量优先**：需要最佳视觉质量的应用
- **复杂缩放**：非整数倍或各向异性缩放
- **开发便利性**：快速迭代，利用现有基础设施
- **格式兼容性**：需要支持多种像素格式而不想为每种编写代码

### 与 HQDownSampler 对比

| **维度** | **DrawDownSampler** | **HQDownSampler** |
|---------|-------------------|------------------|
| **实现方式** | 基于绘制系统 | 模板化像素级算法 |
| **质量** | 优秀（三次插值） | 良好（盒式/三角形过滤） |
| **速度** | 中等 | 快（针对特定格式优化） |
| **代码复杂度** | 低（复用现有） | 高（每种格式单独实现） |
| **格式支持** | 自动支持所有 | 需要逐个添加 |

### 优化建议

- 对于关键性能路径，考虑使用 `HQDownSampler`
- 对于一次性或离线处理，`DrawDownSampler` 更合适
- 可以根据像素格式动态选择策略（当前未实现）

## 相关文件

| **文件路径** | **说明** |
|-------------|---------|
| `src/core/SkMipmapHQDownSampler.cpp` | 替代实现：高质量像素级下采样器 |
| `src/core/SkMipmap.h/cpp` | mipmap 核心类，调用下采样器接口 |
| `src/core/SkDraw.h/cpp` | 绘制引擎，执行实际的像素渲染 |
| `include/core/SkSamplingOptions.h` | 采样选项定义 |
| `include/core/SkPaint.h` | 绘制属性配置 |
| `include/core/SkMatrix.h` | 几何变换 |
| `src/core/SkRasterClip.h` | 光栅裁剪 |
