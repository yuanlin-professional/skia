# SoftwarePathRenderer

> 源文件
> - src/gpu/ganesh/ops/SoftwarePathRenderer.h
> - src/gpu/ganesh/ops/SoftwarePathRenderer.cpp

## 概述

`SoftwarePathRenderer` 是 Skia Ganesh GPU 后端的兜底路径渲染器，当其他 GPU 路径渲染器无法处理复杂路径时作为最后的备用方案。该渲染器采用 CPU 软件光栅化路径到位图，然后将结果上传为 GPU 纹理并混合到目标表面。支持覆盖抗锯齿（Coverage AA），可选地缓存渲染结果以提高重复绘制性能，并支持多线程异步光栅化优化。该渲染器虽然不如纯 GPU 方法快，但保证了 Skia 能够正确渲染任意复杂的路径。

## 架构位置

`SoftwarePathRenderer` 位于 Skia GPU 渲染管线的以下位置：

- **模块层级**：`src/gpu/ganesh/ops/` - Ganesh GPU 操作层
- **继承关系**：继承自 `PathRenderer` 基类
- **命名空间**：`skgpu::ganesh`
- **优先级**：最低优先级，`onCanDrawPath()` 返回 `kAsBackup`
- **依赖组件**：
  - CPU 光栅化：`GrSWMaskHelper` - 软件掩码助手
  - 资源管理：`GrProxyProvider` - 代理提供者
  - 纹理上传：`GrDeferredProxyUploader` - 延迟代理上传器
  - 多线程：`SkTaskGroup` - 任务组调度

## 主要类与结构体

### SoftwarePathRenderer

```cpp
class SoftwarePathRenderer final : public PathRenderer
```

**核心职责**：
- 作为路径渲染的最后备用方案
- 使用 CPU 光栅化路径到 Alpha 掩码
- 将掩码上传为纹理并混合到目标表面
- 可选地缓存掩码以提高重复绘制性能

**数据成员**：
- `GrProxyProvider* fProxyProvider` - 用于创建和查找纹理代理
- `bool fAllowCaching` - 是否允许缓存掩码纹理

**关键方法**：
- `GetShapeAndClipBounds()` - 静态工具方法，计算形状和裁剪边界
- `DrawNonAARect()` - 绘制非抗锯齿矩形
- `DrawAroundInvPath()` - 绘制反向填充路径的外部区域
- `DrawToTargetWithShapeMask()` - 使用形状掩码绘制到目标

### SoftwarePathData

```cpp
class SoftwarePathData
```

**作用**：存储延迟上传器的有效负载数据

**成员变量**：
- `SkIRect fMaskBounds` - 掩码边界
- `SkMatrix fViewMatrix` - 视图变换矩阵
- `GrStyledShape fShape` - 样式化形状
- `GrAA fAA` - 抗锯齿设置

**用途**：传递给工作线程进行异步路径光栅化

## 公共 API 函数

### 构造函数

```cpp
SoftwarePathRenderer(GrProxyProvider* proxyProvider, bool allowCaching)
```

**参数**：
- `proxyProvider` - 代理提供者，用于创建纹理
- `allowCaching` - 是否允许缓存，通常用于动画禁用缓存

### GetShapeAndClipBounds

```cpp
static bool GetShapeAndClipBounds(
    SurfaceDrawContext*,
    const GrClip*,
    const GrStyledShape&,
    const SkMatrix& viewMatrix,
    SkIRect* unclippedDevShapeBounds,
    SkIRect* clippedDevShapeBounds,
    SkIRect* devClipBounds)
```

**功能**：计算形状、裁剪和交集边界

**返回**：
- `true` - 有交集，形状可见
- `false` - 无交集，形状完全裁剪

**输出参数**：
- `unclippedDevShapeBounds` - 未裁剪的设备空间形状边界
- `clippedDevShapeBounds` - 裁剪后的形状边界
- `devClipBounds` - 设备空间裁剪边界

## 内部实现细节

### 绘制路径流程

**onDrawPath 主要步骤**：

1. **边界计算**
   - 调用 `GetShapeAndClipBounds()` 获取三种边界
   - 如果无交集但是反向填充，绘制外部区域后返回

2. **缓存策略决策**
   ```cpp
   bool useCache = fAllowCaching && !inverseFilled &&
                   args.fViewMatrix->preservesAxisAlignment() &&
                   args.fShape->hasUnstyledKey() &&
                   (GrAAType::kCoverage == args.fAAType);
   ```
   **缓存条件**：
   - 允许缓存
   - 非反向填充
   - 矩阵保持轴对齐（防止动画过载缓存）
   - 形状有未样式化键
   - 使用覆盖抗锯齿

3. **可见性优化**
   - 仅当 >50% 路径可见时使用缓存
   - 检查尺寸是否超过 `maxTextureSize`
   - 决定使用 `unclippedDevShapeBounds` 或 `clippedDevShapeBounds`

