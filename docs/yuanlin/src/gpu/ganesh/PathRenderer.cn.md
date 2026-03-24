# PathRenderer

> 源文件
> - `src/gpu/ganesh/PathRenderer.h`
> - `src/gpu/ganesh/PathRenderer.cpp`

## 概述

`PathRenderer` 是 Ganesh GPU 渲染管线中用于将矢量路径光栅化到 GPU 渲染目标的抽象基类。它定义了路径绘制的统一接口,支持多种光栅化策略,包括覆盖率抗锯齿、模板缓冲区操作和特殊的硬件加速路径。

该模块是 Skia GPU 路径渲染系统的核心抽象层,支持通过责任链模式选择最优的渲染器。不同的子类实现针对特定类型的路径(如凸多边形、毛发线、三角化路径、曲面细分路径等)提供专门优化的算法。

## 架构位置

```
Ganesh 路径渲染系统
├── GrDrawOp (绘制操作)
│   └── GrDrawPathOp / GrFillPathOp
│       └── PathRenderer         # 【本模块】路径光栅化抽象基类
│           ├── AAConvexPathRenderer      # 凸路径 AA 渲染
│           ├── AAHairLinePathRenderer    # 毛发线 AA 渲染
│           ├── AALinearizingConvexPathRenderer # 线性化凸路径
│           ├── AtlasPathRenderer         # Atlas 缓存渲染
│           ├── DashLinePathRenderer      # 虚线渲染
│           ├── DefaultPathRenderer       # 默认 fallback 渲染器
│           ├── SmallPathRenderer         # 小路径缓存渲染
│           ├── TessellationPathRenderer  # 硬件曲面细分渲染
│           └── TriangulatingPathRenderer # CPU 三角化渲染
├── PathRendererChain            # 渲染器选择链
└── SurfaceDrawContext           # GPU 绘制上下文
```

`PathRenderer` 位于高层绘制操作与底层 GPU Op 之间,负责将 `SkPath` 转换为可以提交到 GPU 的几何数据和渲染指令。

## 主要类与结构体

### PathRenderer

继承自 `SkRefCnt`,是所有路径渲染器的抽象基类。

**继承关系**
- 基类: `SkRefCnt`
- 子类: 多种专门化的路径渲染器(见架构位置)

**关键常量**

| 常量 | 值 | 说明 |
|------|------|------|
| `kMaxGPUPathRendererVerbs` | `1 << 14` (16384) | GPU 路径渲染器支持的最大顶点数,防止 OOM |

**核心枚举: StencilSupport**

描述渲染器对模板缓冲区操作的支持级别:

| 值 | 说明 |
|----|------|
| `kNoSupport_StencilSupport` | 不支持模板操作 |
| `kStencilOnly_StencilSupport` | 仅支持 `stencilPath()`,不能同时着色和模板 |
| `kNoRestriction_StencilSupport` | 完全支持,可应用任意模板规则并同时着色 |

**核心枚举: CanDrawPath**

表示渲染器绘制路径的能力等级:

| 值 | 说明 |
|----|------|
| `kNo` | 无法绘制此路径 |
| `kAsBackup` | 可作为备用方案(比软件回退好,但不是最优) |
| `kYes` | 最佳选择,可高效绘制 |

### CanDrawPathArgs

传递给 `canDrawPath()` 的参数结构体,描述待绘制路径的完整状态。

**关键字段**

| 字段 | 类型 | 说明 |
|------|------|------|
| `fCaps` | `const GrCaps*` | GPU 能力查询对象 |
| `fProxy` | `const GrRenderTargetProxy*` | 渲染目标代理 |
| `fClipConservativeBounds` | `const SkIRect*` | 裁剪区域的保守边界 |
| `fViewMatrix` | `const SkMatrix*` | 视图变换矩阵 |
| `fShape` | `const GrStyledShape*` | 样式化形状(路径+样式) |
| `fPaint` | `const GrPaint*` | GPU 绘制状态 |
| `fSurfaceProps` | `const SkSurfaceProps*` | 表面属性(像素几何等) |
| `fAAType` | `GrAAType` | 抗锯齿类型(无/MSAA/覆盖率) |
| `fHasUserStencilSettings` | `bool` | 是否有用户自定义模板设置(仅 TessellationPathRenderer 使用) |

### DrawPathArgs

传递给 `drawPath()` 的参数结构体,包含实际绘制所需的完整信息。

**关键字段**

