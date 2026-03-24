# GrMtlSampler

> 源文件
> - `src/gpu/ganesh/mtl/GrMtlSampler.h`
> - `src/gpu/ganesh/mtl/GrMtlSampler.mm`

## 概述

`GrMtlSampler` 是 Ganesh 图形后端中 Metal 实现的采样器类,封装了 Metal 的 `MTLSamplerState` 对象。该类负责将 Skia 的采样器状态配置转换为 Metal 采样器对象,并提供缓存支持以避免重复创建相同配置的采样器。采样器定义了纹理读取时的过滤模式、地址模式、各向异性过滤等参数,是纹理采样管线的关键组件。

## 架构位置

`GrMtlSampler` 位于 Skia 图形库的 GPU 后端纹理采样层次结构中:

```
Skia 图形库
└── GPU 后端 (src/gpu)
    └── Ganesh 渲染引擎 (ganesh)
        ├── GrManagedResource (资源管理基类)
        │   └── GrMtlSampler (Metal 采样器) ← 当前类
        └── Metal 后端实现 (mtl)
            ├── GrMtlGpu (GPU 接口)
            ├── GrMtlResourceProvider (资源提供者)
            └── MTLSamplerState (Metal 采样器对象)
```

该类为 Metal 后端提供采样器管理,与资源提供者协作实现采样器复用。

## 主要类与结构体

### GrMtlSampler 类

Metal 采样器封装类,提供缓存支持。

**继承关系:**
- 继承: `GrManagedResource` (托管资源基类)

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fMtlSamplerState` | `mutable id<MTLSamplerState>` | Metal 采样器状态对象 |
| `fKey` | `Key` (uint32_t) | 采样器配置哈希键 |

### Key 类型

```cpp
typedef uint32_t Key;
```

32 位无符号整数,用于采样器配置的唯一标识和哈希。

## 公共 API 函数

### 工厂方法

```cpp
static GrMtlSampler* Create(const GrMtlGpu* gpu, GrSamplerState samplerState)
```
从 Skia 采样器状态创建 Metal 采样器对象。配置包括过滤模式、地址模式、mipmap 模式和各向异性过滤。

### 访问器

```cpp
id<MTLSamplerState> mtlSampler() const
```
返回底层 Metal 采样器状态对象。

### 哈希支持

```cpp
static Key GenerateKey(GrSamplerState samplerState)
```
从采样器状态生成唯一哈希键,用于缓存查找。

```cpp
static const Key& GetKey(const GrMtlSampler& sampler)
```
获取采样器对象的哈希键。

```cpp
static uint32_t Hash(const Key& key)
```
计算键的哈希值,用于哈希表。

## 内部实现细节

### 采样器创建流程

`Create()` 方法构建 Metal 采样器描述符并创建采样器:

```objc
auto samplerDesc = [[MTLSamplerDescriptor alloc] init];

// 配置地址模式
samplerDesc.sAddressMode = wrap_mode_to_mtl_sampler_address(wrapModeX);
samplerDesc.tAddressMode = wrap_mode_to_mtl_sampler_address(wrapModeY);
samplerDesc.rAddressMode = MTLSamplerAddressModeClampToEdge;

// 配置过滤模式
samplerDesc.minFilter = minMagFilter;
samplerDesc.magFilter = minMagFilter;
samplerDesc.mipFilter = mipFilter;

// 配置 LOD 范围
samplerDesc.lodMinClamp = 0.0f;
samplerDesc.lodMaxClamp = FLT_MAX;

// 配置各向异性过滤
samplerDesc.maxAnisotropy = std::min(maxAniso, 16);

// 创建采样器
id<MTLSamplerState> sampler = [device newSamplerStateWithDescriptor: desc];
```

### 地址模式转换

`wrap_mode_to_mtl_sampler_address()` 将 Skia 地址模式映射到 Metal:

| Skia 模式 | Metal 模式 | 说明 |
|-----------|------------|------|
| `kClamp` | `MTLSamplerAddressModeClampToEdge` | 边缘夹持 |
| `kRepeat` | `MTLSamplerAddressModeRepeat` | 重复平铺 |
| `kMirrorRepeat` | `MTLSamplerAddressModeMirrorRepeat` | 镜像重复 |
| `kClampToBorder` | `MTLSamplerAddressModeClampToBorderColor` | 边界颜色(仅 macOS 10.12+) |

对于 `kClampToBorder`,使用条件编译和运行时检查:

```cpp
#ifdef SK_BUILD_FOR_MAC
    if (@available(macOS 10.12, *)) {
        return MTLSamplerAddressModeClampToBorderColor;
    }
