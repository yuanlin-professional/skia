# sksg - 场景图 (Scene Graph) 库

## 概述

SkSG (Skia Scene Graph) 是 Skia 图形库中的场景图模块,提供了一个轻量级、高效的保留模式 (Retained Mode) 渲染框架。与 Skia 核心的即时模式 (Immediate Mode) 绘制接口不同,SkSG 允许构建一棵持久化的渲染节点树,并通过失效/重验证 (Invalidation/Revalidation) 机制实现高效的增量更新。

SkSG 的设计遵循经典的场景图模式:节点组成有向无环图 (DAG),每个节点负责一个特定的渲染职责。渲染树从根节点开始,递归遍历所有子节点来完成绘制。当节点的属性发生变化时,它会标记自身为"失效"状态,并在下次 `revalidate()` 调用时重新计算边界和缓存。

该模块是 Skottie (Lottie 动画播放器) 的底层渲染基础设施。Skottie 将 Lottie JSON 转换为 SkSG 场景图,然后通过修改节点属性来驱动动画。然而,SkSG 本身是通用的,可以独立于 Skottie 使用,用于构建任何需要保留模式渲染的应用。

SkSG 的节点层次结构清晰分明:最底层是 `Node` 基类,处理失效传播和边界追踪;`RenderNode` 扩展了渲染能力;`GeometryNode` 和 `PaintNode` 分别代表"画什么"和"用什么画";`Draw` 节点将两者组合;`EffectNode` 及其派生类在渲染管线中插入变换、裁剪、遮罩、不透明度、滤镜等效果。

SkSG 还提供了 `Scene` 类作为高层入口,以及 `InvalidationController` 用于跟踪脏区域,支持局部重绘优化。

## 架构图

```
+------------------------------------------------------------------+
|                        Scene (高层入口)                            |
|   render(canvas) / revalidate(ic) / nodeAt(point)                |
+------------------------------------------------------------------+
                            |
                            v
+------------------------------------------------------------------+
|                     RenderNode 渲染树                              |
|                                                                  |
|   Group ──────── [child0, child1, ...]                           |
|     |                                                            |
|     +── TransformEffect ── [Transform] ── child                 |
|     |     |                                                      |
|     |     +── OpacityEffect ── child                             |
|     |     |     |                                                |
|     |     |     +── ClipEffect ── [GeometryNode] ── child       |
|     |     |     |                                                |
|     |     |     +── MaskEffect ── [mask_node] ── child          |
|     |     |     |                                                |
|     |     |     +── ColorFilter ── child                         |
|     |     |     |                                                |
|     |     |     +── ImageFilterEffect ── [ImageFilter] ── child |
|     |     |     |                                                |
|     |     |     +── ShaderEffect ── [Shader] ── child           |
|     |     |                                                      |
|     |     +── Draw ── [GeometryNode] + [PaintNode]              |
|     |                                                            |
|     +── ... (更多子节点)                                         |
|                                                                  |
+------------------------------------------------------------------+

+------------------------------------------------------------------+
|                    节点类型层次结构                                 |
|                                                                  |
|   Node (基类)                                                    |
|     ├── RenderNode (可渲染)                                      |
|     │     ├── Group (多子节点容器)                                |
|     │     ├── Draw (几何体+画笔 绘制)                            |
|     │     ├── CustomRenderNode (外部扩展)                        |
|     │     └── EffectNode (单子节点效果)                           |
|     │           ├── TransformEffect                              |
|     │           ├── OpacityEffect                                |
|     │           ├── ClipEffect                                   |
|     │           ├── MaskEffect                                   |
|     │           ├── ColorFilter / ExternalColorFilter            |
|     │           ├── ImageFilterEffect                            |
|     │           ├── ShaderEffect / MaskShaderEffect              |
|     │           ├── BlenderEffect                                |
|     │           └── LayerEffect                                  |
|     ├── GeometryNode (几何体)                                    |
|     │     ├── Path                                               |
|     │     ├── Rect / RRect                                       |
|     │     ├── Plane                                              |
|     │     ├── Text                                               |
|     │     ├── Merge (路径布尔运算)                                |
|     │     └── GeometryEffect (几何效果)                          |
|     │           ├── TrimEffect                                   |
|     │           ├── RoundEffect                                  |
|     │           ├── OffsetEffect                                 |
|     │           ├── DashEffect                                   |
|     │           ├── GeometryTransform                            |
|     │           └── FillTypeOverride                             |
|     ├── PaintNode (画笔)                                        |
|     │     ├── Color                                              |
|     │     └── ShaderPaint                                        |
|     ├── Transform (变换)                                         |
|     │     ├── Matrix<SkMatrix>                                   |
|     │     ├── Matrix<SkM44>                                      |
|     │     └── (Concat / Inverse 通过工厂方法创建)                 |
|     ├── Shader (着色器)                                          |
|     │     └── Gradient                                           |
|     │           ├── LinearGradient                               |
|     │           └── RadialGradient                               |
|     └── ImageFilter (图像滤镜)                                   |
|           ├── DropShadowImageFilter                              |
|           ├── BlurImageFilter                                    |
|           └── ExternalImageFilter                                |
|                                                                  |
+------------------------------------------------------------------+
```

