# GrProcessorUnitTest

> 源文件: src/gpu/ganesh/GrProcessorUnitTest.h, src/gpu/ganesh/GrProcessorUnitTest.cpp

## 概述

`GrProcessorUnitTest` 是 Ganesh GPU 后端的处理器单元测试框架，提供了用于自动生成和测试各种处理器组合的基础设施。该框架通过静态工厂注册机制，能够随机生成处理器实例，用于模糊测试和回归测试。

主要功能包括：
- **测试数据提供**：`GrProcessorTestData` 封装测试所需的上下文和资源
- **工厂注册系统**：自动注册所有处理器的测试工厂
- **随机生成器**：创建随机处理器实例和组合
- **深度控制**：防止片段处理器树无限递归
- **宏定义支持**：简化测试代码的编写

该模块仅在 `GPU_TEST_UTILS` 宏定义时编译，不影响生产代码的体积。

## 架构位置

`GrProcessorUnitTest` 位于 Ganesh 测试框架的核心：

```
GPU 测试框架
    ↓
GrProcessorUnitTest (处理器测试框架) ← 本模块
    ↓
    ├── GrFragmentProcessorTestFactory (片段处理器工厂)
    ├── GrGeometryProcessorTestFactory (几何处理器工厂)
    └── GrXPFactoryTestFactory (传输处理器工厂)
         ↓
    具体处理器测试实现
         ↓
    测试用例执行
```

与其他模块的关系：

```
测试用例 → GrProcessorTestData → 创建测试上下文
                    ↓
        GrProcessorTestFactory → 随机生成处理器
                    ↓
        验证处理器行为和输出
```

## 主要类与结构体

### GrProcessorTestData

封装处理器测试所需的所有数据和资源。

**继承关系**: 独立类（不可拷贝）

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fRandom` | `SkRandom*` | 随机数生成器 |
| `fCurrentTreeDepth` | `int` | 当前 FP 树深度 |
| `fMaxTreeDepth` | `int` | 最大允许深度 |
| `fContext` | `GrRecordingContext*` | 记录上下文 |
| `fDrawContext` | `skgpu::ganesh::SurfaceDrawContext*` | 绘制上下文 |
| `fViews` | `TArray<ViewInfo>` | 测试纹理视图数组 |
| `fArena` | `std::unique_ptr<SkArenaAlloc>` | 内存分配器 |
| `fInputFP` | `std::unique_ptr<GrFragmentProcessor>` | 输入片段处理器 |

**ViewInfo 类型定义**:

```cpp
using ViewInfo = std::tuple<GrSurfaceProxyView, GrColorType, SkAlphaType>;
```

包含表面代理视图、颜色类型和 alpha 类型的三元组。

### GrProcessorTestFactory<ProcessorSmartPtr>

处理器测试工厂模板类。

**模板参数**:
- `GrFragmentProcessor*` 的 `std::unique_ptr`
- `GrGeometryProcessor*` 原始指针

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fMakeProc` | `MakeProc` | 处理器创建函数指针 |
| `fName` | `SkString` | 处理器名称 |

**MakeProc 定义**:

```cpp
using MakeProc = ProcessorSmartPtr (*)(GrProcessorTestData*);
```

### GrXPFactoryTestFactory

传输处理器工厂测试类（特殊化，不是模板）。

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fGetProc` | `GetFn*` | 工厂获取函数指针 |

**GetFn 定义**:

```cpp
using GetFn = const GrXPFactory*(GrProcessorTestData*);
```

## 公共 API 函数

### GrProcessorTestData 方法

#### 构造函数

```cpp
GrProcessorTestData(SkRandom* random,
                    skgpu::ganesh::SurfaceDrawContext* sdc,
                    int maxTreeDepth,
                    SkSpan<const ViewInfo> views);

GrProcessorTestData(SkRandom* random,
                    skgpu::ganesh::SurfaceDrawContext* sdc,
                    int maxTreeDepth,
                    SkSpan<const ViewInfo> views,
                    std::unique_ptr<GrFragmentProcessor> inputFP);