#endif
```

iOS 不支持此模式,回退到 `ClampToEdge`。

### 过滤模式转换

使用 lambda 表达式简洁转换过滤模式:

```cpp
MTLSamplerMinMagFilter minMagFilter = [&] {
    switch (samplerState.filter()) {
        case Filter::kNearest: return MTLSamplerMinMagFilterNearest;
        case Filter::kLinear:  return MTLSamplerMinMagFilterLinear;
    }
    SkUNREACHABLE;
}();
```

支持最近邻(Nearest)和线性(Linear)过滤。

### Mipmap 模式转换

Mipmap 过滤支持三种模式:

```cpp
MTLSamplerMipFilter mipFilter = [&] {
    switch (samplerState.mipmapMode()) {
        case MipmapMode::kNone:    return MTLSamplerMipFilterNotMipmapped;
        case MipmapMode::kNearest: return MTLSamplerMipFilterNearest;
        case MipmapMode::kLinear:  return MTLSamplerMipFilterLinear;
    }
}();
```

- `kNone`: 不使用 mipmap
- `kNearest`: 选择最近的 mipmap 层级
- `kLinear`: 在 mipmap 层级间线性插值

### 各向异性过滤

Metal 要求各向异性值在 1-16 之间:

```cpp
samplerDesc.maxAnisotropy = std::min(samplerState.maxAniso(), 16);
```

超过 16 的值被截断到 16。

### 比较函数配置

设置深度比较函数为 `Never`:

```objc
if (@available(macOS 10.11, iOS 9.0, tvOS 9.0, *)) {
    samplerDesc.compareFunction = MTLCompareFunctionNever;
}
```

这表示采样器不用于深度比较(shadow map)。

### 键生成策略

`GenerateKey()` 调用 `GrSamplerState::asKey()`:

```cpp
return samplerState.asKey(/*anisoIsOrthogonal=*/true);
```

参数 `anisoIsOrthogonal=true` 表示各向异性过滤与其他设置正交考虑,确保不同各向异性值生成不同键。

### 哈希计算

使用 `SkChecksum::Hash32` 计算键的哈希值:

```cpp
static uint32_t Hash(const Key& key) {
    return SkChecksum::Hash32(&key, sizeof(Key));
}
```

这为动态哈希表提供高效的哈希函数。

### 资源释放

实现 `freeGPUData()` 释放 Metal 采样器:

```cpp
void freeGPUData() const override {
    fMtlSamplerState = nil;
}
```

标记为 `mutable` 的成员变量允许在 `const` 方法中修改。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrManagedResource` | 资源管理基类 |
| `GrMtlGpu` | Metal GPU 接口,提供设备访问 |
| `GrSamplerState` | Skia 采样器状态表示 |
| `GrCaps` | 能力查询接口 |
| `SkChecksum` | 哈希计算工具 |
| `Metal.framework` | Metal API |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|----------|
| `GrMtlResourceProvider` | 缓存和管理采样器对象 |
| `GrMtlPipelineState` | 绑定采样器到渲染管线 |
| `GrMtlOpsRenderPass` | 使用采样器进行纹理采样 |

## 设计模式与设计决策

### 1. 享元模式 (Flyweight Pattern)

采样器对象被缓存和共享,避免重复创建相同配置的采样器:

```cpp
// GrMtlResourceProvider 中
GrMtlSampler* sampler = fSamplers.find(key);
if (!sampler) {
    sampler = GrMtlSampler::Create(fGpu, params);
    fSamplers.add(sampler);
}
```

### 2. 工厂模式 (Factory Pattern)

静态 `Create()` 方法封装复杂的创建逻辑:

```cpp
static GrMtlSampler* Create(const GrMtlGpu* gpu, GrSamplerState);
```

### 3. 适配器模式 (Adapter Pattern)

将 Skia 的 `GrSamplerState` 适配为 Metal 的 `MTLSamplerState`:

```
GrSamplerState → GrMtlSampler → MTLSamplerState
```

### 4. RAII 资源管理

析构函数自动释放 Metal 采样器:

```cpp
~GrMtlSampler() override { fMtlSamplerState = nil; }
```

### 5. 不可变对象

采样器创建后配置不可变,确保缓存安全:

```cpp
private:
    GrMtlSampler(id<MTLSamplerState>, Key);
```

私有构造函数防止外部修改。

### 6. 策略模式 (Strategy)

不同的过滤和地址模式作为策略配置,通过 `GrSamplerState` 传递。

## 性能考量

### 1. 采样器缓存

通过 `GrMtlResourceProvider` 缓存采样器对象,避免重复创建:
- Metal 采样器创建有一定开销
- 缓存提供 O(1) 查找性能
- 相同配置的纹理共享采样器

### 2. 轻量级键

使用 32 位整数作为键,内存占用小:
- 键大小仅 4 字节
- 哈希计算快速
- 比较操作高效

### 3. 静态哈希函数

哈希函数使用高效的 `SkChecksum::Hash32`:
- 针对小数据优化
- 良好的分布特性
- 避免哈希冲突

### 4. 各向异性限制

限制各向异性值到 16:
- 符合 Metal 规范
- 避免无效配置
- 高值收益递减

### 5. LOD 范围默认值

使用最大 LOD 范围(0 到 FLT_MAX):
- 允许所有 mipmap 层级
- 避免意外截断
- 简化配置

### 6. 内联访问器

`mtlSampler()` 等访问器适合内联:
- 简单的返回操作
- 无额外开销
- 编译器优化友好

### 7. 平台条件编译

使用条件编译避免引用不支持的符号:

```cpp
#ifdef SK_BUILD_FOR_MAC
    MTLSamplerAddressModeClampToBorderColor
#endif
```

iOS 构建不会引用 macOS 特定功能,避免链接错误。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrManagedResource.h` | 继承关系 | 资源管理基类 |
| `src/gpu/ganesh/mtl/GrMtlGpu.h/mm` | 使用关系 | GPU 接口 |
| `src/gpu/ganesh/mtl/GrMtlResourceProvider.h/mm` | 被使用关系 | 采样器缓存管理 |
| `src/gpu/ganesh/mtl/GrMtlPipelineState.h/mm` | 被使用关系 | 绑定采样器 |
| `src/gpu/ganesh/GrSamplerState.h` | 使用关系 | 采样器状态表示 |
| `src/core/SkChecksum.h` | 使用关系 | 哈希计算 |
