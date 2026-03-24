# GrContext_Base

> 源文件: `include/private/gpu/ganesh/GrContext_Base.h`

## 概述
GrContext_Base 是 Skia Ganesh GPU 上下文层级体系的根基类,定义了所有 GPU 上下文共有的最基础接口。它封装了 GrContextThreadSafeProxy,提供了后端类型查询、格式查询、采样数量查询等核心功能,是整个 Ganesh 上下文继承树的起点。

## 架构位置
该类位于 Skia GPU 后端 Ganesh 子系统的上下文层顶部,是 GrImageContext、GrRecordingContext 和 GrDirectContext 的共同基类。它处于线程安全代理(ThreadSafeProxy)之上,为所有上下文类型提供统一的基础接口。

## 主要类与结构体

### GrContext_Base
所有 Ganesh GPU 上下文的抽象基类。

**继承关系**: SkRefCnt → GrContext_Base

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fThreadSafeProxy | sk_sp<GrContextThreadSafeProxy> | 线程安全的上下文代理,包含共享的能力和选项信息 |

## 公共 API 函数

### 生命周期管理

#### `~GrContext_Base() override`
- **功能**: 虚析构函数,确保派生类正确清理
- **参数**: 无
- **返回值**: 无

### 类型转换

#### `virtual GrDirectContext* asDirectContext()`
- **功能**: 安全地向下转换到 GrDirectContext
- **参数**: 无
- **返回值**: 如果是 GrDirectContext 返回指针,否则返回 nullptr
- **用途**: 避免使用 dynamic_cast 的类型识别机制

### 后端查询

#### `SK_API GrBackendApi backend() const`
- **功能**: 获取当前上下文使用的 3D API 类型
- **参数**: 无
- **返回值**: GrBackendApi 枚举值(OpenGL/Vulkan/Metal/Direct3D/Dawn 等)

### 格式查询

#### `SK_API GrBackendFormat defaultBackendFormat(SkColorType, GrRenderable) const`
- **功能**: 获取指定颜色类型和可渲染性的默认后端格式
- **参数**:
  - `SkColorType`: Skia 颜色类型(如 kRGBA_8888_SkColorType)
  - `GrRenderable`: 是否需要可渲染(kYes/kNo)
- **返回值**: GrBackendFormat 对象,调用者应检查其有效性
- **用途**: 确保与 createBackendTexture 方法使用相同的格式

#### `SK_API GrBackendFormat compressedBackendFormat(SkTextureCompressionType) const`
- **功能**: 获取压缩纹理格式的后端格式
- **参数**: `SkTextureCompressionType`: 压缩类型(如 ETC1/BC1)
- **返回值**: GrBackendFormat 对象,如果不支持则无效

### 能力查询

#### `SK_API int maxSurfaceSampleCountForColorType(SkColorType colorType) const`
- **功能**: 查询指定颜色类型支持的最大 MSAA 采样数
- **参数**: `colorType`: 要查询的颜色类型
- **返回值**:
  - 返回支持的最大采样数(如 1, 2, 4, 8, 16)
  - 返回 1 表示只支持非 MSAA 渲染
  - 返回 0 表示该颜色类型完全不支持渲染

### 线程安全代理访问

#### `sk_sp<GrContextThreadSafeProxy> threadSafeProxy()`
- **功能**: 获取线程安全的上下文代理的智能指针
- **参数**: 无
- **返回值**: 指向 ThreadSafeProxy 的引用计数指针
- **用途**: 在多线程环境中安全地访问上下文能力信息

### 私有 API 访问

#### `GrBaseContextPriv priv()`
- **功能**: 获取私有 API 访问器(非常量版本)
- **参数**: 无
- **返回值**: GrBaseContextPriv 对象

#### `const GrBaseContextPriv priv() const`
- **功能**: 获取私有 API 访问器(常量版本)
- **参数**: 无
- **返回值**: 常量 GrBaseContextPriv 对象

## 内部实现细节

### 受保护的成员函数

#### 构造函数
```cpp
explicit GrContext_Base(sk_sp<GrContextThreadSafeProxy>);
```
受保护的构造函数,只能由派生类调用,接受线程安全代理作为参数。

#### 初始化
```cpp
virtual bool init();
```
虚初始化方法,派生类可以覆盖以执行特定的初始化逻辑。返回 false 表示初始化失败。

#### 上下文 ID
```cpp
uint32_t contextID() const;
```
获取上下文的唯一标识符,用于验证资源的上下文兼容性。相关的上下文(如录制上下文和直接上下文)共享相同的 ID。

#### 上下文匹配
```cpp
bool matches(GrContext_Base* candidate) const {
    return candidate && candidate->contextID() == this->contextID();
}
```
检查两个上下文是否兼容(通过比较 ID)。

#### 选项和能力访问
```cpp
const GrContextOptions& options() const;
const GrCaps* caps() const;
sk_sp<const GrCaps> refCaps() const;
```
访问上下文选项和能力对象,这些信息存储在 ThreadSafeProxy 中。

