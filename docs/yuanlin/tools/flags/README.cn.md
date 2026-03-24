# tools/flags/ - 命令行标志解析框架

## 概述

`tools/flags/` 目录实现了 Skia 项目自有的命令行标志（flags）解析框架。该框架的设计灵感来源于 Google 的 gflags 库，但针对 Skia 的使用场景进行了简化和定制。它为 Skia 的所有命令行工具（Viewer、DM 测试运行器、nanobench 性能测试、fiddle 等）提供了统一的参数定义、解析和帮助信息生成功能。

核心设计围绕四个 `DEFINE_*` 宏展开：`DEFINE_bool`、`DEFINE_string`、`DEFINE_int` 和 `DEFINE_double`。开发者在全局命名空间中使用这些宏声明标志，宏会自动创建对应类型的全局变量（`FLAGS_name`）并在静态初始化阶段将标志注册到全局链表中。随后在 `main()` 函数中调用 `CommandLineFlags::Parse()` 解析命令行参数，自动将值填入对应的全局变量。

该框架的一个重要特性是字符串标志（`DEFINE_string`）返回的是 `StringArray` 而非单个字符串。这意味着一个标志后面可以跟随多个值（直到遇到下一个以 `-` 开头的标志），这在指定多个文件路径或配置选项时特别有用。

除了核心的 `CommandLineFlags` 类，该目录还包含多个 `CommonFlags*` 模块，它们为特定功能领域预定义了常用的命令行标志。例如 `CommonFlagsConfig` 定义了渲染配置解析（`--config gl msaa16 vk`），`CommonFlagsGanesh` 定义了 Ganesh GPU 后端选项（`--gpuThreads`、`--cachePathMasks`），`CommonFlagsGraphite` 定义了 Graphite 测试选项（`--neverYieldToWebGPU`、`--useWGPUTextureView`），`CommonFlagsImages` 提供了图像路径收集功能。

这种分层的标志组织方式使得各工具可以选择性地引入所需的标志集合，避免了全局标志集合的膨胀。

## 架构图

```
+------------------------------------------------------------------+
|                  tools/flags/ 命令行标志框架                       |
|                                                                   |
|  +----------------------------+                                   |
|  |   DEFINE_* 宏              |  全局命名空间中使用                |
|  |                            |                                   |
|  |  DEFINE_bool(name, val, h) |---> bool FLAGS_name;              |
|  |  DEFINE_string(name, v, h) |---> StringArray FLAGS_name;       |
|  |  DEFINE_int(name, val, h)  |---> int FLAGS_name;               |
|  |  DEFINE_double(name, v, h) |---> double FLAGS_name;            |
|  +----------------------------+                                   |
|              |                                                    |
|              | 创建 SkFlagInfo 并链入全局链表                       |
|              v                                                    |
|  +----------------------------+                                   |
|  |   SkFlagInfo               |  标志元信息节点                    |
|  |                            |                                   |
|  |  fName / fShortName        |  标志名称                         |
|  |  fFlagType                 |  类型 (bool/string/int/double)    |
|  |  fHelpString               |  帮助文本                         |
|  |  fDefaultXxx               |  默认值                           |
|  |  fBoolValue/fIntValue/...  |  指向 FLAGS_* 变量的指针           |
|  |  fNext                     |  链表下一节点                      |
|  +----------------------------+                                   |
|              ^                                                    |
|              | gHead (全局链表头)                                   |
|              |                                                    |
|  +----------------------------+                                   |
|  |   CommandLineFlags         |  核心引擎                          |
|  |                            |                                   |
|  |  SetUsage(usage)           |  设置使用说明                      |
|  |  PrintUsage()              |  打印帮助信息                      |
|  |  Parse(argc, argv)         |  解析命令行参数                    |
|  |  ShouldSkip(strings, name) |  标志匹配过滤                      |
|  +----------------------------+                                   |
|                                                                   |
|  +----------------------------+                                   |
|  |   StringArray              |  字符串数组值容器                   |
|  |                            |                                   |
|  |  operator[](i)             |  按索引访问                       |
|  |  size() / isEmpty()        |  大小查询                         |
|  |  contains(string)          |  包含检查                         |
|  |  parseAndValidate(...)     |  解析并验证枚举值                  |
|  +----------------------------+                                   |
|                                                                   |
|  CommonFlags 扩展模块:                                             |
|  +---------------+  +------------------+  +-------------------+   |
|  | CommonFlags   |  | CommonFlagsConfig|  | CommonFlagsGanesh |   |
|  | Images        |  | 渲染配置解析      |  | Ganesh GPU 选项    |   |
|  | 图像路径收集   |  |                  |  |                   |   |
|  +---------------+  | SkCommandLine    |  | --gpuThreads      |   |
|                     | ConfigGpu        |  | --cachePathMasks   |   |
|  +---------------+  | ConfigGraphite   |  | --pr, --gs, --ts   |   |
|  | CommonFlags   |  | ConfigSvg        |  | --internalSamples  |   |
|  | Graphite      |  +------------------+  +-------------------+   |
|  | Graphite 选项 |                                                 |
|  | --neverYield  |                                                 |
|  | --useWGPU     |                                                 |
|  +---------------+                                                 |
+------------------------------------------------------------------+
```