| 字段 | 类型 | 说明 |
|------|------|------|
| `fContext` | `GrRecordingContext*` | 录制上下文 |
| `fPaint` | `GrPaint&&` | GPU 绘制状态(右值引用) |
| `fUserStencilSettings` | `const GrUserStencilSettings*` | 用户模板设置 |
| `fSurfaceDrawContext` | `SurfaceDrawContext*` | 绘制上下文 |
| `fClip` | `const GrClip*` | 裁剪对象 |
| `fClipConservativeBounds` | `const SkIRect*` | 裁剪保守边界 |
| `fViewMatrix` | `const SkMatrix*` | 视图变换矩阵 |
| `fShape` | `const GrStyledShape*` | 样式化形状 |
| `fAAType` | `GrAAType` | 抗锯齿类型 |
| `fGammaCorrect` | `bool` | 是否启用 gamma 校正 |

### StencilPathArgs

传递给 `stencilPath()` 的参数结构体,用于仅模板绘制。

**关键字段**

| 字段 | 类型 | 说明 |
|------|------|------|
| `fContext` | `GrRecordingContext*` | 录制上下文 |
| `fSurfaceDrawContext` | `SurfaceDrawContext*` | 绘制上下文 |
| `fClip` | `const GrHardClip*` | 硬裁剪(不支持软裁剪) |
| `fClipConservativeBounds` | `const SkIRect*` | 裁剪保守边界 |
| `fViewMatrix` | `const SkMatrix*` | 视图变换矩阵 |
| `fShape` | `const GrStyledShape*` | 样式化形状 |
| `fDoStencilMSAA` | `GrAA` | 是否使用 MSAA 模板 |

## 公共 API 函数

### 查询接口

```cpp
// 获取渲染器名称(纯虚函数,子类必须实现)
virtual const char* name() const = 0;

// 查询对特定路径的模板支持级别
StencilSupport getStencilSupport(const GrStyledShape& shape) const;

// 查询是否能绘制路径及优先级
CanDrawPath canDrawPath(const CanDrawPathArgs& args) const;
```

### 绘制接口

```cpp
// 绘制路径到颜色缓冲区(可能同时写入模板)
bool drawPath(const DrawPathArgs& args);

// 仅绘制到模板缓冲区
void stencilPath(const StencilPathArgs& args);
```

### 工具方法

```cpp
// 静态辅助方法:获取路径的设备空间边界
static void GetPathDevBounds(
    const SkPath& path,
    SkISize devSize,
    const SkMatrix& matrix,
    SkRect* bounds
);
```

## 内部实现细节

### 默认 stencilPath 实现

基类提供了 `stencilPath()` 的默认实现(第 85-108 行),通过调用 `drawPath()` 实现:

```cpp
void PathRenderer::onStencilPath(const StencilPathArgs& args) {
    // 静态常量模板设置:始终写入 0xffff
    static constexpr GrUserStencilSettings kIncrementStencil(
        GrUserStencilSettings::StaticInit<
                0xffff,                         // 模板掩码
                GrUserStencilTest::kAlways,     // 总是通过测试
                0xffff,                         // 写入掩码
                GrUserStencilOp::kReplace,      // 通过时写入参考值
                GrUserStencilOp::kReplace,      // 失败时也写入
                0xffff>()                       // 参考值
    );

    GrPaint paint;  // 空 paint,不写入颜色
    DrawPathArgs drawArgs{
        args.fContext,
        std::move(paint),
        &kIncrementStencil,
        args.fSurfaceDrawContext,
        nullptr,  // 无 clip(已由 fClipConservativeBounds 表示)
        args.fClipConservativeBounds,
        args.fViewMatrix,
        args.fShape,
        (GrAA::kYes == args.fDoStencilMSAA) ? GrAAType::kMSAA : GrAAType::kNone,
        false  // gammaCorrect
    };
    this->drawPath(drawArgs);
}
```

这允许仅支持 `onDrawPath()` 的子类自动获得模板功能。

### 路径边界计算

`GetPathDevBounds()` 处理反向填充路径的特殊情况(第 73-83 行):

```cpp
void PathRenderer::GetPathDevBounds(const SkPath& path,
                                    SkISize devSize,
                                    const SkMatrix& matrix,
                                    SkRect* bounds) {
    if (path.isInverseFillType()) {
        // 反向填充:边界为整个设备
        *bounds = SkRect::Make(devSize);
        return;
    }
    // 正常路径:变换后的边界
    *bounds = path.getBounds();
    matrix.mapRect(bounds);
}
```

反向填充路径绘制路径外部的区域,因此边界等于整个渲染目标。

### drawPath 调试验证

在 Debug 模式下,`drawPath()` 执行广泛的验证(第 48-71 行):

