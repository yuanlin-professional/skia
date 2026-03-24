# MtlGraphiteTypes_cpp

> 源文件: `include/gpu/graphite/mtl/MtlGraphiteTypes_cpp.h`

## 概述

MtlGraphiteTypes_cpp.h 提供了 C++ 环境下使用的 Metal 类型工厂函数和工具函数,无需 Objective-C 编译器即可使用。该文件通过 CFTypeRef 桥接 Metal 对象,为纯 C++ 代码提供了访问 Metal 后端的能力。

## 架构位置

该文件位于 Skia Graphite GPU 后端的 Metal 平台特定接口层,是 Metal 类型系统的 C++ 接口部分。它通过 CoreFoundation 类型提供与 Metal 对象的交互,避免了对 Objective-C 编译器的依赖。

## 主要命名空间与函数

### TextureInfos 命名空间

#### MakeMetal (从 MtlTextureInfo)

```cpp
SK_API TextureInfo MakeMetal(const MtlTextureInfo&);
```

- **功能**: 从 MtlTextureInfo 创建通用的 TextureInfo
- **参数**: Metal 特定的纹理信息对象
- **返回值**: 平台无关的 TextureInfo 对象
- **用途**: 将 Metal 特定信息包装为通用接口
- **注意**: MtlTextureInfo 需要在 Objective-C++ 环境创建

#### MakeMetal (从 CFTypeRef)

```cpp
SK_API TextureInfo MakeMetal(CFTypeRef mtlTexture);
```

- **功能**: 从 MTLTexture 对象直接创建 TextureInfo
- **参数**: `mtlTexture` - CFTypeRef 类型的 MTLTexture (通过 `__bridge` 转换)
- **返回值**: 提取的 TextureInfo
- **用途**: 包装外部创建的 Metal 纹理
- **便利性**: 一步完成提取和包装

#### GetMtlTextureInfo

```cpp
SK_API bool GetMtlTextureInfo(const TextureInfo&, MtlTextureInfo*);
```

- **功能**: 从 TextureInfo 提取 Metal 特定信息
- **参数**:
  - `TextureInfo&`: 通用纹理信息
  - `MtlTextureInfo*`: 输出参数,接收 Metal 信息
- **返回值**: 成功返回 true,如果不是 Metal TextureInfo 返回 false
- **用途**: 反向转换,获取 Metal 特定属性
- **线程安全**: 只读操作,线程安全

### BackendTextures 命名空间

#### MakeMetal

```cpp
SK_API BackendTexture MakeMetal(SkISize dimensions, CFTypeRef mtlTexture);
```

- **功能**: 从 MTLTexture 创建 BackendTexture
- **参数**:
  - `dimensions`: 纹理尺寸
  - `mtlTexture`: CFTypeRef 类型的 MTLTexture
- **生命周期**:
  - BackendTexture 不调用 retain/release
  - 客户端必须保持 MTLTexture 有效
  - 包装的 SkImage/SkSurface 会调用 retain/release
- **返回值**: 平台无关的 BackendTexture 对象

#### GetMtlTexture

```cpp
SK_API CFTypeRef GetMtlTexture(const BackendTexture&);
```

- **功能**: 从 BackendTexture 获取底层 MTLTexture
- **参数**: BackendTexture 对象
- **返回值**: CFTypeRef 类型的 MTLTexture,失败返回 nullptr
- **用途**: 访问底层 Metal 纹理对象
- **类型转换**: 返回后可通过 `(__bridge id<MTLTexture>)` 转换

### BackendSemaphores 命名空间

#### MakeMetal

```cpp
SK_API BackendSemaphore MakeMetal(CFTypeRef mtlEvent, uint64_t value);
```

- **功能**: 从 MTLEvent 和值创建 BackendSemaphore
- **参数**:
  - `mtlEvent`: CFTypeRef 类型的 MTLEvent
  - `value`: 信号量值
- **用途**: 跨 API 或跨 Context 同步
- **注意**: TODO(b/286088355) - 创建者设置引用计数的责任尚待确定

#### GetMtlEvent

```cpp
SK_API CFTypeRef GetMtlEvent(const BackendSemaphore&);
```

