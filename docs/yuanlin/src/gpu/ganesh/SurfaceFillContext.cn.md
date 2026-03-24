# SurfaceFillContext

> 源文件: `src/gpu/ganesh/SurfaceFillContext.h` (212 行), `src/gpu/ganesh/SurfaceFillContext.cpp` (274 行)

## 1. 概述

`SurfaceFillContext` 是 Skia Ganesh GPU 后端中负责表面填充操作的中间层类。它继承自 `SurfaceContext`，添加了渲染目标管理、OpsTask 调度、清除和基于 Fragment Processor 的填充能力。该类**非 final**，被 `SurfaceDrawContext` 继承。

**继承关系**：`SurfaceDrawContext` (final) → `SurfaceFillContext` → `SurfaceContext`

**架构位置**：
```
SkCanvas → SkDevice → SurfaceDrawContext → SurfaceFillContext → SurfaceContext
                                         ↓
                              GrOp → OpsTask → GrDrawingManager → GPU
```

**关键成员变量**：

| 成员 | 类型 | 说明 |
|------|------|------|
| `fWriteView` | `GrSurfaceProxyView` | 写入视图，包含渲染目标代理和 write swizzle（protected） |
| `fOpsTask` | `sk_sp<OpsTask>` | 当前的操作任务，管理 Op 队列（private，只能通过 `getOpsTask()` 访问） |

---

## 2. 构造函数

### SurfaceFillContext(rContext, readView, writeView, colorInfo)

```cpp
SurfaceFillContext(GrRecordingContext* rContext,
                   GrSurfaceProxyView readView,
                   GrSurfaceProxyView writeView,
                   const GrColorInfo& colorInfo);
```

**流程**：
1. 调用基类 `SurfaceContext` 构造函数，传入 `readView` 和 `colorInfo`
2. 初始化 `fWriteView = writeView`
3. 断言 `this->asSurfaceProxy() == fWriteView.proxy()`（read 和 write 指向同一个 proxy）
4. 断言 `this->origin() == fWriteView.origin()`（origin 一致）
5. 通过 `rContext->priv().drawingManager()->getLastOpsTask(this->asSurfaceProxy())` 获取已有的 OpsTask（MDB 模式下允许共享——如果同一 proxy 已有未关闭的 OpsTask，可以复用）
6. 调用 `validate()`（DEBUG 模式）

> **MDB 模式说明**：`getLastOpsTask` 返回的 OpsTask 可能已关闭。如果已关闭，在后续通过 `getOpsTask()` 访问时会自动创建新的。

---

## 3. 公共方法

### 3.1 OpsTask 管理

#### getOpsTask()

```cpp
OpsTask* getOpsTask();
```

获取当前可用的 OpsTask，保证返回的 OpsTask 未关闭。

**流程**：
1. `ASSERT_SINGLE_OWNER` + `validate()`（DEBUG）
2. 如果 `fOpsTask` 为空或已关闭（`fOpsTask->isClosed()`）→ 调用 `replaceOpsTask()` 创建新的
3. 断言新 OpsTask 未关闭（`!fOpsTask->isClosed()`）
4. 返回 `fOpsTask.get()`

#### refRenderTask()

```cpp
sk_sp<GrRenderTask> refRenderTask();
```

返回引用计数的渲染任务指针。

**流程**：
- 调用 `getOpsTask()` 确保有效，返回 `sk_ref_sp(this->getOpsTask())`

#### discard()

```cpp
void discard();
```

提示渲染目标内容可以丢弃，用于 TBR GPU 优化（避免加载前一帧内容）。

**流程**：
1. `ASSERT_SINGLE_OWNER` + `RETURN_IF_ABANDONED` + `validate()`
2. 创建 trace marker `"SurfaceFillContext::discard"`
3. 调用 `this->getOpsTask()->discard()`（标记 OpsTask 内容可丢弃）

#### resolveMSAA()

```cpp
void resolveMSAA();
```

将多采样渲染目标 resolve 到单采样纹理。

**流程**：
1. `ASSERT_SINGLE_OWNER` + `RETURN_IF_ABANDONED` + `validate()`
2. 创建 trace marker `"SurfaceFillContext::resolveMSAA"`
3. 调用 `drawingManager()->newTextureResolveRenderTask(this->asSurfaceProxyRef(), GrSurfaceProxy::ResolveFlags::kMSAA, *this->caps())`