```cpp
bool PathRenderer::drawPath(const DrawPathArgs& args) {
#ifdef SK_DEBUG
    args.validate();

    // 构造 CanDrawPathArgs 进行能力检查
    CanDrawPathArgs canArgs;
    canArgs.fCaps = args.fContext->priv().caps();
    canArgs.fProxy = args.fSurfaceDrawContext->asRenderTargetProxy();
    // ... 填充其他字段
    canArgs.validate();

    canArgs.fHasUserStencilSettings = !args.fUserStencilSettings->isUnused();

    // 断言:必须能绘制此路径
    SkASSERT(CanDrawPath::kNo != this->canDrawPath(canArgs));

    // 如果使用自定义模板设置,必须支持无限制模板
    if (!args.fUserStencilSettings->isUnused()) {
        SkPath path = args.fShape->asPath();
        SkASSERT(args.fShape->style().isSimpleFill());
        SkASSERT(kNoRestriction_StencilSupport == this->getStencilSupport(*args.fShape));
    }
#endif
    return this->onDrawPath(args);
}
```

### StencilPathArgs 验证

仅模板绘制有更严格的约束(第 26-37 行):

```cpp
#ifdef SK_DEBUG
void PathRenderer::StencilPathArgs::validate() const {
    SkASSERT(fContext);
    SkASSERT(fSurfaceDrawContext);
    SkASSERT(fClipConservativeBounds);
    SkASSERT(fViewMatrix);
    SkASSERT(fShape);
    SkASSERT(fShape->style().isSimpleFill());  // 必须是简单填充
    SkPath path = fShape->asPath();
    SkASSERT(!path.isInverseFillType());       // 不支持反向填充
}
#endif
```

### 模板支持查询

`getStencilSupport()` 委托给虚函数 `onGetStencilSupport()`(第 41-46 行):

```cpp
PathRenderer::StencilSupport PathRenderer::getStencilSupport(const GrStyledShape& shape) const {
    SkDEBUGCODE(SkPath path = shape.asPath();)
    SkASSERT(shape.style().isSimpleFill());  // 仅简单填充查询模板支持
    SkASSERT(!path.isInverseFillType());     // 不支持反向填充
    return this->onGetStencilSupport(shape);
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkRefCnt` | 引用计数基类 |
| `SkPath` | Skia 路径对象 |
| `SkMatrix` | 变换矩阵 |
| `GrStyledShape` | 样式化形状(路径+样式+容差) |
| `GrPaint` | GPU 绘制状态 |
| `GrCaps` | GPU 能力查询 |
| `GrClip` / `GrHardClip` | 裁剪对象 |
| `GrRecordingContext` | GPU 录制上下文 |
| `SurfaceDrawContext` | GPU 绘制上下文 |
| `GrRenderTargetProxy` | 渲染目标代理 |
| `GrUserStencilSettings` | 用户模板设置 |
| `GrAAType` / `GrAA` | 抗锯齿类型枚举 |
| `SkSurfaceProps` | 表面属性 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|----------|
| `PathRendererChain` | 管理 `PathRenderer` 实例链,选择最优渲染器 |
| `GrDrawPathOp` | 创建并调用 `PathRenderer::drawPath()` |
| `GrStencilAndCoverPathRenderer` | 继承并实现特定渲染策略 |
| `AAConvexPathRenderer` | 凸路径抗锯齿渲染器 |
| `AAHairLinePathRenderer` | 毛发线抗锯齿渲染器 |
| `TessellationPathRenderer` | 硬件曲面细分渲染器 |
| `DefaultPathRenderer` | 默认 fallback 渲染器 |
| `SurfaceDrawContext` | 调用渲染器绘制路径 |

## 设计模式与设计决策

### 1. 模板方法模式

`PathRenderer` 定义绘制流程框架,子类实现具体步骤:
- **模板方法**: `drawPath()`, `stencilPath()`, `getStencilSupport()`, `canDrawPath()`
- **Hook 方法**: `onDrawPath()`, `onStencilPath()`, `onGetStencilSupport()`, `onCanDrawPath()`

### 2. 策略模式

不同的 `PathRenderer` 子类实现不同的光栅化策略:
- **上下文**: `PathRendererChain`
- **策略**: 各种 `PathRenderer` 子类
- **运行时选择**: 根据路径特性和 GPU 能力选择

### 3. 责任链模式

`PathRendererChain` 维护渲染器链表,依次查询是否能处理:
- 每个渲染器返回 `CanDrawPath` 枚举值
- `kYes`: 立即使用
- `kAsBackup`: 记录但继续搜索
- `kNo`: 跳过,尝试下一个

### 4. NVI (Non-Virtual Interface) 模式

公共接口为非虚函数,调用私有虚函数:
```cpp
// 公共接口:执行验证和通用逻辑
bool drawPath(const DrawPathArgs& args) {
    SkDEBUGCODE(args.validate();)
    // ... 其他检查
    return this->onDrawPath(args);  // 调用私有虚函数
}

// 私有虚函数:子类实现
virtual bool onDrawPath(const DrawPathArgs& args) = 0;
```