## 目录结构

```
tools/flags/
|-- BUILD.bazel                # Bazel 构建定义
|
|-- # 核心标志引擎
|-- CommandLineFlags.h         # 标志定义宏、CommandLineFlags 类、SkFlagInfo 类
|-- CommandLineFlags.cpp       # Parse() 实现、帮助信息打印
|
|-- # 通用标志模块
|-- CommonFlags.h              # 图像路径收集函数 (CollectImages)
|-- CommonFlagsImages.cpp      # 图像路径收集实现
|
|-- # 渲染配置标志
|-- CommonFlagsConfig.h        # SkCommandLineConfig 及其子类
|-- CommonFlagsConfig.cpp      # 配置字符串解析 (ParseConfigs)
|
|-- # Ganesh GPU 标志
|-- CommonFlagsGanesh.h        # GrContextOptions 设置函数
|-- CommonFlagsGanesh.cpp      # Ganesh 标志定义和选项映射
|
|-- # Graphite GPU 标志
|-- CommonFlagsGraphite.h      # TestOptions 设置函数
+-- CommonFlagsGraphite.cpp    # Graphite 标志定义和选项映射
```

## 关键类与函数

### DEFINE/DECLARE 宏

```cpp
// tools/flags/CommandLineFlags.h

// 布尔标志
DEFINE_bool(name, defaultValue, helpString);
DEFINE_bool2(name, shortName, defaultValue, helpString);  // 带短名
DECLARE_bool(name);  // 跨文件声明

// 字符串标志（创建 StringArray）
DEFINE_string(name, defaultValue, helpString);
DEFINE_string2(name, shortName, defaultValue, helpString);
DEFINE_extended_string(name, defaultValue, helpString, extendedHelp);
DECLARE_string(name);

// 整数标志
DEFINE_int(name, defaultValue, helpString);
DEFINE_int_2(name, shortName, defaultValue, helpString);
DECLARE_int(name);

// 浮点标志
DEFINE_double(name, defaultValue, helpString);
DECLARE_double(name);
```

### CommandLineFlags 核心类

```cpp
// tools/flags/CommandLineFlags.h
class CommandLineFlags {
public:
    // 设置全局使用说明
    static void SetUsage(const char* usage);
    static void PrintUsage();

    // 解析命令行参数（必须在 DEFINE_* 之后调用一次）
    static void Parse(int argc, const char* const* argv);

    // 字符串数组值容器
    class StringArray {
    public:
        const char* operator[](int i) const;
        int size() const;
        bool isEmpty() const;
        bool contains(const char* string) const;

        // 模板方法：解析并验证枚举值
        template <class E>
        SkString parseAndValidate(const char* name,
                                  const THashMap<SkString, E>& possibleValues,
                                  E* out) const;
    };

    // 测试名称匹配过滤
    // 支持: ~ (跳过), ^ (前缀匹配), $ (后缀匹配), ^...$ (精确匹配)
    static bool ShouldSkip(const StringArray& strings, const char* name);
};
```

