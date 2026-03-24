# GrMockTypesPriv

> 源文件
> - src/gpu/ganesh/mock/GrMockTypesPriv.h

## 概述

`GrMockTypesPriv` 是 Skia 图形库中 Mock 后端的私有类型定义头文件,提供了 `GrMockTextureSpec` 结构体和相关的转换函数。该文件定义了 Mock 纹理的内部规格表示,用于在测试环境中模拟纹理格式和压缩类型配置。

## 架构位置

```
Skia Graphics Library
└── src/gpu/ganesh/mock/
    ├── GrMockTypes.h        (公共类型)
    └── GrMockTypesPriv.h    (私有类型) ← 当前文件
```

## 主要类与结构体

### GrMockTextureSpec

Mock 纹理规格描述结构体。

**关键成员变量:**

| 成员变量 | 类型 | 默认值 | 说明 |
|---------|------|--------|------|
| `fColorType` | `GrColorType` | `kUnknown` | Skia 颜色类型 |
| `fCompressionType` | `SkTextureCompressionType` | `kNone` | 纹理压缩类型 |

### 构造函数

```cpp
// 默认构造函数
GrMockTextureSpec();

// 从 GrMockSurfaceInfo 构造
GrMockTextureSpec(const GrMockSurfaceInfo& info);
```

## 公共 API 函数

### 转换函数

```cpp
GrMockSurfaceInfo GrMockTextureSpecToSurfaceInfo(
    const GrMockTextureSpec& mockSpec,
    uint32_t sampleCount,
    uint32_t levelCount,
    GrProtected isProtected
);
```
将 Mock 纹理规格转换为表面信息结构体,添加采样数、mipmap 层级和保护标志。

## 内部实现细节

### 类型映射关系

该文件建立了以下类型的映射关系:
```
GrMockTextureSpec <--> GrMockSurfaceInfo
    ├── fColorType         (核心)
    ├── fCompressionType   (核心)
    ├── sampleCount        (扩展)
    ├── levelCount         (扩展)
    └── isProtected        (扩展)
```

### 设计意图

- **分离关注点:** `GrMockTextureSpec` 仅关注格式,`GrMockSurfaceInfo` 包含完整配置
- **测试便利性:** 简化纹理规格的创建和传递
- **类型安全:** 避免直接使用 `GrMockSurfaceInfo` 的复杂初始化

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `GrTypesPriv.h` | Ganesh 私有类型定义 |
| `GrMockTypes.h` | Mock 公共类型 |
| `SkTextureCompressionType` | 压缩类型枚举 |

### 被依赖的模块

| 模块 | 使用场景 |
|-----|---------|
| `GrMockTexture` | 构造 Mock 纹理 |
| `GrMockGpu` | 创建纹理资源 |
| 单元测试 | 配置测试纹理格式 |

## 设计模式与设计决策

### 值对象模式
`GrMockTextureSpec` 是纯数据结构,无行为方法,用于传递配置信息。

### 转换函数分离
将转换逻辑从构造函数中分离出来,提供更灵活的初始化方式。

### 私有命名空间
使用 `Priv` 后缀表明这是内部实现细节,不应被公共 API 依赖。

## 性能考量

### 轻量级结构
仅包含两个枚举字段,总大小约 8 字节,可高效传值。

### 编译时优化
结构体足够简单,编译器可内联所有操作。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/gpu/ganesh/mock/GrMockTypes.h` | 公共接口 | Mock 后端公共类型 |
| `include/private/gpu/ganesh/GrTypesPriv.h` | 基础类型 | Ganesh 私有类型 |
| `src/gpu/ganesh/mock/GrMockTexture.h` | 使用者 | Mock 纹理实现 |
| `include/core/SkTextureCompressionType.h` | 依赖 | 纹理压缩类型定义 |