**优势**:
- 确保验证逻辑始终执行
- 子类只需关注核心逻辑
- 便于添加调试代码和日志

### 5. 参数对象模式

使用结构体封装复杂参数:
- `CanDrawPathArgs`: 8 个字段
- `DrawPathArgs`: 11 个字段
- `StencilPathArgs`: 7 个字段

**优势**:
- 避免长参数列表
- 便于扩展(添加新字段无需修改函数签名)
- 提高可读性(字段有明确命名)

### 6. 默认实现模式

基类提供合理的默认实现:
- `onGetStencilSupport()`: 默认返回 `kNoRestriction_StencilSupport`
- `onStencilPath()`: 默认通过 `onDrawPath()` 实现

子类仅在需要时覆盖。

### 7. 防御性编程

通过 `SkDEBUGCODE` 和 `SkASSERT` 进行广泛验证:
- 仅在 Debug 模式下执行
- Release 模式零开销
- 快速发现不正确的使用

## 性能考量

### 1. 复杂度限制

`kMaxGPUPathRendererVerbs` 限制最大顶点数:
- 防止过于复杂的路径导致 GPU OOM
- 三角化和曲面细分渲染器使用此限制
- 超出限制的路径回退到软件渲染

### 2. 提前退出优化

`canDrawPath()` 返回 `CanDrawPath::kNo` 时立即跳过:
- 避免不必要的资源分配
- 加速渲染器选择过程

### 3. 模板操作优化

使用 `GrUserStencilOp::kReplace` 而非 `kIncr`:
- 避免读-改-写操作
- 直接写入参考值更快
- 适用于简单填充规则

### 4. 静态配置复用

`onStencilPath()` 中的模板设置为静态常量:
```cpp
static constexpr GrUserStencilSettings kIncrementStencil(...);
```
- 编译期初始化
- 多次调用共享同一对象
- 无运行时构造开销

### 5. 右值引用避免拷贝

`DrawPathArgs::fPaint` 使用 `GrPaint&&`:
- 避免昂贵的 `GrPaint` 拷贝
- 所有权转移到渲染器或 Op

### 6. 引用计数管理

继承 `SkRefCnt`:
- 自动生命周期管理
- 避免手动 delete
- 支持智能指针 `sk_sp<PathRenderer>`

### 7. 内联候选

简单的包装方法可被编译器内联:
```cpp
StencilSupport getStencilSupport(const GrStyledShape& shape) const {
    return this->onGetStencilSupport(shape);
}
```

### 8. 条件验证

调试验证仅在 Debug 构建中启用:
```cpp
#ifdef SK_DEBUG
    args.validate();
    // ... 大量断言
#endif
```

Release 构建中这些代码被完全移除。

## 相关文件

| 文件路径 | 关系说明 |
|----------|----------|
| `src/gpu/ganesh/PathRendererChain.h` | 管理渲染器链,实现选择逻辑 |
| `src/gpu/ganesh/ops/AAConvexPathRenderer.h` | 凸路径 AA 渲染实现 |
| `src/gpu/ganesh/ops/AAHairLinePathRenderer.h` | 毛发线 AA 渲染实现 |
| `src/gpu/ganesh/ops/AALinearizingConvexPathRenderer.h` | 线性化凸路径渲染 |
| `src/gpu/ganesh/ops/AtlasPathRenderer.h` | Atlas 缓存渲染实现 |
| `src/gpu/ganesh/ops/DashLinePathRenderer.h` | 虚线渲染实现 |
| `src/gpu/ganesh/ops/DefaultPathRenderer.h` | 默认 fallback 实现 |
| `src/gpu/ganesh/ops/SmallPathRenderer.h` | 小路径缓存实现 |
| `src/gpu/ganesh/ops/TessellationPathRenderer.h` | 硬件曲面细分实现 |
| `src/gpu/ganesh/ops/TriangulatingPathRenderer.h` | CPU 三角化实现 |
| `src/gpu/ganesh/SurfaceDrawContext.h` | 绘制上下文,调用渲染器 |
| `src/gpu/ganesh/GrPaint.h` | GPU 绘制状态 |
| `src/gpu/ganesh/geometry/GrStyledShape.h` | 样式化形状 |
| `src/gpu/ganesh/GrUserStencilSettings.h` | 模板设置定义 |
| `include/core/SkPath.h` | Skia 路径类 |
| `include/core/SkRefCnt.h` | 引用计数基类 |
| `include/private/gpu/ganesh/GrTypesPriv.h` | Ganesh 内部类型 |
