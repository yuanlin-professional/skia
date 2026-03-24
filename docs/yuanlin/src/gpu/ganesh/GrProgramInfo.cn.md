# GrProgramInfo

> 源文件
> - src/gpu/ganesh/GrProgramInfo.h
> - src/gpu/ganesh/GrProgramInfo.cpp

## 概述

`GrProgramInfo` 是 Ganesh GPU 后端中封装渲染程序完整配置信息的核心类。它聚合了创建和执行 GPU 渲染程序所需的所有信息,包括几何处理器(GeometryProcessor)、管线配置(Pipeline)、模板设置(Stencil)、图元类型(Primitive Type)等。

该类的主要作用是:
- 作为创建 GPU 程序的完整参数集合
- 提供程序描述符(Program Descriptor)生成的基础数据
- 在渲染管线的不同阶段传递程序配置
- 支持跨平台的程序配置(OpenGL、Vulkan、Metal、Dawn)

`GrProgramInfo` 是只读的值对象,一旦创建就不可修改,确保了程序配置的不变性和线程安全性。

## 架构位置

`GrProgramInfo` 位于 Ganesh 渲染管线的程序编译层:

```
GrOpsTask
    └── GrOp (绘制操作)
        └── GrProgramInfo (程序配置信息)
            ├── GrGeometryProcessor (几何处理)
            ├── GrPipeline (渲染管线状态)
            └── GrUserStencilSettings (模板设置)
                ↓
        GrProgramDesc (程序描述符)
                ↓
        GrGpu::createProgram() (创建 GPU 程序)
```

它是连接高层绘制操作和底层程序编译的桥梁。

## 主要类与结构体

### GrProgramInfo 类

**继承关系**:
- 无继承关系,独立的配置类

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fNumSamples | int | 渲染采样数(MSAA) |
| fNeedsStencil | bool | 是否需要模板缓冲区 |
| fBackendFormat | GrBackendFormat | 目标渲染表面的后端格式 |
| fOrigin | GrSurfaceOrigin | 表面原点(左上或左下) |
| fTargetHasVkResolveAttachmentWithInput | bool | Vulkan 专用:目标是否有输入附件 |
| fTargetsNumSamples | int | 目标表面的采样数 |
| fPipeline | const GrPipeline* | 渲染管线配置(非拥有) |
| fUserStencilSettings | const GrUserStencilSettings* | 用户模板设置(非拥有) |
| fGeomProc | const GrGeometryProcessor* | 几何处理器(非拥有) |
| fPrimitiveType | GrPrimitiveType | 图元类型(点、线、三角形等) |
| fRenderPassXferBarriers | GrXferBarrierFlags | 渲染通道传输屏障标志 |
| fColorLoadOp | GrLoadOp | 颜色加载操作 |

## 公共 API 函数

### 构造函数

```cpp
GrProgramInfo(const GrCaps& caps,
              const GrSurfaceProxyView& targetView,
              bool usesMSAASurface,
              const GrPipeline* pipeline,
              const GrUserStencilSettings* userStencilSettings,
              const GrGeometryProcessor* geomProc,
              GrPrimitiveType primitiveType,
              GrXferBarrierFlags renderPassXferBarriers,
              GrLoadOp colorLoadOp);
```

构造函数执行以下初始化:
1. 从目标视图提取后端格式、原点和采样数
2. 计算是否需要模板缓冲
3. 确定 Vulkan resolve 附件配置
4. 根据 caps 调整采样数(处理 MSAA Surface)

### 访问器方法

```cpp
int numSamples() const;  // 获取渲染采样数
int needsStencil() const;  // 是否需要模板
bool isStencilEnabled() const;  // 模板是否启用
const GrUserStencilSettings* userStencilSettings() const;
const GrBackendFormat& backendFormat() const;
GrSurfaceOrigin origin() const;
const GrPipeline& pipeline() const;
const GrGeometryProcessor& geomProc() const;
GrPrimitiveType primitiveType() const;
```

### 特定平台方法

```cpp
bool targetHasVkResolveAttachmentWithInput() const;  // Vulkan 专用
int targetsNumSamples() const;  // 目标表面采样数
GrXferBarrierFlags renderPassBarriers() const;  // 渲染通道屏障
GrLoadOp colorLoadOp() const;  // 颜色加载操作
```

### 程序描述符支持

```cpp
uint16_t primitiveTypeKey() const;  // 图元类型键值
GrStencilSettings nonGLStencilSettings() const;  // 非 OpenGL 模板设置
```

### 代理访问

```cpp
void visitFPProxies(const GrVisitProxyFunc& func) const;
```

遍历管线中所有片段处理器的代理。

### 调试支持

```cpp
#ifdef SK_DEBUG
void validate(bool flushTime) const;  // 验证配置有效性
void checkAllInstantiated() const;  // 检查所有代理已实例化
void checkMSAAAndMIPSAreResolved() const;  // 检查 MSAA 和 mipmap 已解析
#endif
```

## 内部实现细节

### 采样数计算逻辑

构造函数中的采样数计算:

