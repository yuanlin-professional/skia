# FillRectOp

> 源文件
> - src/gpu/ganesh/ops/FillRectOp.h
> - src/gpu/ganesh/ops/FillRectOp.cpp

## 概述

`FillRectOp` 是 Ganesh GPU 后端中用于高效渲染填充矩形的专用操作。它支持覆盖抗锯齿（coverage AA）和非抗锯齿模式（可与 MSAA 配合使用），并提供灵活的每边抗锯齿控制。该操作使用 `QuadPerEdgeAA` 几何处理器实现高性能的四边形批处理，支持透视变换和局部坐标映射。

`FillRectOp` 是 Skia 中最常用的绘制操作之一，针对矩形这种最基础的几何图元进行了深度优化，包括操作合并、颜色优化和索引缓冲区重用等多项性能增强。

## 架构位置

`FillRectOp` 位于 Ganesh 渲染管线的操作层：

- **上层**：由 `SurfaceDrawContext` 调用，响应高层绘制 API（如 `drawRect`）
- **同层**：继承自 `GrMeshDrawOp`，与其他几何操作（如 `FillRRectOp`, `TextureOp`）并列
- **下层**：使用 `QuadPerEdgeAA` 几何处理器生成顶点数据，通过 `GrOpFlushState` 提交绘制命令

在绘制流水线中，该操作是矩形从高层形状描述到底层 GPU 四边形渲染的关键转换点。

## 主要类与结构体

### 类层次结构

```
GrOp
    └── GrDrawOp
        └── GrMeshDrawOp
            └── FillRectOpImpl (匿名命名空间)
```

### FillRectOp 工厂类

`FillRectOp` 本身不是可实例化的类，而是一组静态工厂方法的命名空间：

**公共接口**：
- `Make()` - 创建单个四边形操作
- `MakeNonAARect()` - 创建非 AA 矩形的便捷方法
- `AddFillRectOps()` - 批量 API，创建多个四边形操作

**私有接口**：
- `MakeOp()` - 从四边形集合创建操作（尽可能多地合并）

### FillRectOpImpl 关键成员

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fHelper` | `GrSimpleMeshDrawOpHelperWithStencil` | 简化操作辅助类，包含模板支持 |
| `fQuads` | `GrQuadBuffer<ColorAndAA>` | 四边形缓冲区，存储几何和元数据 |
| `fPrePreparedVertices` | `char*` | 预准备的顶点数据（DDL 场景） |
| `fProgramInfo` | `GrProgramInfo*` | 程序信息 |
| `fColorType` | `ColorType` | 颜色类型（None/Byte/Float） |
| `fVertexBuffer` | `sk_sp<const GrBuffer>` | 顶点缓冲区 |
| `fIndexBuffer` | `sk_sp<const GrBuffer>` | 索引缓冲区 |
| `fBaseVertex` | `int` | 基础顶点偏移 |

### DrawQuad 结构体

表示单个要绘制的四边形：

| 成员 | 类型 | 说明 |
|------|------|------|
| `fDevice` | `GrQuad` | 设备空间四边形（变换后的顶点） |
| `fLocal` | `GrQuad` | 局部坐标四边形（纹理/效果采样坐标） |
| `fEdgeFlags` | `GrQuadAAFlags` | 每边抗锯齿标志 |

### ColorAndAA 结构体

存储在 `GrQuadBuffer` 中的元数据：

| 成员 | 类型 | 说明 |
|------|------|------|
| `fColor` | `SkPMColor4f` | 预乘 alpha 颜色 |
| `fAAFlags` | `GrQuadAAFlags` | 抗锯齿标志 |

### GrQuadSetEntry 结构体

批量 API 的输入格式：

| 成员 | 类型 | 说明 |
|------|------|------|
| `fRect` | `SkRect` | 局部空间矩形 |
| `fColor` | `SkPMColor4f` | 颜色 |
| `fLocalMatrix` | `SkMatrix` | 局部变换矩阵 |
| `fAAFlags` | `GrQuadAAFlags` | 每边抗锯齿标志 |

## 公共 API 函数

### 工厂方法

```cpp
static GrOp::Owner Make(GrRecordingContext* context,
                        GrPaint&& paint,
                        GrAAType aaType,
                        DrawQuad* quad,
                        const GrUserStencilSettings* stencilSettings = nullptr,
                        InputFlags inputFlags = InputFlags::kNone)
