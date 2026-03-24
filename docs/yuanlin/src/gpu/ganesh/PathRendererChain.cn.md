# PathRendererChain

> 源文件
> - `src/gpu/ganesh/PathRendererChain.h`
> - `src/gpu/ganesh/PathRendererChain.cpp`

## 概述

`PathRendererChain` 是 Ganesh GPU 渲染管线中负责选择和管理路径渲染器的核心调度类。它维护一个有序的 `PathRenderer` 实例链表,在需要绘制路径时按优先级顺序查询每个渲染器,选择最适合当前路径和绘制上下文的渲染策略。

该模块实现了责任链模式,将路径渲染请求沿着渲染器链传递,直到找到能够高效处理的渲染器。它是 Skia GPU 路径渲染系统的智能调度中心,确保每种类型的路径都能使用最优化的光栅化算法。

## 架构位置

```
Ganesh 路径渲染系统
├── SurfaceDrawContext          # GPU 绘制上下文
│   └── drawPath() / stencilPath()
│       └── PathRendererChain   # 【本模块】渲染器选择器
│           ├── DashLinePathRenderer         # 虚线渲染器
│           ├── AAConvexPathRenderer         # 凸路径 AA 渲染器
│           ├── AAHairLinePathRenderer       # 毛发线 AA 渲染器
│           ├── AALinearizingConvexPathRenderer # 线性化凸路径渲染器
│           ├── AtlasPathRenderer            # Atlas 缓存渲染器
│           ├── SmallPathRenderer            # 小路径缓存渲染器
│           ├── TriangulatingPathRenderer    # CPU 三角化渲染器
│           ├── TessellationPathRenderer     # 硬件曲面细分渲染器
│           └── DefaultPathRenderer          # 默认 fallback 渲染器
└── GrRecordingContext          # GPU 录制上下文(持有 chain 实例)
```

`PathRendererChain` 位于绘制上下文和具体渲染器之间,作为统一的入口点和决策引擎。

## 主要类与结构体

### PathRendererChain

继承自 `SkNoncopyable`,管理路径渲染器的生命周期和选择逻辑。

**继承关系**
- 基类: `SkNoncopyable`(禁止拷贝和赋值)
- 不可继承(非虚析构函数)

**关键成员变量**

| 成员 | 类型 | 说明 |
|------|------|------|
| `fChain` | `skia_private::STArray<8, sk_sp<PathRenderer>>` | 渲染器链表(预分配 8 个位置) |
| `fAtlasPathRenderer` | `AtlasPathRenderer*` | Atlas 渲染器的直接指针(快速访问) |
| `fTessellationPathRenderer` | `PathRenderer*` | 曲面细分渲染器的直接指针(快速访问) |

### Options

配置结构体,控制渲染器链的构建行为。

**字段说明**

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `fAllowPathMaskCaching` | `bool` | `false` | 是否允许路径掩码缓存 |
| `fGpuPathRenderers` | `GpuPathRenderers` | `GpuPathRenderers::kDefault` | 启用的渲染器集合(位标志) |

`GpuPathRenderers` 枚举(位标志):
- `kDashLine`: 虚线渲染器
- `kAAConvex`: 凸路径 AA 渲染器
- `kAAHairline`: 毛发线 AA 渲染器
- `kAALinearizing`: 线性化凸路径渲染器
- `kAtlas`: Atlas 缓存渲染器
- `kSmall`: 小路径缓存渲染器
- `kTriangulating`: 三角化渲染器
- `kTessellation`: 硬件曲面细分渲染器
- `kDefault`: 包含上述所有渲染器

### DrawType

描述路径的预期用途,影响渲染器选择。

| 值 | 说明 |
|----|------|
| `kColor` | 绘制到颜色缓冲区,无 AA |
| `kStencil` | 仅绘制到模板缓冲区 |
| `kStencilAndColor` | 同时绘制颜色和模板,无 AA |

## 公共 API 函数

### 构造函数

```cpp
PathRendererChain(GrRecordingContext* context, const Options& options);
```

