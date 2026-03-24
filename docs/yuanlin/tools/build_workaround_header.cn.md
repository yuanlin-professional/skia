# build_workaround_header.py - GPU 驱动 Bug 规避定义代码生成器

> 源文件: [tools/build_workaround_header.py](../../tools/build_workaround_header.py)

## 概述

此脚本是一个代码生成器，用于从一组输入文件中读取 GPU 驱动 bug 规避项（workaround）名称，合并去重后生成一个 C/C++ 头文件。生成的头文件定义了一个 `GPU_DRIVER_BUG_WORKAROUNDS` 宏，该宏使用 X-Macro 模式列出所有已知的 GPU 驱动 bug 规避项。此机制源自 Chromium 项目，用于在运行时根据检测到的 GPU 硬件和驱动版本启用相应的规避措施。

## 架构位置

该脚本属于 Skia 工具层（`tools/`），参与构建系统的代码生成阶段。生成的头文件被 Skia 的 GPU 后端（Ganesh/Graphite）使用，用于定义和管理各种 GPU 驱动 bug 的规避措施。这是 Skia 与 Chromium GPU 基础设施集成的一部分。

## 主要类与结构体

无类定义。关键函数如下：

- **`merge_files_into_workarounds(files)`**：合并多个输入文件中的规避项名称
- **`write_header(filename, workarounds)`**：生成头文件
- **`main(argv)`**：入口函数

## 公共 API 函数

| 函数 | 参数 | 返回值 | 描述 |
|------|------|--------|------|
| `merge_files_into_workarounds(files)` | `files`: 输入文件路径列表 | 排序后的规避项列表 | 读取并合并所有输入文件中的规避项 |
| `write_header(filename, workarounds)` | `filename`: 输出头文件路径; `workarounds`: 规避项列表 | 无 | 生成 C/C++ 头文件 |
| `main(argv)` | `argv`: 命令行参数 | 无 | 解析参数并执行生成 |

## 内部实现细节

1. **输入解析**（`merge_files_into_workarounds`）：
   - 逐个打开输入文件
   - 每行读取一个规避项名称（去除首尾空白）
   - 使用 `set` 进行去重
   - 排序后返回列表

2. **头文件生成**（`write_header`）：
   - 写入许可证头和 "DO NOT EDIT" 警告
   - 生成 `GPU_DRIVER_BUG_WORKAROUNDS(GPU_OP)` 宏定义
   - 对每个规避项生成两行：
     - `GPU_OP(UPPER_CASE_NAME,` — 大写版本
     - `       lower_case_name)` — 原始名称
   - 使用 `#ifndef` 保护防止重复定义
   - 对齐格式化：计算最大规避项名称长度，使用空格填充实现列对齐

3. **命令行接口**：
   - `--output-file`：输出文件名（默认 `gpu_driver_bug_workaround_autogen.h`）
   - 其余参数为输入文件列表

## 依赖关系

- **Python 标准库**：`os`、`sys`、`optparse`（旧式参数解析）
- **输入**：包含规避项名称的文本文件（每行一个）
- **输出**：C/C++ 头文件

## 设计模式与设计决策

- **X-Macro 模式**：生成的宏使用 X-Macro（也称 X-List）模式，允许消费者通过定义 `GPU_OP` 宏来将规避项列表展开为不同的代码结构（如枚举值、字符串数组等）。
- **双重命名**：每个规避项同时提供大写版本（作为枚举常量）和小写版本（作为字符串标识符），符合 C/C++ 命名惯例。
- **多文件合并**：支持从多个输入文件合并规避项，允许不同组件独立维护各自的规避列表。
- **自动生成警告**：头文件包含自动生成声明和源脚本名称，防止手动编辑。
- **格式化对齐**：使用续行符 `\` 和空格填充确保生成的宏定义格式整齐，提升可读性。

## 性能考量

- 代码生成器只在构建时运行，不影响运行时性能。
- 输入文件通常很小（数十个规避项），处理速度极快。
- 生成的头文件在编译时展开，编译器可以优化掉未使用的规避项。

## 相关文件

- 生成的 `gpu_driver_bug_workaround_autogen.h` 头文件
- Skia GPU 后端中使用 `GPU_DRIVER_BUG_WORKAROUNDS` 宏的代码
- Chromium 中对应的 GPU 驱动 bug 列表文件
- `src/gpu/` 目录下的 GPU 能力检测和规避逻辑

### 补充说明

- 此文件是 Skia 工具生态系统的组成部分，为开发、测试和构建流程提供必要的辅助功能支持。
- 此文件是 Skia 工具生态系统的组成部分，为开发、测试和构建流程提供必要的辅助功能支持。
- 此文件是 Skia 工具生态系统的组成部分，为开发、测试和构建流程提供必要的辅助功能支持。
- 此文件是 Skia 工具生态系统的组成部分，为开发、测试和构建流程提供必要的辅助功能支持。