```
创建单个填充矩形操作。

**参数**：
- `context`：录制上下文
- `paint`：绘制属性（颜色、混合模式、效果等）
- `aaType`：抗锯齿类型（None/MSAA/Coverage）
- `quad`：四边形描述（设备和局部坐标）
- `stencilSettings`：可选的模板设置
- `inputFlags`：输入标志（如无纹理等）

```cpp
static GrOp::Owner MakeNonAARect(GrRecordingContext* context,
                                 GrPaint&& paint,
                                 const SkMatrix& view,
                                 const SkRect& rect,
                                 const GrUserStencilSettings* stencilSettings = nullptr)
```
创建非抗锯齿矩形的便捷方法，用于测试和 GM。

**简化参数**：
- `view`：视图变换矩阵
- `rect`：矩形

```cpp
static void AddFillRectOps(SurfaceDrawContext* sdc,
                           const GrClip* clip,
                           GrRecordingContext* context,
                           GrPaint&& paint,
                           GrAAType aaType,
                           const SkMatrix& viewMatrix,
                           const GrQuadSetEntry quads[],
                           int quadCount,
                           const GrUserStencilSettings* stencilSettings = nullptr)
```
批量 API，从四边形集合创建并添加操作到绘制上下文。

自动处理索引缓冲区容量限制，必要时创建多个操作。

## 内部实现细节

### 构造函数

```cpp
FillRectOpImpl(GrProcessorSet* processorSet, SkPMColor4f paintColor, GrAAType aaType,
               DrawQuad* quad, const GrUserStencilSettings* stencil,
               Helper::InputFlags inputFlags)
