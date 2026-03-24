# SkCanvas

> 源文件: `include/core/SkCanvas.h`, `src/core/SkCanvas.cpp`

## 概述

SkCanvas 是 Skia 图形库中最核心的绘图接口类，提供了完整的 2D 绘图、裁剪和变换功能。它维护了一个由 SkMatrix（变换矩阵）和裁剪区域（clip）组成的状态栈，所有绘图操作都在当前矩阵和裁剪区域的作用下执行。

SkCanvas 与 SkPaint 配合使用，提供绘制到 SkSurface 或 SkDevice 的完整状态。每次绘图调用都会使用状态栈中所有矩阵值的级联来变换几何图形，并使用所有裁剪值的交集来裁剪变换后的几何图形。SkPaint 则提供颜色、字体、描边宽度、着色器等绘图属性。

SkCanvas 可以绑定到多种后端：
- **光栅表面**：通过 CPU 绘制到内存位图
- **GPU 表面**：通过 Vulkan 或 OpenGL 绘制到 GPU
- **文档后端**：SVG 画布、PDF 文档或 SkPictureRecorder

该文件总计约 5764 行代码（头文件约 2500 行，实现文件约 3264 行），是 Skia 中代码量最大、功能最完整的核心类之一。

## 架构位置

```
应用层 (Application)
    │
    ▼
SkCanvas (绘图接口层)        ← 本文件
    │
    ├── SkPaint (绘图属性)
    ├── SkMatrix / SkM44 (变换矩阵)
    ├── SkPath / SkRRect / SkRegion (几何图形)
    │
    ▼
SkDevice (设备抽象层)
    │
    ├── 光栅设备 (SkBitmapDevice)
    ├── GPU 设备 (Ganesh / Graphite)
    └── 文档设备 (PDF / SVG / Picture)
```

SkCanvas 处于 Skia 架构的最上层，是用户与渲染引擎之间的主要接口。它不直接执行像素级渲染，而是将绘图命令委托给底层的 SkDevice 实现。这种分层设计使得同一套绘图 API 可以适配不同的渲染后端。

## 主要类与结构体

### SkCanvas
主类，提供所有绘图、裁剪和变换操作。关键内部类型包括：

### MCRec (Matrix-Clip Record)
```cpp
class MCRec {
    SkDevice* fDevice;           // 当前设备指针
    SkM44 fMatrix;               // 当前全局变换矩阵
    int fDeferredSaveCount = 0;  // 延迟保存计数
    std::unique_ptr<Layer> fLayer;       // 图层信息（saveLayer 时创建）
    std::unique_ptr<BackImage> fBackImage; // saveBehind 的备份图像
};
```
MCRec 是状态栈的核心记录单元，每次 `save()` 或 `saveLayer()` 都会创建新的 MCRec 并入栈。它存储当前的设备指针、变换矩阵和可选的图层信息。

### Layer
```cpp
class Layer {
    sk_sp<SkDevice> fDevice;                      // 图层的设备
    skia_private::STArray<1, sk_sp<SkImageFilter>> fImageFilters; // 图像滤镜列表
    SkPaint fPaint;                               // 恢复时使用的画笔
    bool fIsCoverage;                             // 是否为覆盖图层
    bool fDiscard;                                // 是否在恢复时丢弃
    bool fIncludesPadding;                        // 是否包含填充像素
};
```
Layer 在 `saveLayer()` 时创建，封装了离屏渲染所需的设备和恢复参数。

### SaveLayerRec
```cpp
struct SaveLayerRec {
    const SkRect* fBounds = nullptr;         // 图层大小提示
    const SkPaint* fPaint = nullptr;         // 合成时使用的画笔
    FilterSpan fFilters = {};                // 图像滤镜列表
    const SkImageFilter* fBackdrop = nullptr; // 背景滤镜
    SkTileMode fBackdropTileMode = SkTileMode::kClamp;
    const SkColorSpace* fColorSpace = nullptr;
    SaveLayerFlags fSaveLayerFlags = 0;
};
```

