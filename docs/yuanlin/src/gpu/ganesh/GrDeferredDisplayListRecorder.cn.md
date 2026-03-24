# GrDeferredDisplayListRecorder

> 源文件
> - src/gpu/ganesh/GrDeferredDisplayListRecorder.cpp

## 概述

`GrDeferredDisplayListRecorder` 是 Skia Ganesh 渲染引擎中用于录制延迟显示列表（Deferred Display List，DDL）的核心类。它允许应用程序在一个线程或上下文中预录制渲染命令，然后在另一个线程或上下文中回放这些命令。这是 Chromium 中实现跨线程渲染的关键技术。

该类基于 `GrSurfaceCharacterization`（表面特征描述）创建一个临时的录制上下文，提供一个 `SkCanvas` 用于录制绘制操作。录制完成后，可以分离出一个不可变的 `GrDeferredDisplayList` 对象，该对象可以安全地传递到其他线程并回放到兼容的表面上。

## 架构位置

`GrDeferredDisplayListRecorder` 位于 Skia DDL 录制架构的核心层：

```
Skia DDL Recording Architecture
├── Surface Characterization (表面特征)
│   └── GrSurfaceCharacterization
├── Recording Layer (录制层)
│   ├── GrDeferredDisplayListRecorder ← 当前模块
│   ├── GrRecordingContext (录制上下文)
│   └── SkCanvas (绘制画布)
├── DDL Output (DDL输出)
│   ├── GrDeferredDisplayList
│   └── LazyProxyData (延迟代理数据)
└── Replay Layer (回放层)
    ├── GrDirectContext (直接上下文)
    └── GrDDLTask (DDL任务)
```

该模块在架构中的职责：
- 创建并管理DDL录制上下文
- 提供绘制画布用于录制操作
- 创建延迟目标代理（Lazy Proxy）
- 生成不可变的DDL对象
- 管理唯一键代理的生命周期

## 主要类与结构体

### 核心类

| 类名 | 继承关系 | 作用 |
|-----|---------|------|
| `GrDeferredDisplayListRecorder` | 无 | DDL录制器 |

### 关键成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fCharacterization` | `GrSurfaceCharacterization` | 表面特征描述 |
| `fContext` | `sk_sp<GrRecordingContext>` | DDL录制上下文 |
| `fTargetProxy` | `sk_sp<GrRenderTargetProxy>` | 目标渲染代理 |
| `fLazyProxyData` | `sk_sp<LazyProxyData>` | 延迟代理数据 |
| `fSurface` | `sk_sp<SkSurface>` | 录制表面 |

## 公共 API 函数

### 构造函数
```cpp
GrDeferredDisplayListRecorder(const GrSurfaceCharacterization& characterization);
```
创建DDL录制器实例。

**参数说明：**
- `characterization`: 目标表面的特征描述，包含尺寸、格式、采样数等信息

**构造逻辑：**
1. 保存表面特征描述
2. 如果特征有效，创建DDL录制上下文

### 析构函数
```cpp
~GrDeferredDisplayListRecorder();
```
清理录制器资源。

**清理逻辑：**
1. 孤立所有唯一键代理（orphan unique keys）
2. 保持代理的唯一键，但移除其对代理提供者的反向指针
3. 允许代理在回放时重新连接到缓存的版本或标记新资源

### getCanvas
```cpp
SkCanvas* getCanvas();
```
获取用于录制绘制操作的画布。

**返回值：** 录制画布指针，如果初始化失败则为 `nullptr`

**行为：**
- 首次调用时触发初始化（`init()`）
- 后续调用返回已创建的画布
- 初始化失败返回 `nullptr`

### detach
```cpp
sk_sp<GrDeferredDisplayList> detach();
```
分离并返回录制的DDL对象。

**返回值：** 不可变的DDL对象，如果失败则为 `nullptr`

**分离逻辑：**
1. 恢复画布到初始状态
2. 创建DDL对象
3. 将渲染任务移动到DDL中
4. 清空录制器状态，准备下一次录制

## 内部实现细节

### 初始化流程

`init()` 方法执行复杂的初始化逻辑：

