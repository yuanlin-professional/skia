# GrGLContext

> 源文件: src/gpu/ganesh/gl/GrGLContext.h, src/gpu/ganesh/gl/GrGLContext.cpp

## 概述

`GrGLContext` 是 Skia 图形库中 Ganesh OpenGL 后端的核心上下文类,用于封装 OpenGL 上下文的所有关键信息,包括 OpenGL 版本、标准类型、GLSL 版本、驱动信息以及功能集合(Caps)。该类通过 `GrGLInterface` 与底层 OpenGL API 交互,为 Skia 的 OpenGL 渲染提供统一的抽象层。

## 架构位置

`GrGLContext` 位于 Skia GPU 渲染架构的 OpenGL 后端层,具体位置如下:

```
skia/
└── src/gpu/ganesh/gl/
    ├── GrGLContext.h/cpp      <- 本模块
    ├── GrGLCaps.h/cpp         <- 功能集合
    ├── GrGLInterface.h        <- OpenGL 函数接口
    ├── GrGLUtil.h             <- 工具函数
    └── GrGLGpu.h/cpp          <- GPU 实现类
```

该模块在 Ganesh 架构中充当 OpenGL 上下文信息的中心仓库,被 `GrGLGpu` 等更高层次的类依赖。

## 主要类与结构体

### 继承关系

```
GrGLContextInfo (基类)
    └── GrGLContext (派生类)
```

### GrGLContextInfo 类

作为基类提供 OpenGL 上下文的核心信息访问接口。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fInterface` | `sk_sp<const GrGLInterface>` | OpenGL 函数接口指针 |
| `fDriverInfo` | `GrGLDriverInfo` | 驱动信息(供应商、渲染器、版本) |
| `fGLSLGeneration` | `SkSL::GLSLGeneration` | GLSL 版本代次 |
| `fGLCaps` | `sk_sp<GrGLCaps>` | OpenGL 功能集合 |

### GrGLContext 类

扩展 `GrGLContextInfo`,提供完整的上下文管理功能。

| 成员 | 类型 | 说明 |
|------|------|------|
| 继承所有基类成员 | - | 包括接口、驱动信息、功能集合 |

### ConstructorArgs 结构体

用于构造函数参数传递的内部结构。

| 字段 | 类型 | 说明 |
|------|------|------|
| `fInterface` | `sk_sp<const GrGLInterface>` | OpenGL 接口 |
| `fDriverInfo` | `GrGLDriverInfo` | 驱动信息 |
| `fGLSLGeneration` | `SkSL::GLSLGeneration` | GLSL 版本 |
| `fContextOptions` | `const GrContextOptions*` | 上下文选项 |

## 公共 API 函数

### GrGLContext 类

#### 静态工厂方法

```cpp
static std::unique_ptr<GrGLContext> Make(
    sk_sp<const GrGLInterface> interface,
    const GrContextOptions& options
);
```

创建 `GrGLContext` 实例。首先验证接口有效性,然后获取驱动信息和 GLSL 版本,并应用特定平台的驱动修正。

**关键逻辑:**
- 验证 OpenGL 接口有效性
- 获取驱动信息(版本、供应商、渲染器)
- 确定 GLSL 版本代次
- 应用 Android 平台的驱动修正(Adreno 3xx、Android Emulator)
- 处理外部纹理扩展兼容性问题

#### 访问器方法

```cpp
const GrGLInterface* glInterface() const;
```

返回底层 OpenGL 接口指针。

### GrGLContextInfo 类

#### 版本与标准查询

```cpp
GrGLStandard standard() const;          // OpenGL 标准类型(GL/GLES/WebGL)
GrGLVersion version() const;            // OpenGL 版本
SkSL::GLSLGeneration glslGeneration() const;  // GLSL 版本代次
```

#### 供应商与渲染器信息

```cpp
GrGLVendor vendor() const;              // GPU 供应商
GrGLRenderer renderer() const;          // GPU 渲染器型号
```

这两个方法会智能处理 ANGLE 后端情况,返回底层真实的供应商和渲染器信息。

#### ANGLE 相关查询

```cpp
GrGLANGLEBackend angleBackend() const;
GrGLDriver angleDriver() const;
GrGLDriverVersion angleDriverVersion() const;
GrGLVendor angleVendor() const;
GrGLRenderer angleRenderer() const;
```

提供详细的 ANGLE 后端信息,用于应用特定的驱动修正。

#### WebGL 相关查询

```cpp
GrGLVendor webglVendor() const;
GrGLRenderer webglRenderer() const;
```

#### 驱动信息查询

```cpp
GrGLDriver driver() const;              // 驱动类型(Mesa/ANGLE 等)
GrGLDriverVersion driverVersion() const;
bool isOverCommandBuffer() const;       // 是否运行在 CommandBuffer 上
bool isRunningOverVirgl() const;        // 是否运行在 Virgl 上
```

#### 功能查询

```cpp
const GrGLCaps* caps() const;
GrGLCaps* caps();
bool hasExtension(const char* ext) const;
const GrGLExtensions& extensions() const;
```

## 内部实现细节

### 驱动修正机制

#### Android Adreno 3xx 修正

针对 Adreno 3xx GPU 在 Android O 之前版本的 GLSL 编译器 bug:

```cpp
if (args.fDriverInfo.fRenderer == GrGLRenderer::kAdreno3xx) {
    if (getAndroidAPIVersion() < 26) {
        args.fGLSLGeneration = SkSL::GLSLGeneration::k100es;
    }
}
```

虽然驱动声称支持 GLES 3.0,但会将 GLSL 版本降级为 1.00 ES 以避免编译失败。

#### Android Emulator 修正

针对旧版 Android Emulator 运行 SwiftShader 时的崩溃问题:

```cpp
if (args.fDriverInfo.fRenderer == GrGLRenderer::kAndroidEmulator) {
    args.fGLSLGeneration = SkSL::GLSLGeneration::k100es;
}
```

### 外部纹理扩展兼容性处理

处理 GLES 3.0 环境下外部纹理扩展的兼容性问题:

```cpp
if (GR_IS_GR_GL_ES(interface->fStandard) &&
    options.fPreferExternalImagesOverES3 &&
    !options.fDisableDriverCorrectnessWorkarounds &&
    interface->hasExtension("GL_OES_EGL_image_external") &&
    args.fGLSLGeneration >= SkSL::GLSLGeneration::k330 &&
    !interface->hasExtension("GL_OES_EGL_image_external_essl3") &&
    !interface->hasExtension("OES_EGL_image_external_essl3")) {
    args.fGLSLGeneration = SkSL::GLSLGeneration::k100es;
}
```

当设备仅支持 ES2 的外部纹理扩展但不支持 ES3 版本时,可选择降级到 GLSL 1.00 ES。

### 构造流程

1. 验证 OpenGL 接口有效性
2. 获取驱动信息
3. 确定 GLSL 版本代次
4. 应用平台特定修正
5. 创建 `GrGLCaps` 功能集合对象

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGLInterface` | OpenGL 函数接口抽象 |
| `GrGLCaps` | OpenGL 功能集合 |
| `GrGLUtil` | 工具函数(获取驱动信息、GLSL 版本) |
| `GrGLGLSL` | GLSL 版本判断 |
| `GrContextOptions` | 上下文配置选项 |
| `SkSL::GLSLGeneration` | GLSL 版本枚举 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `GrGLGpu` | 通过 `glContext()` 访问上下文信息 |
| `GrGLCaps` | 在构造时作为参数传递 |
| `GrGLProgram` | 查询 GLSL 版本以编译着色器 |
| `GrGLRenderTarget` | 查询功能以选择渲染策略 |