根据配置和 GPU 能力构建渲染器链:
- 按优先级顺序添加渲染器
- 跳过不支持的渲染器
- 始终添加 `DefaultPathRenderer` 作为 fallback

### 渲染器选择

```cpp
PathRenderer* getPathRenderer(
    const PathRenderer::CanDrawPathArgs& args,
    DrawType drawType,
    PathRenderer::StencilSupport* stencilSupport
);
```

核心方法:遍历渲染器链,选择最适合的渲染器。

**返回值**:
- 成功: 返回选中的 `PathRenderer` 指针
- 失败: 返回 `nullptr`(通常不会发生,因为有 `DefaultPathRenderer`)

**参数**:
- `args`: 路径绘制参数(路径、变换、裁剪、AA 类型等)
- `drawType`: 绘制类型(颜色/模板/两者)
- `stencilSupport`: 输出参数,返回选中渲染器的模板支持级别

### 快速访问器

```cpp
// 获取 Atlas 渲染器(如果存在)
AtlasPathRenderer* getAtlasPathRenderer();

// 获取曲面细分渲染器(如果存在)
PathRenderer* getTessellationPathRenderer();
```

这两个渲染器较为特殊,提供直接访问以避免链表遍历。

## 内部实现细节

### 构造函数:渲染器链初始化

完整的初始化流程(第 29-68 行):

```cpp
PathRendererChain::PathRendererChain(GrRecordingContext* context, const Options& options) {
    const GrCaps& caps = *context->priv().caps();

    // 1. 虚线渲染器(优先级最高,专门处理虚线)
    if (options.fGpuPathRenderers & GpuPathRenderers::kDashLine) {
        fChain.push_back(sk_make_sp<ganesh::DashLinePathRenderer>());
    }

    // 2. AA 凸路径渲染器
    if (options.fGpuPathRenderers & GpuPathRenderers::kAAConvex) {
        fChain.push_back(sk_make_sp<AAConvexPathRenderer>());
    }

    // 3. AA 毛发线渲染器
    if (options.fGpuPathRenderers & GpuPathRenderers::kAAHairline) {
        fChain.push_back(sk_make_sp<AAHairLinePathRenderer>());
    }

    // 4. AA 线性化凸路径渲染器
    if (options.fGpuPathRenderers & GpuPathRenderers::kAALinearizing) {
        fChain.push_back(sk_make_sp<AALinearizingConvexPathRenderer>());
    }

    // 5. Atlas 缓存渲染器(需要额外初始化和注册回调)
    if (options.fGpuPathRenderers & GpuPathRenderers::kAtlas) {
        if (auto atlasPathRenderer = AtlasPathRenderer::Make(context)) {
            fAtlasPathRenderer = atlasPathRenderer.get();
            context->priv().addOnFlushCallbackObject(atlasPathRenderer.get());
            fChain.push_back(std::move(atlasPathRenderer));
        }
    }

    // 6. 小路径和三角化渲染器(在优化尺寸构建中禁用)
#if !defined(SK_ENABLE_OPTIMIZE_SIZE)
    if (options.fGpuPathRenderers & GpuPathRenderers::kSmall) {
        fChain.push_back(sk_make_sp<SmallPathRenderer>());
    }
    if (options.fGpuPathRenderers & GpuPathRenderers::kTriangulating) {
        fChain.push_back(sk_make_sp<TriangulatingPathRenderer>());
    }
#endif

    // 7. 硬件曲面细分渲染器(需要检查硬件支持)
    if (options.fGpuPathRenderers & GpuPathRenderers::kTessellation) {
        if (TessellationPathRenderer::IsSupported(caps)) {
            auto tess = sk_make_sp<TessellationPathRenderer>();
            fTessellationPathRenderer = tess.get();
            fChain.push_back(std::move(tess));
        }
    }

    // 8. 默认渲染器(总是添加,作为最后的 fallback)
    fChain.push_back(sk_make_sp<DefaultPathRenderer>());
}
```

**优先级顺序说明**:
1. **专用渲染器优先**(虚线、毛发线):处理特定类型路径最高效
2. **几何优化渲染器**(凸路径、线性化):利用路径的几何特性
3. **缓存渲染器**(Atlas、小路径):复用已光栅化的结果
4. **通用渲染器**(三角化、曲面细分):处理任意复杂路径
5. **默认渲染器**:保证所有路径都能渲染

