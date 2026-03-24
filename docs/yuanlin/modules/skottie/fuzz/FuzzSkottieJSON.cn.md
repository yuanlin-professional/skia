# FuzzSkottieJSON.cpp

> 源文件: `modules/skottie/fuzz/FuzzSkottieJSON.cpp`

## 概述

`FuzzSkottieJSON.cpp` 是 Skottie 模块的模糊测试（fuzzing）入口程序，用于通过随机/变异输入数据来检测 Skottie JSON 解析器和动画引擎中的潜在崩溃、内存错误和未定义行为。该文件实现了标准的 libFuzzer 接口，将任意字节数据作为 Lottie JSON 输入送入 Skottie 的解析和帧跳转流程，是 Skia 项目持续安全和稳定性测试的重要组成部分。

## 架构位置

该文件位于 `modules/skottie/fuzz/` 目录下，属于 Skottie 模块的测试基础设施。在 Skia 的测试架构中，模糊测试程序独立于单元测试，通常由 CI/CD 系统或专门的模糊测试平台（如 Google 的 OSS-Fuzz）驱动运行。模糊测试与单元测试互补：单元测试验证已知输入的正确行为，模糊测试发现未知输入导致的异常行为。

## 主要类与结构体

该文件不定义任何类或结构体，仅包含两个独立函数。

## 公共 API 函数

### `FuzzSkottieJSON(const uint8_t*, size_t)`
```cpp
void FuzzSkottieJSON(const uint8_t *data, size_t size);
```
- **功能**: 模糊测试的核心函数，将任意数据作为 Lottie JSON 进行解析和帧跳转。
- **流程**:
  1. 将输入数据包装为 `SkMemoryStream`
  2. 尝试通过 `skottie::Animation::Make()` 解析为动画
  3. 如果解析成功，执行 `animation->seek(0.1337f)` 跳转到一个特定帧
- **"Nothing up my sleeve" 数字**: `0.1337f` 是一个故意选择的非特殊值（不是 0、0.5 或 1 等边界值），以测试非边界情况下的帧跳转逻辑。该值来自密码学中的"无隐藏信息"概念，表明选择不含特殊含义。

### `LLVMFuzzerTestOneInput(const uint8_t*, size_t)`
```cpp
extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size);
```
- **功能**: libFuzzer 标准入口点（仅在 `SK_BUILD_FOR_LIBFUZZER` 定义时编译）。
- **额外设置**: 调用 `ToolUtils::UsePortableFontMgr()` 确保使用可移植的字体管理器，消除平台字体差异对模糊测试的影响。
- **返回值**: 始终返回 0（libFuzzer 约定）。

## 内部实现细节

- **优雅的失败处理**: `Animation::Make()` 返回 `nullptr` 表示解析失败，函数直接返回而非崩溃。模糊测试的目标是确保即使输入是完全随机的字节流，解析过程也不会导致崩溃、内存泄漏或未定义行为。
- **可移植字体管理器**: 使用 `ToolUtils::UsePortableFontMgr()` 确保测试结果不受系统字体环境影响，保证可重现性。可移植字体管理器使用内置的测试字体，消除了对系统字体的依赖。
- **条件编译**: `LLVMFuzzerTestOneInput` 仅在 `SK_BUILD_FOR_LIBFUZZER` 定义时存在，支持独立函数调用和 libFuzzer 集成两种使用方式。当不作为 libFuzzer 目标使用时，可以从其他测试代码直接调用 `FuzzSkottieJSON` 函数。
- **extern "C" 链接**: `LLVMFuzzerTestOneInput` 使用 C 链接规约（`extern "C"`），以便 libFuzzer 运行时能正确找到并调用该函数。
- **测试覆盖范围**: 该模糊测试覆盖了 Skottie 的 JSON 解析路径（`skjson::DOM` 构建、动画参数提取、场景图构建）以及帧跳转路径（`seek` 方法中的动画器遍历和场景图重验证）。不覆盖渲染路径，以保持测试的高吞吐量。
- **OSS-Fuzz 集成**: Skia 项目注册了多个模糊测试目标到 Google 的 OSS-Fuzz 平台，该文件即为其中之一。OSS-Fuzz 会持续运行这些测试并自动报告发现的问题。

## 依赖关系

- **`include/core/SkStream.h`**: `SkMemoryStream` 内存流封装
- **`modules/skottie/include/Skottie.h`**: `skottie::Animation` 动画类
- **`tools/fonts/FontToolUtils.h`**: `ToolUtils::UsePortableFontMgr()` 可移植字体设置

## 设计模式与设计决策

- **标准 libFuzzer 接口**: 遵循 LLVM libFuzzer 的标准函数签名 `LLVMFuzzerTestOneInput`，可直接被 libFuzzer 和 OSS-Fuzz 集成。
- **最小化测试表面**: 测试函数尽可能简洁，仅覆盖"解析 + 一次帧跳转"的核心路径，减少无关代码引入的噪声。不测试渲染路径，因为渲染需要额外的资源（画布、表面），会降低模糊测试的吞吐量。
- **确定性**: 使用固定的 seek 值（`0.1337f`）和可移植字体管理器，确保给定相同输入时行为完全一致，这对于问题复现至关重要。
- **两层函数**: `FuzzSkottieJSON` 是核心逻辑（不含 libFuzzer 特定设置），`LLVMFuzzerTestOneInput` 是 libFuzzer 入口（含初始化代码）。这种分离使得核心逻辑可以从其他测试代码中复用。
- **无副作用**: 函数不修改全局状态（`UsePortableFontMgr` 除外，且仅在首次调用时生效），不写入文件系统，不分配持久资源，确保每次调用都是独立的。

## 性能考量

- 模糊测试需要极高的吞吐量（每秒数千到数万次迭代），因此测试函数保持极简，避免不必要的渲染操作。
- `Animation::Make()` 的快速失败路径（无效 JSON 在 `skjson::DOM` 解析阶段即返回 `nullptr`）确保了大部分随机输入能被快速处理，不进入场景图构建阶段。
- 不执行 `render()` 操作，仅测试解析和帧跳转，避免了画布分配、表面创建和实际渲染的开销。
- `SkMemoryStream` 包装零拷贝，不复制输入数据，保持了最小的内存开销。
- 可移植字体管理器使用内存中的固定测试字体，避免了文件系统 I/O。

## 相关文件

- `modules/skottie/include/Skottie.h` -- `Animation::Make()` 和 `seek()` 接口定义
- `modules/skottie/src/Skottie.cpp` -- 动画解析的核心实现（JSON DOM 构建、参数验证、场景图构建）
- `modules/skottie/src/SkottieTest.cpp` -- 常规单元测试，包含 `Skottie_OssFuzz8956` 等模糊测试发现的 bug 回归测试
- `tools/fonts/FontToolUtils.h` -- 测试字体管理工具，`UsePortableFontMgr()` 的实现
- `modules/jsonreader/SkJSONReader.h` -- JSON DOM 解析器，模糊测试的第一道防线