## 目录结构

```
modules/sksg/
├── BUILD.gn                 # GN 构建配置
├── BUILD.bazel              # Bazel 构建配置
├── sksg.gni                 # GN 导入配置
├── include/                 # 公开头文件
│   ├── BUILD.bazel
│   ├── SkSGNode.h           # Node 基类, SG_ATTRIBUTE 宏
│   ├── SkSGRenderNode.h     # RenderNode, RenderContext, CustomRenderNode
│   ├── SkSGGroup.h          # Group 容器节点
│   ├── SkSGDraw.h           # Draw 绘制节点
│   ├── SkSGEffectNode.h     # EffectNode 效果基类
│   ├── SkSGGeometryNode.h   # GeometryNode 几何体基类
│   ├── SkSGGeometryEffect.h # TrimEffect, RoundEffect, OffsetEffect, DashEffect 等
│   ├── SkSGPath.h           # Path 路径节点
│   ├── SkSGRect.h           # Rect, RRect 矩形节点
│   ├── SkSGPlane.h          # Plane 无限平面节点
│   ├── SkSGMerge.h          # Merge 路径合并节点
│   ├── SkSGImage.h          # Image 图像节点
│   ├── SkSGText.h           # Text 文本节点
│   ├── SkSGPaint.h          # PaintNode, Color, ShaderPaint
│   ├── SkSGGradient.h       # Gradient, LinearGradient, RadialGradient
│   ├── SkSGTransform.h      # Transform, Matrix<T>, TransformEffect
│   ├── SkSGOpacityEffect.h  # OpacityEffect
│   ├── SkSGClipEffect.h     # ClipEffect
│   ├── SkSGMaskEffect.h     # MaskEffect
│   ├── SkSGColorFilter.h    # ColorFilter, ExternalColorFilter, ModeColorFilter, GradientColorFilter
│   ├── SkSGRenderEffect.h   # Shader, ShaderEffect, MaskShaderEffect, ImageFilter, ImageFilterEffect, BlenderEffect, LayerEffect
│   ├── SkSGScene.h          # Scene 高层入口
│   └── SkSGInvalidationController.h  # InvalidationController 脏区域追踪
├── src/                     # 实现文件
│   ├── BUILD.bazel
│   ├── SkSGNode.cpp         # Node 基类实现
│   ├── SkSGNodePriv.h       # NodePriv 内部访问辅助
│   ├── SkSGRenderNode.cpp   # RenderNode, RenderContext, ScopedRenderContext
│   ├── SkSGGroup.cpp        # Group 实现
│   ├── SkSGDraw.cpp         # Draw 实现
│   ├── SkSGEffectNode.cpp   # EffectNode 实现
│   ├── SkSGGeometryNode.cpp # GeometryNode 实现
│   ├── SkSGGeometryEffect.cpp # 几何效果实现
│   ├── SkSGPath.cpp         # Path 实现
│   ├── SkSGRect.cpp         # Rect, RRect 实现
│   ├── SkSGPlane.cpp        # Plane 实现
│   ├── SkSGMerge.cpp        # Merge 实现
│   ├── SkSGImage.cpp        # Image 实现
│   ├── SkSGText.cpp         # Text 实现
│   ├── SkSGPaint.cpp        # PaintNode, Color, ShaderPaint 实现
│   ├── SkSGGradient.cpp     # Gradient 实现
│   ├── SkSGTransform.cpp    # Transform, TransformEffect 实现
│   ├── SkSGTransformPriv.h  # TransformPriv 内部访问
│   ├── SkSGOpacityEffect.cpp # OpacityEffect 实现
│   ├── SkSGClipEffect.cpp   # ClipEffect 实现
│   ├── SkSGMaskEffect.cpp   # MaskEffect 实现
│   ├── SkSGColorFilter.cpp  # ColorFilter 实现
│   ├── SkSGRenderEffect.cpp # ShaderEffect, ImageFilterEffect 等实现
│   ├── SkSGScene.cpp        # Scene 实现
│   └── SkSGInvalidationController.cpp # InvalidationController 实现
├── tests/                   # 测试
│   ├── BUILD.bazel
│   └── SGTest.cpp           # 场景图单元测试
└── slides/                  # 演示幻灯片
    ├── BUILD.bazel
    └── SVGPongSlide.cpp     # SVG Pong 游戏演示
```

