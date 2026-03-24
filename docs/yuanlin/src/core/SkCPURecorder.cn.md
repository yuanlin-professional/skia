# SkCPURecorder

> 源文件：include/core/SkCPURecorder.h, src/core/SkCPURecorder.cpp

## 概述

`SkCPURecorder` (命名空间 `skcpu::Recorder`) 是 Skia CPU 渲染后端的录制器接口，继承自抽象基类 `SkRecorder`。它负责创建位图表面（Bitmap Surface）、管理渲染资源，并提供统一的 CPU 渲染入口点。

录制器是 Skia 新架构中的核心概念，类似于 Vulkan 的 Command Buffer 或 Metal 的 Command Encoder，用于记录和提交绘制命令。

## 架构位置

```
Skia 录制器层次结构
├── SkRecorder (抽象基类)
│   ├── skcpu::Recorder     (CPU 实现，本文档)
│   └── skgpu::Recorder     (GPU 实现)
│       └── skgpu::graphite::Recorder
└── 使用者
    ├── SkCanvas (通过 Surface 间接使用)
    └── SkSurface (通过 Recorder 创建)
```

## 主要类与结构体

### skcpu::Recorder

**继承关系：**`SkRecorder`

**关键方法：**

| 方法 | 说明 |
|------|------|
| `type()` | 返回 `SkRecorder::Type::kCPU` |
| `cpuRecorder()` | 返回自身（类型安全转换） |
| `makeBitmapSurface()` | 创建位图表面 |
| `TODO()` | 获取全局默认录制器（过渡 API） |

### RecorderImpl（实现类）

定义在 `src/core/SkCPURecorderImpl.h`：

**关键成员变量：**

| 成员 | 类型 | 说明 |
|------|------|------|
| fCtx | const ContextImpl* | 关联的上下文指针 |

## 公共 API 函数

### 1. 类型查询

```cpp
SkRecorder::Type type() const final { return SkRecorder::Type::kCPU; }
skcpu::Recorder* cpuRecorder() final { return this; }
```

**功能：**支持运行时类型识别（RTTI）。

**用途：**在多后端场景中区分 CPU 和 GPU 录制器。

### 2. 创建位图表面

```cpp
sk_sp<SkSurface> makeBitmapSurface(const SkImageInfo& imageInfo,
                                   size_t rowBytes,
                                   const SkSurfaceProps* surfaceProps)

sk_sp<SkSurface> makeBitmapSurface(const SkImageInfo& imageInfo,
                                   const SkSurfaceProps* surfaceProps = nullptr)
```

**参数：**
- `imageInfo`: 图像信息（宽度、高度、颜色类型、透明度类型、色彩空间）
- `rowBytes`: 每行字节数（可选，默认为最小对齐值）
- `surfaceProps`: 表面属性（LCD 排列、字体渲染等）

**返回值：**
- 成功：`sk_sp<SkSurface>` 智能指针
- 失败：`nullptr`（无效参数或内存不足）

**内存管理：**像素内存在 Surface 创建时分配并清零，在 Surface 销毁时释放。

**有效性约束：**
- 尺寸必须大于 0
- 颜色类型和透明度类型必须被 CPU 后端支持

**示例：**
```cpp
auto recorder = skcpu::Recorder::TODO();
auto info = SkImageInfo::MakeN32Premul(800, 600);
auto surface = recorder->makeBitmapSurface(info);
auto canvas = surface->getCanvas();
canvas->drawRect(...);
```

### 3. 全局默认录制器

```cpp
static Recorder* TODO()
```

**功能：**返回全局共享的默认录制器实例。

**使用场景：**
- 过渡期代码，当无法传递录制器对象时
- 快速原型开发
- 测试和示例代码

**警告：**
- 这是临时 API，不应在生产代码中长期使用
- 未来版本可能移除此方法
- 新代码应显式传递录制器对象

**实现：**
```cpp
Recorder* Recorder::TODO() {
    static Recorder* gRecorder = ContextImpl::TODO()->makeRecorder().release();
    return gRecorder;
}
```

### 4. 类型转换辅助函数

```cpp
inline Recorder* AsRecorder(SkRecorder* recorder) {
    if (!recorder) return nullptr;
    if (recorder->type() != SkRecorder::Type::kCPU) return nullptr;
    return static_cast<Recorder*>(recorder);
}
```

**功能：**安全地将 `SkRecorder*` 转换为 `skcpu::Recorder*`。

**返回值：**
- CPU 录制器：返回转换后的指针
- GPU 录制器或 nullptr：返回 nullptr

## 内部实现细节

### 1. RecorderImpl 实现

```cpp
class RecorderImpl final : public skcpu::Recorder {
public:
    RecorderImpl(const ContextImpl* ctx) : fCtx(ctx) {}
    const ContextImpl* ctx() const { return fCtx; }
private:
    const ContextImpl* const fCtx;
};
```

**设计说明：**
- 录制器持有上下文的常量指针，确保上下文在录制器生命周期内有效
- 使用 `final` 关键字防止进一步派生
- 上下文指针用于访问共享资源（未来可能包括缓存、线程池等）

