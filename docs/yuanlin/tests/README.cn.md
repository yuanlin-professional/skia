# tests/ - Skia 单元测试目录

## 概述

`tests/` 目录是 Skia 图形库的核心单元测试目录，包含约 457 个测试文件，涵盖了 Skia 的几乎所有公共 API 和内部实现。这些测试确保了 Skia 在各种平台和图形后端上的正确性和稳定性。

测试框架基于自定义的 `skiatest` 命名空间实现，核心类定义在 `Test.h` 中。框架支持四种测试类型：CPU 并行测试（`kCPU`）、CPU 串行测试（`kCPUSerial`）、Ganesh GPU 测试（`kGanesh`）和 Graphite GPU 测试（`kGraphite`）。每种类型通过对应的宏进行注册，由 `dm`（Dungeon Master）测试运行器统一调度执行。

测试目录采用扁平化组织结构，绝大多数测试文件直接位于根目录下，以被测功能命名（如 `BlurTest.cpp`、`CanvasTest.cpp`）。同时包含三个子目录：`ganesh/` 存放 Ganesh GPU 后端专用的测试工具，`graphite/` 存放下一代 Graphite GPU 后端的测试，`sksl/` 存放 SkSL 着色器语言的生成输出文件。

该测试套件还集成了 Android CTS（兼容性测试套件）支持，通过 `CtsEnforcement` 类控制测试在不同 Android API 级别下的执行模式。这使得 Skia 能够作为 Android 图形栈的核心组件参与兼容性认证。

## 架构图

```
+------------------------------------------------------------------+
|                        DM (测试运行器)                            |
|  +------------------------------------------------------------+  |
|  |                    TestRegistry (注册表)                     |  |
|  |  +-----------+ +-----------+ +-----------+ +-----------+    |  |
|  |  | CPU Tests | |CPU Serial | | Ganesh    | | Graphite  |    |  |
|  |  | (并行)    | | (串行)    | | GPU Tests | | GPU Tests |    |  |
|  |  +-----------+ +-----------+ +-----------+ +-----------+    |  |
|  +------------------------------------------------------------+  |
|                              |                                    |
|  +------------------------------------------------------------+  |
|  |                    Reporter (报告器)                         |  |
|  |  +---------------+ +------------------+ +--------------+    |  |
|  |  | Failure 报告  | | ReporterContext  | | 上下文栈管理  |    |  |
|  |  +---------------+ +------------------+ +--------------+    |  |
|  +------------------------------------------------------------+  |
|                              |                                    |
|  +------------------------------------------------------------+  |
|  |               断言宏 & 工具函数                              |  |
|  |  REPORTER_ASSERT  |  ERRORF  |  INFOF  |  Timer            |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
                               |
        +----------------------+----------------------+
        |                      |                      |
+-------v--------+   +--------v-------+   +----------v--------+
| tests/*.cpp    |   | tests/ganesh/  |   | tests/graphite/   |
| (核心测试文件)  |   | (Ganesh工具)   |   | (Graphite测试)    |
+----------------+   +----------------+   +-------------------+
                                                    |
                                          +---------v---------+
                                          | precompile/       |
                                          | (预编译测试)       |
                                          +-------------------+
```

## 目录结构

