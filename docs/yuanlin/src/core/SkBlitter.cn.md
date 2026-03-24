# SkBlitter

> 源文件: src/core/SkBlitter.h, src/core/SkBlitter.cpp

## 概述

`SkBlitter` 是 Skia 图形库中负责实际像素写入的核心抽象类。它的主要职责是将渲染结果高效地写入到目标位图中，同时处理裁剪、抗锯齿、混合模式等复杂的图形操作。Blitter 接收来自扫描转换器的几何信息（如扫描线、游程），并根据绘制参数将像素数据写入设备缓冲区。每个 blitter 子类针对特定的颜色格式、混合模式或渲染策略进行优化。

## 架构位置

`SkBlitter` 位于 Skia 渲染管线的最底层，是像素操作的最终执行者：

```
SkCanvas (高层绘图 API)
    ↓
SkDraw (坐标变换和绘制调度)
    ↓
SkScan (扫描转换，生成扫描线)
    ↓
SkBlitter (像素写入) ← 当前模块
    ↓
SkPixmap (设备内存)
```

它与以下组件紧密配合：

- **扫描转换器** (`SkScan`): 将几何图形转换为扫描线和游程，调用 blitter 的各种 blit 方法
- **绘制引擎** (`SkDraw`): 协调变换、裁剪和 blitter 选择
- **Paint 系统**: 提供颜色、shader、blend mode 等绘制属性
- **Pixmap**: 提供对设备像素缓冲区的访问

## 主要类与结构体

### SkBlitter (抽象基类)

所有 blitter 实现的基类，定义了像素绘制的统一接口。

**继承关系:**
```
SkBlitter (抽象基类)
  ├── SkNullBlitter (什么都不绘制)
  ├── SkA8_Coverage_Blitter (Alpha 8 覆盖率绘制)
  ├── SkA8_Blitter (Alpha 8 混合绘制)
  ├── SkARGB32_Blitter (32 位颜色绘制)
  ├── SkRasterPipelineBlitter (通用管线绘制)
  ├── SkRectClipBlitter (矩形裁剪包装器)
  └── SkRgnClipBlitter (区域裁剪包装器)
```

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fBlitMemory` | `SkAutoMalloc` | Blitter 拥有的临时内存，用于存储 runs/alpha 数组等 |

**核心虚函数:**

| 函数名 | 说明 |
|--------|------|
| `blitH` | 绘制水平不透明像素行（纯虚函数） |
| `blitAntiH` | 绘制抗锯齿水平像素行，使用 run-length 编码（纯虚函数） |
| `blitV` | 绘制垂直像素列，带有恒定 alpha |
| `blitRect` | 绘制矩形区域 |
| `blitAntiRect` | 绘制带有左右边缘抗锯齿的矩形 |
| `blitFatAntiRect` | 绘制宽度至少为 3 的抗锯齿矩形 |
| `blitMask` | 根据遮罩图案绘制像素 |

### SkNullBlitter

空操作 blitter，所有绘制方法都不执行任何操作。用于完全裁剪掉的绘制或无效的颜色格式。

**继承关系:**
```
SkBlitter
  └── SkNullBlitter
```

### SkRectClipBlitter

包装器 blitter，在调用实际 blitter 之前对坐标进行矩形裁剪。

**继承关系:**
```
SkBlitter
  └── SkRectClipBlitter
```

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fBlitter` | `SkBlitter*` | 被包装的实际 blitter |
| `fClipRect` | `SkIRect` | 裁剪矩形 |

### SkRgnClipBlitter

包装器 blitter，对坐标进行区域裁剪（支持复杂的非矩形裁剪区域）。

**继承关系:**
```
SkBlitter
  └── SkRgnClipBlitter
```

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fBlitter` | `SkBlitter*` | 被包装的实际 blitter |
| `fRgn` | `const SkRegion*` | 裁剪区域 |

### SkBlitterClipper

工厂类，根据裁剪需求选择合适的 blitter 包装器。

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fNullBlitter` | `SkNullBlitter` | 用于完全裁剪的情况 |
| `fRectBlitter` | `SkRectClipBlitter` | 用于矩形裁剪 |
| `fRgnBlitter` | `SkRgnClipBlitter` | 用于复杂区域裁剪 |