```

初始化步骤：
1. 解析抗锯齿类型和边缘标志的不一致性（通过 `GrQuadUtils::ResolveAAType`）
2. 设置边界（考虑 AA 扩展和细线检测）
3. 裁剪到 W>0（透视投影处理）
4. 将四边形添加到 `fQuads` 缓冲区

**透视裁剪**：
```cpp
DrawQuad extra;
int count = GrQuadUtils::ClipToW0(quad, &extra);
```
当四边形跨越 W=0 平面时，可能被分割成两个四边形。

### 顶点规格

`vertexSpec()` 方法计算顶点布局：

```cpp
VertexSpec vertexSpec() const {
    auto indexBufferOption = QuadPerEdgeAA::CalcIndexBufferOption(
            fHelper.aaType(), fQuads.count());

    return VertexSpec(fQuads.deviceQuadType(), fColorType, fQuads.localQuadType(),
                      fHelper.usesLocalCoords(), Subset::kNo, fHelper.aaType(),
                      fHelper.compatibleWithCoverageAsAlpha(), indexBufferOption);
}
```

顶点规格包含：
- 设备四边形类型（矩形/标准/透视）
- 颜色类型（None/Byte/Float）
- 局部四边形类型
- 是否需要局部坐标
- 抗锯齿类型
- 索引缓冲区选项

### 颜色优化

`finalize()` 方法执行颜色分析和优化：

```cpp
GrProcessorSet::Analysis finalize(const GrCaps& caps, const GrAppliedClip* clip,
                                  GrClampType clampType) override {
    // 聚合所有四边形的颜色
    auto iter = fQuads.metadata();
    SkAssertResult(iter.next());
    GrProcessorAnalysisColor quadColors(iter->fColor);
    while(iter.next()) {
        quadColors = GrProcessorAnalysisColor::Combine(quadColors, iter->fColor);
        if (quadColors.isUnknown()) {
            break;
        }
    }

    auto result = fHelper.finalizeProcessors(caps, clip, clampType, coverage, &quadColors);

    // 如果分析后是常量颜色，统一所有四边形颜色
    SkPMColor4f colorOverride;
    if (quadColors.isConstant(&colorOverride)) {
        fColorType = QuadPerEdgeAA::MinColorType(colorOverride);
        iter = fQuads.metadata();
        while(iter.next()) {
            iter->fColor = colorOverride;
        }
    } else {
        // 否则计算所需的最大颜色类型
        fColorType = ColorType::kNone;
        iter = fQuads.metadata();
        while(iter.next()) {
            fColorType = std::max(fColorType, QuadPerEdgeAA::MinColorType(iter->fColor));
        }
    }

    // 特殊处理：无颜色 FP 时使用 Byte 而非 None
    if (fColorType == ColorType::kNone && !result.hasColorFragmentProcessor()) {
        fColorType = ColorType::kByte;
    }

    return result;
}
```

优化策略：
- **常量颜色**：所有四边形使用相同颜色，简化着色器
- **最小颜色类型**：根据实际颜色值选择最小表示（None=乘以1，Byte=8位，Float=32位）
- **白色矩形优化**：无颜色 FP 时使用 Byte 避免生成特殊着色器

### 操作合并

`onCombineIfPossible()` 实现智能合并：

```cpp
CombineResult onCombineIfPossible(GrOp* t, SkArenaAlloc*, const GrCaps& caps) override {
    auto that = t->cast<FillRectOpImpl>();

    bool upgradeToCoverageAAOnMerge = false;
    if (fHelper.aaType() != that->fHelper.aaType()) {
        if (!CanUpgradeAAOnMerge(fHelper.aaType(), that->fHelper.aaType())) {
            return CombineResult::kCannotCombine;
        }
        upgradeToCoverageAAOnMerge = true;
    }

    if (CombinedQuadCountWillOverflow(fHelper.aaType(), upgradeToCoverageAAOnMerge,
                                      fQuads.count() + that->fQuads.count())) {
        return CombineResult::kCannotCombine;
    }

    if (!fHelper.isCompatible(that->fHelper, caps, this->bounds(), that->bounds(), true)) {
        return CombineResult::kCannotCombine;
    }

    fColorType = std::max(fColorType, that->fColorType);

    if (upgradeToCoverageAAOnMerge) {
        fHelper.setAAType(GrAAType::kCoverage);
    }

    fQuads.concat(that->fQuads);
    return CombineResult::kMerged;
}
```

合并条件：
1. **AA 类型兼容**：相同或可升级（None → Coverage）
2. **容量检查**：合并后不超过索引缓冲区限制
3. **辅助类兼容**：混合模式、裁剪、模板等兼容

特殊功能：允许混合 None 和 Coverage AA（通过升级到 Coverage）。

### 批量添加

`addQuad()` 方法直接添加四边形而不创建新操作：

```cpp
bool addQuad(DrawQuad* quad, const SkPMColor4f& color, GrAAType aaType) {
    SkRect newBounds = this->bounds();
    newBounds.joinPossiblyEmptyRect(quad->fDevice.bounds());

    DrawQuad extra;
    int count = quad->fEdgeFlags != GrQuadAAFlags::kNone ? GrQuadUtils::ClipToW0(quad, &extra) : 1;
    if (count == 0 ) {
        return true;  // 平凡成功
    } else if (!this->canAddQuads(count, aaType)) {
        return false;  // 容量不足
    } else {
        fQuads.append(quad->fDevice, { color, quad->fEdgeFlags },
                      fHelper.isTrivial() ? nullptr : &quad->fLocal);
        if (count > 1) {
            fQuads.append(extra.fDevice, { color, extra.fEdgeFlags },
                          fHelper.isTrivial() ? nullptr : &extra.fLocal);
        }
        this->setBounds(newBounds, HasAABloat(fHelper.aaType() == GrAAType::kCoverage),
                        IsHairline::kNo);
        return true;
    }
}
```

用于 `MakeOp()` 批量构建场景，避免创建多个操作对象的开销。

### 网格化（Tessellation）

`tessellate()` 方法生成顶点数据：

```cpp
void tessellate(const VertexSpec& vertexSpec, char* dst) const {
    static constexpr SkRect kEmptyDomain = SkRect::MakeEmpty();

    QuadPerEdgeAA::Tessellator tessellator(vertexSpec, dst);
    auto iter = fQuads.iterator();
    while (iter.next()) {
        SkASSERT(iter.isLocalValid() != fHelper.isTrivial());
        auto info = iter.metadata();
        tessellator.append(iter.deviceQuad(), iter.localQuad(),
                           info.fColor, kEmptyDomain, info.fAAFlags);
    }
}
```

`QuadPerEdgeAA::Tessellator` 根据 `VertexSpec` 生成每个四边形的顶点：
- 每个四边形 4 个或 8 个顶点（取决于 AA 类型）
- 顶点包含位置、颜色、局部坐标、AA 覆盖率等属性

### 预准备支持

`onPrePrepareDraws()` 支持 DDL（延迟显示列表）：

```cpp
void onPrePrepareDraws(GrRecordingContext* rContext, ...) override {
    INHERITED::onPrePrepareDraws(rContext, writeView, clip, dstProxyView,
                                 renderPassXferBarriers, colorLoadOp);

    SkArenaAlloc* arena = rContext->priv().recordTimeAllocator();
    const VertexSpec vertexSpec = this->vertexSpec();

    const int totalNumVertices = fQuads.count() * vertexSpec.verticesPerQuad();
    const size_t totalVertexSizeInBytes = vertexSpec.vertexSize() * totalNumVertices;

    fPrePreparedVertices = arena->makeArrayDefault<char>(totalVertexSizeInBytes);
    this->tessellate(vertexSpec, fPrePreparedVertices);
}
```

在录制时（而非刷新时）生成顶点数据，存储在录制时 arena 中。

### 准备绘制

`onPrepareDraws()` 在刷新时执行：

```cpp
void onPrepareDraws(GrMeshDrawTarget* target) override {
    const VertexSpec vertexSpec = this->vertexSpec();
    const int totalNumVertices = fQuads.count() * vertexSpec.verticesPerQuad();

    void* vdata = target->makeVertexSpace(vertexSpec.vertexSize(), totalNumVertices,
                                          &fVertexBuffer, &fBaseVertex);
    if (!vdata) {
        SkDebugf("Could not allocate vertices\n");
        return;
    }

    if (fPrePreparedVertices) {
        const size_t totalVertexSizeInBytes = vertexSpec.vertexSize() * totalNumVertices;
        memcpy(vdata, fPrePreparedVertices, totalVertexSizeInBytes);
    } else {
        this->tessellate(vertexSpec, (char*) vdata);
    }

    if (vertexSpec.needsIndexBuffer()) {
        fIndexBuffer = QuadPerEdgeAA::GetIndexBuffer(target, vertexSpec.indexBufferOption());
        if (!fIndexBuffer) {
            SkDebugf("Could not allocate indices\n");
            return;
        }
    }
}
```

处理两种路径：
- **有预准备数据**：直接拷贝（DDL 场景）
- **无预准备数据**：现场网格化（常规场景）

### 执行绘制

`onExecute()` 提交 GPU 命令：

```cpp
void onExecute(GrOpFlushState* flushState, const SkRect& chainBounds) override {
    if (!fVertexBuffer) {
        return;
    }

    const VertexSpec vertexSpec = this->vertexSpec();

    if (vertexSpec.needsIndexBuffer() && !fIndexBuffer) {
        return;
    }

    if (!fProgramInfo) {
        this->createProgramInfo(flushState);
    }

    const int totalNumVertices = fQuads.count() * vertexSpec.verticesPerQuad();

    flushState->bindPipelineAndScissorClip(*fProgramInfo, chainBounds);
    flushState->bindBuffers(std::move(fIndexBuffer), nullptr, std::move(fVertexBuffer));
    flushState->bindTextures(fProgramInfo->geomProc(), nullptr, fProgramInfo->pipeline());
    QuadPerEdgeAA::IssueDraw(flushState->caps(), flushState->opsRenderPass(),
                             vertexSpec, 0, fQuads.count(), totalNumVertices, fBaseVertex);
}
```

步骤：
1. 验证缓冲区存在
2. 按需创建程序信息
3. 绑定管线、裁剪、缓冲区、纹理
4. 发出绘制调用（实例化或索引绘制）

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrMeshDrawOp` | 基类 |
| `GrSimpleMeshDrawOpHelperWithStencil` | 操作辅助类，包含模板支持 |
| `QuadPerEdgeAA` | 几何处理器和网格化逻辑 |
| `GrQuadBuffer` | 四边形缓冲区 |
| `GrQuad` | 四边形表示 |
| `GrQuadUtils` | 四边形工具（裁剪、AA 解析等） |
| `GrPaint` | 绘制属性 |
| `GrOpFlushState` | 刷新状态 |
| `GrMeshDrawTarget` | 网格绘制目标 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| `SurfaceDrawContext` | 调用 `FillRectOp::Make` 创建操作 |
| `SkCanvas` | 通过 `drawRect` 间接创建 `FillRectOp` |
| `GrOpsTask` | 管理和调度 `FillRectOp` |
| 各种高层 API | 矩形是最基础的图元，被广泛使用 |