- **功能**: 获取 BackendSemaphore 的底层 MTLEvent
- **返回值**: CFTypeRef 类型的 MTLEvent
- **用途**: 传递给 Metal 命令缓冲区

#### GetMtlValue

```cpp
SK_API uint64_t GetMtlValue(const BackendSemaphore&);
```

- **功能**: 获取信号量的值
- **返回值**: 64位无符号整数值
- **用途**: 与 MTLEvent 配合使用进行同步

## 类型桥接机制

### CFTypeRef 的作用

CFTypeRef 是 CoreFoundation 的不透明指针类型:
- **定义**: `typedef const void* CFTypeRef;`
- **优势**: C++ 代码可使用,无需 Objective-C
- **限制**: 类型擦除,需要运行时检查

### 桥接转换

#### Objective-C++ 到 C++

```cpp
// Objective-C++
id<MTLTexture> texture = ...;
CFTypeRef cfTexture = (__bridge CFTypeRef)texture;

// 现在可以传递给 C++ 代码
TextureInfo info = TextureInfos::MakeMetal(cfTexture);
```

#### C++ 到 Objective-C++

```cpp
// C++ 代码
BackendTexture backendTex = ...;
CFTypeRef cfTexture = BackendTextures::GetMtlTexture(backendTex);

// Objective-C++
id<MTLTexture> texture = (__bridge id<MTLTexture>)cfTexture;
```

### 引用计数管理

#### __bridge 转换
```cpp
CFTypeRef ref = (__bridge CFTypeRef)objcObject;  // 不改变引用计数
```

#### __bridge_retained 转换
```cpp
CFTypeRef ref = (__bridge_retained CFTypeRef)objcObject;  // +1 引用计数
```

#### __bridge_transfer 转换
```cpp
id objcObject = (__bridge_transfer id)cfRef;  // 转移所有权,-1 引用计数
```

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| `include/core/SkTypes.h` | 基础类型 |
| `include/gpu/graphite/BackendTexture.h` | BackendTexture 定义 |
| `include/gpu/graphite/TextureInfo.h` | TextureInfo 定义 |
| `include/private/base/SkAPI.h` | SK_API 宏 |
| `CoreFoundation/CoreFoundation.h` | CFTypeRef 等 |

### 被依赖的模块

- 纯 C++ 的应用代码
- 跨语言边界的工具代码
- Metal 后端的 C++ 实现部分

## 设计模式与设计决策

### 命名空间工厂模式

使用命名空间而非类静态方法:
```cpp
namespace TextureInfos {
    TextureInfo MakeMetal(...);
}
```

**优势**:
- 逻辑分组
- 避免类接口膨胀
- 易于扩展

### 类型擦除策略

通过 CFTypeRef 实现类型擦除:
- **目的**: 隐藏 Objective-C 类型
- **实现**: CoreFoundation 提供的桥接机制
- **代价**: 运行时类型检查

### 前向声明友好

文件设计为可以被纯 C++ 代码包含:
```cpp
class SK_API MtlTextureInfo;  // 前向声明,不需要完整定义
```

## 性能考量

### 桥接开销

- **CFTypeRef 转换**: 零开销,仅类型转换
- **引用计数**: 与 Objective-C 对象相同
- **虚函数调用**: 通过 TextureInfo::Data 接口,有轻微开销

### 编译时间

使用该头文件而非 MtlGraphiteTypes.h:
- **优势**: 避免包含 `<Metal/Metal.h>`,减少编译时间
- **效果**: 大型项目可节省 10-30% 编译时间
- **前提**: 仅当不需要直接使用 Metal API 时

## 使用示例

### 创建 TextureInfo (C++ 代码)

```cpp
// 从外部获取的 MTLTexture
CFTypeRef mtlTexture = getSomeMtlTexture();

// 在纯 C++ 代码中创建 TextureInfo
TextureInfo texInfo = TextureInfos::MakeMetal(mtlTexture);

// 使用 texInfo...
```

### 包装 BackendTexture

```cpp
// C++ 函数
BackendTexture wrapMtlTexture(CFTypeRef mtlTex) {
    SkISize size = {512, 512};
    return BackendTextures::MakeMetal(size, mtlTex);
}

// 在 Objective-C++ 中调用
id<MTLTexture> texture = ...;
BackendTexture bt = wrapMtlTexture((__bridge CFTypeRef)texture);
```