```cpp
bool GrDeferredDisplayListRecorder::init() {
    SkASSERT(fContext);
    SkASSERT(!fTargetProxy);
    SkASSERT(!fLazyProxyData);
    SkASSERT(!fSurface);

    if (!fCharacterization.isValid()) {
        return false;
    }

    // 1. 创建延迟代理数据
    fLazyProxyData = sk_sp<GrDeferredDisplayList::LazyProxyData>(
                                            new GrDeferredDisplayList::LazyProxyData);

    // 2. 检查GL FBO 0支持
    bool usesGLFBO0 = fCharacterization.usesGLFBO0();
    if (usesGLFBO0) {
        if (GrBackendApi::kOpenGL != fContext->backend() ||
            fCharacterization.isTextureable()) {
            return false;
        }
    }

    // 3. 检查Vulkan特性
    bool vkRTSupportsInputAttachment = fCharacterization.vkRTSupportsInputAttachment();
    if (vkRTSupportsInputAttachment && GrBackendApi::kVulkan != fContext->backend()) {
        return false;
    }

    // 4. 检查Vulkan二级命令缓冲区兼容性
    if (fCharacterization.vulkanSecondaryCBCompatible()) {
        if (usesGLFBO0 || vkRTSupportsInputAttachment ||
            fCharacterization.isTextureable() ||
            fCharacterization.origin() == kBottomLeft_GrSurfaceOrigin) {
            return false;
        }
    }

    // 5. 设置表面标志
    GrInternalSurfaceFlags surfaceFlags = GrInternalSurfaceFlags::kNone;
    if (usesGLFBO0) {
        surfaceFlags |= GrInternalSurfaceFlags::kGLRTFBOIDIs0;
    } else if (fCharacterization.sampleCount() > 1 &&
               !caps->msaaResolvesAutomatically() &&
               fCharacterization.isTextureable()) {
        surfaceFlags |= GrInternalSurfaceFlags::kRequiresManualMSAAResolve;
    }
    if (vkRTSupportsInputAttachment) {
        surfaceFlags |= GrInternalSurfaceFlags::kVkRTSupportsInputAttachment;
    }

    // 6. 创建延迟目标代理
    fTargetProxy = proxyProvider->createLazyRenderTargetProxy(
        [lazyProxyData = fLazyProxyData](GrResourceProvider* resourceProvider,
                                         const GrSurfaceProxy::LazySurfaceDesc&) {
            SkASSERT(lazyProxyData->fReplayDest->peekSurface());
            auto surface = sk_ref_sp<GrSurface>(lazyProxyData->fReplayDest->peekSurface());
            return GrSurfaceProxy::LazyCallbackResult(std::move(surface));
        },
        fCharacterization.backendFormat(),
        fCharacterization.dimensions(),
        fCharacterization.sampleCount(),
        surfaceFlags,
        optionalTextureInfo,
        GrMipmapStatus::kNotAllocated,
        SkBackingFit::kExact,
        skgpu::Budgeted::kYes,
        fCharacterization.isProtected(),
        fCharacterization.vulkanSecondaryCBCompatible(),
        GrSurfaceProxy::UseAllocator::kYes);

    if (!fTargetProxy) {
        return false;
    }
    fTargetProxy->priv().setIsDDLTarget();

    // 7. 创建设备和表面
    auto device = fContext->priv().createDevice(grColorType,
                                                fTargetProxy,
                                                fCharacterization.refColorSpace(),
                                                fCharacterization.origin(),
                                                fCharacterization.surfaceProps(),
                                                skgpu::ganesh::Device::InitContents::kUninit);
    if (!device) {
        return false;
    }

    fSurface = sk_make_sp<SkSurface_Ganesh>(std::move(device));
    return SkToBool(fSurface.get());
}
```

### 延迟代理机制

延迟代理（Lazy Proxy）是DDL的核心技术：

**录制阶段：**
```cpp
fTargetProxy = createLazyRenderTargetProxy(
    [lazyProxyData = fLazyProxyData](...) {
        // 回调在回放时执行
        return lazyProxyData->fReplayDest->peekSurface();
    },
    ...
);
```

**回放阶段：**
1. 设置 `lazyProxyData->fReplayDest` 为实际目标
2. 延迟代理的回调被触发
3. 返回实际的GPU表面

这种设计允许录制与回放使用不同的表面实例。

### 唯一键代理的孤立

```cpp
GrDeferredDisplayListRecorder::~GrDeferredDisplayListRecorder() {
    if (fContext) {
        auto proxyProvider = fContext->priv().proxyProvider();
        proxyProvider->orphanAllUniqueKeys();
    }
}
```

**目的：**
- 保持代理的唯一键，但移除反向指针
- 允许在回放上下文中重新连接到缓存资源
- 避免跨上下文的代理提供者引用

### DDL分离流程