## 关键类与函数

### Node - 场景图节点基类 (SkSGNode.h)

所有场景图节点的基类,管理失效传播和边界计算:

```cpp
class Node : public SkRefCnt {
    // 重验证: 遍历 DAG, 返回边界矩形
    const SkRect& revalidate(InvalidationController*, const SkMatrix&);

    // 标记失效 (可选触发损伤)
    void invalidate(bool damage = true);

protected:
    // 派生类实现: 重新计算本地边界
    virtual SkRect onRevalidate(InvalidationController*, const SkMatrix& ctm) = 0;

    // 注册/注销失效观察者 (实现 DAG 父子关联)
    void observeInval(const sk_sp<Node>&);
    void unobserveInval(const sk_sp<Node>&);
};
```

**SG_ATTRIBUTE 宏** - 属性声明辅助:
```cpp
#define SG_ATTRIBUTE(attr_name, attr_type, attr_container)
    const attr_type& get##attr_name() const;
    void set##attr_name(const attr_type& v);  // 值变更时自动 invalidate()
```

### RenderNode - 可渲染节点 (SkSGRenderNode.h)

```cpp
class RenderNode : public Node {
    // 渲染到画布
    void render(SkCanvas*, const RenderContext* = nullptr) const;

    // 命中测试
    const RenderNode* nodeAt(const SkPoint& point) const;

    // 可见性控制
    bool isVisible() const;
    void setVisible(bool);

protected:
    virtual void onRender(SkCanvas*, const RenderContext*) const = 0;
    virtual const RenderNode* onNodeAt(const SkPoint&) const = 0;

    // 渲染上下文: 累积的绘制属性覆盖
    struct RenderContext {
        sk_sp<SkColorFilter> fColorFilter;
        sk_sp<SkShader>      fShader;
        sk_sp<SkShader>      fMaskShader;
        sk_sp<SkBlender>     fBlender;
        float                fOpacity = 1;

        bool requiresIsolation() const;
        void modulatePaint(ctm, paint, is_layer_paint) const;
    };

    // 作用域渲染上下文: 管理图层保存/恢复
    class ScopedRenderContext {
        ScopedRenderContext&& modulateOpacity(float);
        ScopedRenderContext&& modulateColorFilter(sk_sp<SkColorFilter>);
        ScopedRenderContext&& modulateShader(sk_sp<SkShader>, const SkMatrix&);
        ScopedRenderContext&& modulateMaskShader(sk_sp<SkShader>, const SkMatrix&);
        ScopedRenderContext&& modulateBlender(sk_sp<SkBlender>);
        ScopedRenderContext&& setIsolation(bounds, ctm, do_isolate);
        ScopedRenderContext&& setFilterIsolation(bounds, ctm, filter);
    };
};
```