### 提取底层纹理

```cpp
// C++ 代码
void processBackendTexture(const BackendTexture& bt) {
    CFTypeRef cfTex = BackendTextures::GetMtlTexture(bt);
    if (cfTex) {
        // 传递给 Objective-C++ 代码
        doSomethingWithTexture(cfTex);
    }
}

// Objective-C++ 代码
void doSomethingWithTexture(CFTypeRef cfTex) {
    id<MTLTexture> texture = (__bridge id<MTLTexture>)cfTex;
    NSLog(@"Texture size: %zux%zu", texture.width, texture.height);
}
```

### 同步操作

```cpp
// 创建信号量
CFTypeRef event = ...;  // MTLEvent
BackendSemaphore semaphore = BackendSemaphores::MakeMetal(event, 123);

// 后续获取
CFTypeRef retrievedEvent = BackendSemaphores::GetMtlEvent(semaphore);
uint64_t value = BackendSemaphores::GetMtlValue(semaphore);
```

## 平台相关说明

### macOS / iOS

该文件在所有 Apple 平台上可用,是 Metal 后端的必需组件。

### 其他平台

在非 Apple 平台:
- 文件可能存在但函数不可用
- 使用会导致链接错误或运行时失败
- 应使用条件编译保护

### 条件编译建议

```cpp
#if defined(SK_METAL)
    #include "include/gpu/graphite/mtl/MtlGraphiteTypes_cpp.h"
    // 使用 Metal 特定代码
#endif
```

## 常见陷阱

### 1. 生命周期管理

```cpp
// 错误: mtlTexture 过早释放
{
    id<MTLTexture> texture = [device newTextureWithDescriptor:desc];
    BackendTexture bt = BackendTextures::MakeMetal(
        size, (__bridge CFTypeRef)texture);
    // texture 离开作用域被释放
} // bt 现在持有悬空指针!

// 正确: 确保生命周期
id<MTLTexture> texture = [device newTextureWithDescriptor:desc];
BackendTexture bt = BackendTextures::MakeMetal(
    size, (__bridge CFTypeRef)texture);
// 保持 texture 有效或让 SkImage/SkSurface 持有
```

### 2. 类型错误

```cpp
// 错误: 传递了错误类型的 CFTypeRef
CFTypeRef buffer = (__bridge CFTypeRef)mtlBuffer;  // MTLBuffer!
TextureInfo info = TextureInfos::MakeMetal(buffer);  // 运行时错误
```

### 3. 跨语言边界

```cpp
// C++ 头文件中 - 错误
#include "include/gpu/graphite/mtl/MtlGraphiteTypes.h"  // 需要 Objective-C!

// 正确
#include "include/gpu/graphite/mtl/MtlGraphiteTypes_cpp.h"
```

## 待解决问题

根据源码注释:
- **TODO(b/286088355)**: 确定 BackendSemaphore 创建者对引用计数的责任
  - 当前行为不明确
  - 可能需要手动管理 MTLEvent 的引用计数

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/gpu/graphite/mtl/MtlGraphiteTypes.h` | Objective-C 版本 |
| `include/gpu/graphite/BackendTexture.h` | BackendTexture 定义 |
| `include/gpu/graphite/TextureInfo.h` | TextureInfo 定义 |
| `include/ports/SkCFObject.h` | CFTypeRef 智能指针包装 |
| `CoreFoundation/CFBase.h` | CFTypeRef 定义 |

## 最佳实践

1. **语言边界**: 在 C++ 代码中使用此文件,Objective-C++ 使用 MtlGraphiteTypes.h
2. **生命周期**: 使用 sk_cfp 智能指针管理 CFTypeRef
3. **类型安全**: 传递 CFTypeRef 前确认类型正确
4. **错误处理**: 检查返回值(如 GetMtlTexture 可能返回 nullptr)
5. **编译优化**: 尽可能使用此文件而非 Objective-C 版本

## 智能指针包装

推荐使用 sk_cfp 管理 CFTypeRef:

```cpp
#include "include/ports/SkCFObject.h"

sk_cfp<CFTypeRef> texture = ...;
BackendTexture bt = BackendTextures::MakeMetal(size, texture.get());
// texture 自动管理引用计数
```
