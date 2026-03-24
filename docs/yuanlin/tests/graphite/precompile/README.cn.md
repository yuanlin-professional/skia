# tests/graphite/precompile/ - Graphite Pipeline 预编译测试

## 概述

`tests/graphite/precompile/` 目录包含 Skia Graphite GPU 后端 Pipeline 预编译系统的专用测试。Pipeline 预编译是 Graphite 的核心特性之一，它允许应用程序在实际绘制之前预先编译 GPU Pipeline，从而避免首次绘制时因 Pipeline 编译造成的帧率卡顿（即"shader jank"问题）。

该目录包含 17 个文件，其中 3 个头文件定义测试工具，其余文件实现具体的预编译验证测试。测试验证的核心目标是：通过 `PaintOptions` API 指定的预编译组合，是否能够覆盖实际绘制时所需的所有 Pipeline。测试通过收集实际绘制产生的 Pipeline 标签（label），与预编译产生的 Pipeline 进行比对。

目录中的测试针对多个重要应用场景进行验证：Android 系统绘制（`AndroidPrecompileTest.cpp`）、Chrome 浏览器渲染（`ChromePrecompileTest.cpp`）、YCbCr 视频纹理处理（`AndroidYCbCrPrecompileTest.cpp`）等。此外还包括多线程预编译安全性测试（`ThreadedPrecompileTest.cpp`）和用户自定义稳定键测试（`UserdefinedStableKeyTest.cpp`）。

## 架构图

```
+------------------------------------------------------------------+
|               预编译测试执行流程                                    |
|  +------------------------------------------------------------+  |
|  |  PrecompileSettings                                        |  |
|  |  +-----------------+ +------------------+ +-------------+  |  |
|  |  | PaintOptions    | | DrawTypeFlags    | | RenderPass  |  |  |
|  |  | (绘制选项组合)  | | (绘制类型标志)    | | Properties  |  |  |
|  |  +-----------------+ +------------------+ +-------------+  |  |
|  +------------------------------------------------------------+  |
|                              |                                    |
|                              v                                    |
|  +------------------------------------------------------------+  |
|  |  PrecompileContext::precompile()                            |  |
|  |  生成预编译的 Pipeline 集合                                  |  |
|  +------------------------------------------------------------+  |
|                              |                                    |
|                              v                                    |
|  +------------------------------------------------------------+  |
|  |  PipelineLabelInfoCollector                                |  |
|  |  +-----------------------+ +---------------------------+   |  |
|  |  | processLabel()        | | 对比预编译与实际Pipeline   |   |  |
|  |  | (处理生成的标签)       | | 覆盖率分析                 |   |  |
|  |  +-----------------------+ +---------------------------+   |  |
|  +------------------------------------------------------------+  |
|                              |                                    |
|                              v                                    |
|  +------------------------------------------------------------+  |
|  |  finalReport() -- 输出覆盖率报告和未匹配的Pipeline          |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
```

## 目录结构

```
tests/graphite/precompile/
├── PrecompileTestUtils.h           # 核心测试工具声明
├── PrecompileTestUtils.cpp         # 核心测试工具实现
├── PaintOptionsBuilder.h           # PaintOptions 构建器声明
├── PaintOptionsBuilder.cpp         # PaintOptions 构建器实现
├── PaintParamsTestUtils.h          # 绘制参数测试工具声明
├── PaintParamsTestUtils.cpp        # 绘制参数测试工具实现
├── AndroidRuntimeEffectManager.h   # Android 运行时效果管理器声明
├── AndroidRuntimeEffectManager.cpp # Android 运行时效果管理器实现
│
├── [平台/应用场景测试]
│   ├── AndroidPrecompileTest.cpp       # Android 系统绘制预编译测试
│   ├── AndroidPaintOptions.cpp         # Android 绘制选项验证
│   ├── AndroidYCbCrPrecompileTest.cpp  # Android YCbCr 视频纹理预编译
│   └── ChromePrecompileTest.cpp        # Chrome 浏览器渲染预编译测试
│
├── [核心功能测试]
│   ├── CombinationBuilderTest.cpp      # PaintOptions 组合构建器测试
│   ├── PaintParamsKeyTest.cpp          # 绘制参数键匹配测试
│   ├── PrecompileStatsTest.cpp         # 预编译统计信息测试
│   ├── ThreadedPrecompileTest.cpp      # 多线程预编译安全性测试
│   └── UserdefinedStableKeyTest.cpp    # 用户自定义稳定键测试
```

## 关键类与函数

### PrecompileTestUtils 命名空间

#### PrecompileSettings 结构体

```cpp
struct PrecompileSettings {
    PaintOptions fPaintOptions;      // 描述所有可能的绘制选项组合
    DrawTypeFlags fDrawTypeFlags;    // 指定绘制类型 (填充、描边、文本等)
    SkSpan<const RenderPassProperties> fRenderPassProps; // 渲染通道属性
    bool fAnalyticClipping;          // 是否启用解析裁剪
};
```

#### PipelineLabel 结构体

```cpp
struct PipelineLabel {
    int fNumHits;         // 在最常访问的网站中的出现次数
    const char* fString;  // Pipeline 标签字符串
};
```

