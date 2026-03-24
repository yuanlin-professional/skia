# sksg/src - 实现文件

## 概述

`src/` 目录包含 SkSG 模块所有节点类型的实现代码。这些实现涵盖了场景图节点的核心机制:失效传播、重验证、渲染和命中测试。每个 `.cpp` 文件与 `include/` 中的对应头文件一一对应。

该目录还包含两个内部头文件 `SkSGNodePriv.h` 和 `SkSGTransformPriv.h`,提供受限的内部访问能力,仅供 Skottie 等核心客户端使用。

## 目录结构

```
src/
├── BUILD.bazel
├── SkSGNode.cpp                # Node 基类: 失效传播, DAG 管理, 重验证框架
├── SkSGNodePriv.h              # NodePriv: 内部访问辅助 (标志位读写)
├── SkSGRenderNode.cpp          # RenderNode: 渲染流程, RenderContext, ScopedRenderContext
├── SkSGGroup.cpp               # Group: 子节点遍历, 隔离判断
├── SkSGDraw.cpp                # Draw: GeometryNode + PaintNode 组合绘制
├── SkSGEffectNode.cpp          # EffectNode: 默认子节点转发
├── SkSGGeometryNode.cpp        # GeometryNode: clip/draw/contains 转发
├── SkSGGeometryEffect.cpp      # 几何效果: Trim/Round/Offset/Dash/Transform/FillType
├── SkSGPath.cpp                # Path: SkPath 包装
├── SkSGRect.cpp                # Rect/RRect: SkRect/SkRRect 包装
├── SkSGPlane.cpp               # Plane: 无限平面
├── SkSGMerge.cpp               # Merge: 路径布尔运算 (SkPathOps)
├── SkSGImage.cpp               # Image: SkImage 渲染
├── SkSGText.cpp                # Text: SkTextBlob 渲染
├── SkSGPaint.cpp               # PaintNode/Color/ShaderPaint: SkPaint 构建
├── SkSGGradient.cpp            # Gradient: 线性/径向渐变着色器
├── SkSGTransform.cpp           # Transform/TransformEffect: 矩阵变换
├── SkSGTransformPriv.h         # TransformPriv: 内部变换访问
├── SkSGOpacityEffect.cpp       # OpacityEffect: 不透明度
├── SkSGClipEffect.cpp          # ClipEffect: 几何裁剪
├── SkSGMaskEffect.cpp          # MaskEffect: Alpha/Luma 遮罩
├── SkSGColorFilter.cpp         # ColorFilter 族: Mode/Gradient/External
├── SkSGRenderEffect.cpp        # Shader/ImageFilter/Blender 族效果
├── SkSGScene.cpp               # Scene: 高层入口封装
└── SkSGInvalidationController.cpp # InvalidationController: 脏区域收集
```

## 关键实现细节

### SkSGNode.cpp - 失效传播核心

Node 基类的实现是 SkSG 最关键的部分。它管理:

1. **观察者存储优化**: 单观察者时内联存储指针,多观察者时使用 `vector<Node*>`。通过 `kObserverArray_Flag` 区分两种模式,避免单父节点场景的堆分配。

2. **失效传播**: `invalidate()` 设置当前节点的 `kInvalidated_Flag` 和 `kDamage_Flag`,然后递归通知所有观察者(父节点)。`kBubbleDamage_Trait` 节点不直接产生损伤,而是将损伤传播到祖先。

3. **重验证**: `revalidate()` 检查失效标志,调用 `onRevalidate()` 获取新边界,更新缓存,并向 `InvalidationController` 报告脏区域。

4. **循环检测**: `kInTraversal_Flag` 在重验证遍历中设置,用于检测 DAG 中的循环。

### SkSGRenderNode.cpp - 渲染上下文

`RenderContext` 累积绘制属性覆盖。核心设计决策:

- **延迟隔离**: 属性覆盖不立即创建图层,而是通过 `RenderContext` 向下传递。只有当非原子绘制(如 Group)需要这些覆盖时,才通过 `ScopedRenderContext::setIsolation()` 创建隔离图层。
- **原子绘制优化**: 如果只有单个 `Draw` 子节点,属性覆盖直接应用到 `SkPaint` 上,避免离屏图层的开销。
- **遮罩着色器**: `fMaskShader` 在图层恢复时应用,而非绘制时。