#### 类型识别虚函数
```cpp
virtual GrImageContext* asImageContext() { return nullptr; }
virtual GrRecordingContext* asRecordingContext() { return nullptr; }
```
派生类覆盖这些方法以支持安全的向下转型。

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| SkRefCnt | 引用计数基类 |
| GrTypes | GPU 类型定义(GrBackendApi, GrRenderable) |
| SkAPI | API 导出宏 |
| GrContextThreadSafeProxy | 线程安全的上下文代理,核心组件 |
| GrBackendFormat | 后端格式表示 |
| GrCaps | GPU 能力查询 |
| GrContextOptions | 上下文配置选项 |

### 被依赖的模块
- GrImageContext: 直接派生类,用于图像上下文
- GrRecordingContext: 派生类,提供录制功能
- GrDirectContext: 最终派生类,提供完整的 GPU 操作能力
- SkSurface: GPU 表面使用上下文
- SkImage: GPU 图像使用上下文
- 所有需要访问 GPU 上下文的 Skia 组件

## 设计模式与设计决策

### 抽象基类模式
GrContext_Base 定义了纯接口,不包含具体实现:
- 使用虚函数实现多态
- 提供类型转换的安全机制
- 强制派生类实现特定功能

### 代理模式
通过持有 GrContextThreadSafeProxy 实现功能委托:
- 将线程安全的部分(Caps, Options)与非线程安全的部分分离
- 允许多个上下文对象共享相同的能力信息
- 支持在不同线程创建兼容的上下文

### 非虚接口(NVI)模式
某些功能(如 backend(), defaultBackendFormat())作为非虚公共接口:
- 公共接口调用受保护的虚函数
- 提供稳定的 API,同时保留实现灵活性

### 权限控制模式
通过友元类 GrBaseContextPriv 控制内部访问:
- 公共 API 保持最小化
- 内部实现通过 priv() 访问
- 平衡了封装和内部使用需求

### 上下文 ID 共享机制
所有兼容上下文共享相同的 ID:
```
创建线程 → ImageCreationContext (ID: 42)
     ↓
录制线程 → DDLRecorder (ID: 42)
     ↓
回放线程 → DirectContext (ID: 42)
```
这允许在不同线程和上下文类型间安全地传递 GPU 资源。

## 性能考量

### 线程安全代理优化
ThreadSafeProxy 是线程安全的,可以在多线程环境中自由共享:
- 避免了为每个上下文复制能力信息的开销
- 减少内存占用
- 支持高效的多线程图形管线

### 虚函数开销
基类使用虚函数表,引入少量间接调用开销:
- 对于 GPU 操作而言,这个开销可以忽略不计
- 提供的灵活性和类型安全性价值远大于开销
- 现代 CPU 的分支预测可以有效缓解虚函数调用成本

### 格式查询缓存
defaultBackendFormat 的结果应该被缓存使用:
- 保证与 createBackendTexture 的一致性
- 避免重复查询相同格式
- 上层代码通常在初始化时查询一次

### 智能指针开销
使用 sk_sp 管理 ThreadSafeProxy:
- 引用计数有少量原子操作开销
- 保证线程安全的生命周期管理
- 避免手动内存管理的错误

## 上下文继承层级

```
GrContext_Base (基础接口)
    ├─ GrImageContext (图像上下文,用于 SkImage)
    │   └─ GrRecordingContext (录制上下文,用于 DDL)
    │       └─ GrDirectContext (直接上下文,完整功能)
```

每个层级添加新能力:
- **Base**: 格式查询、后端类型、基础能力
- **Image**: 单一所有者守卫、放弃机制
- **Recording**: 录制操作、延迟显示列表支持
- **Direct**: 立即执行、资源管理、上下文刷新

## 使用场景

### 跨上下文资源验证
使用 contextID 验证资源是否属于兼容的上下文:
```cpp
if (!context->matches(resource->getContext())) {
    // 错误:资源属于不同的上下文系列
}
```

### 后端格式协商
在创建纹理前查询支持的格式:
```cpp
auto format = context->defaultBackendFormat(kRGBA_8888_SkColorType, GrRenderable::kYes);
if (!format.isValid()) {
    // 不支持可渲染的 RGBA8 格式
}
```

### 能力查询
确定是否支持 MSAA:
```cpp
int maxSamples = context->maxSurfaceSampleCountForColorType(colorType);
if (maxSamples > 1) {
    // 支持 MSAA,可以使用抗锯齿
}
```

## 相关文件
| 文件 | 关系 |
|------|------|
| include/gpu/GrContextThreadSafeProxy.h | 包装的线程安全代理 |
| include/private/gpu/ganesh/GrImageContext.h | 派生类 |
| include/gpu/GrRecordingContext.h | 进一步派生类 |
| include/gpu/GrDirectContext.h | 最终派生类 |
| include/private/gpu/ganesh/GrBaseContextPriv.h | 私有 API 访问器 |
| include/gpu/GrBackendSurface.h | 后端格式定义 |
| src/gpu/ganesh/GrCaps.h | 能力查询实现 |
| include/gpu/GrContextOptions.h | 上下文选项 |
