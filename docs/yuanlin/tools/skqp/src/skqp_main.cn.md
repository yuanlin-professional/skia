# skqp_main.cpp - SkQP 命令行测试运行器

> 源文件: `tools/skqp/src/skqp_main.cpp`

## 概述

`skqp_main.cpp` 是 SkQP（Skia Quality Program）测试框架的命令行版本入口。与 Android JNI 版本不同，此文件提供了一个独立的命令行程序，可以在桌面平台（Linux、macOS、Windows）上运行 SkQP 单元测试套件。它主要用于开发调试和 CI 环境中的非 Android 测试。

程序接受资源目录和输出目录作为必选参数，并支持灵活的测试名称匹配规则进行测试过滤。

## 架构位置

```
SkQP 测试框架
├── 核心引擎
│   └── tools/skqp/src/skqp.h/.cpp  <-- SkQP 测试引擎
├── 运行入口
│   ├── jni_skqp.cpp                <-- Android JNI 版本
│   └── skqp_main.cpp               <-- 本文件：命令行版本
└── GPU 测试支持
    └── skqp_GpuTestProcs.cpp       <-- GPU 测试过程实现
```

## 主要类与结构体

### `StdAssetManager`
基于标准文件系统的资源管理器实现，继承自 `SkQPAssetManager`。

```cpp
class StdAssetManager : public SkQPAssetManager {
public:
    StdAssetManager(const char* prefix);
    sk_sp<SkData> open(const char* subpath) override;          // 从文件系统读取文件
    std::vector<std::string> iterateDir(const char* directory,
                                         const char* extension) override;  // 遍历目录
private:
    std::string fPrefix;  // 资源根目录路径
};
```

与 Android 版本的 `AndroidAssetManager` 对应，但使用标准文件系统 API。

### `Args`
简单的命令行参数结构体：

```cpp
struct Args {
    char* assetDir;   // 资源目录
    char* outputDir;  // 输出目录
};
```

## 公共 API 函数

### `main(int argc, char* argv[])`
程序入口，执行流程：
1. 解析命令行参数
2. 设置资源路径
3. 创建资源管理器并初始化 SkQP
4. 遍历并执行所有单元测试（应用匹配规则过滤）
5. 生成测试报告

用法：
```
skqp_main ASSET_DIR OUTPUT_DIR [TEST_MATCH_RULES]
```

返回值：0 表示所有测试通过，1 表示有测试失败。

## 内部实现细节

### 测试匹配规则

`should_skip()` 函数实现了灵活的测试名称匹配机制：

| 规则语法 | 含义 |
|---------|------|
| `substring` | 名称包含该子串则匹配（运行） |
| `~substring` | 名称包含该子串则跳过 |
| `^prefix` | 名称以该前缀开头则匹配 |
| `suffix$` | 名称以该后缀结尾则匹配 |
| `^exact$` | 精确匹配 |

匹配逻辑：
- 如果没有指定任何规则，默认运行所有测试
- 排除规则（`~`）优先级高于包含规则
- 如果所有规则都是排除规则，未匹配的测试默认运行
- 如果存在包含规则，未匹配的测试默认跳过

```cpp
static bool should_skip(const char* const* rules, size_t count, const char* name);
```

### 测试执行流程

```cpp
for (SkQP::UnitTest test : skqp.getUnitTests()) {
    auto testName = std::string("unitTest_") + SkQP::GetUnitTestName(test);
    if (should_skip(matchRules, matchRulesCount, testName.c_str())) {
        continue;
    }
    std::vector<std::string> errors = skqp.executeTest(test);
    // 输出结果...
}
skqp.makeReport();
```

每个测试名称自动添加 `unitTest_` 前缀，测试结果实时输出到 stdout。

### 资源路径设置

```cpp
SetResourcePath(std::string(args.assetDir + std::string("/resources")).c_str());
```

资源目录下需要有 `resources` 子目录，包含 Skia 测试所需的图像和字体等资源文件。

## 依赖关系

- **Skia 核心**：`SkData`, `SkOSFile`, `SkOSPath`
- **Skia 工具**：`tools/Resources.h`（资源路径管理）
- **SkQP 框架**：`tools/skqp/src/skqp.h`
- **C++ 标准库**：`<iostream>`, `<sys/stat.h>`

## 设计模式与设计决策

1. **策略模式的资源管理**：`SkQPAssetManager` 接口使得 SkQP 核心引擎不依赖于具体的资源加载方式。命令行版本使用 `StdAssetManager`（标准文件系统），Android 版本使用 `AndroidAssetManager`（APK Asset）。

2. **灵活的测试过滤**：匹配规则语法与 Google Test 的过滤规则类似，支持前缀匹配、后缀匹配、子串匹配和排除模式，便于在调试时快速运行特定测试。

3. **简洁的输出格式**：每个测试一行输出，包含测试名和结果（`[PASSED]` 或 `[FAILED: N error(s)]`），适合 CI 日志解析。

4. **单次报告生成**：所有测试执行完毕后才调用 `makeReport()`，确保报告包含完整结果。

## 性能考量

- **无并行执行**：测试按顺序串行执行，简化了实现但可能影响大量测试时的执行时间。SkQP 的设计目标是合规性验证而非速度。
- **文件系统资源加载**：`StdAssetManager` 直接使用 `SkData::MakeFromFileName` 从文件系统加载，比 Android Asset 加载更快且支持内存映射。
- **延迟初始化**：资源仅在测试实际需要时才加载，避免启动时的大量 I/O。
- **匹配规则效率**：`should_skip` 函数对每个测试名称遍历所有规则，时间复杂度为 O(rules * name_length)。对于典型的少量规则（< 10 条），这不构成瓶颈。
- **stdout 刷新**：每个测试完成后显式调用 `std::cout.flush()`，确保在长时间运行的测试中输出不会被缓冲。

## 相关文件

- `tools/skqp/src/skqp.h` - SkQP 核心测试引擎（`SkQP` 类定义）
- `tools/skqp/src/jni_skqp.cpp` - Android JNI 版本入口
- `tools/skqp/src/skqp_GpuTestProcs.cpp` - GPU 测试过程实现
- `tools/Resources.h` - Skia 资源路径管理（`SetResourcePath`, `GetResourcePath`）
- `src/core/SkOSFile.h` - 文件系统操作（`sk_mkdir`, `SkOSFile::Iter`）
- `src/utils/SkOSPath.h` - 路径拼接工具
- `include/core/SkData.h` - 不可变数据容器（`MakeFromFileName`）