```

创建测试数据对象，第二个重载允许指定输入片段处理器。

#### 访问器方法

```cpp
GrRecordingContext* context();
skgpu::ganesh::SurfaceDrawContext* surfaceDrawContext();
GrProxyProvider* proxyProvider();
const GrCaps* caps();
SkArenaAlloc* allocator();
```

#### inputFP()

```cpp
std::unique_ptr<GrFragmentProcessor> inputFP();
```

返回输入片段处理器：
- **顶层**（depth == 0）：返回 `fInputFP` 的克隆
- **深层**：返回随机生成的子处理器

#### randomView() / randomAlphaOnlyView()

```cpp
ViewInfo randomView();
ViewInfo randomAlphaOnlyView();
```

从视图数组中随机选择一个（alpha-only）视图。

### GrProcessorTestFactory 方法

#### Make()

```cpp
static ProcessorSmartPtr Make(GrProcessorTestData* data);
```

从所有注册的工厂中随机选择一个，创建处理器实例。

#### MakeIdx()

```cpp
static ProcessorSmartPtr MakeIdx(int idx, GrProcessorTestData* data);
```

使用指定索引的工厂创建处理器。

#### Count()

```cpp
static int Count();
```

返回注册的工厂数量。

### GrProcessorUnitTest 命名空间函数

#### MakeChildFP()

```cpp
std::unique_ptr<GrFragmentProcessor> MakeChildFP(GrProcessorTestData*);
```

创建子片段处理器，确保不超过最大深度：
- 深度达到上限时返回简单的颜色处理器
- 否则随机生成处理器，拒绝有子节点的处理器

#### MakeOptionalChildFP()

```cpp
std::unique_ptr<GrFragmentProcessor> MakeOptionalChildFP(GrProcessorTestData*);
```

50% 概率返回子处理器，50% 返回 `nullptr`。

## 内部实现细节

### 静态工厂注册

使用全局静态数组存储工厂：

```cpp
template <>
TArray<GrFragmentProcessorTestFactory*, true>*
GrFragmentProcessorTestFactory::GetFactories() {
    static TArray<GrFragmentProcessorTestFactory*, true> gFactories;
    return &gFactories;
}
```

工厂在构造时自动注册：

```cpp
template <class ProcessorSmartPtr>
GrProcessorTestFactory<ProcessorSmartPtr>::GrProcessorTestFactory(
        MakeProc makeProc, const char* name)
        : fMakeProc(makeProc), fName(name) {
    GetFactories()->push_back(this);
}
```

### 深度控制机制

防止片段处理器树无限递归：

```cpp
std::unique_ptr<GrFragmentProcessor> GrProcessorUnitTest::MakeChildFP(
        GrProcessorTestData* data) {
    std::unique_ptr<GrFragmentProcessor> fp;

    ++data->fCurrentTreeDepth;
    if (data->fCurrentTreeDepth > data->fMaxTreeDepth) {
        // 达到深度上限，返回简单处理器
        fp = GrFragmentProcessor::MakeColor(SK_PMColor4fTRANSPARENT);
    } else {
        for (;;) {
            fp = GrFragmentProcessorTestFactory::Make(data);
            SkASSERT(fp);
            // 如果深度未达上限或 FP 没有子节点，接受它
            if (data->fCurrentTreeDepth < data->fMaxTreeDepth ||
                fp->numNonNullChildProcessors() == 0) {
                break;
            }
        }
    }

    --data->fCurrentTreeDepth;
    return fp;
}
```

### 工厂计数验证

使用硬编码的期望数量验证静态初始化：

```cpp
static constexpr int kFPFactoryCount = 10;
static constexpr int kGPFactoryCount = 14;
static constexpr int kXPFactoryCount = 4;

template <> void GrFragmentProcessorTestFactory::VerifyFactoryCount() {
    if (kFPFactoryCount != GetFactories()->size()) {
        SkDebugf("\nExpected %d fragment processor factories, found %d.\n",
                 kFPFactoryCount, GetFactories()->size());
        SK_ABORT("Wrong number of fragment processor factories!");
    }
}
```

当添加新工厂时，必须更新这些常量。

### 内存池管理

使用 `SkArenaAlloc` 为几何处理器提供内存：

```cpp
GrProcessorTestData::GrProcessorTestData(...)
        : ... {
    fViews.reset(views);
    fArena = std::make_unique<SkArenaAlloc>(1000);
}
```

起始大小为 1000 字节，足够大部分测试使用。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrFragmentProcessor` | 被测试的处理器类型 |
| `GrGeometryProcessor` | 被测试的处理器类型 |
| `GrXPFactory` | 传输处理器工厂 |
| `GrRecordingContext` | 提供 GPU 上下文 |
| `SurfaceDrawContext` | 提供绘制上下文 |
| `GrSurfaceProxyView` | 测试纹理视图 |
| `SkRandom` | 随机数生成 |
| `SkArenaAlloc` | 内存分配 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| 所有处理器实现 | 使用 `GR_DECLARE/DEFINE_*_TEST` 宏 |
| GPU 单元测试 | 使用工厂生成测试实例 |
| 模糊测试工具 | 生成随机处理器组合 |
| 回归测试 | 验证处理器行为 |