### CustomRenderNode - 外部扩展节点

```cpp
class CustomRenderNode : public RenderNode {
    const vector<sk_sp<RenderNode>>& children() const;
    bool hasChildrenInval() const;
};
```

### Group - 分组容器 (SkSGGroup.h)

```cpp
class Group : public RenderNode {
    static sk_sp<Group> Make();
    static sk_sp<Group> Make(vector<sk_sp<RenderNode>> children);

    void addChild(sk_sp<RenderNode>);
    void removeChild(const sk_sp<RenderNode>&);
    size_t size() const;
    bool empty() const;
    void clear();
};
```

### Draw - 绘制节点 (SkSGDraw.h)

```cpp
class Draw : public RenderNode {
    static sk_sp<Draw> Make(sk_sp<GeometryNode> geo, sk_sp<PaintNode> paint);
};
```

Draw 是场景图的叶子节点,将几何体和画笔组合进行实际绘制,等价于 `SkCanvas::draw*(geometry, paint)` 调用。

### GeometryNode - 几何体基类 (SkSGGeometryNode.h)

```cpp
class GeometryNode : public Node {
    void clip(SkCanvas*, bool antiAlias) const;
    void draw(SkCanvas*, const SkPaint&) const;
    bool contains(const SkPoint&) const;
    SkPath asPath() const;
};
```

**具体几何体:**
- `Path`: 包装 `SkPath`
- `Rect`: 包装 `SkRect`,支持路径方向和起始点
- `RRect`: 包装 `SkRRect`,支持圆角矩形
- `Plane`: 无限平面 (总是命中)
- `Text`: 文本几何体
- `Merge`: 路径布尔运算 (合并/并集/交集/差集/异或)

### PaintNode - 画笔基类 (SkSGPaint.h)

```cpp
class PaintNode : public Node {
    SkPaint makePaint() const;

    // 属性: AntiAlias, Opacity, BlendMode, StrokeWidth, StrokeMiter,
    //        Style, StrokeJoin, StrokeCap
};
```

**具体画笔:**
- `Color`: 纯色画笔 (`SkColor`)
- `ShaderPaint`: 基于 `Shader` 的画笔

### Transform - 变换节点 (SkSGTransform.h)

```cpp
class Transform : public Node {
    static sk_sp<Transform> MakeConcat(a, b);   // T' = A x B
    static sk_sp<Transform> MakeInverse(t);      // T' = Inv(T)
};

template <typename T>  // T = SkMatrix 或 SkM44
class Matrix : public Transform {
    static sk_sp<Matrix> Make(const T& m);
    SG_ATTRIBUTE(Matrix, T, fMatrix);
};

class TransformEffect : public EffectNode {
    static sk_sp<TransformEffect> Make(child, transform);
    const sk_sp<Transform>& getTransform() const;
};
```

### EffectNode 及派生类

| 效果类 | 头文件 | 说明 |
|--------|--------|------|
| `EffectNode` | SkSGEffectNode.h | 单子节点效果基类 |
| `TransformEffect` | SkSGTransform.h | 变换效果 |
| `OpacityEffect` | SkSGOpacityEffect.h | 不透明度效果 |
| `ClipEffect` | SkSGClipEffect.h | 裁剪效果 (几何体遮罩) |
| `MaskEffect` | SkSGMaskEffect.h | 遮罩效果 (Alpha/Luma, Normal/Invert) |
| `ColorFilter` | SkSGColorFilter.h | 颜色滤镜基类 |
| `ModeColorFilter` | SkSGColorFilter.h | 混合模式颜色滤镜 |
| `GradientColorFilter` | SkSGColorFilter.h | 渐变色调映射 |
| `ExternalColorFilter` | SkSGColorFilter.h | 外部颜色滤镜 |
| `ShaderEffect` | SkSGRenderEffect.h | 着色器效果 |
| `MaskShaderEffect` | SkSGRenderEffect.h | 遮罩着色器效果 |
| `ImageFilterEffect` | SkSGRenderEffect.h | 图像滤镜效果 |
| `BlenderEffect` | SkSGRenderEffect.h | 混合器效果 |
| `LayerEffect` | SkSGRenderEffect.h | 图层效果 |