4. **唯一键生成**（如果使用缓存）
   ```cpp
   skgpu::UniqueKey::Builder builder(&maskKey, kDomain, 7 + keySize, "SW Path Mask");
   builder[0] = width;
   builder[1] = height;
   builder[2] = SkFloat2Bits(sx);  // 缩放X
   builder[3] = SkFloat2Bits(sy);  // 缩放Y
   builder[4] = SkFloat2Bits(kx);  // 倾斜X
   builder[5] = SkFloat2Bits(ky);  // 倾斜Y
   builder[6] = fracX | (fracY >> 8) | (styleBits << 16);
   // + 形状未样式化键
   ```
   **键组成部分**：
   - 尺寸（宽度、高度）
   - 2x2 上部矩阵（sx, sy, kx, ky）
   - 子像素位置（8位 X 和 Y，Android 忽略）
   - 样式位（发丝笔触端点样式）
   - 形状几何键

5. **缓存查找**
   - 调用 `fProxyProvider->findOrCreateProxyByUniqueKey(maskKey)`
   - 命中时增加统计计数器

6. **掩码生成**（如果未命中）

   **多线程路径**（DirectContext 可用）：
   ```cpp
   view = make_deferred_mask_texture_view(context, fit, size);
   auto uploader = std::make_unique<GrTDeferredProxyUploader<SoftwarePathData>>(...);
   taskGroup->add([uploaderRaw] {
       GrSWMaskHelper helper(uploaderRaw->getPixels());
       helper.init(bounds);
       helper.drawShape(shape, viewMatrix, aa, 0xFF);
       uploaderRaw->signalAndFreeData();
   });
   view.asTextureProxy()->texPriv().setDeferredUploader(std::move(uploader));
   ```
   - 创建延迟纹理视图
   - 创建上传器存储路径数据
   - 提交到任务组异步执行
   - GPU 首次使用纹理时触发上传

   **单线程路径**：
   ```cpp
   GrSWMaskHelper helper;
   helper.init(*boundsForMask);
   helper.drawShape(*args.fShape, *args.fViewMatrix, aa, 0xFF);
   view = helper.toTextureView(args.fContext, fit);
   ```
   - 同步创建 `GrSWMaskHelper`
   - 直接光栅化路径
   - 转换为纹理视图

7. **缓存写入**（如果使用缓存）
   ```cpp
   auto listener = GrMakeUniqueKeyInvalidationListener(&maskKey, contextID);
   fProxyProvider->assignUniqueKeyToProxy(maskKey, view.asTextureProxy());
   args.fShape->addGenIDChangeListener(std::move(listener));
   ```
   - 分配唯一键到代理
   - 添加生成 ID 变更监听器
   - 形状变化时自动失效缓存

8. **反向填充处理**
   - 调用 `DrawAroundInvPath()` 绘制路径外部四个矩形区域

9. **最终混合**
   - 调用 `DrawToTargetWithShapeMask()` 使用掩码混合到目标

### 反向填充绘制

**DrawAroundInvPath 实现**：

将裁剪边界分解为四个不与路径相交的矩形：
- **上部矩形**：`[clipLeft, clipTop, clipRight, pathTop]`
- **左侧矩形**：`[clipLeft, pathTop, pathLeft, pathBottom]`
- **右侧矩形**：`[pathRight, pathTop, clipRight, pathBottom]`
- **下部矩形**：`[clipLeft, pathBottom, clipRight, clipBottom]`

每个矩形使用反向视图矩阵（`viewMatrix.invert()`）作为局部矩阵绘制。

### 掩码纹理混合

**DrawToTargetWithShapeMask 实现**：

1. **Swizzle 设置**：`view.concatSwizzle(skgpu::Swizzle("aaaa"))`
   - 将 Alpha 通道复制到所有通道（RGBA = AAAA）

2. **纹理坐标计算**：
   ```cpp
   SkMatrix maskMatrix = SkMatrix::Translate(-textureOriginX, -textureOriginY);
   maskMatrix.preConcat(viewMatrix);
   ```
   - 平移使纹理原点映射到设备空间边界左上角
   - 预乘视图矩阵

3. **片段处理器设置**：
   ```cpp
   paint.setCoverageFragmentProcessor(
       GrTextureEffect::Make(view, kPremul_SkAlphaType, maskMatrix, kNearest));
   ```
   - 使用最近邻过滤采样掩码
   - 作为覆盖处理器调制最终颜色

4. **绘制矩形**：
   - 在设备空间绘制矩形
   - 使用反向视图矩阵作为局部矩阵

### 边界安全处理

**get_unclipped_shape_dev_bounds 函数**：

**Int32 范围保护**：
```cpp
static constexpr int32_t kMaxInt = 2147483520;  // 最大精确浮点表示的int32
shapeDevBounds.intersect(SkRect::MakeLTRB(INT32_MIN, INT32_MIN, kMaxInt, kMaxInt));
```