### 渲染器选择算法

`getPathRenderer()` 的核心逻辑(第 70-117 行):

```cpp
PathRenderer* PathRendererChain::getPathRenderer(
        const PathRenderer::CanDrawPathArgs& args,
        DrawType drawType,
        PathRenderer::StencilSupport* stencilSupport) {

    // 1. 确定所需的最小模板支持级别
    static_assert(PathRenderer::kNoSupport_StencilSupport <
                  PathRenderer::kStencilOnly_StencilSupport);
    static_assert(PathRenderer::kStencilOnly_StencilSupport <
                  PathRenderer::kNoRestriction_StencilSupport);

    PathRenderer::StencilSupport minStencilSupport;
    if (DrawType::kStencil == drawType) {
        minStencilSupport = PathRenderer::kStencilOnly_StencilSupport;
    } else if (DrawType::kStencilAndColor == drawType) {
        minStencilSupport = PathRenderer::kNoRestriction_StencilSupport;
    } else {
        minStencilSupport = PathRenderer::kNoSupport_StencilSupport;
    }

    // 2. 验证路径必须是简单填充(如果需要模板)
    if (minStencilSupport != PathRenderer::kNoSupport_StencilSupport) {
        if (!args.fShape->style().isSimpleFill()) {
            return nullptr;  // 描边路径不支持模板
        }
    }

    // 3. 遍历渲染器链
    PathRenderer* bestPathRenderer = nullptr;
    for (const sk_sp<PathRenderer>& pr : fChain) {
        // 3a. 检查模板支持
        PathRenderer::StencilSupport support = PathRenderer::kNoSupport_StencilSupport;
        if (PathRenderer::kNoSupport_StencilSupport != minStencilSupport) {
            support = pr->getStencilSupport(*args.fShape);
            if (support < minStencilSupport) {
                continue;  // 模板支持不足,跳过
            }
        }

        // 3b. 查询是否能绘制
        PathRenderer::CanDrawPath canDrawPath = pr->canDrawPath(args);
        if (PathRenderer::CanDrawPath::kNo == canDrawPath) {
            continue;  // 无法绘制,跳过
        }

        // 3c. 处理备用渲染器
        if (PathRenderer::CanDrawPath::kAsBackup == canDrawPath && bestPathRenderer) {
            continue;  // 已有备用渲染器,跳过当前备用
        }

        // 3d. 记录结果
        if (stencilSupport) {
            *stencilSupport = support;
        }
        bestPathRenderer = pr.get();

        // 3e. 找到最佳渲染器,提前退出
        if (PathRenderer::CanDrawPath::kYes == canDrawPath) {
            break;
        }
    }

    return bestPathRenderer;
}
```

**选择策略**:
- **模板优先**: 先检查模板支持,不满足直接跳过
- **能力查询**: 调用 `canDrawPath()` 获取优先级
- **备用机制**: 如果遇到 `kAsBackup`,继续搜索,可能找到 `kYes`
- **贪心策略**: 找到 `kYes` 立即返回,不再继续搜索

### 模板支持级别比较

使用静态断言确保枚举值的顺序关系(第 73-76 行):

```cpp
static_assert(PathRenderer::kNoSupport_StencilSupport <
              PathRenderer::kStencilOnly_StencilSupport);
static_assert(PathRenderer::kStencilOnly_StencilSupport <
              PathRenderer::kNoRestriction_StencilSupport);
```

这允许用简单的 `<` 比较判断支持级别是否足够。

### Atlas 渲染器的特殊处理

Atlas 渲染器需要注册为 flush 回调(第 44-47 行):

```cpp
if (auto atlasPathRenderer = AtlasPathRenderer::Make(context)) {
    fAtlasPathRenderer = atlasPathRenderer.get();
    context->priv().addOnFlushCallbackObject(atlasPathRenderer.get());
    fChain.push_back(std::move(atlasPathRenderer));
}
```