### AutoUpdateQRBounds
内部辅助类，在裁剪操作前后自动更新快速拒绝边界（Quick Reject Bounds）。利用 RAII 模式确保构造时验证裁剪状态，析构时重新计算设备裁剪边界。

## 公共 API 函数

### 构造与工厂方法
| 方法 | 说明 |
|------|------|
| `SkCanvas()` | 创建空画布，无后备像素存储 |
| `SkCanvas(int width, int height, const SkSurfaceProps*)` | 创建指定尺寸的无像素画布 |
| `SkCanvas(const SkBitmap&)` | 从位图构造画布 |
| `MakeRasterDirect(info, pixels, rowBytes, props)` | 直接在内存像素上创建光栅画布 |
| `MakeRasterDirectN32(width, height, pixels, rowBytes)` | 创建 N32 格式光栅画布 |

### 状态保存与恢复（Save/Restore Stack）
| 方法 | 说明 |
|------|------|
| `save()` | 保存当前矩阵和裁剪状态，返回保存深度 |
| `restore()` | 恢复上一次保存的状态 |
| `getSaveCount()` | 获取当前保存栈深度 |
| `restoreToCount(int)` | 恢复到指定深度 |
| `saveLayer(bounds, paint)` | 保存状态并创建离屏图层 |
| `saveLayer(SaveLayerRec)` | 使用完整配置创建离屏图层 |
| `saveLayerAlphaf(bounds, alpha)` | 创建带透明度的离屏图层 |

`save()` 使用延迟保存（deferred save）优化：仅递增计数器，真正的保存操作延迟到下一次裁剪或变换修改时才执行，避免不必要的状态复制。

### 变换操作（Matrix Transforms）
| 方法 | 说明 |
|------|------|
| `translate(dx, dy)` | 平移变换 |
| `scale(sx, sy)` | 缩放变换 |
| `rotate(degrees)` / `rotate(degrees, px, py)` | 旋转变换 |
| `skew(sx, sy)` | 倾斜变换 |
| `concat(SkMatrix)` / `concat(SkM44)` | 级联矩阵 |
| `setMatrix(SkM44)` | 直接设置矩阵（覆盖当前状态） |
| `resetMatrix()` | 重置为单位矩阵 |
| `getLocalToDevice()` | 获取当前局部到设备的 4x4 变换矩阵 |
| `getTotalMatrix()` | （已弃用）获取 3x3 变换矩阵 |

所有变换操作都是预乘（pre-multiply）语义：新变换在当前矩阵之前应用。

### 裁剪操作（Clip Operations）
| 方法 | 说明 |
|------|------|
| `clipRect(rect, op, doAA)` | 矩形裁剪 |
| `clipRRect(rrect, op, doAA)` | 圆角矩形裁剪 |
| `clipPath(path, op, doAA)` | 路径裁剪 |
| `clipShader(shader, op)` | 着色器裁剪 |
| `clipRegion(region, op)` | 区域裁剪（设备坐标空间） |
| `quickReject(rect)` / `quickReject(path)` | 快速拒绝测试 |
| `getLocalClipBounds()` | 获取局部坐标系的裁剪边界 |
| `getDeviceClipBounds()` | 获取设备坐标系的裁剪边界 |

裁剪操作支持 `SkClipOp::kIntersect`（交集）和 `SkClipOp::kDifference`（差集）两种操作。`clipPath` 内部会尝试优化：若路径实际是矩形、椭圆或圆角矩形，则自动降级为更高效的裁剪调用。