### DirectBlit 结构体

描述直接像素写入的优化路径。

**关键成员:**

| 成员名 | 类型 | 说明 |
|--------|------|------|
| `pm` | `SkPixmap` | 目标像素映射 |
| `value` | `uint64_t` | 要写入的像素值（低位匹配位深度） |

## 公共 API 函数

### 工厂方法

#### SkBlitter::Choose

```cpp
static SkBlitter* Choose(const SkPixmap& dst,
                        const SkMatrix& ctm,
                        const SkPaint& paint,
                        SkArenaAlloc* alloc,
                        SkDrawCoverage coverage,
                        sk_sp<SkShader> clipShader,
                        const SkSurfaceProps& props,
                        const SkRect& devBounds);
```

根据设备格式、绘制参数和矩阵变换选择最优的 blitter 实现。这是 blitter 系统的核心入口点。

**选择逻辑:**
1. 检查颜色格式是否有效
2. 优化混合模式（将某些模式转换为 SrcOver 或跳过绘制）
3. 处理 Clear 混合模式
4. 展平 color filter
5. 对于覆盖率绘制，选择 A8 coverage blitter
6. 决定是否使用 legacy blitter 或 raster pipeline blitter
7. 对于 legacy 路径，根据 shader 和颜色选择 ARGB32 blitter 变体

#### SkBlitter::ChooseSprite

```cpp
static SkBlitter* ChooseSprite(const SkPixmap& dst,
                               const SkPaint& paint,
                               const SkPixmap& src,
                               int left, int top,
                               SkArenaAlloc* alloc,
                               sk_sp<SkShader> clipShader);
```

为 sprite（精灵）绘制选择 blitter。Sprite 是预先光栅化的小图像，可以快速绘制到设备上。

### 辅助方法

#### blitMaskRegion

```cpp
void blitMaskRegion(const SkMask& mask, const SkRegion& clip);
```

在区域裁剪下绘制遮罩。内部迭代裁剪区域的所有矩形并调用 `blitMask`。

#### blitRectRegion

```cpp
void blitRectRegion(const SkIRect& rect, const SkRegion& clip);
```

在区域裁剪下绘制矩形。

#### blitRegion

```cpp
void blitRegion(const SkRegion& clip);
```

绘制整个区域。

#### allocBlitMemory

```cpp
virtual void* allocBlitMemory(size_t sz);
```

分配 blitter 拥有的临时内存。这些内存在 blitter 析构时自动释放。

### 虚函数实现

#### blitFatAntiRect

```cpp
void blitFatAntiRect(const SkRect& rect);
```

绘制"胖"抗锯齿矩形（宽度至少为 3 像素）。该函数处理边缘的部分覆盖，使用 run-length 编码表示顶部和底部行的 alpha 值，中间行使用 `blitAntiRect`。

#### blitV

```cpp
virtual void blitV(int x, int y, int height, SkAlpha alpha);
```

默认实现：如果 alpha 为 255，调用 `blitRect`；否则逐行调用 `blitAntiH`。

#### blitRect

```cpp
virtual void blitRect(int x, int y, int width, int height);
```

默认实现：逐行调用 `blitH`。

#### blitAntiRect

```cpp
virtual void blitAntiRect(int x, int y, int width, int height,
                          SkAlpha leftAlpha, SkAlpha rightAlpha);
```

默认实现：绘制左边缘列、中间矩形和右边缘列。

#### blitMask

```cpp
virtual void blitMask(const SkMask& mask, const SkIRect& clip);
```

默认实现处理 BW（1 位）和 A8（8 位 alpha）遮罩格式。LCD16 格式需要子类实现。

### 裁剪 Blitter 实现

#### SkRectClipBlitter 方法

所有 blit 方法首先将坐标裁剪到 `fClipRect` 内，然后调用被包装 blitter 的对应方法。

#### SkRgnClipBlitter 方法

使用 `SkRegion::Spanerator` 或 `SkRegion::Cliperator` 迭代裁剪区域，仅在区域内部调用被包装 blitter。

#### SkBlitterClipper::apply

```cpp
SkBlitter* apply(SkBlitter* blitter, const SkRegion* clip,
                 const SkIRect* bounds = nullptr);
```