**原因**:
- Atlas 缓存需要在 GPU flush 时上传和更新
- 通过回调机制确保 atlas 纹理同步

### 条件编译优化

在优化尺寸的构建中禁用大型渲染器(第 50-57 行):

```cpp
#if !defined(SK_ENABLE_OPTIMIZE_SIZE)
    if (options.fGpuPathRenderers & GpuPathRenderers::kSmall) {
        fChain.push_back(sk_make_sp<SmallPathRenderer>());
    }
    if (options.fGpuPathRenderers & GpuPathRenderers::kTriangulating) {
        fChain.push_back(sk_make_sp<TriangulatingPathRenderer>());
    }
#endif
```

小路径和三角化渲染器代码量较大,在嵌入式设备上可禁用。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `PathRenderer` | 基类和接口定义 |
| `GrRecordingContext` | GPU 录制上下文,查询能力 |
| `GrCaps` | GPU 能力查询 |
| `SkRefCnt` | 智能指针 `sk_sp` 支持 |
| `SkNoncopyable` | 禁止拷贝基类 |
| `SkTArray` | 动态数组容器 |
| `GpuPathRenderers` | 渲染器标志枚举 |
| `DashLinePathRenderer` | 虚线渲染实现 |
| `AAConvexPathRenderer` | 凸路径 AA 渲染实现 |
| `AAHairLinePathRenderer` | 毛发线 AA 渲染实现 |
| `AALinearizingConvexPathRenderer` | 线性化凸路径实现 |
| `AtlasPathRenderer` | Atlas 缓存实现 |
| `SmallPathRenderer` | 小路径缓存实现 |
| `TriangulatingPathRenderer` | 三角化实现 |
| `TessellationPathRenderer` | 曲面细分实现 |
| `DefaultPathRenderer` | 默认实现 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|----------|
| `SurfaceDrawContext` | 调用 `getPathRenderer()` 选择渲染器,然后调用其 `drawPath()` |
| `GrRecordingContextPriv` | 在上下文私有接口中持有 `PathRendererChain` 实例 |
| `GrDrawingManager` | 间接通过 `SurfaceDrawContext` 使用 |
| `GrOpsTask` | 通过 `SurfaceDrawContext` 间接使用 |

## 设计模式与设计决策

### 1. 责任链模式

核心设计模式,将请求沿链传递:
- **处理者**: 各个 `PathRenderer` 实例
- **链管理器**: `PathRendererChain`
- **请求**: `CanDrawPathArgs`
- **响应**: `CanDrawPath` 枚举(kNo/kAsBackup/kYes)

**优势**:
- 松耦合:添加新渲染器无需修改链管理逻辑
- 动态选择:运行时根据路径特性选择最优渲染器
- 可扩展:轻松添加或移除渲染器

### 2. 策略模式

每个 `PathRenderer` 是不同的路径光栅化策略:
- **上下文**: `PathRendererChain`
- **策略接口**: `PathRenderer`
- **具体策略**: 各种渲染器子类

### 3. 工厂模式

构造函数根据配置和能力创建渲染器:
- **产品**: `PathRenderer` 子类实例
- **工厂方法**: 各渲染器的构造函数和 `Make()` 方法
- **配置**: `Options` 结构体

### 4. 单例模式变体

每个 `GrRecordingContext` 持有一个 `PathRendererChain` 实例:
- 非全局单例,但在上下文范围内唯一
- 避免重复构建渲染器链
- 所有绘制操作共享同一链

### 5. 优先级队列模式

链表按优先级排序,高优先级渲染器在前:
- 专用渲染器(虚线、毛发线)
- 几何优化渲染器(凸路径)
- 缓存渲染器(Atlas、小路径)
- 通用渲染器(三角化、曲面细分)
- 默认渲染器(fallback)

### 6. 快速路径优化

提供直接访问器跳过链表遍历:
```cpp
AtlasPathRenderer* getAtlasPathRenderer() { return fAtlasPathRenderer; }
PathRenderer* getTessellationPathRenderer() { return fTessellationPathRenderer; }
```

用于特殊情况下需要显式使用特定渲染器。

### 7. 防御性设计

