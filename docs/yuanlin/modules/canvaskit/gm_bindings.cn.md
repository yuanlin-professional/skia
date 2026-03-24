# CanvasKit GM 测试绑定 (gm_bindings)

> 源文件: `modules/canvaskit/gm_bindings.cpp`

## 概述

`gm_bindings.cpp` 是 CanvasKit 中用于在 WebAssembly 环境下运行 Skia GM（Graphics Method）测试和单元测试的绑定文件，约 364 行代码。它通过 Emscripten 的 `embind` 将 GM 和 Test 的发现、执行、结果收集功能暴露给 JavaScript，支持 GPU 渲染（通过 WebGL）、像素哈希比较（MD5）、PNG 编码和已知摘要管理。该文件是 Skia 在 Web 平台上运行图形正确性测试的基础设施。

## 架构位置

```
JavaScript 测试框架
  └── gm_bindings.cpp (Emscripten 绑定)
      ├── skiagm::GM 注册表 ← GM 测试用例
      ├── skiatest::TestRegistry ← 单元测试用例
      ├── GrDirectContext (WebGL) ← GPU 渲染上下文
      ├── HashAndEncode ← 像素哈希与 PNG 编码
      └── WasmWebGlTestContext ← WebGL 测试上下文适配
```

## 主要类与结构体

### WasmReporter

`skiatest::Reporter` 的 WASM 适配实现，将测试失败信息记录到 JS 对象中：

| 属性 | 说明 |
|------|------|
| `fName` | 测试名称 |
| `fResult` | JS 结果对象 |
| `reportFailed(failure)` | 记录失败信息到 JS 对象 |

### WasmWebGlTestContext

`sk_gpu_test::GLTestContext` 的最小化 WebGL 实现。假设 WebGL 只有一个上下文且始终为当前上下文，因此大多数上下文管理方法返回 null 或空操作。

### gKnownDigests

`std::set<std::string>` 全局变量，存储已知的 MD5 摘要。用于避免重复编码相同的 PNG 图像。

### gResources

`std::map<std::string, sk_sp<SkData>>` 全局变量，存储通过 `LoadResource` 加载的测试资源。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `Init()` | 初始化测试环境（使用可移植字体管理器） |
| `ListGMs()` | 列出所有注册的 GM 名称（返回 JS 数组） |
| `ListTests()` | 列出所有注册的测试名称（返回 JS 数组） |
| `LoadKnownDigest(md5)` | 注册已知的 MD5 摘要 |
| `_LoadResource(name, bPtr, len)` | 从 WASM 堆加载命名资源 |
| `MakeGrContext(context)` | 从 WebGL 上下文创建 GrDirectContext |
| `RunGM(ctx, name)` | 运行指定 GM 并返回结果 |
| `RunTest(name)` | 运行指定测试并返回结果 |

### RunGM 返回值

| 属性 | 说明 |
|------|------|
| `png` | `Uint8Array` — PNG 编码数据（仅当摘要为新时） |
| `hash` | `string` — 像素内容的 MD5 哈希 |

### RunTest 返回值

| 属性 | 说明 |
|------|------|
| `result` | `"passed"` / `"failed"` / `"skipped"` |
| `msg` | 失败时的错误消息 |

## 内部实现细节

### GM 执行流程

1. 通过名称在 `GMRegistry` 中查找 GM 工厂
2. 创建 GPU 渲染表面（`SkSurfaces::RenderTarget`），预乘 alpha、N32 颜色类型
3. 执行 `onceBeforeDraw()` → `gpuSetup()` → `draw()`
4. `flushAndSubmit` 确保 GPU 渲染完成
5. 通过 `readPixels` 读回像素到 `SkBitmap`
6. 使用 `HashAndEncode` 计算 MD5 摘要
7. 如果摘要不在已知集合中，编码为 PNG 并返回

### PNG 数据的安全拷贝

使用 `typed_memory_view` 创建 WASM 堆的视图，然后调用 JS 的 `slice()` 创建独立副本。这避免了 SkData 被释放后出现的 use-after-free 问题。

### 测试执行

`RunTest` 支持 CPU 测试和 Ganesh (GPU) 测试。Graphite 测试标记为不支持。Ganesh 测试通过 `RunWithGaneshTestContexts` 执行，支持 GLES 和 Mock 两种上下文类型。

### 上下文类型过滤

只支持 OpenGL 和 Mock 上下文，Vulkan、Metal、Direct3D、Dawn 均返回 false。

### 资源加载

`LoadResource` 使用 `SkData::MakeFromMalloc` 接管 WASM 堆内存所有权，并注册全局的 `gResourceFactory` 回调。

## 依赖关系

| 类别 | 依赖项 |
|------|-------|
| Skia 核心 | SkBitmap, SkCanvas, SkData, SkImageInfo, SkStream, SkSurface |
| GPU | GrDirectContext, GrContextOptions, GrGLInterface, SkSurfaceGanesh |
| 测试框架 | gm/gm.h, tests/Test.h, tests/TestHarness.h |
| 工具 | HashAndEncode, ResourceFactory, CommandLineFlags, FontToolUtils |
| CanvasKit | WasmCommon.h |
| Emscripten | emscripten.h, emscripten/bind.h, emscripten/html5.h |

## 设计模式与设计决策

- **注册表模式**: GM 和 Test 通过全局注册表（`GMRegistry`、`TestRegistry`）自动发现
- **摘要缓存**: `gKnownDigests` 避免重复编码已知 PNG，节省带宽和存储
- **最小化测试上下文**: `WasmWebGlTestContext` 提供了最小化的 WebGL 上下文实现，假设单一上下文场景
- **安全数据传输**: PNG 数据通过 `slice()` 创建独立副本，避免 WASM 堆内存管理问题
- **结果对象模式**: GM 和 Test 结果通过 JS 对象返回，包含可选的 PNG 数据和状态信息

## 性能考量

- GM 执行涉及 GPU 渲染、像素回读和 MD5 计算，是重量级操作
- 已知摘要检查可跳过 PNG 编码，对大量重复测试有显著加速效果
- `readPixels` 会导致 GPU 同步等待，是主要性能瓶颈
- 资源通过 `MakeFromMalloc` 接管内存所有权，避免额外拷贝
- 使用 `ToolUtils::UsePortableFontMgr()` 确保跨平台测试结果一致

## 相关文件

- `gm/gm.h` — GM 测试框架基础
- `tests/Test.h` — 单元测试框架
- `tools/HashAndEncode.h` — 像素哈希和 PNG 编码工具
- `modules/canvaskit/WasmCommon.h` — WASM 通用类型
- `tools/gpu/ContextType.h` — GPU 上下文类型定义