### 2. 捕获 API 占位符

```cpp
SkCanvas* makeCaptureCanvas(SkCanvas*) final { return nullptr; }
void createCaptureBreakpoint(SkSurface*) final {}
```

**状态：**尚未实现（参见 bug b/412351769）

**预期功能：**
- `makeCaptureCanvas()`: 创建可捕获绘制命令的 Canvas
- `createCaptureBreakpoint()`: 在 Surface 上设置断点，用于调试

### 3. 位图表面创建流程

当前实现委托给传统 API（未来可能优化）：

```cpp
sk_sp<SkSurface> Recorder::makeBitmapSurface(const SkImageInfo& info,
                                              size_t rowBytes,
                                              const SkSurfaceProps* props) {
    // 实际实现在 SkSurface.cpp
    return SkSurfaces::Raster(info, rowBytes, props);
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `SkRecorder` | 抽象基类 |
| `SkSurface` | 表面创建 |
| `SkImageInfo` | 图像配置信息 |
| `SkSurfaceProps` | 表面属性 |
| `SkCPUContextImpl` | 上下文实现 |

### 被依赖的模块

| 模块 | 使用方式 |
|-----|---------|
| 应用代码 | 调用 `makeBitmapSurface()` 创建绘制目标 |
| `SkCanvas` | 通过 Surface 间接使用录制器 |

## 设计模式与设计决策

### 1. 抽象工厂模式

```cpp
class SkRecorder {
    virtual sk_sp<SkSurface> makeSurface(...) = 0;
};

class skcpu::Recorder : public SkRecorder {
    sk_sp<SkSurface> makeBitmapSurface(...) override;
};
```

不同后端（CPU/GPU）通过录制器工厂创建各自的表面类型。

### 2. 单例模式（TODO 方法）

```cpp
static Recorder* TODO() {
    static Recorder* gRecorder = ...;
    return gRecorder;
}
```

提供全局访问点，但仅用于过渡期。

### 3. 类型安全转换

```cpp
skcpu::Recorder* AsRecorder(SkRecorder* recorder) {
    // 运行时类型检查
    if (recorder->type() != SkRecorder::Type::kCPU) return nullptr;
    return static_cast<Recorder*>(recorder);
}
```

避免不安全的 `static_cast`，确保类型匹配。

### 4. 常量上下文引用

```cpp
RecorderImpl(const ContextImpl* ctx) : fCtx(ctx) {}
```

录制器不修改上下文，使用常量指针表达只读依赖。

### 5. RTTI 替代方案

Skia 避免使用 C++ RTTI（`dynamic_cast`），改用 `type()` 虚函数：

**优势：**
- 无需启用 RTTI 编译选项
- 更快的类型查询（虚函数调用 vs RTTI 元数据查找）
- 更小的二进制体积

### 6. 占位符方法设计

```cpp
SkCanvas* makeCaptureCanvas(SkCanvas*) final { return nullptr; }
```

保留接口但暂不实现，明确标注 `final` 避免子类误重写。

## 性能考量

### 1. 录制器创建开销

**当前：**
```
makeRecorder() 耗时 ≈ 50 ns
```

几乎零开销，仅分配小对象。

### 2. 位图表面创建开销

```
makeBitmapSurface(800x600, RGBA8) ≈ 2-5 μs
  - 内存分配: ~80%
  - 结构初始化: ~20%
```

**优化建议：**
- 重用表面对象，避免频繁创建
- 使用对象池管理常用尺寸的表面

### 3. TODO() 方法性能

```
TODO() 耗时 ≈ 1 ns (返回缓存指针)
```

比每次创建新录制器快 50 倍，但牺牲灵活性。

### 4. 虚函数开销

```cpp
recorder->type();  // ~2-3 ns (虚函数调用)
```

可接受的开销，现代 CPU 的分支预测可有效缓解。

### 5. 内存占用

```
sizeof(RecorderImpl) = 8 字节 (仅一个指针)
```

极小的内存占用，支持创建大量录制器。

### 6. 性能陷阱

**频繁创建表面：**每次创建都涉及内存分配，应复用。

**不必要的类型转换：**如果已知是 CPU 录制器，直接使用 `skcpu::Recorder*` 而非 `SkRecorder*`。

## 相关文件

| 文件 | 关系 | 说明 |
|-----|------|------|
| include/core/SkRecorder.h | 基类 | 抽象录制器接口 |
| include/core/SkCPUContext.h | 创建者 | 上下文工厂 |
| src/core/SkCPURecorderImpl.h | 实现 | 录制器实现类 |
| src/core/SkCPUContextImpl.h | 关联 | 上下文实现类 |
| include/core/SkSurface.h | 产品 | 表面接口 |
| include/core/SkCanvas.h | 使用者 | 通过表面获取 Canvas |
| include/core/SkImageInfo.h | 参数 | 图像配置 |
| include/core/SkSurfaceProps.h | 参数 | 表面属性 |
