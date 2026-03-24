# SkDraw

> 源文件: src/core/SkDraw.h, src/core/SkDraw.cpp

## 概述

`SkDraw` 是 Skia 软件渲染后端的核心工作类，负责将各种图形元素（矩形、路径、位图等）光栅化到 CPU 内存中的像素缓冲区。它是 `SkCanvas` 的实现细节，充当图形绘制管道的中间层。`Draw` 类配置了目标像素缓冲区、变换矩阵和裁剪区域，将高层绘制命令转换为底层的像素写入操作。其核心职责是根据绘制元素、`SkPaint` 参数和设备状态选择最优的 `SkBlitter`，然后由 `SkBlitter` 执行实际的像素写入。

该类位于 `skcpu` 命名空间中，专为 CPU 渲染设计，与 GPU 渲染路径分离。它支持抗锯齿、遮罩滤镜、路径效果等多种渲染特性。

## 架构位置

`SkDraw` 处于 Skia 软件渲染管道的中间层：

```
SkCanvas（用户接口层）
    ↓
SkDevice（设备抽象层）
    ↓
skcpu::Draw（绘制编排层）← 当前模块
    ↓
SkBlitter（像素写入层）
    ↓
SkPixmap（像素缓冲区）
```

- 上层：接收来自 `SkCanvas` 和 `SkDevice` 的绘制请求
- 下层：协调 `SkBlitter`、`SkScan` 和 `SkMask` 进行实际光栅化
- 同层：与 `GlyphRunListPainter`（文本绘制）协作

## 主要类与结构体

### Draw 类