## 设计模式与设计决策

### 1. 两层继承设计

将上下文信息分为 `GrGLContextInfo`(基础信息)和 `GrGLContext`(完整功能)两层:

- **优点**: 允许其他类仅依赖只读的上下文信息,避免暴露管理接口
- **应用场景**: `GrGLCaps` 构造时仅需要 `GrGLContextInfo`

### 2. 工厂模式

使用静态 `Make()` 方法而非公共构造函数:

- **优点**: 可以在构造失败时返回 `nullptr`,避免异常处理
- **验证时机**: 在对象创建前完成所有验证

### 3. ANGLE 智能查询

`vendor()` 和 `renderer()` 方法自动检测 ANGLE 后端:

```cpp
GrGLVendor vendor() const {
    if (this->angleBackend() == GrGLANGLEBackend::kOpenGL) {
        return this->angleVendor();
    }
    return fDriverInfo.fVendor;
}
```

**设计理念**: 向用户透明地返回真实的底层硬件信息,因为许多驱动修正是基于实际 GPU 供应商的。

### 4. 条件编译与平台修正

使用条件编译和运行时检测相结合:

```cpp
#ifdef SK_BUILD_FOR_ANDROID
    auto getAndroidAPIVersion = []() { /* ... */ };
    if (args.fDriverInfo.fRenderer == GrGLRenderer::kAdreno3xx) {
        if (getAndroidAPIVersion() < 26) {
            args.fGLSLGeneration = SkSL::GLSLGeneration::k100es;
        }
    }
#endif
```

**设计理念**: 最小化跨平台代码的复杂度,仅在必要时引入平台特定逻辑。

## 性能考量

### 1. 惰性初始化

`GrGLCaps` 在构造函数中创建,而非延迟创建:

- **权衡**: 虽然增加初始化时间,但避免后续访问时的空指针检查
- **理由**: 功能集合是频繁访问的对象,提前创建可简化访问逻辑

### 2. 智能指针使用

使用 `sk_sp` 管理接口和功能集合:

- **优点**: 自动内存管理,避免泄漏
- **开销**: 引用计数带来的原子操作开销可忽略不计

### 3. 驱动信息缓存

在构造时获取并缓存所有驱动信息:

- **优点**: 避免重复查询 OpenGL 状态(可能触发驱动调用)
- **内存成本**: 约 100 字节的结构体存储

### 4. 移动语义支持

支持移动构造和移动赋值:

```cpp
GrGLContextInfo(GrGLContextInfo&&) = default;
GrGLContextInfo& operator=(GrGLContextInfo&&) = default;
```

**优点**: 避免不必要的引用计数操作和对象拷贝。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/gpu/ganesh/gl/GrGLCaps.h` | OpenGL 功能集合定义 |
| `src/gpu/ganesh/gl/GrGLInterface.h` | OpenGL 函数接口 |
| `src/gpu/ganesh/gl/GrGLUtil.h` | OpenGL 工具函数 |
| `src/gpu/ganesh/gl/GrGLGLSL.h` | GLSL 版本判断 |
| `src/gpu/ganesh/gl/GrGLGpu.h` | OpenGL GPU 实现 |
| `include/gpu/ganesh/GrContextOptions.h` | 上下文配置选项 |
| `src/sksl/SkSLGLSL.h` | GLSL 版本枚举定义 |