- 总是添加 `DefaultPathRenderer`,保证有 fallback
- 检查硬件支持后才添加 `TessellationPathRenderer`
- 验证路径类型(简单填充)后才允许模板操作

## 性能考量

### 1. 预分配容器

使用 `STArray<kPreAllocCount, ...>`,预分配 8 个位置:
```cpp
static constexpr size_t kPreAllocCount = 8;
skia_private::STArray<kPreAllocCount, sk_sp<PathRenderer>> fChain;
```

**优势**:
- 避免小数组的堆分配
- 减少内存碎片
- 常见配置(7-8 个渲染器)无需动态扩展

### 2. 提前退出

找到 `CanDrawPath::kYes` 时立即返回:
```cpp
if (PathRenderer::CanDrawPath::kYes == canDrawPath) {
    break;  // 不再继续搜索
}
```

平均情况下只需查询前几个渲染器。

### 3. 智能指针开销最小化

使用 `sk_sp` 管理生命周期:
- 非原子引用计数(单线程使用)
- 轻量级,接近裸指针性能

### 4. 缓存直接指针

存储常用渲染器的裸指针:
```cpp
AtlasPathRenderer* fAtlasPathRenderer = nullptr;
PathRenderer* fTessellationPathRenderer = nullptr;
```

避免链表遍历和智能指针解引用。

### 5. 静态断言

编译期检查枚举值顺序:
```cpp
static_assert(PathRenderer::kNoSupport_StencilSupport <
              PathRenderer::kStencilOnly_StencilSupport);
```

零运行时开销,确保比较逻辑正确。

### 6. 条件编译

根据构建配置排除不需要的渲染器:
```cpp
#if !defined(SK_ENABLE_OPTIMIZE_SIZE)
    // ... 大型渲染器
#endif
```

减小二进制体积,加快链表遍历。

### 7. 移动语义

使用 `std::move` 转移所有权:
```cpp
fChain.push_back(std::move(atlasPathRenderer));
```

避免引用计数的增减操作。

### 8. 局部性优化

渲染器按优先级顺序存储:
- 常用渲染器在数组前端
- 提高缓存命中率
- 减少分支预测失败

## 相关文件

| 文件路径 | 关系说明 |
|----------|----------|
| `src/gpu/ganesh/PathRenderer.h` | 基类定义,提供接口 |
| `src/gpu/ganesh/SurfaceDrawContext.h` | 调用链选择渲染器并绘制 |
| `src/gpu/ganesh/GrRecordingContext.h` | 持有链实例 |
| `src/gpu/ganesh/GrRecordingContextPriv.h` | 私有接口,访问链 |
| `src/gpu/ganesh/GrCaps.h` | GPU 能力查询 |
| `src/gpu/ganesh/GrStyle.h` | 路径样式定义 |
| `src/gpu/ganesh/geometry/GrStyledShape.h` | 样式化形状 |
| `src/gpu/ganesh/ops/AAConvexPathRenderer.h` | 凸路径 AA 渲染器 |
| `src/gpu/ganesh/ops/AAHairLinePathRenderer.h` | 毛发线 AA 渲染器 |
| `src/gpu/ganesh/ops/AALinearizingConvexPathRenderer.h` | 线性化凸路径渲染器 |
| `src/gpu/ganesh/ops/AtlasPathRenderer.h` | Atlas 缓存渲染器 |
| `src/gpu/ganesh/ops/DashLinePathRenderer.h` | 虚线渲染器 |
| `src/gpu/ganesh/ops/DefaultPathRenderer.h` | 默认渲染器 |
| `src/gpu/ganesh/ops/SmallPathRenderer.h` | 小路径缓存渲染器 |
| `src/gpu/ganesh/ops/TessellationPathRenderer.h` | 曲面细分渲染器 |
| `src/gpu/ganesh/ops/TriangulatingPathRenderer.h` | 三角化渲染器 |
| `include/private/base/SkNoncopyable.h` | 禁止拷贝基类 |
| `include/private/base/SkTArray.h` | 动态数组容器 |
| `include/private/gpu/ganesh/GrTypesPriv.h` | 内部类型定义 |