## 设计模式与设计决策

### 工厂类模式

`FillRectOp` 不是可实例化的类，而是工厂方法的集合：
- 隐藏实现细节（`FillRectOpImpl` 在匿名命名空间中）
- 提供多种便捷构造方式
- 统一接口风格

### 批处理优化

支持三种批处理方式：
1. **操作合并**：通过 `onCombineIfPossible()` 自动合并兼容操作
2. **直接添加**：通过 `addQuad()` 向现有操作添加四边形
3. **批量 API**：通过 `AddFillRectOps()` 一次性处理多个四边形

### 颜色类型优化

动态选择颜色表示：
- **ColorType::kNone**：所有颜色为白色或常量，着色器中省略颜色乘法
- **ColorType::kByte**：颜色可用 8 位表示
- **ColorType::kFloat**：需要完整 32 位浮点颜色

减少顶点数据大小和着色器复杂度。

### AA 类型升级

允许混合非 AA 和 Coverage AA 操作：
```cpp
if (upgradeToCoverageAAOnMerge) {
    fHelper.setAAType(GrAAType::kCoverage);
}
```

优势：
- 增加合并机会
- 简化管线状态
- Coverage AA 可以正确处理非 AA 边缘（通过设置 `GrQuadAAFlags::kNone`）

### 透视处理