```
tests/
├── BUILD.bazel                    # Bazel 构建配置
├── Test.h                         # 核心测试框架头文件
├── Test.cpp                       # 测试框架实现
├── TestType.h                     # 测试类型枚举定义
├── TestHarness.h / TestHarness.cpp # 测试线束（harness）
├── CtsEnforcement.h / .cpp        # Android CTS 强制执行级别
├── ComparePixels.h / .cpp         # 像素比较工具
├── CodecPriv.h                    # 编解码器测试私有工具
├── SubsetPath.h / .cpp            # 路径子集工具
├── CanvasStateHelpers.h / .cpp    # Canvas 状态辅助函数
│
├── ganesh/                        # Ganesh GPU 后端测试工具
│   ├── GaneshTestUtils.h
│   └── GaneshTestUtils.cpp
│
├── graphite/                      # Graphite GPU 后端测试
│   ├── *.cpp / *.mm               # ~50 个 Graphite 测试文件
│   └── precompile/                # 预编译系统测试
│       ├── PrecompileTestUtils.h
│       └── *.cpp                  # ~17 个预编译测试文件
│
├── sksl/                          # SkSL 着色器生成输出（非独立测试）
│   ├── blend/                     # 混合模式着色器输出
│   ├── compute/                   # 计算着色器输出
│   ├── errors/                    # 错误着色器输出
│   ├── folding/                   # 常量折叠输出
│   ├── glsl/                      # GLSL 转换输出
│   ├── inliner/                   # 内联优化输出
│   ├── intrinsics/                # 内置函数输出
│   ├── mesh/                      # 网格着色器输出
│   ├── metal/                     # Metal 转换输出
│   ├── realistic/                 # 真实场景着色器输出
│   ├── runtime/                   # 运行时效果输出
│   ├── shared/                    # 共享着色器输出
│   ├── spirv/                     # SPIR-V 转换输出
│   ├── wgsl/                      # WGSL 转换输出
│   └── workarounds/               # 变通方案输出
│
├── [核心功能测试 ~400+ 文件]
│   ├── AAClipTest.cpp             # 抗锯齿裁剪测试
│   ├── BitmapTest.cpp             # 位图操作测试
│   ├── BlurTest.cpp               # 模糊效果测试
│   ├── CanvasTest.cpp             # Canvas API 测试
│   ├── CodecTest.cpp              # 图像编解码测试
│   ├── ColorSpaceTest.cpp         # 色彩空间测试
│   ├── DrawPathTest.cpp           # 路径绘制测试
│   ├── ImageTest.cpp              # 图像处理测试
│   ├── MatrixTest.cpp             # 矩阵变换测试
│   ├── PathTest.cpp               # 路径操作测试
│   ├── SkRuntimeEffectTest.cpp    # 运行时效果测试
│   ├── SkSLTest.cpp               # SkSL 编译器测试
│   ├── SurfaceTest.cpp            # Surface 测试
│   └── ...                        # 更多测试文件
│
└── [GPU 特定测试]
    ├── BackendAllocationTest.cpp   # GPU 后端内存分配
    ├── EGLImageTest.cpp            # EGL 图像测试
    ├── VkBackendSurfaceTest.cpp    # Vulkan 后端 Surface
    ├── VkHardwareBufferTest.cpp    # Vulkan 硬件缓冲区
    ├── TransferPixelsTest.cpp      # GPU 像素传输
    └── ...                         # 更多 GPU 测试
```

## 关键类与函数

### 核心测试框架（Test.h）

| 类/结构体 | 说明 |
|-----------|------|
| `skiatest::Reporter` | 测试报告基类，管理失败报告和上下文栈 |
| `skiatest::Failure` | 测试失败信息，包含文件名、行号、条件和消息 |
| `skiatest::ReporterContext` | RAII 上下文管理器，自动推送/弹出测试上下文 |
| `skiatest::Test` | 测试用例结构体，支持 CPU/Ganesh/Graphite 三种类型 |
| `skiatest::TestRegistry` | 测试注册表，基于 `sk_tools::Registry` 链表模式 |
| `skiatest::Timer` | 高精度计时器，基于 `SkTime::GetNSecs()` |

### 测试类型（TestType.h）

```cpp
enum class TestType : uint8_t {
    kCPU,       // CPU 并行测试
    kCPUSerial, // CPU 串行测试（在所有并行工作前执行）
    kGanesh,    // Ganesh GPU 测试（GPU 间串行，与 CPU 并行）
    kGraphite   // Graphite GPU 测试
};
```

### CTS 强制执行级别（CtsEnforcement.h）

```cpp
class CtsEnforcement {
    enum ApiLevel : int32_t {
        kNever = INT32_MAX,       // 跳过此测试
        kApiLevel_T = 33,         // Android 13
        kApiLevel_U = 34,         // Android 14
        kApiLevel_202404 = 202404,// Android 14-QPR3+ (YYYYMM 格式)
        kApiLevel_202504 = 202504,
        kNextRelease = 202604     // 下一个版本占位符
    };
    enum class RunMode { kSkip, kRunWithWorkarounds, kRunStrict };
};
```

### 关键测试注册宏