### 3.2 清除操作

#### clear(rect, color)（模板，内联）

```cpp
template <SkAlphaType AlphaType>
void clear(const SkIRect& rect, const SkRGBA4f<AlphaType>& color);
```

清除指定矩形区域为给定颜色。

**流程**：
- 调用 `internalClear(&rect, this->adjustColorAlphaType(color))`

#### clear(color)（模板，内联）

```cpp
template <SkAlphaType AlphaType>
void clear(const SkRGBA4f<AlphaType>& color);
```

清除整个渲染目标为给定颜色。

**流程**：
- 调用 `internalClear(nullptr, this->adjustColorAlphaType(color))`（`scissor = nullptr` 表示全屏）

#### clearAtLeast(scissor, color)（模板，内联）

```cpp
template <SkAlphaType AlphaType>
void clearAtLeast(const SkIRect& scissor, const SkRGBA4f<AlphaType>& color);
```

清除至少指定区域，允许升级为全屏清除以提高性能。

**流程**：
- 调用 `internalClear(&scissor, this->adjustColorAlphaType(color), /* upgradePartialToFull */ true)`

### 3.3 Fragment Processor 填充

#### fillRectWithFP(dstRect, fp)

```cpp
void fillRectWithFP(const SkIRect& dstRect, std::unique_ptr<GrFragmentProcessor> fp);
```

使用 Fragment Processor 填充矩形。

**流程**：
1. `ASSERT_SINGLE_OWNER` + `RETURN_IF_ABANDONED` + `validate()`
2. 创建 trace marker `"SurfaceFillContext::fillRectWithFP"`
3. 创建 `GrPaint`，设置 `colorFragmentProcessor = fp`
4. 设置 `XPFactory = SkBlendMode::kSrc`（完全覆盖，FP 填充不需要与底色混合）
5. 调用 `FillRectOp::MakeNonAARect(fContext, paint, SkMatrix::I(), SkRect::Make(dstRect))` 创建无 AA 的矩形填充 op
6. 调用 `this->addDrawOp(op)`

#### fillRectWithFP(dstRect, localMatrix, fp)

```cpp
void fillRectWithFP(const SkIRect& dstRect, const SkMatrix& localMatrix,
                    std::unique_ptr<GrFragmentProcessor> fp);
```

带坐标变换的 FP 填充。

**流程**：
1. 用 `GrMatrixEffect::Make(localMatrix, fp)` 包装 FP（添加坐标变换）
2. 委托给第一个 `fillRectWithFP(dstRect, fp)` 重载

#### fillRectToRectWithFP(srcRect, dstRect, fp)（内联）

```cpp
void fillRectToRectWithFP(const SkRect& srcRect, const SkIRect& dstRect,
                          std::unique_ptr<GrFragmentProcessor> fp);
```

将 FP 从 srcRect 映射到 dstRect 进行填充。

**流程**：
1. 计算 `localMatrix = SkMatrix::RectToRectOrIdentity(SkRect::Make(dstRect), srcRect)`（将 dstRect 坐标映射到 srcRect 坐标）
2. 委托给 `fillRectWithFP(dstRect, localMatrix, fp)`

#### fillRectToRectWithFP(srcIRect, dstRect, fp)（内联）

```cpp
void fillRectToRectWithFP(const SkIRect& srcRect, const SkIRect& dstRect,
                          std::unique_ptr<GrFragmentProcessor> fp);
```

整数版重载。

**流程**：
- 将 `srcIRect` 转为 `SkRect::Make(srcRect)`，委托给上一个重载

#### fillWithFP(fp)（内联）

```cpp
void fillWithFP(std::unique_ptr<GrFragmentProcessor> fp);
```

使用 FP 填充整个渲染目标。

**流程**：
- 调用 `fillRectWithFP(SkIRect::MakeSize(fWriteView.proxy()->dimensions()), fp)`（以 proxy 的 dimensions 作为目标矩形）

### 3.4 纹理 Blit

#### blitTexture(view, srcRect, dstPoint)

```cpp
bool blitTexture(GrSurfaceProxyView view, const SkIRect& srcRect, const SkIPoint& dstPoint);
```

从源纹理拷贝矩形区域到目标表面，无变换和过滤。