### 绘图操作（Drawing Methods）
**基本图形绘制：**
| 方法 | 说明 |
|------|------|
| `drawColor(color, mode)` / `clear(color)` | 填充整个裁剪区域 |
| `drawPaint(paint)` | 用画笔填充裁剪区域 |
| `drawPoint(x, y, paint)` | 绘制点 |
| `drawLine(x0, y0, x1, y1, paint)` | 绘制线段 |
| `drawRect(rect, paint)` | 绘制矩形 |
| `drawRRect(rrect, paint)` | 绘制圆角矩形 |
| `drawDRRect(outer, inner, paint)` | 绘制双圆角矩形（环形） |
| `drawCircle(cx, cy, radius, paint)` | 绘制圆形 |
| `drawOval(oval, paint)` | 绘制椭圆 |
| `drawArc(oval, startAngle, sweepAngle, useCenter, paint)` | 绘制弧形 |
| `drawPath(path, paint)` | 绘制路径 |
| `drawRegion(region, paint)` | 绘制区域 |

**图像绘制：**
| 方法 | 说明 |
|------|------|
| `drawImage(image, x, y, sampling, paint)` | 在指定位置绘制图像 |
| `drawImageRect(image, src, dst, sampling, paint, constraint)` | 将图像源区域绘制到目标区域 |
| `drawImageNine(image, center, dst, filter, paint)` | 九宫格拉伸绘制 |
| `drawImageLattice(image, lattice, dst, filter, paint)` | 网格拉伸绘制 |
| `drawAtlas(atlas, xform, tex, colors, mode, sampling, cull, paint)` | 精灵图集绘制 |

**文本绘制：**
| 方法 | 说明 |
|------|------|
| `drawSimpleText(text, byteLength, encoding, x, y, font, paint)` | 绘制简单文本 |
| `drawString(str, x, y, font, paint)` | 绘制字符串 |
| `drawGlyphs(glyphs, positions, origin, font, paint)` | 绘制字形数组 |
| `drawTextBlob(blob, x, y, paint)` | 绘制文本 Blob |

**高级绘制：**
| 方法 | 说明 |
|------|------|
| `drawPicture(picture, matrix, paint)` | 回放录制的绘图命令 |
| `drawVertices(vertices, mode, paint)` | 绘制三角网格 |
| `drawMesh(mesh, blender, paint)` | 绘制自定义网格 |
| `drawPatch(cubics, colors, texCoords, mode, paint)` | 绘制 Coons 曲面片 |
| `drawDrawable(drawable, matrix)` | 绘制可绘制对象 |
| `drawAnnotation(rect, key, value)` | 添加注释（用于 PDF 等） |

### 像素读写
| 方法 | 说明 |
|------|------|
| `readPixels(dstInfo, dstPixels, rowBytes, x, y)` | 从画布读取像素 |
| `writePixels(srcInfo, pixels, rowBytes, x, y)` | 向画布写入像素 |
| `peekPixels(pixmap)` | 直接访问画布像素 |
| `accessTopLayerPixels(info, rowBytes, origin)` | 访问顶层图层像素 |

## 内部实现细节

### 延迟保存机制（Deferred Save）
`save()` 不会立即创建新的 MCRec 压栈，而是递增 `fMCRec->fDeferredSaveCount`。只有在后续操作（如 `clipRect`、`concat` 等）真正需要修改状态时，才通过 `checkForDeferredSave()` 触发 `doSave()` 完成实际保存。这大幅减少了 save/restore 对频繁出现但无实际修改时的开销。

### saveLayer 的图层创建流程
`internalSaveLayer()` 是图层创建的核心方法，流程如下：
1. 执行 `internalSave()` 压栈
2. 检查裁剪是否为空，为空则提前返回
3. 构建恢复用的 `restorePaint`，移除路径效果、遮罩滤镜和图像滤镜
4. 通过 `get_layer_mapping_and_bounds()` 计算图层的变换映射和边界
5. 根据图像滤镜需求可能添加 1 像素的填充（padding）
6. 创建新的 SkDevice 作为图层的渲染目标
7. 如需要，初始化图层的背景内容（backdrop）
8. 将图层信息存入 MCRec

