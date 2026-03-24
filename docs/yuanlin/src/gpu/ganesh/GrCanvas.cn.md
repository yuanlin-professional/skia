# GrCanvas

> 源文件
> - src/gpu/ganesh/GrCanvas.h
> - src/gpu/ganesh/GrCanvas.cpp

## 概述

`GrCanvas` 是 Ganesh GPU 后端的工具命名空间，提供了一组函数用于从 `SkCanvas` 对象中提取底层的 Ganesh GPU 渲染上下文和目标代理。这些函数作为桥梁，连接 Skia 的高级 Canvas API 和底层的 GPU 渲染基础设施。

该模块不包含类定义，仅提供命名空间 `skgpu::ganesh` 下的实用函数，用于访问 GPU 设备相关的内部对象。

## 架构位置

`GrCanvas` 位于 Skia 图形库的架构中：

- **模块**: Ganesh GPU 后端
- **层级**: Canvas 辅助工具层
- **命名空间**: `skgpu::ganesh`
- **协作对象**: 与 `SkCanvas`、`Device`、`SurfaceDrawContext`、`SurfaceFillContext`、`GrRenderTargetProxy` 协作

该模块是 Android 特定功能和 Ganesh 内部实现之间的接口层。

## 主要类与结构体

此文件不定义类或结构体，仅在 `skgpu::ganesh` 命名空间中声明和实现自由函数。

## 公共 API 函数

所有函数都位于 `skgpu::ganesh` 命名空间中，接受 `const SkCanvas*` 参数。

### TopDeviceSurfaceDrawContext()

```cpp
SurfaceDrawContext* TopDeviceSurfaceDrawContext(const SkCanvas* canvas);
```

**功能**: 获取 Canvas 顶层设备的 `SurfaceDrawContext`。

**参数**:
- `canvas`: SkCanvas 指针

**返回值**:
- 如果顶层设备是 Ganesh GPU 设备，返回其 `SurfaceDrawContext*`
- 否则返回 `nullptr`

**使用场景**: 访问绘制上下文以执行 GPU 特定的绘制操作。

### TopDeviceSurfaceFillContext()

```cpp
SurfaceFillContext* TopDeviceSurfaceFillContext(const SkCanvas* canvas);
```

**功能**: 获取 Canvas 顶层设备的 `SurfaceFillContext`。

**参数**:
- `canvas`: SkCanvas 指针

**返回值**:
- 如果顶层设备是 Ganesh GPU 设备，返回其 `SurfaceFillContext*`
- 否则返回 `nullptr`

**使用场景**: 访问填充上下文以执行清除、填充等操作。

### TopDeviceTargetProxy()

```cpp
GrRenderTargetProxy* TopDeviceTargetProxy(const SkCanvas* canvas);
```

**功能**: 获取 Canvas 顶层设备的渲染目标代理。

**参数**:
- `canvas`: SkCanvas 指针

**返回值**:
- 如果顶层设备是 Ganesh GPU 设备，返回其 `GrRenderTargetProxy*`
- 否则返回 `nullptr`

**使用场景**: 访问底层渲染目标资源。

### TopLayerBounds() (未在头文件声明)

```cpp
SkIRect TopLayerBounds(const SkCanvas* canvas);
```

**功能**: 获取 Canvas 顶层设备的全局边界。

**返回值**: `SkIRect` 表示设备的边界矩形。

### TopLayerBackendRenderTarget() (未在头文件声明)

```cpp
GrBackendRenderTarget TopLayerBackendRenderTarget(const SkCanvas* canvas);
```

**功能**: 获取 Canvas 顶层设备的后端渲染目标。

**返回值**:
- 如果顶层设备是 Ganesh GPU 设备且有渲染目标，返回 `GrBackendRenderTarget`
- 否则返回空对象

## 内部实现细节

### 实现模式

所有函数都遵循相同的实现模式：