根据裁剪情况返回合适的 blitter：
- 无裁剪或裁剪包含整个绘制区域：返回原 blitter
- 裁剪为空：返回 `fNullBlitter`
- 矩形裁剪：返回 `fRectBlitter`
- 复杂区域裁剪：返回 `fRgnBlitter`

## 内部实现细节

### Run-Length 编码

抗锯齿水平扫描线使用稀疏的 run-length 编码：

- `runs[]`: 包含连续像素数量的数组，以 0 结尾
- `antialias[]`: 对应的 alpha 值数组
- 如果 `runs[i] = n`，则接下来 `n` 个像素使用 `antialias[i]`，下一个有效条目在 `runs[i+n]`

例如：
```
runs = [5, 3, 0]
antialias = [128, 255, ...]
```
表示：5 个像素 alpha=128，接下来 3 个像素 alpha=255。

### 遮罩绘制优化

对于 1 位遮罩（BW 格式），使用 `bits_to_runs` 函数将位图转换为水平扫描线：

1. 逐字节读取遮罩数据
2. 逐位测试，检测连续的 1 位游程
3. 调用 `blitH` 绘制每个游程

对于 8 位遮罩（A8 格式），构造统一的 runs 数组（每个像素占一个条目），直接使用 alpha 值调用 `blitAntiH`。

### 混合模式优化

`Choose` 函数包含复杂的混合模式优化逻辑：

1. **快速路径检测** (`CheckFastPath`): 将某些混合模式在特定条件下转换为 SrcOver
2. **跳过绘制**: 某些混合模式在特定颜色/alpha 下不产生可见效果，直接返回 `SkNullBlitter`
3. **Clear 模式简化**: 将 Clear 转换为 Src + 透明黑色

### Legacy vs Raster Pipeline 决策

`UseLegacyBlitter` 函数判断是否可以使用 legacy blitter：

**Legacy blitter 要求:**
- 设备颜色类型为 `kN32_SkColorType`
- 混合模式为 SrcOver
- 无抖动
- 无 unpremul alpha type
- 无 3D mask filter
- 对于无 shader 的情况，颜色必须能用字节表示且色彩空间为 sRGB

不满足条件时使用 `SkCreateRasterPipelineBlitter` 创建通用管线 blitter。

### Color Filter 展平

在 blitter 选择前，color filter 会被"展平"到 paint 中：

```cpp
if (paint->getColorFilter()) {
    SkPaintPriv::RemoveColorFilter(paint.writable(), device.colorSpace());
}
```

这将 color filter 与 shader 组合，或转换为等价的 paint 参数。

### Shader Context 创建

Legacy blitter 需要为 shader 创建 context：

```cpp
shaderContext = as_SB(paint->getShader())
                    ->makeContext({...}, alloc);
```

