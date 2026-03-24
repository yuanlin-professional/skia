# GrMtlDepthStencil

> 源文件
> - src/gpu/ganesh/mtl/GrMtlDepthStencil.h
> - src/gpu/ganesh/mtl/GrMtlDepthStencil.mm

## 概述

`GrMtlDepthStencil` 是 Skia 图形库中 Metal 后端的深度模板状态管理类,继承自 `GrManagedResource`。它封装了 Metal 的 `id<MTLDepthStencilState>` 对象,并提供基于 Skia 的 `GrStencilSettings` 的状态创建和缓存机制。该类通过哈希键实现状态对象的高效查找和复用。

## 架构位置

```
Skia Graphics Library
└── src/gpu/ganesh/mtl/
    ├── GrMtlGpu              (Metal GPU管理器)
    ├── GrMtlDepthStencil     (深度模板状态) ← 当前类
    └── GrMtlRenderCommandEncoder (使用深度模板状态)
```

## 主要类与结构体

### GrMtlDepthStencil

Metal 深度模板状态封装类,支持缓存和快速查找。

**继承关系:**
- 基类: `GrManagedResource`
- 派生类: 无(终端类)

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fMtlDepthStencilState` | `mutable id<MTLDepthStencilState>` | Metal 深度模板状态对象 |
| `fKey` | `Key` | 状态的唯一标识键 |

### Key 结构体

用于状态哈希和比较的键类型。

**成员变量:**

| 成员 | 类型 | 说明 |
|-----|------|------|
| `fFront` | `Face` | 前向面模板配置 |
| `fBack` | `Face` | 背向面模板配置 |

### Face 结构体

单个面的模板配置。

| 成员 | 类型 | 说明 |
|-----|------|------|
| `fReadMask` | `uint32_t` | 模板读取掩码 |
| `fWriteMask` | `uint32_t` | 模板写入掩码 |
| `fOps` | `uint32_t` | 压缩的操作码(测试+通过操作+失败操作) |

## 公共 API 函数

### 工厂方法

```cpp
static GrMtlDepthStencil* Create(
    const GrMtlGpu* gpu,
    const GrStencilSettings& stencil,
    GrSurfaceOrigin origin
);
```
根据 Skia 模板设置和表面方向创建 Metal 深度模板状态。

### 访问器

```cpp
id<MTLDepthStencilState> mtlDepthStencil() const;
```
获取底层 Metal 状态对象。

### 哈希和查找辅助

```cpp
static Key GenerateKey(const GrStencilSettings&, GrSurfaceOrigin);
static const Key& GetKey(const GrMtlDepthStencil& depthStencil);
static uint32_t Hash(const Key& key);
```
生成哈希键和计算哈希值,用于状态缓存。

### 资源管理

```cpp
void freeGPUData() const override;  // 释放 Metal 对象

#ifdef SK_TRACE_MANAGED_RESOURCES
void dumpInfo() const override;     // 调试信息输出
#endif
```

## 内部实现细节

### 模板操作转换

#### Skia 操作到 Metal 操作映射

```cpp
MTLStencilOperation skia_stencil_op_to_mtl(GrStencilOp op) {
    switch (op) {
        case GrStencilOp::kKeep:      return MTLStencilOperationKeep;
        case GrStencilOp::kZero:      return MTLStencilOperationZero;
        case GrStencilOp::kReplace:   return MTLStencilOperationReplace;
        case GrStencilOp::kInvert:    return MTLStencilOperationInvert;
        case GrStencilOp::kIncWrap:   return MTLStencilOperationIncrementWrap;
        case GrStencilOp::kDecWrap:   return MTLStencilOperationDecrementWrap;
        case GrStencilOp::kIncClamp:  return MTLStencilOperationIncrementClamp;
        case GrStencilOp::kDecClamp:  return MTLStencilOperationDecrementClamp;
    }
}
```

#### Skia 测试到 Metal 比较函数映射

```cpp
MTLStencilDescriptor* skia_stencil_to_mtl(GrStencilSettings::Face face) {
    MTLStencilDescriptor* result = [[MTLStencilDescriptor alloc] init];

    switch (face.fTest) {
        case GrStencilTest::kAlways:   result.stencilCompareFunction = MTLCompareFunctionAlways; break;
        case GrStencilTest::kNever:    result.stencilCompareFunction = MTLCompareFunctionNever; break;
        case GrStencilTest::kGreater:  result.stencilCompareFunction = MTLCompareFunctionGreater; break;
        case GrStencilTest::kGEqual:   result.stencilCompareFunction = MTLCompareFunctionGreaterEqual; break;
        case GrStencilTest::kLess:     result.stencilCompareFunction = MTLCompareFunctionLess; break;
        case GrStencilTest::kLEqual:   result.stencilCompareFunction = MTLCompareFunctionLessEqual; break;
        case GrStencilTest::kEqual:    result.stencilCompareFunction = MTLCompareFunctionEqual; break;
        case GrStencilTest::kNotEqual: result.stencilCompareFunction = MTLCompareFunctionNotEqual; break;
    }

    result.readMask = face.fTestMask;
    result.writeMask = face.fWriteMask;
    result.depthStencilPassOperation = skia_stencil_op_to_mtl(face.fPassOp);
    result.stencilFailureOperation = skia_stencil_op_to_mtl(face.fFailOp);

    return result;
}
```

### 状态创建流程

```cpp
GrMtlDepthStencil* GrMtlDepthStencil::Create(
    const GrMtlGpu* gpu,
    const GrStencilSettings& stencil,
    GrSurfaceOrigin origin
) {
    MTLDepthStencilDescriptor* desc = [[MTLDepthStencilDescriptor alloc] init];

    if (!stencil.isDisabled()) {
        if (stencil.isTwoSided()) {
            // 双面模板:根据表面方向分配前后面
            desc.frontFaceStencil = skia_stencil_to_mtl(
                stencil.postOriginCCWFace(origin));
            desc.backFaceStencil = skia_stencil_to_mtl(
                stencil.postOriginCWFace(origin));
        } else {
            // 单面模板:前后面使用相同配置
            desc.frontFaceStencil = skia_stencil_to_mtl(
                stencil.singleSidedFace());
            desc.backFaceStencil = desc.frontFaceStencil;
        }
    }

    id<MTLDepthStencilState> mtlState =
        [gpu->device() newDepthStencilStateWithDescriptor:desc];

    return new GrMtlDepthStencil(mtlState, GenerateKey(stencil, origin));
}
```

### 哈希键生成

```cpp
void skia_stencil_to_key(GrStencilSettings::Face face,
                        GrMtlDepthStencil::Key::Face* faceKey) {
    const int kPassOpShift = 3;
    const int kFailOpShift = 6;

    faceKey->fReadMask = face.fTestMask;
    faceKey->fWriteMask = face.fWriteMask;

    // 将操作压缩到 uint32_t 的不同位段
    SkASSERT(static_cast<int>(face.fTest) <= 7);
    faceKey->fOps = static_cast<uint32_t>(face.fTest);

    SkASSERT(static_cast<int>(face.fPassOp) <= 7);
    faceKey->fOps |= (static_cast<uint32_t>(face.fPassOp) << kPassOpShift);

    SkASSERT(static_cast<int>(face.fFailOp) <= 7);
    faceKey->fOps |= (static_cast<uint32_t>(face.fFailOp) << kFailOpShift);
}