### GeometryEffect 及派生类 (SkSGGeometryEffect.h)

| 效果类 | 说明 | 关键属性 |
|--------|------|---------|
| `TrimEffect` | 路径裁剪 | Start, Stop, Mode |
| `GeometryTransform` | 几何变换 | Transform |
| `FillTypeOverride` | 填充类型覆盖 | FillType |
| `DashEffect` | 虚线效果 | Intervals, Phase |
| `RoundEffect` | 圆角效果 | Radius |
| `OffsetEffect` | 路径偏移 | Offset, MiterLimit, Join |

### InvalidationController (SkSGInvalidationController.h)

```cpp
class InvalidationController {
    void inval(const SkRect&, const SkMatrix& ctm = SkMatrix::I());
    const SkRect& bounds() const;  // 聚合脏区域
    void reset();
};
```

### Scene (SkSGScene.h)

```cpp
class Scene {
    static unique_ptr<Scene> Make(sk_sp<RenderNode> root);
    void render(SkCanvas*) const;
    void revalidate(InvalidationController* = nullptr);
    const RenderNode* nodeAt(const SkPoint&) const;
};
```

## 依赖关系

```
sksg 模块依赖图:

sksg
  ├── include/core/SkCanvas.h      # 渲染输出
  ├── include/core/SkPaint.h       # 绘制属性
  ├── include/core/SkPath.h        # 路径几何体
  ├── include/core/SkMatrix.h      # 2D 变换
  ├── include/core/SkM44.h         # 3D 变换
  ├── include/core/SkRect.h        # 边界矩形
  ├── include/core/SkRRect.h       # 圆角矩形
  ├── include/core/SkRefCnt.h      # 引用计数
  ├── include/core/SkColor.h       # 颜色值
  ├── include/core/SkShader.h      # 着色器
  ├── include/core/SkColorFilter.h # 颜色滤镜
  ├── include/core/SkImageFilter.h # 图像滤镜
  ├── include/core/SkBlender.h     # 混合器
  ├── include/effects/SkImageFilters.h  # 图像滤镜工厂
  ├── include/effects/SkTrimPathEffect.h # 路径裁剪
  └── include/pathops/              # 路径布尔运算 (Merge)

被依赖:
  └── modules/skottie/             # Lottie 动画播放器
```

## 设计模式分析

### 1. 组合模式 (Composite Pattern)
场景图的核心设计模式。`Group` 包含多个 `RenderNode`,`EffectNode` 包装单个 `RenderNode`,形成树状结构。所有节点共享 `Node` 接口,支持统一的 `revalidate()` 和 `render()` 遍历。

### 2. 装饰器模式 (Decorator Pattern)
`EffectNode` 及其派生类是典型的装饰器:每个效果节点包装一个子渲染节点,在渲染时添加额外的视觉效果(变换、不透明度、裁剪、滤镜等),而不修改被装饰节点的接口。

### 3. 观察者模式 (Observer Pattern)
失效传播机制使用观察者模式:`observeInval()` / `unobserveInval()` 建立父子失效关系。当子节点的属性变化时,`invalidate()` 沿着 DAG 向上传播到所有祖先节点。

### 4. 访问者模式变体 (Visitor Pattern)
`RenderContext` 作为累积状态在渲染遍历中传递。`ScopedRenderContext` 在遍历过程中累积绘制属性覆盖(不透明度、颜色滤镜等),并在需要时创建隔离图层。

### 5. 模板方法模式 (Template Method)
`Node::revalidate()` 是模板方法:它处理失效标志检查和边界更新的通用逻辑,然后调用 `onRevalidate()` 由派生类实现具体的重验证逻辑。同样,`RenderNode::render()` 处理可见性和上下文,调用 `onRender()` 由派生类实现具体渲染。

### 6. 工厂方法 (Factory Method)
大多数节点类使用静态 `Make()` 工厂方法创建实例,隐藏构造函数,确保节点通过 `sk_sp` 智能指针管理。