| 宏名 | 用途 |
|------|------|
| `DEF_TEST(name, reporter)` | 注册 CPU 并行测试 |
| `DEF_SERIAL_TEST(name, reporter)` | 注册 CPU 串行测试 |
| `DEF_GANESH_TEST(name, reporter, options, cts)` | 注册 Ganesh GPU 测试 |
| `DEF_GANESH_TEST_FOR_RENDERING_CONTEXTS(...)` | 注册所有渲染上下文的 Ganesh 测试 |
| `DEF_GANESH_TEST_FOR_VULKAN_CONTEXT(...)` | 注册 Vulkan 专用测试 |
| `DEF_GANESH_TEST_FOR_METAL_CONTEXT(...)` | 注册 Metal 专用测试 |
| `DEF_GRAPHITE_TEST(name, reporter, cts)` | 注册 Graphite 测试 |
| `DEF_GRAPHITE_TEST_FOR_RENDERING_CONTEXTS(...)` | 注册所有渲染上下文的 Graphite 测试 |
| `DEF_GRAPHITE_TEST_FOR_VULKAN_CONTEXT(...)` | 注册 Vulkan 上的 Graphite 测试 |
| `DEF_GRAPHITE_TEST_FOR_DAWN_CONTEXT(...)` | 注册 Dawn 上的 Graphite 测试 |

### 断言宏

| 宏名 | 用途 |
|------|------|
| `REPORTER_ASSERT(r, cond, ...)` | 条件断言，支持可选消息 |
| `ERRORF(r, ...)` | 无条件报告错误，支持 printf 格式 |
| `INFOF(REPORTER, ...)` | 仅在 verbose 模式输出调试信息 |
| `REPORT_FAILURE(reporter, cond, message)` | 底层失败报告 |

## 依赖关系

```
tests/ 依赖关系图:

    tests/Test.h
    ├── include/core/SkString.h          (字符串处理)
    ├── include/core/SkTypes.h           (基础类型)
    ├── include/private/base/SkNoncopyable.h (不可拷贝基类)
    ├── include/private/base/SkTArray.h  (动态数组)
    ├── src/core/SkTraceEvent.h          (事件追踪)
    ├── tests/CtsEnforcement.h           (CTS 强制级别)
    ├── tests/TestType.h                 (测试类型定义)
    ├── tools/Registry.h                 (注册表模板)
    ├── tools/timer/TimeUtils.h          (时间工具)
    ├── tools/gpu/ContextType.h          (GPU 上下文类型)
    └── tools/ganesh/GrContextFactory.h  (Ganesh 上下文工厂)

    外部依赖:
    ├── dm/ (测试运行器 - 负责执行所有注册的测试)
    ├── tools/flags/ (命令行参数解析)
    └── tools/ (通用工具库)
```

## 设计模式分析

### 1. 注册表模式（Registry Pattern）

整个测试框架的核心是 `sk_tools::Registry<Test>` 模板实现的全局注册表。每个 `DEF_TEST` 宏在编译时创建一个静态 `TestRegistry` 对象，将测试用例添加到全局链表中。DM 运行器在启动时遍历该链表获取所有测试。

```cpp
// 宏展开示例
static void test_MyTest(skiatest::Reporter*);
skiatest::TestRegistry MyTestTestRegistry(Test::MakeCPU("MyTest", test_MyTest));
void test_MyTest(skiatest::Reporter* reporter) { /* 测试代码 */ }
```

### 2. 报告器模式（Reporter Pattern）

`Reporter` 类采用了观察者模式的变体。测试函数通过 `Reporter` 指针报告结果，具体的报告行为由 DM 或其他测试运行器通过子类化实现。`ReporterContext` 使用 RAII 模式自动管理上下文栈。

### 3. 工厂方法模式（Factory Method）

`Test` 结构体使用静态工厂方法（`MakeCPU`、`MakeGanesh`、`MakeGraphite`）代替构造函数，使得不同类型测试的创建更加清晰且不易出错。

### 4. 上下文过滤器模式（Context Filter）

GPU 测试通过 `ContextTypeFilterFn` 函数指针实现上下文选择，如 `IsGLContextType`、`IsVulkanContextType`、`IsMetalContextType` 等，使得同一测试可以在多个 GPU 后端上运行。

### 5. 条件编译模式

通过 `SK_GANESH`、`SK_GRAPHITE` 等预处理宏，测试框架在编译时决定哪些 GPU 后端可用，确保测试代码能在任何平台配置下编译通过。