**流程**：
1. 断言 `view.asTextureProxy()` 非空（必须是纹理代理）
2. 调用 `GrClipSrcRectAndDstPoint(this->dimensions(), &clippedDstPoint, view.dimensions(), &clippedSrcRect)` 将 src/dst 裁剪到各自 bounds
3. 如果裁剪后无交集 → 返回 `false`
4. 构造 `clippedDstRect = SkIRect::MakePtSize(clippedDstPoint, clippedSrcRect.size())`
5. 创建 `GrTextureEffect::Make(view, kUnknown_SkAlphaType)` 纹理效果 FP
6. 调用 `fillRectToRectWithFP(SkRect::Make(clippedSrcRect), clippedDstRect, fp)`
7. 返回 `true`

### 3.5 查询方法

| 方法 | 实现 |
|------|------|
| `numSamples()` | `this->asRenderTargetProxy()->numSamples()` |
| `wrapsVkSecondaryCB()` | `this->asRenderTargetProxy()->wrapsVkSecondaryCB()` |
| `arenaAlloc()` | `this->arenas()->arenaAlloc()` |
| `subRunAlloc()` | `this->arenas()->subRunAlloc()` |
| `writeSurfaceView()` | 返回 `fWriteView` 的 `const&` |
| `asFillContext()` | 返回 `this`（override 自 SurfaceContext） |

---

## 4. 保护方法

### replaceOpsTask()

```cpp
OpsTask* replaceOpsTask();
```

创建新的 OpsTask 替换当前的。

**流程**：
1. 调用 `drawingManager()->newOpsTask(this->writeSurfaceView(), this->arenas())` 创建新 OpsTask
2. 调用 `this->willReplaceOpsTask(fOpsTask.get(), newOpsTask.get())`（虚函数通知子类，默认空实现，SurfaceDrawContext 重写以处理 stencil 保存/恢复和 DMSAA 统计）
3. `fOpsTask = std::move(newOpsTask)`
4. 返回 `fOpsTask.get()`

### ClearToGrPaint(color, paint)（static）

```cpp
static void ClearToGrPaint(std::array<float, 4> color, GrPaint* paint);
```

为清除操作创建常量色 paint，优化混合模式选择。

**流程**：
1. 设置 `paint->setColor4f({color[0], color[1], color[2], color[3]})`
2. 如果 `alpha == 1.0f` → 使用 `SkBlendMode::kSrcOver`
   - 理由：alpha=1 时 src 和 srcOver 结果相同，但 srcOver 不需要禁用 blend，利于与后续操作批处理
3. 否则 → 使用 `SkBlendMode::kSrc`
   - 理由：透明色必须完全覆盖底色，不能与底色混合

### addOp(op)

```cpp
void addOp(GrOp::Owner op);
```

将非绘制 Op（如 ClearOp）添加到当前 OpsTask。

**流程**：
1. 获取 `drawingManager`
2. 调用 `getOpsTask()->addOp(drawingMgr, op, GrTextureResolveManager(drawingMgr), *this->caps())`

### ConvertColor\<AlphaType\>(color)（模板特化）

```cpp
template <SkAlphaType AlphaType>
static std::array<float, 4> ConvertColor(SkRGBA4f<AlphaType> color);
```

在 premul 和 unpremul 之间转换颜色。

**模板特化**：
- `kPremul_SkAlphaType` → 返回 `color.unpremul().array()`（premul → unpremul）
- `kUnpremul_SkAlphaType` → 返回 `color.premul().array()`（unpremul → premul）

### adjustColorAlphaType\<AlphaType\>(color)（模板）

```cpp
template <SkAlphaType AlphaType>
std::array<float, 4> adjustColorAlphaType(SkRGBA4f<AlphaType> color) const;
```

将输入颜色的 alpha 类型调整为与表面一致。

**流程**：
1. 如果输入的 `AlphaType == kUnknown_SkAlphaType` 或表面的 `alphaType() == kUnknown_SkAlphaType` → 直接返回 `color.array()`（无法判断，不做转换）
2. 如果输入与表面的 `alphaType` 相同 → 直接返回 `color.array()`（无需转换）
3. 否则 → 调用 `ConvertColor(color)` 进行 premul/unpremul 转换

---

## 5. 私有方法

### addDrawOp(op)

```cpp
void addDrawOp(GrOp::Owner owner);
```