**继承关系：**
```
SkRefCnt
    ↑
BitmapDevicePainter
    ↑
Draw
```

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fDst` | `SkPixmap` | 目标像素缓冲区，存储渲染结果 |
| `fCTM` | `const SkMatrix*` | 当前变换矩阵（必需） |
| `fRC` | `const SkRasterClip*` | 光栅裁剪区域（必需） |
| `fBlitterChooser` | `BlitterChooser*` | Blitter 选择函数指针（必需） |
| `fProps` | `const SkSurfaceProps*` | 表面属性（可选） |
| `fCtx` | `const ContextImpl*` | 上下文实现（可选） |

### BitmapDevicePainter 接口

抽象基类，定义了预光栅化对象（如字形和位图）的绘制接口：

| 方法 | 说明 |
|------|------|
| `paintMasks()` | 绘制遮罩字形 |
| `drawBitmap()` | 绘制位图 |

### RectType 枚举

矩形的渲染类型分类：

| 类型 | 说明 |
|------|------|
| `kHair` | 单像素线宽 |
| `kFill` | 填充矩形 |
| `kStroke` | 描边矩形 |
| `kPath` | 需要路径处理的复杂矩形 |

### PtProcRec 结构体

点绘制处理记录，用于优化点/线的绘制：

| 成员 | 类型 | 说明 |
|------|------|------|
| `fMode` | `SkCanvas::PointMode` | 点绘制模式（点/线/多边形） |
| `fPaint` | `const SkPaint*` | 绘制参数 |
| `fClip` | `const SkRegion*` | 裁剪区域 |
| `fRC` | `const SkRasterClip*` | 光栅裁剪 |
| `fRadius` | `SkScalar` | 点半径 |
| `Proc` | 函数指针类型 | 点处理函数 |

## 公共 API 函数

### 基本图元绘制

| 函数 | 说明 |
|------|------|
| `drawPaint(const SkPaint&)` | 用指定 Paint 填充整个表面 |
| `drawRect(...)` | 绘制矩形，支持预/后变换矩阵 |
| `drawOval(const SkRect&, const SkPaint&)` | 绘制椭圆 |
| `drawRRect(const SkRRect&, const SkPaint&)` | 绘制圆角矩形 |
| `drawRRectNinePatch(...)` | 九宫格优化的圆角矩形绘制 |
| `drawPath(...)` | 绘制路径，支持预变换矩阵 |

### 位图与精灵绘制

| 函数 | 说明 |
|------|------|
| `drawBitmap(...)` | 绘制位图，支持变换、采样和 Mipmap |
| `drawSprite(...)` | 快速路径：无变换的位图绘制 |
| `drawBitmapAsMask(...)` | 将 A8 位图作为遮罩绘制 |

### 文本与遮罩

| 函数 | 说明 |
|------|------|
| `drawGlyphRunList(...)` | 绘制字形列表 |
| `paintMasks(...)` | 绘制字形遮罩（覆写） |
| `drawDevMask(...)` | 绘制设备空间的遮罩 |

### 几何图形

| 函数 | 说明 |
|------|------|
| `drawPoints(...)` | 绘制点、线或多边形 |
| `drawDevicePoints(...)` | 绘制设备空间的点 |
| `drawVertices(...)` | 绘制顶点数组 |
| `drawAtlas(...)` | 绘制图集精灵 |

### 静态工具函数

| 函数 | 说明 |
|------|------|
| `ComputeRectType(...)` | 分析矩形的最优绘制策略 |
| `DrawToMask(...)` | 将路径渲染到遮罩中（命名空间函数） |

## 内部实现细节

### Blitter 选择机制

`Draw` 的核心任务是选择正确的 Blitter：

1. **默认选择器**：构造函数设置 `fBlitterChooser = SkBlitter::Choose`
2. **上下文考量**：基于目标像素格式、Paint 属性、变换矩阵、裁剪区域
3. **专用 Blitter**：支持自定义 Blitter（如 `drawPathCoverage` 的覆盖率 Blitter）
4. **Sprite 优化**：`SkBlitter::ChooseSprite` 用于无变换的快速路径

### 矩形绘制优化

`ComputeRectType` 实现智能分类：

```cpp
RectType::kHair    // 零宽度线 → 单像素快速路径
RectType::kFill    // 填充 → 直接扫描填充
RectType::kStroke  // 简单描边（矩阵保持矩形） → 框架扫描
RectType::kPath    // 复杂情况 → 完整路径处理
```

### 路径处理流程

1. **细线优化**：`modifyPaintForHairlines` 将极细描边转换为单像素线
2. **路径变换**：
   - 无路径效果：直接变换路径
   - 有路径效果：先应用效果再变换
3. **裁剪优化**：计算保守裁剪边界以跳过不可见区域
4. **遮罩滤镜**：特殊处理（`filterPath` / `filterRRect`）

### 点绘制优化

`PtProcRec` 提供专门的处理过程：

- **发丝模式**：`bw_pt_hair_proc` / `aa_line_hair_proc`
- **方形笔刷**：`bw_square_proc` / `aa_square_proc`
- **直接写入**：`DIRECT_BLIT_LOOP` 宏利用 `canDirectBlit()` 绕过 Blitter

### Sprite 快速路径

条件：
- 变换矩阵接近单位矩阵（`SkTreatAsSprite`）
- 位图非 Alpha-only（或特殊配置）
- 裁剪区域简单（BW 或包含 Sprite）

实现：
- 直接像素拷贝，避免完整的变换-采样-混合流程

### 遮罩处理

`drawDevMask`：
1. 应用遮罩滤镜（如果存在）
2. 选择适当的 Blitter
3. 处理抗锯齿裁剪（`SkAAClipBlitterWrapper`）
4. 调用 `blitMaskRegion`

### A8 位图遗留行为

```cpp
#ifdef SK_SUPPORT_LEGACY_ALPHA_BITMAP_AS_COVERAGE
// Android 兼容：A8 位图作为覆盖率而非 Alpha
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkBlitter` | 实际像素写入 |
| `SkScan` | 扫描转换算法（填充、描边、抗锯齿） |
| `SkRasterClip` | 裁剪区域管理 |
| `SkMask` | 遮罩数据结构 |
| `SkMaskFilterBase` | 遮罩滤镜处理 |
| `SkPathEffectBase` | 路径效果应用 |
| `SkMatrix` | 几何变换 |
| `SkPaint` | 绘制属性 |
| `SkPixmap` | 像素数据访问 |
| `SkAutoBlitterChoose` | 自动 Blitter 选择 |
| `SkArenaAlloc` | 内存分配器 |

### 被依赖的模块

| 模块 | 依赖方式 |
|------|----------|
| `SkDevice` | 调用 Draw 方法执行软件渲染 |
| `SkCanvas` | 通过 Device 间接使用 |
| `GlyphRunListPainter` | 文本渲染时调用 `paintMasks` |

## 设计模式与设计决策

### 策略模式

通过 `BlitterChooser` 函数指针动态选择 Blitter 策略，支持不同的像素格式和渲染模式。

### 模板方法模式

`BitmapDevicePainter` 定义接口，`Draw` 实现具体算法，支持未来扩展（如 `SkOverdrawCanvas` 的可视化）。

### 组合优于继承

`Draw` 持有指针而非继承关系（`fCTM`、`fRC`），保持轻量级且易于配置。

### 快速路径优化

多层级的快速路径判断：
1. Sprite 路径（无变换）
2. 点/线专用处理
3. 矩形分类优化
4. 通用路径降级

### 渐进式复杂度

从简单情况（发丝线、单像素点）到复杂情况（遮罩滤镜、路径效果）逐步增加处理复杂度。

### 避免冗余变换

`prePathMatrix` 机制允许在路径处理前应用变换，避免重复变换计算。

### 内存安全

使用 `SkAutoBlitterChoose`、`SkAutoMaskFreeImage`、`AutoTMalloc` 等 RAII 封装确保资源正确释放。

## 性能考量

### 关键优化点

1. **Sprite 检测**：`SkTreatAsSprite` 识别无变换情况，使用 `ChooseSprite` 避免完整管道
2. **矩形快速路径**：`ComputeRectType` 跳过路径生成，直接调用 `SkScan::FillRect` 等
3. **点绘制批处理**：`MAX_DEV_PTS` 批量变换点以减少函数调用开销
4. **直接写入**：`canDirectBlit()` 允许跳过 Blitter 接口直接写入像素
5. **裁剪提前退出**：`clipped_out` 检查避免不可见内容的处理
6. **边界预检查**：`SkRectPriv::FitsInFixed` / `SkPathPriv::TooBigForMath` 避免大数值计算

### 细线处理

`DrawTreatAsHairline` 函数：
- 检测变换后宽度 ≤ 1 像素的描边
- 转换为发丝线并调节 Alpha 模拟半透明

### 遮罩缓存

```cpp
SkResourceCache* cache = nullptr;  // TODO: 从 fCtx 获取
```
计划支持遮罩滤镜结果缓存以避免重复计算。

### 内存布局

使用栈分配的小型缓冲区（`MAX_DEV_PTS`、`SkSTArenaAlloc<kSkBlitterContextSize>`）减少堆分配。

### 条件编译优化

```cpp
#if defined(SK_BUILD_FOR_FUZZER)
if (raw->points().size() > 1000) return;  // 防止模糊测试超时
#endif
```

## 相关文件

| 文件路径 | 关系 |
|----------|------|
| `src/core/SkBlitter.h/.cpp` | Blitter 选择与像素写入 |
| `src/core/SkScan.h/.cpp` | 扫描转换算法 |
| `src/core/SkRasterClip.h/.cpp` | 光栅裁剪管理 |
| `src/core/SkAutoBlitterChoose.h` | RAII Blitter 选择器 |
| `src/core/SkMask.h` | 遮罩数据结构 |
| `src/core/SkMaskFilterBase.h` | 遮罩滤镜基类 |
| `src/core/SkDevice.h/.cpp` | 设备抽象层 |
| `include/core/SkCanvas.h` | 用户 API 层 |
| `include/core/SkPaint.h` | 绘制属性 |
| `include/core/SkPath.h` | 路径数据结构 |
| `src/core/SkPathPriv.h` | 路径内部工具 |
| `src/core/SkDrawProcs.h` | 绘制过程辅助 |
| `src/text/gpu/GlyphRunListPainter.h` | 文本绘制协作 |