```cpp
SurfaceDrawContext* TopDeviceSurfaceDrawContext(const SkCanvas* canvas) {
    if (auto gpuDevice = SkCanvasPriv::TopDevice(canvas)->asGaneshDevice()) {
        return gpuDevice->surfaceDrawContext();
    }
    return nullptr;
}
```

**步骤**:
1. 使用 `SkCanvasPriv::TopDevice()` 获取顶层设备
2. 尝试将设备转换为 Ganesh GPU 设备（`asGaneshDevice()`）
3. 如果转换成功，调用相应的访问器方法
4. 否则返回 `nullptr` 或默认值

### 设备类型检查

通过 `asGaneshDevice()` 进行动态类型检查：
- 成功返回非空指针，表示是 Ganesh GPU 设备
- 失败返回 `nullptr`，表示是 CPU 光栅设备或其他后端设备

### TopLayerBackendRenderTarget 实现

```cpp
GrBackendRenderTarget TopLayerBackendRenderTarget(const SkCanvas* canvas) {
    auto proxy = TopDeviceTargetProxy(canvas);
    if (!proxy) {
        return {};
    }
    const GrRenderTarget* renderTarget = proxy->peekRenderTarget();
    return renderTarget ? renderTarget->getBackendRenderTarget() : GrBackendRenderTarget();
}
```

此函数额外检查代理是否已实例化为实际的渲染目标。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkCanvas` | 主要接口参数 |
| `SkCanvasPriv` | 访问 Canvas 内部设备 |
| `SkDevice` | 基础设备接口 |
| `skgpu::ganesh::Device` | Ganesh GPU 设备类 |
| `SurfaceDrawContext` | 绘制上下文 |
| `SurfaceFillContext` | 填充上下文 |
| `GrRenderTargetProxy` | 渲染目标代理 |
| `GrRenderTarget` | 实际渲染目标 |
| `GrBackendSurface` | 后端表面类型 |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| Android 特定代码 | 访问底层渲染目标（如 `SkCanvasAndroid.h`） |
| Ganesh 测试工具 | 验证 GPU 渲染状态 |
| 混合渲染路径 | 在 CPU 和 GPU 渲染之间切换 |

## 设计模式与设计决策

### 1. 命名空间函数（非成员函数）

选择自由函数而非类方法，因为：
- `SkCanvas` 不应依赖 Ganesh 具体实现
- 提供松耦合的访问接口
- 遵循 Skia 的模块化设计原则

### 2. 空对象模式

所有函数在失败时返回 `nullptr` 或空对象，避免异常，简化错误处理。

### 3. 类型安全的向下转型

使用 `asGaneshDevice()` 进行安全的类型转换，避免危险的 C 风格转型。

### 4. 单一职责原则

每个函数只负责提取一种特定类型的对象。

### 5. 透明访问

这些函数充当透明代理，不修改状态，仅提供访问。

## 性能考量

### 1. 零开销访问

- 函数调用是内联候选
- 无额外分配或拷贝
- 直接指针返回

### 2. 类型检查开销

`asGaneshDevice()` 涉及虚函数调用或类型检查，但开销很小。

### 3. 适合频繁调用

由于开销极低，这些函数可以在热路径中频繁调用。

### 4. 编译时优化潜力

简单的实现允许编译器进行积极的内联优化。

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `include/core/SkCanvas.h` | Canvas 公共 API |
| `src/core/SkCanvasPriv.h` | Canvas 内部访问器 |
| `src/core/SkDevice.h` | 设备基类 |
| `src/gpu/ganesh/Device.h` | Ganesh GPU 设备类 |
| `src/gpu/ganesh/SurfaceDrawContext.h` | 绘制上下文类 |
| `src/gpu/ganesh/SurfaceFillContext.h` | 填充上下文类 |
| `src/gpu/ganesh/GrRenderTargetProxy.h` | 渲染目标代理类 |
| `src/gpu/ganesh/GrRenderTarget.h` | 渲染目标类 |
| `include/gpu/ganesh/GrBackendSurface.h` | 后端表面类型 |
| `include/android/SkCanvasAndroid.h` | Android Canvas 扩展 |