### SkFlagInfo 标志元信息

```cpp
// tools/flags/CommandLineFlags.h
class SkFlagInfo {
public:
    enum FlagTypes { kBool_FlagType, kString_FlagType, kInt_FlagType, kDouble_FlagType };

    // 创建各类型标志（由 DEFINE_* 宏调用）
    static bool CreateBoolFlag(const char* name, const char* shortName,
                               bool* pBool, bool defaultValue, const char* helpString);
    static bool CreateStringFlag(const char* name, const char* shortName,
                                 StringArray* pStrings, const char* defaultValue,
                                 const char* helpString, const char* extendedHelp);
    static bool CreateIntFlag(const char* name, int* pInt, int defaultValue, const char* help);
    static bool CreateDoubleFlag(const char* name, double* pDouble, double defaultValue, const char* help);

    bool match(const char* string);  // 匹配命令行参数
    SkString defaultValue() const;   // 获取默认值字符串表示
    SkString typeAsString() const;   // 获取类型字符串表示

private:
    SkString fName, fShortName;
    FlagTypes fFlagType;
    SkString fHelpString, fExtendedHelpString;
    // 指向全局 FLAGS_* 变量的类型化指针
    bool* fBoolValue;
    int* fIntValue;
    double* fDoubleValue;
    StringArray* fStrings;
    SkFlagInfo* fNext;  // 链表指针
};
```

### CommonFlagsConfig - 渲染配置解析

```cpp
// tools/flags/CommonFlagsConfig.h

// 基类：表示一个渲染配置字符串
class SkCommandLineConfig {
public:
    const SkString& getTag() const;       // 完整标签
    const SkString& getBackend() const;   // 后端名称
    const TArray<SkString>& getViaParts() const;  // Via 处理链
    virtual const SkCommandLineConfigGpu* asConfigGpu() const;
    virtual const SkCommandLineConfigGraphite* asConfigGraphite() const;
};

// GPU (Ganesh) 配置
class SkCommandLineConfigGpu : public SkCommandLineConfig {
    ContextType getContextType() const;   // GL/GLES/Vulkan/Metal/...
    int getSamples() const;               // MSAA 采样数
    SkColorType getColorType() const;     // 颜色类型
};

// Graphite 配置
class SkCommandLineConfigGraphite : public SkCommandLineConfig {
    ContextType getContextType() const;
    SkColorType getColorType() const;
};

// 解析 --config 标志值
void ParseConfigs(const StringArray& configList, SkCommandLineConfigArray* outResult);
```

### CommonFlags 辅助函数

```cpp
// tools/flags/CommonFlags.h
namespace CommonFlags {
    bool CollectImages(const StringArray& dir, TArray<SkString>* output);
}

// tools/flags/CommonFlagsGanesh.h
namespace CommonFlags {
    void SetCtxOptions(GrContextOptions*);  // --gpuThreads, --pr, --gs 等
}

// tools/flags/CommonFlagsGraphite.h
namespace CommonFlags {
    void SetTestOptions(skiatest::graphite::TestOptions*);  // --neverYieldToWebGPU 等
}
```

## 依赖关系

```
CommandLineFlags (核心)
    |
    +---> SkString, TArray, TDArray (Skia 基础类型)
    +---> SkTHash (用于 StringArray::parseAndValidate)
    +---> SkMacros (SK_MACRO_STRINGIFY, SK_MACRO_APPEND_LINE)

CommonFlagsConfig
    |
    +---> CommandLineFlags
    +---> skgpu::ContextType (tools/gpu/ContextType.h)
    +---> GrContextFactory (SK_GANESH, tools/ganesh/)
    +---> graphite::ContextFactory (SK_GRAPHITE, tools/graphite/)
    +---> SkColorType, SkAlphaType, SkColorSpace

CommonFlagsGanesh
    |
    +---> CommandLineFlags
    +---> GrContextOptions

CommonFlagsGraphite
    |
    +---> CommandLineFlags
    +---> skiatest::graphite::TestOptions

使用者:
    +---> Viewer (tools/viewer/) - 使用几乎所有 CommonFlags
    +---> DM (dm/) - 测试运行器
    +---> nanobench (bench/) - 性能测试
    +---> fiddle (tools/fiddle/) - 在线编辑器
    +---> skpbench (tools/skpbench/) - SKP 性能测试
```

