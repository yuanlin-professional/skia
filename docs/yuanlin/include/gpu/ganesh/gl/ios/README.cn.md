# include/gpu/ganesh/gl/ios - iOS EAGL 平台 OpenGL ES 接口

## 概述

`include/gpu/ganesh/gl/ios` 目录提供了在 iOS 平台上通过 EAGL 创建 Ganesh OpenGL ES 接口的
入口。EAGL (Embedded Apple GL) 是 iOS 上管理 OpenGL ES 渲染上下文的框架。

此目录仅包含一个头文件 `GrGLMakeIOSInterface.h`，提供了通过 iOS 的 OpenGL ES 框架获取
GL 函数指针并创建 `GrGLInterface` 的工厂函数。

注意：Apple 已在 iOS 12 中弃用 OpenGL ES，推荐使用 Metal 替代。对于新的 iOS 应用，
应优先考虑使用 Metal 后端（`include/gpu/ganesh/mtl/` 或 `include/gpu/graphite/mtl/`）。

## 架构图

```
include/gpu/ganesh/gl/ios/
    |
    +-- GrGLMakeIOSInterface.h
            |
            +-- GrGLInterfaces::MakeIOS()
                    |
                    +--> sk_sp<const GrGLInterface>
                            |
                            +--> GrDirectContexts::MakeGL(interface)
```

## 目录结构

| 文件 | 说明 |
|------|------|
| `GrGLMakeIOSInterface.h` | iOS EAGL 平台 GL 接口创建函数 |
| `BUILD.bazel` | Bazel 构建配置 |

## 关键类与函数

### `GrGLInterfaces::MakeIOS()` 函数

```cpp
namespace GrGLInterfaces {
    sk_sp<const GrGLInterface> MakeIOS();
}
```

通过 iOS OpenGL ES 框架获取 GL 函数指针，创建并返回完整的 `GrGLInterface`。
返回的接口适用于 OpenGL ES 上下文。

## 依赖关系

- **上游依赖**: `include/gpu/ganesh/gl/GrGLInterface.h`
- **系统依赖**: iOS OpenGLES 框架
- **平台**: iOS (已弃用，推荐 Metal)

## 相关文档与参考

- `include/gpu/ganesh/gl/` - GL 后端主目录
- `include/gpu/ganesh/mtl/` - Metal 后端（iOS 推荐）