SurfaceFillContext 的简化版 addDrawOp，不处理 clip/stencil/dst texture（因为填充操作总是全覆盖无裁剪）。SurfaceDrawContext 提供了处理完整 clip 的重写版本。

**流程**：
1. 将 `owner` 转为 `GrDrawOp*`
2. 计算 `clampType = GrColorTypeClampType(this->colorInfo().colorType())`
3. 创建 `GrAppliedClip::Disabled()`（无裁剪）
4. 调用 `op->finalize(caps, &clip, clampType)` 获取 `analysis`
5. 断言检查：
   - `!op->usesStencil()`（填充操作不使用 stencil）
   - `!analysis.requiresDstTexture()`（填充操作不需要读取 dst）
   - `!op->hasAABloat() && !op->hasZeroArea()`（不应有 coverage AA 或 hairline）
6. 获取 op bounds，与 surface proxy 的 `getBoundsRect()` 取交集，无交集则丢弃 op
7. 设置 `op->setClippedBounds(op->bounds())`
8. DEBUG 模式设置 `op->fAddDrawOpCalled = true`
9. 创建空的 `GrDstProxyView`
10. 调用 `opsTask->addDrawOp(drawingManager, owner, op->usesMSAA(), analysis, clip, dstProxyView, GrTextureResolveManager(drawingManager), caps)`

### willReplaceOpsTask(prevTask, nextTask)（虚函数）

```cpp
virtual void willReplaceOpsTask(OpsTask* prevTask, OpsTask* nextTask) {}
```

OpsTask 被替换时的通知回调。默认空实现。

SurfaceDrawContext 重写此方法以：
- 如果 `fNeedsStencil`：保存 prevTask 的 stencil 并加载到 nextTask
- DMSAA 统计：递增 `fNumRenderPasses`

### canDiscardPreviousOpsOnFullClear()（虚函数）

```cpp
virtual OpsTask::CanDiscardPreviousOps canDiscardPreviousOpsOnFullClear() const;
```

判断全屏清除时是否可以丢弃之前的 ops。默认返回 `kYes`。

SurfaceDrawContext 重写：如果 `fNeedsStencil` → 返回 `kNo`（stencil 数据可能被后续 op 使用）。

### internalClear(scissor, color, upgradePartialToFull)

```cpp
void internalClear(const SkIRect* scissor, std::array<float, 4> color,
                   bool upgradePartialToFull = false);
```

清除操作的核心实现，包含三条路径：load op（全屏，最快）→ native clear（硬件清除）→ draw clear（兼容性 fallback）。

**流程**：
1. `ASSERT_SINGLE_OWNER` + `RETURN_IF_ABANDONED` + `validate()`
2. 创建 trace marker `"SurfaceFillContext::clear"`
3. 创建 `GrScissorState(this->asSurfaceProxy()->backingStoreDimensions())`
4. 如果提供了 `scissor` 且 `scissorState.set(*scissor)` 失败（清除区域在屏幕外）→ 返回
5. **升级判断**：如果 `scissorState` 启用且非 `performColorClearsAsDraws`：
   - 如果 `upgradePartialToFull` 且（`caps->preferFullscreenClears()` 或 `caps->shouldInitializeTextures()`）→ `scissorState.setDisabled()`（升级为全屏清除）
   - 否则 → `scissorState.relaxTest(this->dimensions())`（允许溢出到 approx-fit padding 区域，与 stencil clear 不同，color clear 可以安全溢出）
6. **全屏清除路径**（`!scissorState.enabled()`）：
   - 获取 `opsTask = this->getOpsTask()`
   - 调用 `opsTask->resetForFullscreenClear(this->canDiscardPreviousOpsOnFullClear())`
   - 如果成功重置且非 `performColorClearsAsDraws`：
     - 应用 `writeSurfaceView().swizzle()` 到 color
     - 设置 `opsTask->setColorLoadOp(GrLoadOp::kClear, color)`（使用 load op 清除，最快路径）
     - 返回
   - 否则：
     - 设置 `opsTask->setColorLoadOp(GrLoadOp::kDiscard)`（后续用 op 清除，先标记 discard 避免无用加载）
7. **Draw 清除路径**（`performColorClearsAsDraws` 或 `performPartialClearsAsDraws` 且有 scissor）：
   - 调用 `ClearToGrPaint(color, &paint)` 创建 paint
   - 调用 `FillRectOp::MakeNonAARect(fContext, paint, SkMatrix::I(), SkRect::Make(scissorState.rect()))` 创建填充矩形 op
   - 调用 `this->addDrawOp(op)`
