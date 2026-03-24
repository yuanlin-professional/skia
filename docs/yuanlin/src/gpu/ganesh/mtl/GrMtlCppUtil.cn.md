# GrMtlCppUtil

> 源文件
> - src/gpu/ganesh/mtl/GrMtlCppUtil.h

## 概述

`GrMtlCppUtil` 是 Skia 图形库中 Metal 后端的 C++ 工具头文件,提供了可从纯 C++ 代码访问的 Metal 类型转换和查询函数。由于 Metal API 是 Objective-C 接口,这些工具函数充当了 C++ 代码和 Objective-C++ 实现之间的桥梁。

## 架构位置

```
Skia Graphics Library
└── src/gpu/ganesh/mtl/
    ├── GrMtlCppUtil.h       (C++工具接口) ← 当前文件
    └── GrMtlUtil.h/.mm      (Objective-C++实现)
```

## 公共 API 函数

### 像素格式查询

```cpp
GrMTLPixelFormat GrGetMTLPixelFormatFromMtlTextureInfo(
    const GrMtlTextureInfo& info
);
```
从 `GrMtlTextureInfo` 结构体提取 Metal 像素格式。

**用途:** 允许 C++ 代码查询纹理格式而无需直接访问 Objective-C 对象。

### 采样数查询

```cpp
int GrMtlTextureInfoSampleCount(const GrMtlTextureInfo& info);
```
获取纹理的采样数,如果纹理为 nil 则返回 0。

**返回值:**
- `> 0`: 纹理的采样级别
- `0`: 纹理为空或不存在

### 格式检查(调试/测试)

```cpp
#if defined(SK_DEBUG) || defined(GPU_TEST_UTILS)
bool GrMtlFormatIsBGRA8(GrMTLPixelFormat mtlFormat);
#endif
```
检查给定格式是否为 BGRA8 格式。

**可用性:** 仅在调试模式或 GPU 测试工具启用时可用。

## 内部实现细节

### C++/Objective-C 桥接

这些函数的实际实现位于对应的 `.mm` 文件中,通过以下方式工作:

```cpp
// .h 文件(纯C++)
GrMTLPixelFormat GrGetMTLPixelFormatFromMtlTextureInfo(
    const GrMtlTextureInfo& info);

// .mm 文件(Objective-C++)
GrMTLPixelFormat GrGetMTLPixelFormatFromMtlTextureInfo(
    const GrMtlTextureInfo& info) {
    id<MTLTexture> texture = (__bridge id<MTLTexture>)info.fTexture.get();
    return texture ? (GrMTLPixelFormat)texture.pixelFormat : MTLPixelFormatInvalid;
}
```

### 类型转换策略

- **输入:** Skia 的 C++ 类型(`GrMtlTextureInfo`)
- **桥接:** Objective-C 的 `id<MTLTexture>` 类型
- **输出:** 平台无关的整数或枚举类型

### 条件编译

调试函数使用条件编译避免在发布版本中增加二进制大小:
```cpp
#if defined(SK_DEBUG) || defined(GPU_TEST_UTILS)
// 调试专用函数
#endif
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `GrMtlTypes.h` | Metal 类型定义 |
| `GrTypesPriv.h` | Ganesh 私有类型 |

### 被依赖的模块

| 模块 | 使用场景 |
|-----|---------|
| `GrMtlCaps` | 查询纹理格式能力 |
| `GrMtlTexture` | 获取纹理属性 |
| 单元测试 | 验证格式和采样配置 |

## 设计模式与设计决策

### 桥接模式
在 C++ 代码和 Objective-C 代码之间提供桥接层,隔离语言差异。

### 头文件纯净性
头文件不包含任何 Objective-C 语法,可安全地被纯 C++ 文件包含。

### 最小接口原则
仅暴露必要的查询函数,避免过度暴露 Metal API 细节。

### 空值安全
函数处理空纹理情况,返回安全的默认值(0 或 Invalid)。

## 性能考量

### 内联潜力
简单的查询函数可能被编译器内联,接近零开销。

### 无额外分配
所有函数仅执行类型转换和属性读取,无内存分配。

### 桥接成本
Objective-C 桥接(`__bridge`)是零成本抽象,无运行时开销。

## 使用场景

### 跨模块格式查询
```cpp
// 纯C++代码中查询纹理格式
GrMtlTextureInfo info = texture->getMtlTextureInfo();
GrMTLPixelFormat format = GrGetMTLPixelFormatFromMtlTextureInfo(info);
if (format == MTLPixelFormatBGRA8Unorm) {
    // 处理BGRA格式
}
```

### 采样级别验证
```cpp
int sampleCount = GrMtlTextureInfoSampleCount(info);
if (sampleCount > 1) {
    // MSAA 纹理处理
}
```

### 单元测试
```cpp
#if defined(GPU_TEST_UTILS)
REPORTER_ASSERT(reporter, GrMtlFormatIsBGRA8(format));
#endif
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/gpu/ganesh/mtl/GrMtlTypes.h` | 类型 | Metal 公共类型定义 |
| `include/private/gpu/ganesh/GrTypesPriv.h` | 类型 | Ganesh 私有类型 |
| `src/gpu/ganesh/mtl/GrMtlUtil.h` | 实现 | Objective-C++ 工具实现 |
| `src/gpu/ganesh/mtl/GrMtlCaps.mm` | 使用者 | 能力查询 |
| `src/gpu/ganesh/mtl/GrMtlTexture.mm` | 使用者 | 纹理管理 |