```cpp
fNumSamples = fTargetsNumSamples;
if (fNumSamples == 1 && usesMSAASurface) {
    fNumSamples = caps.internalMultisampleCount(this->backendFormat());
}
```

这支持 DMSAA(Dynamic MSAA)功能,即使目标是单采样,也可以使用内部 MSAA 表面。

### Vulkan Resolve 附件检测

```cpp
fTargetHasVkResolveAttachmentWithInput =
    targetView.asRenderTargetProxy()->supportsVkInputAttachment() &&
    ((targetView.asRenderTargetProxy()->numSamples() > 1 &&
      targetView.asTextureProxy()) ||
     targetView.asRenderTargetProxy()->numSamples() == 1);
```

检测 Vulkan 特定的 resolve 附件配置,影响渲染通道创建。

### 模板启用判断

```cpp
bool isStencilEnabled() const {
    return fUserStencilSettings != &GrUserStencilSettings::kUnused ||
           fPipeline->hasStencilClip();
}
```

模板在以下情况启用:
1. 用户显式设置了模板
2. 管线有模板裁剪

### 非 OpenGL 模板设置生成

```cpp
GrStencilSettings GrProgramInfo::nonGLStencilSettings() const {
    GrStencilSettings stencil;
    if (this->isStencilEnabled()) {
        stencil.reset(*fUserStencilSettings,
                      this->pipeline().hasStencilClip(),
                      8);  // Dawn/Metal/Vulkan 模板位数已知
    }
    return stencil;
}
```

Dawn、Metal 和 Vulkan 的模板位数在创建时已知(通常是 8 位),可以预先创建模板设置。OpenGL 需要在运行时查询。

### 验证检查

调试模式下的验证包括:
- 刷新时检查所有代理已实例化
- 检查 MSAA 和 mipmap 已解析
- 验证纹理采样器的 mipmap 状态

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| GrCaps | 查询 GPU 能力和限制 |
| GrPipeline | 渲染管线状态(混合、裁剪等) |
| GrGeometryProcessor | 几何处理器(顶点属性、变换) |
| GrUserStencilSettings | 用户模板配置 |
| GrSurfaceProxyView | 目标表面视图 |
| GrRenderTargetProxy | 渲染目标代理 |
| GrBackendFormat | 后端图形 API 格式 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| GrProgramDesc | 使用 GrProgramInfo 生成程序描述符键 |
| GrOp | 创建 GrProgramInfo 描述绘制配置 |
| GrGpu | 使用 GrProgramInfo 创建 GPU 程序 |
| GrRecordingContext | 记录程序信息用于 DDL |

## 设计模式与设计决策

### 值对象模式(Value Object)

`GrProgramInfo` 是不可变的值对象:
- 所有成员通过构造函数初始化
- 只提供 const 访问器
- 确保配置的一致性和线程安全

### 聚合模式(Aggregation)

聚合多个配置对象(Pipeline、GeometryProcessor、Stencil),提供统一接口,简化参数传递。

### 指针语义 vs 值语义

使用指针存储 Pipeline 和 GeometryProcessor:
- 避免大对象拷贝
- 这些对象通常生命周期更长
- 责任链:调用者保证对象生命周期

### 平台抽象

通过方法如 `nonGLStencilSettings()` 和 `targetHasVkResolveAttachmentWithInput()` 处理平台差异,上层代码保持平台无关。

## 性能考量

### 避免拷贝

- 存储指针而非值
- 返回 const 引用

### 内联访问器

简单的访问器方法都内联在头文件中,避免函数调用开销。

### 懒计算

某些派生信息(如 `nonGLStencilSettings()`)按需计算,避免不必要的计算。

### 缓存键生成

`primitiveTypeKey()` 提供高效的键值生成,用于程序缓存查找。

### 调试开销隔离

使用 `#ifdef SK_DEBUG` 隔离调试代码,确保发布版本无性能影响。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| src/gpu/ganesh/GrProgramDesc.h/cpp | 使用者 | 基于 GrProgramInfo 生成程序描述符 |
| src/gpu/ganesh/GrPipeline.h/cpp | 组件 | 渲染管线配置 |
| src/gpu/ganesh/GrGeometryProcessor.h | 组件 | 几何处理器接口 |
| src/gpu/ganesh/GrUserStencilSettings.h | 组件 | 用户模板设置 |
| src/gpu/ganesh/GrOp.h | 创建者 | 绘制操作创建 GrProgramInfo |
| src/gpu/ganesh/GrGpu.h | 使用者 | 使用 GrProgramInfo 创建 GPU 程序 |
| src/gpu/ganesh/GrCaps.h | 依赖 | GPU 能力查询 |
| src/gpu/ganesh/GrStencilSettings.h | 相关 | 完整模板设置 |
| src/gpu/ganesh/gl/GrGLGpu.h | 使用者 | OpenGL 程序创建 |
| src/gpu/ganesh/vk/GrVkGpu.h | 使用者 | Vulkan 程序创建 |
| src/gpu/ganesh/mtl/GrMtlGpu.h | 使用者 | Metal 程序创建 |