通过 `GrQuadUtils::ClipToW0()` 处理透视投影：
- 裁剪跨越 W=0 平面的四边形
- 可能生成 1 或 2 个输出四边形
- 确保所有顶点 W>0（避免除零和反向投影）

### 索引缓冲区管理

使用 `QuadPerEdgeAA::GetIndexBuffer()` 获取共享索引缓冲区：
- 根据 AA 类型和四边形数量选择合适的索引模式
- 全局缓存和重用
- 自动处理容量限制

### 预准备双路径

支持两种准备路径：
- **DDL 路径**：录制时网格化，存储在录制时 arena
- **常规路径**：刷新时网格化，直接写入 GPU 缓冲区

灵活支持不同使用场景。

### 模板测试支持

通过 `GrUserStencilSettings` 参数支持模板测试：
- 用于裁剪
- 用于绘制效果（如文本渲染）
- 通过 `GrSimpleMeshDrawOpHelperWithStencil` 集成

## 性能考量

### 操作合并

通过合并多个矩形到单个操作：
- 减少操作数量和管理开销
- 减少绘制调用（单次绘制多个四边形）
- 减少状态切换

典型场景：UI 中的多个按钮、卡片等。

### 共享索引缓冲区

四边形索引模式是固定的：
```
[0, 1, 2, 2, 1, 3]  // 每个四边形
```

通过模式重复和全局缓存：
- 避免重复创建索引缓冲区
- 减少 GPU 内存占用
- 提高缓存命中率

### 颜色优化

最小化颜色表示：
- `ColorType::kNone`：0 字节/顶点（常量颜色）
- `ColorType::kByte`：4 字节/顶点（RGBA8）
- `ColorType::kFloat`：16 字节/顶点（RGBA32F）

对于大量白色或单色矩形，节省显著。

### 顶点规格缓存

`vertexSpec()` 结果在多处复用：
- 一次计算，多次使用
- 包含顶点布局所有信息
- 驱动几何处理器选择

### 预准备优化

DDL 场景中预准备顶点数据：
- 将网格化工作移到录制线程
- 刷新时只需拷贝数据
- 并行化 CPU 工作

### AA 类型解析

`GrQuadUtils::ResolveAAType()` 统一 AA 类型和边缘标志：
- 避免不一致状态
- 简化后续逻辑
- 提前检测细线情况

### 容量溢出保护

`CombinedQuadCountWillOverflow()` 和 `canAddQuads()` 确保不超过限制：
- 索引缓冲区有最大容量
- AA 和非 AA 有不同限制
- 提前拒绝过大的合并

### 批量 API 效率

`AddFillRectOps()` 自动处理容量限制：
```cpp
while (numLeft) {
    int numConsumed = 0;
    GrOp::Owner op = MakeOp(context, GrPaint::Clone(paint), aaType, viewMatrix,
                            &quads[offset], numLeft, stencilSettings, &numConsumed);
    offset += numConsumed;
    numLeft -= numConsumed;
    sdc->addDrawOp(clip, std::move(op));
}
```

每个操作消耗尽可能多的四边形，创建最少的操作数。

### 平凡/不平凡优化

`fHelper.isTrivial()` 标记纯色绘制：
- 跳过局部坐标存储和处理
- 简化着色器（无纹理采样）
- 减少顶点数据

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/ops/GrMeshDrawOp.h` | 继承 | 网格绘制操作基类 |
| `src/gpu/ganesh/ops/GrSimpleMeshDrawOpHelperWithStencil.h` | 使用 | 操作辅助类，包含模板 |
| `src/gpu/ganesh/ops/QuadPerEdgeAA.h` | 使用 | 四边形几何处理器和工具 |
| `src/gpu/ganesh/geometry/GrQuad.h` | 依赖 | 四边形表示 |
| `src/gpu/ganesh/geometry/GrQuadBuffer.h` | 依赖 | 四边形缓冲区 |
| `src/gpu/ganesh/geometry/GrQuadUtils.h` | 依赖 | 四边形工具函数 |
| `src/gpu/ganesh/SurfaceDrawContext.h` | 被使用 | 绘制上下文 |
| `src/gpu/ganesh/GrOpFlushState.h` | 依赖 | 刷新状态 |
| `src/gpu/ganesh/ops/FillRRectOp.h` | 相关 | 圆角矩形填充 |
| `src/gpu/ganesh/ops/TextureOp.h` | 相关 | 纹理绘制（也使用四边形） |