```cpp
sk_sp<GrDeferredDisplayList> GrDeferredDisplayListRecorder::detach() {
    if (!fContext || !fTargetProxy) {
        return nullptr;
    }

    if (fSurface) {
        SkCanvas* canvas = fSurface->getCanvas();
        canvas->restoreToCount(0);  // 恢复所有保存的状态
    }

    auto ddl = sk_sp<GrDeferredDisplayList>(new GrDeferredDisplayList(
        fCharacterization,
        std::move(fTargetProxy),
        std::move(fLazyProxyData)));

    fContext->priv().moveRenderTasksToDDL(ddl.get());

    // 强制重新生成表面，为下一次录制准备新的延迟代理
    fSurface = nullptr;
    return ddl;
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `GrSurfaceCharacterization` | 表面特征描述 |
| `GrRecordingContext` | DDL录制上下文 |
| `GrRecordingContextPriv` | 录制上下文特权访问 |
| `GrDeferredDisplayList` | DDL容器 |
| `GrRenderTargetProxy` | 渲染目标代理 |
| `GrProxyProvider` | 代理提供者 |
| `GrCaps` | GPU能力查询 |
| `skgpu::ganesh::Device` | Ganesh设备 |
| `SkSurface_Ganesh` | Ganesh表面 |
| `SkCanvas` | 绘制画布 |

### 被依赖的模块

| 模块 | 使用方式 |
|-----|---------|
| Chromium渲染器 | 跨线程DDL录制 |
| DDL测试 | 测试DDL功能 |
| SkSurface | 通过 `SkSurface::MakeRenderTarget` 创建录制器 |

## 设计模式与设计决策

### 建造者模式（Builder Pattern）

录制器逐步构建DDL：
1. 创建录制器
2. 获取画布并录制操作
3. 分离DDL

### 延迟初始化（Lazy Initialization）

`init()` 仅在首次调用 `getCanvas()` 时执行，避免不必要的初始化开销。

### 延迟代理模式（Lazy Proxy Pattern）

使用回调函数创建延迟代理：
```cpp
createLazyRenderTargetProxy([lazyProxyData](...) {
    return lazyProxyData->fReplayDest->peekSurface();
}, ...);
```

**优点：**
- 录制时无需实际表面
- 回放时动态绑定目标
- 支持跨上下文传递

### 资源所有权转移

使用智能指针和移动语义清晰管理资源所有权：
```cpp
auto ddl = new GrDeferredDisplayList(
    fCharacterization,
    std::move(fTargetProxy),      // 转移所有权
    std::move(fLazyProxyData));   // 转移所有权
```

### 状态重置

`detach()` 后重置录制器状态，支持多次录制：
```cpp
fSurface = nullptr;  // 强制下次getCanvas()重新初始化
```

### 设计决策

1. **基于表面特征录制**：无需实际表面，仅需特征描述
2. **延迟代理机制**：核心技术，实现跨上下文DDL
3. **唯一键孤立**：允许代理在回放上下文中重新连接
4. **严格的兼容性检查**：确保录制和回放环境兼容
5. **支持特殊GPU特性**：GL FBO 0、Vulkan输入附件、Vulkan二级命令缓冲区

## 性能考量

### 延迟初始化

避免不必要的初始化：
```cpp
SkCanvas* getCanvas() {
    if (!fSurface && !this->init()) {
        return nullptr;
    }
    return fSurface->getCanvas();
}
```

### 避免状态查询

使用表面特征描述而非查询实际表面，减少GPU同步。

### 渲染任务移动

使用移动语义避免拷贝渲染任务：
```cpp
fContext->priv().moveRenderTasksToDDL(ddl.get());
```

### 代理缓存重用

唯一键孤立机制允许回放时重用缓存的资源：
- 录制时的唯一键代理保持键
- 回放时重新连接到缓存或创建新资源

### MSAA解析优化

根据能力自动处理MSAA解析：
```cpp
if (fCharacterization.sampleCount() > 1 &&
    !caps->msaaResolvesAutomatically() &&
    fCharacterization.isTextureable()) {
    surfaceFlags |= GrInternalSurfaceFlags::kRequiresManualMSAAResolve;
}
```

### 多次录制优化

分离后重置状态，允许重用录制器：
```cpp
fSurface = nullptr;  // 下次调用getCanvas()会重新初始化
```

避免重复创建录制上下文。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/private/chromium/GrDeferredDisplayListRecorder.h` | 头文件 | 公共接口定义 |
| `include/private/chromium/GrDeferredDisplayList.h` | 创建 | DDL容器 |
| `include/private/chromium/GrSurfaceCharacterization.h` | 依赖 | 表面特征 |
| `include/gpu/ganesh/GrRecordingContext.h` | 依赖 | 录制上下文 |
| `src/gpu/ganesh/GrRecordingContextPriv.h` | 依赖 | 录制上下文特权访问 |
| `src/gpu/ganesh/GrRenderTargetProxy.h` | 依赖 | 渲染目标代理 |
| `src/gpu/ganesh/GrProxyProvider.h` | 使用 | 代理提供者 |
| `src/gpu/ganesh/surface/SkSurface_Ganesh.h` | 创建 | Ganesh表面 |
| `src/gpu/ganesh/Device.h` | 创建 | Ganesh设备 |
| `src/gpu/ganesh/GrDDLTask.h` | 被使用 | DDL回放任务 |