### SkSGGroup.cpp - 分组容器

Group 的关键逻辑:
- `onRevalidate()`: 遍历子节点重验证,合并边界
- `onRender()`: 判断是否需要隔离 (多子节点 + 非平凡渲染上下文)
- `fRequiresIsolation`: 缓存隔离决策

### SkSGDraw.cpp - 绘制核心

```
onRender(canvas, ctx):
    paint = fPaint->makePaint()
    ctx->modulatePaint(ctm, &paint)
    fGeometry->draw(canvas, paint)
```

### SkSGTransform.cpp - 变换

- `Matrix<SkMatrix>::asMatrix()`: 直接返回 fMatrix
- `Matrix<SkM44>::asMatrix()`: 从 4x4 矩阵提取 3x3
- `TransformEffect::onRender()`: `canvas->save()` + `canvas->concat()` + 子节点渲染 + `canvas->restore()`

### SkSGMerge.cpp - 路径合并

使用 Skia 的 `SkPathOps` 进行路径布尔运算:
- Merge: 简单路径追加
- Union/Intersect/Difference/ReverseDifference/XOR: 通过 `Op()` 函数执行

### SkSGGradient.cpp - 渐变实现

`onRevalidateShader()`:
1. 从 `fColorStops` 提取颜色和位置数组
2. 调用 `LinearGradient::onMakeShader()` 或 `RadialGradient::onMakeShader()`
3. 使用 `SkGradientShader::MakeLinear()` 或 `SkGradientShader::MakeTwoPointConical()`

### SkSGMaskEffect.cpp - 遮罩效果

四种遮罩模式的实现:
- AlphaNormal: 遮罩节点的 Alpha 通道作为不透明度
- AlphaInvert: 反转 Alpha
- LumaNormal: 遮罩节点的亮度作为不透明度
- LumaInvert: 反转亮度

通过渲染遮罩到离屏层,然后使用 `SkBlendMode` 或自定义着色器合成。

### SkSGNodePriv.h / SkSGTransformPriv.h

内部访问辅助类,提供对节点私有成员的受限访问:

```cpp
class NodePriv {
    static uint32_t GetNodeFlags(const Node& node);
    static void SetNodeFlags(Node& node, uint32_t flags);
};

class TransformPriv {
    static bool Is44(const Transform&);
    static SkMatrix AsMatrix(const Transform&);
    static SkM44 AsM44(const Transform&);
};
```

## 依赖关系

```
src/ 内部依赖:
  SkSGNode.cpp       -> (无内部依赖, 纯基类)
  SkSGRenderNode.cpp -> SkSGNodePriv.h
  SkSGGroup.cpp      -> SkSGNodePriv.h
  SkSGDraw.cpp       -> (无额外内部依赖)
  SkSGTransform.cpp  -> SkSGTransformPriv.h
  SkSGMerge.cpp      -> include/pathops/SkPathOps.h
  SkSGColorFilter.cpp -> (SkColorFilter API)
  SkSGRenderEffect.cpp -> (SkImageFilter, SkShader API)

外部依赖:
  ├── include/core/ (SkCanvas, SkPaint, SkPath, SkMatrix, SkM44, etc.)
  ├── include/effects/ (SkImageFilters, SkTrimPathEffect, SkDashPathEffect)
  └── include/pathops/ (SkPathOps - 路径布尔运算)
```

## 设计模式分析

- **内存优化**: Node 使用位域 (`fInvalTraits:2`, `fFlags:4`, `fNodeFlags:8`) 最小化每节点内存。观察者数组仅在需要时分配。
- **虚函数分派**: 所有节点行为 (revalidate/render/clip/draw) 通过虚函数实现,允许类型特化而保持统一接口。
- **RAII**: `ScopedRenderContext` 管理 canvas save/restore 和图层创建,确保异常安全。
- **缓存**: `fBounds` 缓存重验证结果,`fRequiresIsolation` 缓存隔离决策,`KFSegment` 缓存最近搜索段。

## 相关文档与参考

- **sksg 主文档**: `docs/yuanlin/modules/sksg/README.md`
- **sksg 头文件**: `docs/yuanlin/modules/sksg/include/README.md`
- **sksg 测试**: `docs/yuanlin/modules/sksg/tests/README.md`