## 设计模式与设计决策

### 抽象工厂模式

`GrProcessorTestFactory` 实现抽象工厂：
- **产品**：各种处理器对象
- **工厂**：测试工厂类
- **创建者**：静态 `Make()` 方法
- **注册表**：全局工厂数组

### 模板方法模式

处理器测试遵循固定流程：
1. 创建 `GrProcessorTestData`
2. 调用工厂的 `Make()` 或 `MakeIdx()`
3. 工厂调用处理器的 `TestCreate()`
4. 返回处理器实例

### 单例模式

工厂注册表使用函数局部静态变量：

```cpp
static TArray<...>* GetFactories() {
    static TArray<...> gFactories;  // 单例
    return &gFactories;
}
```

保证全局唯一且延迟初始化。

### 策略模式

不同类型的处理器使用不同的工厂策略：
- **片段处理器**：返回 `unique_ptr`，自动管理生命周期
- **几何处理器**：返回原始指针，由内存池管理
- **传输处理器工厂**：返回工厂指针，不创建实例

### 宏驱动设计

使用宏简化测试代码编写：

```cpp
// 声明宏
#define GR_DECLARE_FRAGMENT_PROCESSOR_TEST \
    static GrFragmentProcessorTestFactory* gTestFactory; \
    static std::unique_ptr<GrFragmentProcessor> TestCreate(GrProcessorTestData*);

// 定义宏
#define GR_DEFINE_FRAGMENT_PROCESSOR_TEST(Effect) \
    GrFragmentProcessorTestFactory* Effect::gTestFactory = \
            new GrFragmentProcessorTestFactory(Effect::TestCreate, #Effect);
```

**优点**：
- 减少样板代码
- 强制统一的接口
- 自动注册工厂

## 性能考量

### 惰性初始化

工厂列表使用函数局部静态变量：
- **延迟创建**：首次使用时初始化
- **线程安全**：C++11 保证静态初始化的线程安全
- **零开销**：生产代码完全不包含

### 内存效率

#### Arena 分配器

几何处理器使用 arena 分配：
- **批量释放**：销毁 arena 时一次性释放所有对象
- **无碎片**：顺序分配，无碎片化
- **快速分配**：指针移动而非系统调用

#### 视图数组

```cpp
fViews.reset(views);
```

直接拷贝视图元组，避免纹理代理的引用计数开销（视图本身是轻量级的）。

### 深度限制优化

通过限制 FP 树深度避免：
- **编译超时**：过深的着色器树导致编译缓慢
- **栈溢出**：递归处理器创建可能耗尽栈空间
- **测试超时**：复杂处理器执行时间过长

### 条件编译

```cpp
#if defined(GPU_TEST_UTILS)
    // 测试代码
#else
    // 空宏定义
#endif
```

**收益**：
- **零开销**：生产构建完全排除测试代码
- **二进制体积**：减小最终可执行文件
- **安全性**：避免测试钩子进入生产环境

## 相关文件

| 文件路径 | 关系 |
|---------|------|
| `src/gpu/ganesh/GrFragmentProcessor.h` | 被测试的处理器基类 |
| `src/gpu/ganesh/GrGeometryProcessor.h` | 被测试的处理器基类 |
| `src/gpu/ganesh/GrXferProcessor.h` | 被测试的处理器基类 |
| `include/gpu/ganesh/GrRecordingContext.h` | 提供 GPU 上下文 |
| `src/gpu/ganesh/SurfaceDrawContext.h` | 提供绘制上下文 |
| `src/gpu/ganesh/GrSurfaceProxyView.h` | 测试纹理视图 |
| `src/base/SkRandom.h` | 随机数生成 |
| `src/base/SkArenaAlloc.h` | Arena 内存分配器 |
| `src/gpu/ganesh/GrRecordingContextPriv.h` | 上下文私有接口 |
| `src/gpu/ganesh/effects/*.cpp` | 使用测试宏的处理器实现 |