## 数据流

### 失效传播 (自底向上)

```
节点属性变更 (如 Color::setColor)
    |
    v
node->invalidate(damage=true)
    设置 kInvalidated_Flag
    设置 kDamage_Flag
    |
    v
forEachInvalObserver():
    对每个父节点: parent->invalidate(damage=true)
    |
    v
递归向上传播直到根节点
(所有祖先节点都被标记为 kInvalidated_Flag)
```

### 重验证 (自顶向下)

```
Scene::revalidate(ic) 或 Node::revalidate(ic, ctm)
    |
    v
检查 kInvalidated_Flag: 若未失效,直接返回缓存边界
    |
    v
onRevalidate(ic, ctm):
    |
    +---> [Group] 遍历子节点, 各自 revalidate, 合并边界
    +---> [Draw] geo->revalidate() + paint->revalidate()
    +---> [TransformEffect] child->revalidate(ic, ctm * transform)
    +---> [EffectNode] child->revalidate(ic, ctm)
    +---> [GeometryNode] 重新计算路径边界
    +---> [PaintNode] 重建 SkPaint
    |
    v
fBounds = onRevalidate 返回的边界
清除 kInvalidated_Flag
    |
    v
如果 kDamage_Flag: ic->inval(oldBounds ∪ newBounds, ctm)
    清除 kDamage_Flag
```

### 渲染 (自顶向下)

```
Scene::render(canvas) 或 RenderNode::render(canvas, ctx)
    |
    v
检查可见性: 若不可见,跳过
    |
    v
onRender(canvas, ctx):
    |
    +---> [Group]
    |       若需要隔离: ScopedRenderContext::setIsolation()
    |       遍历子节点: child->render(canvas, ctx)
    |
    +---> [TransformEffect]
    |       canvas->save()
    |       canvas->concat(transform)
    |       child->render(canvas, ctx)
    |       canvas->restore()
    |
    +---> [OpacityEffect]
    |       ScopedRenderContext::modulateOpacity(opacity)
    |       child->render(canvas, newCtx)
    |
    +---> [ClipEffect]
    |       clipNode->clip(canvas, antiAlias)
    |       child->render(canvas, ctx)
    |
    +---> [MaskEffect]
    |       渲染子节点到离屏层
    |       应用遮罩混合
    |
    +---> [Draw]
    |       paint = paintNode->makePaint()
    |       ctx->modulatePaint(ctm, &paint)
    |       geoNode->draw(canvas, paint)
    |
    +---> [ImageFilterEffect]
    |       ScopedRenderContext::setFilterIsolation(bounds, ctm, filter)
    |       child->render(canvas, newCtx)
    |
    +---> [ColorFilter]
    |       ScopedRenderContext::modulateColorFilter(filter)
    |       child->render(canvas, newCtx)
    |
    +---> [ShaderEffect]
            ScopedRenderContext::modulateShader(shader, shaderCTM)
            child->render(canvas, newCtx)
```

## 性能特性

1. **增量更新**: 只有失效的节点才需要重新验证,未变化的子树直接返回缓存结果
2. **脏区域追踪**: `InvalidationController` 记录变化区域,支持局部重绘
3. **延迟隔离**: `RenderContext` 推迟图层创建,只在真正需要时(非原子绘制+需要隔离)才创建离屏图层
4. **段缓存**: DAG 节点内联 observer 存储(单父节点时避免数组分配)
5. **位标志优化**: 使用位域存储节点标志,最小化内存开销

## 相关文档与参考

- **sksg include**: `docs/yuanlin/modules/sksg/include/README.md`
- **sksg src**: `docs/yuanlin/modules/sksg/src/README.md`
- **skottie 模块**: `docs/yuanlin/modules/skottie/README.md` - 主要客户端
- **Skia 核心**: `include/core/` - SkCanvas, SkPaint, SkPath 等
- **Skia 效果**: `include/effects/` - SkImageFilters, SkTrimPathEffect 等
- **场景图理论**: 经典的图形学场景图 (Scene Graph) 设计范式
