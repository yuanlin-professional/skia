# GrGLBackendSurfacePriv

> 源文件
> - src/gpu/ganesh/gl/GrGLBackendSurfacePriv.h

## 概述

`GrGLBackendSurfacePriv.h` 定义了 OpenGL 后端表面的私有实现细节，主要包含 `GrGLBackendTextureData` 类和相关的工厂函数。该文件是 Skia Ganesh 渲染引擎中用于封装 OpenGL 纹理信息的内部接口，提供了创建和管理跨平台后端纹理对象的能力。这是一个头文件，不包含实现代码。

## 架构位置

该文件位于 Ganesh OpenGL 后端的私有接口层：

```
src/gpu/ganesh/
├── GrBackendSurface (跨平台抽象)
│   └── GrBackendSurfacePriv (私有实现接口)
│       └── gl/
│           └── GrGLBackendSurfacePriv.h (OpenGL 私有实现)
└── gl/
    └── GrGLGpu (OpenGL GPU 管理)
```

该文件桥接跨平台的 `GrBackendTexture` 和 OpenGL 特定的 `GrGLTextureInfo`。

## 主要类与结构体

### GrGLBackendTextureData

**继承关系：**
```
GrBackendTextureData (抽象基类)
  └── GrGLBackendTextureData (OpenGL 实现)
```

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fGLInfo` | `GrGLBackendTextureInfo` | OpenGL 纹理信息（ID、格式、参数等） |

## 公共 API 函数

### 命名空间 GrBackendTextures

#### MakeGL

```cpp
GrBackendTexture MakeGL(int width,
                        int height,
                        skgpu::Mipmapped,
                        const GrGLTextureInfo& glInfo,
                        sk_sp<GrGLTextureParameters> params,
                        std::string_view label = {});
```

**功能**：创建 OpenGL 后端纹理对象

**参数：**
- `width`, `height`：纹理尺寸
- `Mipmapped`：是否包含 mipmap
- `glInfo`：OpenGL 纹理信息（必须包含有效的 `fFormat`）
- `params`：纹理参数对象（过滤、wrap 模式等）
- `label`：可选的调试标签

**重要约束**：`GrGLTextureInfo` 必须包含有效的 `fFormat` 字段

### GrGLBackendTextureData 类

#### 构造函数

```cpp
GrGLBackendTextureData(const GrGLTextureInfo& info,
                       sk_sp<GrGLTextureParameters> params);
```

#### 查询方法

| 方法 | 返回类型 | 功能 |
|------|---------|------|
| `info()` | `const GrGLBackendTextureInfo&` | 获取 OpenGL 纹理信息 |

## 内部实现细节

### 私有虚函数覆盖

`GrGLBackendTextureData` 实现了 `GrBackendTextureData` 的所有虚函数：

| 虚函数 | 功能 |
|--------|------|
| `copyTo(AnyTextureData&)` | 复制纹理数据到通用容器 |
| `isProtected()` | 查询纹理是否受保护内容 |
| `equal(const GrBackendTextureData*)` | 比较两个纹理数据是否相等 |
| `isSameTexture(const GrBackendTextureData*)` | 判断是否指向同一 OpenGL 纹理 |
| `getBackendFormat()` | 获取后端格式 |
| `type()` (仅调试) | 返回 `GrBackendApi::kOpenGL` |

### GrGLBackendTextureInfo 类型

该类型封装 OpenGL 纹理的关键信息：
- **fID**：OpenGL 纹理对象 ID（`GLuint`）
- **fTarget**：纹理目标（如 `GL_TEXTURE_2D`）
- **fFormat**：内部格式（如 `GL_RGBA8`）
- **fProtected**：受保护内容标志
- **fParameters**：纹理参数状态

### GrGLTextureParameters

智能指针管理的纹理参数对象：
- 过滤模式（MIN/MAG filter）
- Wrap 模式（S/T wrap）
- Mipmap 级别范围
- 各向异性过滤

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrBackendSurface` | 跨平台后端表面抽象 |
| `GrBackendSurfacePriv` | 私有实现基类 |
| `GrGLTypesPriv` | OpenGL 类型定义 |
| `skgpu::Mipmapped` | Mipmap 枚举 |
| `SkRefCnt` | 智能指针支持 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|---------|
| `GrGLGpu` | 创建 OpenGL 纹理时使用 |
| `GrGLTexture` | 包装 OpenGL 纹理对象 |
| `GrBackendTexture` | 存储 OpenGL 纹理数据 |
| `SkImage_Ganesh` | 从 OpenGL 纹理创建 Skia 图像 |