#### PipelineLabelInfoCollector 类

```cpp
class PipelineLabelInfoCollector {
public:
    explicit PipelineLabelInfoCollector(SkSpan<const PipelineLabel> cases, SkipFunc);

    int numNotCovered() const;           // 未覆盖的 Pipeline 数量
    int processLabel(const std::string& precompiledLabel, int precompileCase);
    void finalReport();                  // 输出最终覆盖率报告

private:
    class PipelineLabelInfo {
        const int fCasesIndex;
        static constexpr int kSkipped = -2;
        static constexpr int kUninit = -1;
        int fPrecompileCase;
    };
    std::map<const char*, PipelineLabelInfo, comparator> fMap;
    std::map<std::string, OverGenInfo> fOverGenerated; // 过度生成的 Pipeline
};
```

#### 核心测试函数

```cpp
// 运行单个预编译设置的测试
void RunTest(PrecompileContext*, Reporter*, const PrecompileSettings&,
             int settingsIndex, SkSpan<const PipelineLabel> cases,
             PipelineLabelInfoCollector*, bool checkPaintOptionCoverage);

// 运行完整的预编译测试
void PrecompileTest(Reporter*, Context*,
                    SkSpan<const PipelineLabel> labels,
                    VisitSettingsFunc visitSettings,
                    bool checkPaintOptionCoverage = true,
                    bool checkPipelineLabelCoverage = false);

// Vulkan 专用：解码 YCbCr Pipeline 标签
void Base642YCbCr(const char*);  // SK_VULKAN only
```

#### VisitSettingsFunc 类型

```cpp
typedef void (*VisitSettingsFunc)(
    PrecompileContext*,
    RuntimeEffectManager& effectManager,
    const std::function<void(PrecompileContext*,
                             const PrecompileSettings&,
                             int index)>& func);
```

### 调试控制宏

```cpp
//#define FINAL_REPORT           // 启用最终报告，包含未匹配的 Pipeline
//#define PRINT_COVERAGE         // 打印每个预编译设置的覆盖率
//#define PRINT_GENERATED_LABELS // 打印所有生成的标签及其匹配状态
```

## 依赖关系

```
precompile/ 依赖:
├── include/gpu/graphite/GraphiteTypes.h        (Graphite 类型)
├── include/gpu/graphite/precompile/PaintOptions.h (绘制选项)
├── include/gpu/graphite/precompile/Precompile.h   (预编译 API)
├── include/gpu/graphite/PrecompileContext.h     (预编译上下文)
├── include/gpu/graphite/Context.h               (Graphite 上下文)
├── tests/Test.h                                  (测试框架)
└── src/gpu/graphite/                              (Graphite 内部)
```

## 设计模式分析

### 1. 覆盖率驱动测试模式

测试的核心目标不是验证单个 Pipeline 的正确性，而是验证预编译 API 的**覆盖率**。通过从真实应用场景（Android 系统 UI、Chrome 浏览器）收集的 Pipeline 标签作为"真相源"，验证预编译产生的 Pipeline 是否足够覆盖这些真实需求。

### 2. 访问者模式（Visitor Pattern）

`VisitSettingsFunc` 回调遍历所有预编译设置，对每个设置调用传入的函数。这种设计将预编译设置的遍历逻辑与测试逻辑解耦，允许不同测试复用相同的设置集合。

### 3. 收集器模式（Collector Pattern）

`PipelineLabelInfoCollector` 收集预编译过程中产生的所有 Pipeline 标签，并与期望列表进行交叉引用。收集器同时跟踪"过度生成"（生成了但不需要的 Pipeline）和"未覆盖"（需要但未生成的 Pipeline）两个维度。

## 数据流

```
预编译测试数据流:

1. 准备阶段
   加载 PipelineLabel 列表 (来自真实应用数据)
          |
          v
   创建 PipelineLabelInfoCollector

2. 预编译阶段
   VisitSettingsFunc 遍历所有 PrecompileSettings
          |
          +-- 对每个 Setting:
          |     |
          |     v
          |   PrecompileContext::precompile(PaintOptions, DrawTypeFlags, ...)
          |     |
          |     v
          |   收集生成的 Pipeline 标签
          |     |
          |     v
          |   collector.processLabel(label, settingIndex)
          |
          v
   所有 Settings 遍历完毕

3. 分析阶段
   collector.numNotCovered() -- 检查未覆盖数
          |
          v
   collector.finalReport() -- 输出详细覆盖率报告
          |
          v
   REPORTER_ASSERT(未覆盖数 == 0)
```

## 相关文档与参考

- `tests/graphite/precompile/PrecompileTestUtils.h` - 核心测试工具 API
- `include/gpu/graphite/precompile/PaintOptions.h` - PaintOptions 公共 API
- `include/gpu/graphite/precompile/Precompile.h` - 预编译核心 API
- `include/gpu/graphite/PrecompileContext.h` - 预编译上下文
- `dm/DMSrcSink.h` - `GraphitePrecompileTestingSink` DM 集成
- `tests/graphite/` - Graphite 通用测试目录