**可表示性检查**：
```cpp
if (SkScalarRoundToInt(shapeDevBounds.width()) > kMaxInt ||
    SkScalarRoundToInt(shapeDevBounds.height()) > kMaxInt) {
    return false;
}
```

防止极大路径导致整数溢出或不可表示的纹理尺寸。

## 依赖关系

**核心依赖**：
- `PathRenderer` - 基类
- `GrSWMaskHelper` - CPU 软件掩码光栅化
- `GrProxyProvider` - 纹理代理管理
- `GrDeferredProxyUploader` - 延迟纹理上传

**渲染基础设施**：
- `SurfaceDrawContext` - 表面绘制上下文
- `GrPaint` - 绘制参数
- `GrClip` - 裁剪区域
- `GrTextureEffect` - 纹理效果片段处理器

**多线程支持**：
- `SkTaskGroup` - 任务组调度器
- `GrTDeferredProxyUploader<T>` - 模板化延迟上传器

**形状与几何**：
- `GrStyledShape` - 样式化形状
- `SkMatrix` - 变换矩阵
- `SkPath` - 路径几何

## 设计模式与设计决策

### 回退模式（Fallback Pattern）

`SoftwarePathRenderer` 实现兜底策略：
- `onCanDrawPath()` 返回 `kAsBackup`
- 仅在其他渲染器拒绝后才被选择
- 保证 Skia 能渲染任意复杂路径

### 延迟执行模式

使用 `GrDeferredProxyUploader` 延迟纹理上传：
- 路径光栅化在后台线程异步执行
- 纹理内容在 GPU 首次使用时上传
- 减少主线程阻塞，提高响应性

### 缓存失效监听器模式

通过 `GrMakeUniqueKeyInvalidationListener` 实现自动缓存失效：
- 形状几何变化时自动触发
- 避免使用过时缓存数据
- 基于生成 ID 的轻量级追踪

### 条件缓存策略

**保守缓存条件**：
- 轴对齐矩阵（防止动画过载缓存）
- 覆盖 AA（其他 AA 类型不适合缓存）
- 非反向填充（反向填充依赖裁剪边界）
- >50% 可见性（避免缓存大部分不可见内容）

### 分层次键设计

唯一键包含几何和变换信息：
- 2x2 矩阵精确匹配
- 子像素位置（8位精度，Android 忽略）
- 样式信息（发丝端点）
- 形状几何键

### 平台差异化

**Android 优化**：
```cpp
#ifdef SK_BUILD_FOR_ANDROID_FRAMEWORK
    SkFixed fracX = 0;
    SkFixed fracY = 0;
#else
    // 允许8位子像素定位
#endif
```
Android 忽略子像素位置，匹配 HWUI 行为，提高缓存命中率。

## 性能考量

### 多线程异步光栅化

**优化效果**：
- CPU 光栅化在后台线程执行，不阻塞主线程
- GPU 和 CPU 并行工作
- 适用于复杂路径的长时间光栅化

**限制**：
- 仅在 `GrDirectContext` 可用时启用
- 需要任务组调度器支持

### 缓存命中优化

**缓存收益**：
- 避免重复 CPU 光栅化
- 适用于重复绘制相同路径（UI 控件、图标）
- 轴对齐约束防止动画帧过载缓存

**缓存成本**：
- 纹理内存占用
- 唯一键查找开销
- 生成 ID 监听器管理

### 可见性剪枝

**50% 阈值**：
```cpp
if (unclippedArea > 2 * clippedArea) {
    useCache = false;  // 大部分不可见，不缓存
}
```
避免缓存大型纹理但仅绘制小部分的场景。

### 反向填充优化

分解为四个矩形而非整个裁剪区域减去路径：
- 避免复杂的布尔路径运算
- 利用 GPU 矩形绘制快速路径
- 四个绘制调用成本低于布尔运算

### 纹理大小限制

检查 `maxTextureSize` 避免创建超大纹理：
- 防止分配失败
- 避免过度内存占用
- 超限路径不缓存

## 相关文件

**CPU 光栅化**：
- `src/gpu/ganesh/GrSWMaskHelper.h/cpp` - 软件掩码助手

**资源管理**：
- `src/gpu/ganesh/GrProxyProvider.h` - 代理提供者
- `src/gpu/ganesh/GrDeferredProxyUploader.h` - 延迟上传器

**基础设施**：
- `src/gpu/ganesh/PathRenderer.h` - 路径渲染器基类
- `src/gpu/ganesh/SurfaceDrawContext.h` - 表面绘制上下文

**效果**：
- `src/gpu/ganesh/effects/GrTextureEffect.h` - 纹理效果

**形状**：
- `src/gpu/ganesh/geometry/GrStyledShape.h` - 样式化形状

**多线程**：
- `src/core/SkTaskGroup.h` - 任务组调度器