### 图层恢复与合成
`internalRestore()` 在弹出 MCRec 时执行图层合成：
- 若图层有图像滤镜，调用 `internalDrawDeviceWithFilter()` 应用滤镜后绘制到父设备
- 若无滤镜，直接调用 `dstDev->drawDevice()` 进行设备到设备的绘制
- 恢复裁剪栈和全局变换矩阵
- 更新快速拒绝边界

### 预绘制通知（Predraw Notification）
每次绘图操作前都会调用 `aboutToDraw()`，该方法：
1. 通过 `predrawNotify()` 通知关联的 SkSurface，触发 Copy-on-Write 机制
2. 创建 `AutoLayerForImageFilter`，若画笔包含图像滤镜或遮罩滤镜，自动创建临时图层

### 快速拒绝（Quick Reject）
`quickReject()` 使用预计算的 `fQuickRejectBounds`（设备坐标空间的裁剪边界，向外扩展 1 像素用于抗锯齿）来快速判断绘图是否完全在裁剪区域外。这避免了不必要的设备绘图调用，是重要的性能优化。

### 图像滤镜的图层映射计算
`get_layer_mapping_and_bounds()` 是 saveLayer 中最复杂的辅助函数，负责为图像滤镜计算合适的图层坐标空间和边界：

1. **CTM 分解**：通过 `skif::Mapping::decomposeCTM()` 将 local-to-device 变换分解为 layer-to-device 和 parameter-to-layer 两部分，使图像滤镜在中间图层空间中工作
2. **缩放因子调整**：可选的 `scaleFactor` 参数允许降低图层分辨率以节省内存
3. **图层大小限制**：设置 `maxLayerDim`（默认 2048 或设备尺寸的 2 倍）防止透视/倾斜变换导致过大的图层分配
4. **滤镜输入边界**：调用 `getInputBounds()` 让每个图像滤镜声明其所需的输入区域
5. **内容边界裁剪**：若提供了用户边界（`rec.fBounds`），将图层限制在该区域内

### 颜色类型选择
`image_filter_color_type()` 为图像滤镜选择合适的中间颜色类型。对于低位深格式（如 A8、RGB565、RGBA4444），自动升级为 `kN32_SkColorType`（通常是 RGBA8888），以确保滤镜处理有足够的 Alpha 位深度。高位深格式（如 RGBA_F16）则保持不变。

### 虚函数重写点
SkCanvas 提供了丰富的虚函数重写点，使子类可以在不同层级拦截绘图操作：

**状态通知虚函数：**
- `willSave()` / `willRestore()` / `didRestore()` — 保存/恢复通知
- `getSaveLayerStrategy()` — 控制图层分配策略
- `didConcat44()` / `didSetM44()` / `didTranslate()` / `didScale()` — 变换通知

**绘图虚函数（on-methods）：**
- `onDrawPaint()`, `onDrawRect()`, `onDrawPath()` 等基本图形
- `onDrawImage2()`, `onDrawImageRect2()` 等图像操作
- `onDrawTextBlob()`, `onDrawGlyphRunList()` 等文本操作
- `onDrawVerticesObject()`, `onDrawMesh()` 等网格操作
- `onDrawPicture()`, `onDrawDrawable()` 等复合操作
- `onClipRect()`, `onClipRRect()`, `onClipPath()` 等裁剪操作

子类如 `SkRecorder`（用于录制）、`SkPaintFilterCanvas`（用于画笔过滤）、`SkNWayCanvas`（用于多路分发）等都通过重写这些虚函数实现其功能。

### Copy-on-Write 与 Surface 协作
当 SkCanvas 关联一个 SkSurface 时，每次绘图前都需要通过 `predrawNotify()` 通知 Surface。若 Surface 有未完成的图像快照（`outstandingImageSnapshot()`），Surface 会在绘图前复制后备像素存储，确保先前获取的快照不受后续绘图影响。这就是 Copy-on-Write 机制。

`wouldOverwriteEntireSurface()` 的优化在于：如果即将进行的绘图会完全覆盖表面（不透明、不受裁剪、满覆盖），则可以跳过 COW 复制，直接丢弃旧内容。