## 设计模式与设计决策

### 桥接模式

`GrGLBackendTextureData` 作为桥接：
- **抽象侧**：`GrBackendTexture`（跨平台）
- **实现侧**：`GrGLTextureInfo`（OpenGL 特定）
- **优势**：允许 Skia 公共 API 不依赖 OpenGL 头文件

### Pimpl 习语

通过抽象基类隐藏实现细节：
- 公共 API 只暴露 `GrBackendTexture`
- 内部使用 `GrGLBackendTextureData` 存储 OpenGL 数据
- 减少编译依赖，提高封装性

### 智能指针管理

使用 `sk_sp<GrGLTextureParameters>` 共享纹理参数：
- 多个纹理可共享同一参数对象
- 自动内存管理，避免泄漏
- 支持写时复制优化

### 类型安全检查

在 `SK_DEBUG` 模式下，`type()` 方法确保类型安全：
```cpp
#if defined(SK_DEBUG)
GrBackendApi type() const override { return GrBackendApi::kOpenGL; }
#endif
```

### 格式验证

工厂函数注释明确要求：
```cpp
// The GrGLTextureInfo must have a valid fFormat.
```

这确保纹理创建时格式信息完整，避免运行时错误。

## 性能考量

### 数据复制优化

`copyTo` 方法设计为浅拷贝：
- 共享 `GrGLTextureParameters` 智能指针
- 只复制 POD 类型的 `GrGLTextureInfo`
- 避免不必要的参数对象复制

### 比较操作

提供两种比较语义：
- **equal**：值相等（深比较）
- **isSameTexture**：对象相同（浅比较，比较纹理 ID）
- 根据使用场景选择适当的比较方式

### 格式查询缓存

`getBackendFormat()` 可能被频繁调用：
- 实现应缓存格式对象
- 避免每次重新构造 `GrBackendFormat`

## 使用场景

### 外部纹理导入

允许应用程序导入已存在的 OpenGL 纹理：
```cpp
GrGLTextureInfo info;
info.fID = existingTextureID;
info.fTarget = GL_TEXTURE_2D;
info.fFormat = GL_RGBA8;

GrBackendTexture backendTex = GrBackendTextures::MakeGL(
    width, height, skgpu::Mipmapped::kNo, info, nullptr, "ImportedTexture"
);
```

### 跨 API 互操作

在 OpenGL 和其他 GPU API 之间传递纹理信息：
- 通过 `GrBackendTexture` 作为中间层
- 使用 `GrGLBackendTextureData` 提取 OpenGL 信息
- 支持 Metal、Vulkan 等其他后端

### 纹理参数同步

通过共享 `GrGLTextureParameters`：
- 多个 `GrBackendTexture` 引用同一纹理
- 修改参数影响所有引用
- 避免状态不一致

## 相关文件

| 文件 | 关系 | 说明 |
|------|------|------|
| `GrBackendSurface.h` | 公共接口 | 跨平台后端表面抽象 |
| `GrBackendSurfacePriv.h` | 基类 | 私有实现抽象基类 |
| `GrGLTypesPriv.h` | 类型定义 | OpenGL 类型和结构体 |
| `GrGLTexture.h/cpp` | 使用者 | OpenGL 纹理实现 |
| `GrGLGpu.h/cpp` | 创建者 | 创建和管理 OpenGL 纹理 |
| `GrGLBackendSurface.h` | 公共工厂 | 公共的后端纹理创建函数 |
| `SkImage_Ganesh.cpp` | 使用者 | 从后端纹理创建 Skia 图像 |