## 数据流

```
编译期:
  DEF_TEST/DEF_GANESH_TEST/DEF_GRAPHITE_TEST 宏
         |
         v
  静态 TestRegistry 对象创建
         |
         v
  Test 结构体插入全局链表 (gHead)

运行期:
  DM main() 启动
         |
         v
  遍历 TestRegistry 链表获取所有 Test
         |
         +-- 按 TestType 分类 --+
         |                       |
    +---------+           +-----------+
    | CPU     |           | GPU       |
    | 测试池  |           | 测试队列  |
    +---------+           +-----------+
         |                       |
    (并行执行)             (串行执行, 与CPU并行)
         |                       |
         v                       v
    Reporter 收集结果     RunWithGaneshTestContexts /
         |               RunWithGraphiteTestContexts
         v                       |
    检查 REPORTER_ASSERT         v
    / ERRORF 结果         遍历所有匹配的 GPU 上下文
         |                       |
         v                       v
    汇总测试结果 --> JSON 输出 / 控制台报告
```

## 测试分类概览

### 核心功能测试

| 测试文件 | 测试目标 |
|----------|----------|
| `PathTest.cpp` | SkPath 路径操作、几何计算 |
| `CanvasTest.cpp` | SkCanvas 绘制 API |
| `BitmapTest.cpp` | SkBitmap 位图操作 |
| `MatrixTest.cpp` | SkMatrix 矩阵变换 |
| `ColorSpaceTest.cpp` | 色彩空间转换 |
| `BlurTest.cpp` | 模糊滤镜效果 |
| `CodecTest.cpp` | 图像编解码 (PNG, JPEG, WebP, AVIF) |
| `SurfaceTest.cpp` | SkSurface 表面管理 |
| `SkRuntimeEffectTest.cpp` | 运行时着色器效果 |
| `SkSLTest.cpp` | SkSL 着色器语言编译 |

### GPU 后端测试

| 测试文件 | 测试目标 |
|----------|----------|
| `BackendAllocationTest.cpp` | GPU 后端内存分配 |
| `VkBackendSurfaceTest.cpp` | Vulkan 后端 Surface 操作 |
| `EGLImageTest.cpp` | OpenGL EGL 图像互操作 |
| `TransferPixelsTest.cpp` | GPU 像素数据传输 |
| `TextureProxyTest.cpp` | 纹理代理生命周期 |
| `DMSAATest.cpp` | 距离多采样抗锯齿 |

### SkSL 着色器测试子目录

`tests/sksl/` 子目录包含 SkSL 编译器的**生成输出文件**（golden files），而非独立的可执行测试。这些目录存储不同后端的预期编译结果：

- `blend/` - 混合模式着色器的编译输出
- `compute/` - 计算着色器输出
- `errors/` - 预期编译错误的输出
- `folding/` - 常量折叠优化后的输出
- `glsl/` - GLSL 后端转换输出
- `metal/` - Metal 后端转换输出
- `spirv/` - SPIR-V 后端转换输出
- `wgsl/` - WGSL (WebGPU) 后端转换输出
- `inliner/` - 函数内联优化输出
- `intrinsics/` - 内置函数处理输出
- `mesh/` - 网格着色器输出
- `runtime/` - 运行时效果输出
- `shared/` - 共享测试输出
- `realistic/` - 真实场景着色器输出
- `workarounds/` - GPU 驱动变通方案输出

实际的 SkSL 测试逻辑位于根目录的 `SkSLTest.cpp`、`SkSLErrorTest.cpp`、`SkSLMemoryLayoutTest.cpp` 等文件中，它们在编译和运行时将输出与这些 golden files 进行比对。

## 相关文档与参考

- `tests/Test.h` - 测试框架核心头文件，包含所有宏和类定义
- `tests/TestType.h` - 测试类型枚举定义
- `tests/CtsEnforcement.h` - Android CTS 兼容性测试级别
- `dm/DM.cpp` - Dungeon Master 测试运行器主入口
- `dm/DMSrcSink.h` - 数据源和输出目标抽象层
- `tools/Registry.h` - 注册表模板基类
- `tools/gpu/ContextType.h` - GPU 上下文类型定义
- `site/dev/testing/` - Skia 官方测试文档