## 依赖关系

**核心依赖：**
- `SkDevice` — 底层设备抽象，执行实际绘图
- `SkPaint` — 绘图属性（颜色、样式、滤镜等）
- `SkMatrix` / `SkM44` — 2D/3D 变换矩阵
- `SkPath`, `SkRRect`, `SkRegion` — 几何图形
- `SkImage`, `SkBitmap`, `SkPixmap` — 图像和像素数据
- `SkSurface` — 画布的拥有者，管理后备存储
- `SkImageFilter` — 图像滤镜框架
- `SkBlender` / `SkBlendMode` — 混合模式
- `SkTextBlob`, `sktext::GlyphRunBuilder` — 文本渲染支持
- `SkPicture` — 绘图命令录制与回放
- `SkColorFilter`, `SkShader`, `SkMaskFilter` — 画笔效果组件

**内部依赖：**
- `SkCanvasPriv` — 私有辅助接口
- `SkNoPixelsDevice` — 无像素设备（用于空画布和裁剪优化）
- `SkSpecialImage` — 特殊图像（用于滤镜和图层）
- `SkDeque` — 双端队列，用于 MCRec 状态栈存储

## 设计模式与设计决策

### 模板方法模式（Template Method）
SkCanvas 的绘图方法采用两层设计：
- 公共方法（如 `drawRect`）：执行参数校验、快速拒绝和通用预处理
- 虚函数（如 `onDrawRect`）：可被子类重写以自定义行为

这允许 `SkRecorder`、`SkPaintFilterCanvas` 等子类在不破坏基础逻辑的情况下拦截和修改绘图命令。

### 状态栈模式
使用 `SkDeque` 实现的 MCRec 栈管理变换和裁剪状态，支持嵌套的 save/restore 调用。栈底预分配了 `fMCRecStorage` 内联存储，避免小规模使用时的堆分配。

### 延迟执行（Lazy Evaluation）
延迟保存和 Copy-on-Write 通知都体现了按需执行的设计理念，只在状态真正被修改时才产生开销。

### 策略模式
`SaveLayerStrategy` 枚举允许子类控制 `saveLayer` 是否真正分配图层（`kFullLayer_SaveLayerStrategy`）还是仅做记录（`kNoLayer_SaveLayerStrategy`），让录制器等子类可以优化存储。

### 观察者模式
SkCanvas 与 SkSurface 之间存在双向关联：SkCanvas 持有 `fSurfaceBase` 指针，在每次绘图前通过 `predrawNotify()` 通知 Surface；Surface 则通过 `fCanvas` 反向引用画布。这种协作实现了透明的 Copy-on-Write 语义。

### 类型化图层（Layer Variants）
图层系统支持多种变体以满足不同需求：
- **标准图层**：通过 `saveLayer()` 创建，用于透明度合成和图像滤镜
- **覆盖图层**（Coverage Layer）：使用 `kAlpha_8_SkColorType`，专门用于遮罩滤镜的 coverage mask 处理，节省内存
- **初始化图层**（InitWithPrevious）：通过 `kInitWithPrevious_SaveLayerFlag` 创建，图层初始内容来自父设备的当前像素，用于 backdrop 效果
- **SaveBehind 图层**：通过 `only_axis_aligned_saveBehind()` 创建，保存并清除指定区域的像素，恢复时用 `DstOver` 混合恢复，用于实现 Android 框架的特殊需求

### SkCanvas 的子类生态
SkCanvas 的设计允许多种子类化策略，主要的子类包括：
- `SkRecorder` — 将绘图命令序列化为 SkPicture
- `SkPaintFilterCanvas` — 在每次绘图前修改 SkPaint（如强制半透明）
- `SkNWayCanvas` — 将绘图命令分发到多个子画布
- `SkNoDrawCanvas` — 仅跟踪状态变化但不执行绘图
- `SkOverdrawCanvas` — 可视化每个像素被绘制的次数
- `SkDebugCanvas` — 支持逐命令回放和审查