## 设计模式分析

### 1. 自注册模式 (Self-Registration)

`DEFINE_*` 宏利用 C++ 静态初始化在程序启动前自动将标志注册到全局链表 (`gHead`)。每个 `SkFlagInfo` 在构造函数中将自身链入链表头部，无需集中管理。`Parse()` 方法遍历链表匹配命令行参数。

```cpp
// 静态初始化驱动的自注册
DEFINE_bool(verbose, false, "Enable verbose output");
// 展开为:
bool FLAGS_verbose;
static bool unused_verbose = SkFlagInfo::CreateBoolFlag("verbose", nullptr,
                                                         &FLAGS_verbose, false, "...");
```

### 2. 侵入式链表 (Intrusive Linked List)

`SkFlagInfo` 通过 `fNext` 指针维护一个全局单链表，由 `CommandLineFlags::gHead` 指向链表头。这种侵入式设计避免了额外的容器分配，适合静态初始化场景。

### 3. 模式匹配语言

`ShouldSkip()` 实现了一个小型匹配语言：
- `~pattern`: 匹配的测试总是被跳过
- `^pattern`: 要求测试名称以 pattern 开头
- `pattern$`: 要求测试名称以 pattern 结尾
- `^pattern$`: 要求精确匹配

### 4. 类型擦除与类型恢复

`SkFlagInfo` 使用联合式设计存储不同类型的标志值指针（`fBoolValue`、`fIntValue`、`fDoubleValue`、`fStrings`），通过 `fFlagType` 枚举在运行时确定类型。这是一种简单的类型擦除，使得所有类型的标志可以存储在同一个链表中。

### 5. 命名空间化的扩展模块

`CommonFlags*` 模块使用 `CommonFlags` 命名空间组织预定义标志，每个模块聚焦特定领域。这种设计允许工具选择性包含所需的标志头文件，避免不必要的依赖。

### 6. 不可变字符串数组

`StringArray` 的公开接口只提供只读访问（`operator[]`、`contains`），写操作（`reset`、`append`）被限制为 `private`，只有 `SkFlagInfo`（作为友元类）能够修改。这确保了解析完成后标志值不会被意外修改。

## 使用示例

```cpp
// 定义标志（全局命名空间）
DEFINE_string(input, "", "Input file path");
DEFINE_int(iterations, 100, "Number of iterations");
DEFINE_bool(verbose, false, "Enable verbose output");
DEFINE_double(scale, 1.0, "Scale factor");

int main(int argc, char** argv) {
    CommandLineFlags::SetUsage("MyTool [options] ...");
    CommandLineFlags::Parse(argc, argv);

    // 使用标志值
    if (FLAGS_verbose) {
        printf("Input: %s\n", FLAGS_input[0]);
        printf("Iterations: %d\n", FLAGS_iterations);
        printf("Scale: %.2f\n", FLAGS_scale);
    }
}
```

命令行使用：
```bash
./MyTool --input test.skp --iterations 500 --verbose --scale 2.0
./MyTool --noinput  # 布尔标志取反
./MyTool -h         # 显示帮助
```

## 相关文档与参考

- **Skia 工具主目录**: `tools/README.md` - 所有工具概览
- **Viewer**: `tools/viewer/README.md` - 标志系统的主要用户
- **DM 测试运行器**: `dm/` - 使用 CommonFlagsConfig 解析渲染配置
- **gflags 项目**: https://github.com/gflags/gflags - CommandLineFlags 的灵感来源
- **GPU 上下文类型**: `tools/gpu/ContextType.h` - CommonFlagsConfig 使用的上下文枚举
- **Ganesh 上下文选项**: `include/gpu/ganesh/GrContextOptions.h`