如果创建失败（某些 shader 不支持 legacy 模式），fallback 到 raster pipeline。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkPixmap` | 提供设备像素缓冲区访问 |
| `SkPaint` | 提供颜色、混合模式、shader 等绘制参数 |
| `SkMatrix` | 提供坐标变换信息 |
| `SkMask` | 定义遮罩数据格式 |
| `SkRegion` | 提供复杂裁剪区域支持 |
| `SkArenaAlloc` | 用于 blitter 对象的高效内存分配 |
| `SkShaderBase` | Shader 的内部接口 |
| `SkBlendModePriv` | 混合模式优化辅助函数 |
| `SkCoreBlitters.h` | 具体 blitter 实现（ARGB32 等） |
| `SkBlitter_A8.h` | Alpha 8 blitter 实现 |
| `SkOpts` | CPU 优化的 memset16 等操作 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| `SkDraw` | 创建和使用 blitter 执行绘制操作 |
| `SkScan` | 扫描转换器，调用 blitter 的 blit 方法填充像素 |
| `SkAAClip` | 抗锯齿裁剪，使用 blitter 绘制 |
| `SkMaskFilter` | 遮罩滤镜，使用 blitter 应用效果 |

## 设计模式与设计决策

### 策略模式

`SkBlitter` 使用策略模式封装不同的像素写入算法。不同的 blitter 子类实现了不同的策略（颜色格式、混合模式、渲染技术）。

### 抽象工厂模式

`Choose` 和 `ChooseSprite` 方法是抽象工厂，根据输入参数创建合适的 blitter 对象。

### 装饰器模式

`SkRectClipBlitter` 和 `SkRgnClipBlitter` 是装饰器，在不修改原 blitter 的情况下添加裁剪功能。

### 模板方法模式

基类 `SkBlitter` 提供了某些虚函数的默认实现（如 `blitRect` 调用 `blitH`），子类可以选择性覆盖以优化。

### 设计决策

1. **虚函数接口**: 使用虚函数而非函数指针，因为 blitter 调用频率虽高但每次绘制只创建一个 blitter，虚函数开销可接受

2. **Run-Length 编码**: 稀疏编码节省内存和处理时间，特别是对于大部分透明或不透明的扫描线

3. **Legacy vs Pipeline 分离**: 保留 legacy blitter 用于最常见的情况（N32 + SrcOver），使用 raster pipeline 处理复杂情况，平衡性能和灵活性

4. **裁剪包装器设计**: 将裁剪逻辑与像素写入逻辑分离，避免在每个 blitter 子类中重复裁剪代码

5. **Arena 分配**: 使用 `SkArenaAlloc` 而非堆分配，减少内存碎片和分配开销，所有对象在绘制结束后一次性释放

6. **选择逻辑集中**: 所有 blitter 选择逻辑集中在 `Choose` 函数，便于维护和优化

## 性能考量

### Blitter 选择开销

虽然 `Choose` 函数包含复杂的逻辑，但它在每次绘制操作中只调用一次，开销相对于后续的像素写入可忽略。

### 虚函数调用

虚函数调用在现代 CPU 上开销较小，且可能被分支预测器优化。相比于手动 switch/if-else，虚函数提供了更好的代码组织。

### 内存布局

裁剪 blitter 作为栈变量存储在 `SkBlitterClipper` 中，避免额外的堆分配。

### Run-Length 编码处理

处理 run-length 编码的循环通常很紧凑，利用缓存局部性。对于大部分不透明的扫描线，循环次数很少。

### 遮罩绘制优化

- 1 位遮罩使用位操作快速检测游程
- 8 位遮罩使用预分配的 runs 数组，避免动态内存分配
- 使用 `SkOpts::memset16` 快速初始化 runs 数组

### 矩形裁剪快速路径

`SkRectClipBlitter` 对于每种操作都有专门的实现，避免不必要的 alpha runs 处理。

### 区域裁剪优化

使用 `SkRegion::Spanerator` 和 `Cliperator` 高效迭代复杂裁剪区域，避免测试每个像素。

### Fat Anti-Rect 特殊处理

`blitFatAntiRect` 针对宽矩形优化，避免处理大量小游程。它将矩形分为顶部行、中间区域和底部行，中间区域使用更高效的 `blitAntiRect`。

### 内存复用

`fBlitMemory` 在 blitter 生命周期内复用，使用 `SkAutoMalloc::kReuse_OnShrink` 策略，避免重复分配。

## 相关文件

| 文件路径 | 关系 |
|---------|------|
| `src/core/SkBlitter_A8.h` | Alpha 8 blitter 实现 |
| `src/core/SkBlitter_ARGB32.cpp` | 32 位 ARGB blitter 实现 |
| `src/core/SkCoreBlitters.h` | 核心 blitter 类型声明 |
| `src/core/SkRasterPipelineBlitter.cpp` | Raster pipeline blitter 实现 |
| `src/core/SkDraw.h` | 绘制调度器，使用 blitter |
| `src/core/SkScan.h` | 扫描转换器，调用 blitter |
| `src/core/SkMask.h` | 遮罩数据结构 |
| `include/core/SkPixmap.h` | 像素映射接口 |
| `include/core/SkPaint.h` | 绘制参数 |
| `include/core/SkRegion.h` | 区域裁剪 |
| `src/core/SkAlphaRuns.h` | Alpha runs 处理工具 |
| `src/core/SkBlendModePriv.h` | 混合模式优化 |
| `src/shaders/SkShaderBase.h` | Shader 内部接口 |