## 性能考量

1. **延迟保存**：`save()` 仅递增计数器 `fDeferredSaveCount`，避免无修改的 save/restore 对的状态复制开销。这在 SkPicture 回放等场景中尤其有效，因为许多 save/restore 之间可能没有实际的裁剪或变换修改

2. **快速拒绝**：`quickReject()` 使用预计算的浮点数边界 `fQuickRejectBounds` 进行比较，在绘图命令完全在裁剪区域外时跳过后续所有处理（包括画笔分析、设备调用等）。边界向外扩展 1 像素以正确处理抗锯齿

3. **图层边界优化**：`saveLayer` 通过内容边界、裁剪区域和图像滤镜输入边界的交集来最小化离屏图层的尺寸。`maxLayerDim` 限制防止透视变换导致的天文数字级图层分配

4. **图层填充**：为含图像滤镜的图层添加 1 像素填充，使滤镜可以使用 clamp 而非 decal 采样模式，避免着色器中额外的边界检查分支

5. **裁剪优化**：`clipPath` 自动检测路径是否为矩形、椭圆或圆角矩形，降级为更高效的 `clipRect` 或 `clipRRect` 调用。这避免了通用路径裁剪的高昂开销

6. **wouldOverwriteEntireSurface**：在绘图前检测是否会覆盖整个表面，若是则可丢弃先前内容，触发 `kDiscard_ContentChangeMode`，避免不必要的 Copy-on-Write 像素拷贝

7. **TRACE_EVENT 宏**：所有公共绘图方法都标记了 `TRACE_EVENT0("skia", TRACE_FUNC)` 跟踪事件，方便 Chrome Tracing 等工具进行性能分析，而在非跟踪构建中编译为零开销

8. **MCRec 栈内存预分配**：`fMCStack` 使用 `fMCRecStorage` 数组作为初始内联存储（在 SkCanvas 对象内部），对于浅层 save/restore（通常不超过几层），完全避免堆分配

9. **nothingToDraw 提前退出**：大多数绘图方法在 `aboutToDraw()` 之前检查 `nothingToDraw(paint)`，若画笔的混合模式和颜色组合不会产生可见效果（如完全透明的 SrcOver），则跳过整个绘图流程

10. **区域绘制优化**：`drawRegion()` 检测单矩形区域并降级为 `drawIRect()`，避免通用区域扫描线处理的开销

11. **EdgeAA 图像集路由优化**：`experimental_DrawEdgeAAImageSet` 在单条目且有图像滤镜时自动路由到 `drawImageRect()`，利用后者的图层优化避免创建不必要的临时图层

## 相关文件

- `/Users/yuanlin/workspace/skia/include/core/SkCanvas.h` — 公共头文件，包含类声明和 API 文档
- `/Users/yuanlin/workspace/skia/src/core/SkCanvas.cpp` — 实现文件
- `/Users/yuanlin/workspace/skia/src/core/SkCanvasPriv.h` — 私有辅助接口
- `/Users/yuanlin/workspace/skia/src/core/SkDevice.h` — 设备抽象基类
- `/Users/yuanlin/workspace/skia/include/core/SkPaint.h` — 绘图属性类
- `/Users/yuanlin/workspace/skia/include/core/SkMatrix.h` — 2D 变换矩阵
- `/Users/yuanlin/workspace/skia/include/core/SkM44.h` — 4x4 变换矩阵
- `/Users/yuanlin/workspace/skia/include/core/SkSurface.h` — 表面管理
- `/Users/yuanlin/workspace/skia/include/utils/SkNoDrawCanvas.h` — 不绘制的画布子类
- `/Users/yuanlin/workspace/skia/src/core/SkImageFilter_Base.h` — 图像滤镜基础实现
- `/Users/yuanlin/workspace/skia/src/core/SkImageFilterTypes.h` — 滤镜类型和映射系统