8. **Native 清除路径**（硬件原生清除）：
   - 应用 `writeSurfaceView().swizzle()` 到 color
   - 调用 `ClearOp::MakeColor(fContext, scissorState, color)` 创建 ClearOp
   - 调用 `this->addOp(op)`

### onValidate()（DEBUG 模式）

```cpp
SkDEBUGCODE(void onValidate() const override;)
```

调试验证。

**流程**：
- 如果 `fOpsTask` 存在且未关闭 → 断言 `drawingManager()->getLastRenderTask(fWriteView.proxy()) == fOpsTask.get()`（确保 drawing manager 记录的最后一个 render task 就是当前的 fOpsTask）

### arenas()（私有辅助）

```cpp
sk_sp<GrArenas> arenas();
```

**流程**：
- 返回 `fWriteView.proxy()->asRenderTargetProxy()->arenas()`

---

## 6. 关键设计决策

- **Read/Write 双 View**：`readSwizzle` 用于纹理采样，`writeSwizzle` 用于渲染写入。某些格式（如 BGRA）二者不同。基类 SurfaceContext 持有 readView，本类新增 fWriteView
- **OpsTask 惰性获取**：`getOpsTask()` 自动在 OpsTask 关闭后创建新的。MDB（Multi-Draw-Buffer）模式下允许跨 context 共享同一 OpsTask——构造函数通过 `getLastOpsTask` 复用已有的
- **清除三路径**：load op（全屏，最快，直接设置 GPU load 操作）→ native clear（ClearOp，硬件清除命令）→ draw clear（FillRectOp，兼容性 fallback，用于不支持原生清除的驱动）
- **Alpha = 1.0 用 SrcOver**：`ClearToGrPaint` 中，当 alpha=1 时 src 和 srcOver 结果相同，但 srcOver 不需要禁用 blend，利于与后续操作批处理
- **addDrawOp 简化版**：SurfaceFillContext 的 `addDrawOp` 不处理 clip/stencil/dst texture，因为填充操作总是全覆盖无裁剪。SurfaceDrawContext 提供了处理完整 clip、stencil、DMSAA、dst proxy 的完整版 `addDrawOp(clip, op, willAddFn)`
- **upgradePartialToFull**：`clearAtLeast` 传入 `true`，允许在 `preferFullscreenClears` 或 `shouldInitializeTextures` 的 GPU 上将部分清除升级为全屏清除，性能更优
- **scissorState.relaxTest**：对非全屏清除，允许清除范围溢出到 approx-fit backing store 的 padding 区域，这对 color clear 是安全的（与 stencil clear 不同）

---

## 7. 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/SurfaceContext.h/.cpp` | 基类 | 像素读写和缩放 |
| `src/gpu/ganesh/SurfaceDrawContext.h/.cpp` | 派生类 | 完整绘制功能，重写 willReplaceOpsTask/canDiscardPreviousOpsOnFullClear/addDrawOp |
| `src/gpu/ganesh/ops/OpsTask.h/.cpp` | 成员 | Op 队列管理，fOpsTask 的类型 |
| `src/gpu/ganesh/ops/FillRectOp.h` | 依赖 | 矩形填充 op（draw clear 和 FP 填充的底层） |
| `src/gpu/ganesh/ops/ClearOp.h` | 依赖 | 原生清除 op |
| `src/gpu/ganesh/GrFragmentProcessor.h` | 依赖 | 着色器效果基类 |
| `src/gpu/ganesh/effects/GrTextureEffect.h` | 依赖 | 纹理采样 FP（blitTexture 使用） |
| `src/gpu/ganesh/effects/GrMatrixEffect.h` | 依赖 | 坐标变换 FP 包装器 |
| `src/gpu/ganesh/GrPaint.h` | 依赖 | 绘制状态（颜色、混合模式、FP 链） |
| `src/gpu/ganesh/GrDrawingManager.h` | 依赖 | 管理 OpsTask 创建和 render task 调度 |
| `src/gpu/ganesh/GrScissorState.h` | 依赖 | 裁剪状态（internalClear 中使用） |
| `src/gpu/ganesh/GrAppliedClip.h` | 依赖 | 已应用的裁剪（addDrawOp 中使用 Disabled） |
