# Skia Skottie iOS 示例应用

## 概述

`tools/skottie_ios_app` 是一个 iOS 原生应用示例，演示如何在 iOS 设备上使用 Skottie（Skia 的 Lottie 动画引擎）渲染 Lottie 动画。该应用支持三种图形后端：Metal、OpenGL 和 CPU 纯软件渲染，展示了 Skia 在 iOS 平台上的集成方式。

## 目录结构

```
tools/skottie_ios_app/
├── BUILD.gn                      # GN 构建配置
├── README.md                     # 英文编译说明
├── Info.plist                    # iOS 应用配置
├── main.mm                       # 应用主入口（Objective-C++）
├── SkiaContext.h                  # Skia 渲染上下文抽象接口
├── SkiaContext.mm                 # Skia 渲染上下文基础实现
├── SkiaGLContext.mm               # OpenGL 渲染上下文实现
├── SkiaMetalContext.mm            # Metal 渲染上下文实现
├── SkiaUIContext.mm               # CPU 渲染上下文实现
├── SkiaViewController.h           # 视图控制器声明
├── SkiaViewController.mm          # 视图控制器实现
├── SkottieViewController.h        # Skottie 动画控制器声明
├── SkottieViewController.mm       # Skottie 动画控制器实现
├── GrContextHolder.h              # GrContext 生命周期管理
├── GrContextHolder.mm             # GrContext 生命周期管理实现
├── SkMetalViewBridge.h            # Metal 视图桥接声明
└── SkMetalViewBridge.mm           # Metal 视图桥接实现
```

## 核心架构

### 渲染上下文层级

```
SkiaContext（抽象基类）
├── SkiaMetalContext  -> Metal GPU 渲染
├── SkiaGLContext     -> OpenGL ES GPU 渲染
└── SkiaUIContext     -> CPU 软件渲染（使用 UIKit）
```

### SkiaContext

抽象接口，定义渲染上下文的生命周期管理：

- 创建和管理 `GrDirectContext`
- 提供 `SkSurface` 用于 Skia 绘制
- 处理帧的开始和提交

### SkottieViewController

Skottie 动画的控制器，负责：

- 加载 Lottie JSON 动画文件
- 创建 `skottie::Animation` 实例
- 管理动画时间线和回放控制
- 在每帧中通过 `SkCanvas` 渲染动画

### GrContextHolder

管理 `GrDirectContext` 的生命周期：

- 在 Objective-C++ 环境中安全持有 C++ 智能指针
- 处理 GPU 上下文的创建和销毁

### SkMetalViewBridge

连接 `MTKView`（Metal 视图）和 Skia 的桥接层：

- 从 `MTKView` 获取 Metal 设备和命令队列
- 创建 Skia 的 Metal 后端 `GrDirectContext`
- 管理 Metal 纹理和渲染目标

## 构建指南

### Metal 后端

```bash
cd $SKIA_ROOT_DIRECTORY

mkdir -p out/ios_arm64_mtl
cat > out/ios_arm64_mtl/args.gn <<EOM
target_os="ios"
target_cpu="arm64"
skia_use_metal=true
skia_use_expat=false
skia_enable_pdf=false
EOM

tools/git-sync-deps
bin/gn gen out/ios_arm64_mtl
ninja -C out/ios_arm64_mtl skottie_example
```

### CPU 后端

```bash
mkdir -p out/ios_arm64_cpu
cat > out/ios_arm64_cpu/args.gn <<EOM
target_cpu="arm64"
target_os="ios"
skia_enable_ganesh=false
skia_enable_pdf=false
skia_use_expat=false
EOM

tools/git-sync-deps
bin/gn gen out/ios_arm64_cpu
ninja -C out/ios_arm64_cpu skottie_example
```

### OpenGL 后端

```bash
mkdir -p out/ios_arm64_gl
cat > out/ios_arm64_gl/args.gn <<EOM
target_cpu="arm64"
target_os="ios"
skia_enable_ganesh=true
skia_use_metal=false
skia_enable_pdf=false
skia_use_expat=false
EOM

tools/git-sync-deps
bin/gn gen out/ios_arm64_gl
ninja -C out/ios_arm64_gl skottie_example
```

### 安装

构建完成后，安装对应的 `.app` bundle 到 iOS 设备。

## 与其他模块的关系

- **modules/skottie/**: Skottie 动画引擎核心实现
- **include/gpu/ganesh/**: Ganesh GPU 后端接口
- **include/gpu/ganesh/mtl/**: Metal 后端接口
- **tools/sk_app/**: 更通用的 Skia 窗口应用框架
- **modules/canvaskit/**: CanvasKit 提供 Web 端的 Skottie 支持