GrMtlDepthStencil::Key GrMtlDepthStencil::GenerateKey(
    const GrStencilSettings& stencil,
    GrSurfaceOrigin origin
) {
    Key depthStencilKey;

    if (stencil.isDisabled()) {
        memset(&depthStencilKey, 0, sizeof(Key));
    } else {
        if (stencil.isTwoSided()) {
            skia_stencil_to_key(stencil.postOriginCCWFace(origin),
                               &depthStencilKey.fFront);
            skia_stencil_to_key(stencil.postOriginCWFace(origin),
                               &depthStencilKey.fBack);
        } else {
            skia_stencil_to_key(stencil.singleSidedFace(),
                               &depthStencilKey.fFront);
            memcpy(&depthStencilKey.fBack, &depthStencilKey.fFront,
                   sizeof(Key::Face));
        }
    }

    return depthStencilKey;
}
```

### 哈希计算

```cpp
static uint32_t Hash(const Key& key) {
    return SkChecksum::Hash32(&key, sizeof(Key));
}
```
使用 Skia 的校验和工具计算键的哈希值。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `GrManagedResource` | 基类,资源生命周期管理 |
| `GrStencilSettings` | Skia 模板配置 |
| `GrMtlGpu` | GPU 管理器,提供 Metal 设备 |
| `Metal/Metal.h` | Metal API |
| `SkChecksum` | 哈希计算 |

### 被依赖的模块

| 模块 | 使用场景 |
|-----|---------|
| `GrMtlRenderCommandEncoder` | 绑定深度模板状态 |
| `GrMtlResourceProvider` | 缓存深度模板状态 |
| `GrMtlPipelineState` | 管线状态包含深度模板配置 |

## 设计模式与设计决策

### 不可变对象模式
Metal 的深度模板状态是不可变的,创建后无法修改,符合函数式编程范式。

### 哈希表缓存
通过 `Key` 结构体和哈希函数支持高效的状态对象缓存和查找。

### 操作码压缩
将测试函数、通过操作和失败操作压缩到单个 `uint32_t` 的不同位段:
- Bit 0-2: 测试函数(8 种)
- Bit 3-5: 通过操作(8 种)
- Bit 6-8: 失败操作(8 种)

这使得键的大小最小化(24 字节),提高缓存效率。

### 表面方向处理
通过 `postOriginCCWFace` 和 `postOriginCWFace` 方法自动处理表面方向对前后面定义的影响。

### 调试支持
在 `SK_TRACE_MANAGED_RESOURCES` 宏开启时提供状态对象的引用计数追踪。

## 性能考量

### 状态对象复用
Metal 深度模板状态创建有显著开销(~50μs),通过缓存机制避免重复创建。

### 哈希键优化
- **固定大小:** `Key` 结构体为 24 字节,适合缓存行
- **快速比较:** `operator==` 仅需 6 次整数比较
- **高效哈希:** 使用 Murmur3 哈希算法,冲突率低

### 位域压缩
操作码压缩减少键的大小和比较开销。

### 延迟释放
使用 `mutable` 标记 `fMtlDepthStencilState`,允许 `freeGPUData` 在 const 对象上调用,支持延迟清理策略。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrManagedResource.h` | 基类 | 资源生命周期管理 |
| `src/gpu/ganesh/GrStencilSettings.h` | 配置 | Skia 模板设置 |
| `src/gpu/ganesh/mtl/GrMtlGpu.h` | 管理者 | GPU 设备提供者 |
| `src/gpu/ganesh/mtl/GrMtlResourceProvider.h` | 缓存 | 状态对象缓存管理 |
| `src/core/SkChecksum.h` | 工具 | 哈希计算 |
| `Metal/Metal.h` | API | Metal 框架 |
