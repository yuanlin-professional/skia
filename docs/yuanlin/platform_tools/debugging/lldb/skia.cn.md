# skia.py - Skia LLDB 调试器可视化扩展

> 源文件: `platform_tools/debugging/lldb/skia.py`

## 概述

本文件是 Skia 项目的 LLDB 调试器扩展脚本，为 Skia 核心数据类型提供原生的可视化支持。通过注册自定义的类型摘要（summary）和合成提供器（synthetic provider），开发者在 LLDB 调试会话中可以直观地查看 `SkString`、`SkTArray`、`AutoTArray`、`SkSpan`、`sk_sp` 和 `SkFixed` 等 Skia 类型的内容，而无需手动解引用内部成员。

## 架构位置

该文件位于 `platform_tools/debugging/lldb/` 目录下，属于 Skia 项目的开发工具链层。它不参与 Skia 的编译或运行时逻辑，仅在调试阶段通过 LLDB 的 Python 脚本接口加载。可以通过在 `~/.lldbinit` 文件中添加 `command script import` 指令实现自动加载。

## 主要类与结构体

### SkString_SummaryProvider（函数）
- 为 `SkString` 类型提供摘要格式化
- 从 `fRec` 智能指针中提取 `fLength` 和 `fBeginningOfData`，将内部数据格式化为带引号的字符串

### SkTArray_SynthProvider（类）
- 为 `skia_private::TArray` 和 `skia_private::STArray` 模板类型提供合成子元素视图
- 成员：`fData`（数据指针）、`fSize`（元素数量）
- 限制最大显示 10000 个元素以防止调试器卡顿

### AutoTArray_SynthProvider（类）
- 为 `skia_private::AutoTArray` 和 `skia_private::AutoSTArray` 类型提供合成子元素视图
- 成员：`fCount`（元素数量）、`fArray`（通过 `unique_ptr` 内部的 `__ptr_.__value_` 访问数据）
- 依赖 `unique_ptr` 和 `__compressed_pair` 的实现细节

### SkSpan_SynthProvider（类）
- 为 `SkSpan<T>` 模板类型提供合成子元素视图
- 成员：`fPtr`（数据指针）、`fSize`（元素数量）

### sk_sp_SynthProvider（类）
- 为 `sk_sp<T>` 智能指针类型提供透明解引用视图
- 直接将 `fPtr` 的子元素暴露为智能指针的子元素，使调试时无需手动访问内部指针

## 公共 API 函数

- **`SkString_SummaryProvider(valobj, dict)`**: LLDB 调用的摘要提供函数，返回 `SkString` 的可读字符串表示
- **`__lldb_init_module(debugger, dict)`**: LLDB 模块初始化入口点，注册所有类型的可视化规则到 "skia" 类别中

## 内部实现细节

### 支持的 Skia 类型完整列表

| Skia 类型 | 可视化方式 | Provider |
|-----------|-----------|----------|
| `SkString` | 摘要（显示字符串内容） | `SkString_SummaryProvider` |
| `sk_sp<T>` | 合成 + 摘要（透明解引用） | `sk_sp_SynthProvider` |
| `skia_private::TArray<T>` | 合成 + 摘要（显示大小和元素） | `SkTArray_SynthProvider` |
| `skia_private::STArray<T>` | 合成 + 摘要 | `SkTArray_SynthProvider` |
| `SkSpan<T>` | 合成（显示元素） | `SkSpan_SynthProvider` |
| `skia_private::AutoTArray<T>` | 合成 + 摘要 | `AutoTArray_SynthProvider` |
| `skia_private::AutoSTArray<T>` | 合成 + 摘要 | `AutoTArray_SynthProvider` |
| `SkFixed` | 摘要（同时显示整数和浮点） | 内联 Python 脚本 |

### 合成提供器协议
每个 SynthProvider 类都实现了 LLDB 的合成子元素协议：
- `__init__(valobj, dict)`: 初始化，保存值对象引用
- `num_children()`: 返回子元素数量（数组长度）
- `get_child_index(name)`: 将 `[N]` 格式的名称转换为数组索引
- `get_child_at_index(index)`: 通过偏移量计算访问指定索引的元素
- `update()`: 在值变化时刷新内部缓存的指针和类型信息
- `has_children()`: 返回 True（所有容器类型都有子元素）

### SkString 解码流程
1. 通过 `sk_sp` 的 `fRec` 成员访问内部记录
2. 读取 `fLength` 获取字符串长度
3. 获取 `fBeginningOfData` 的地址并读取指定长度的字节数据
4. 追加零终止符后转换为 Python 字符串

### 类型注册
`__lldb_init_module` 中使用 LLDB 命令注册：
- `type summary add`: 注册摘要格式（SkString、sk_sp、TArray、SkFixed）
- `type synthetic add`: 注册合成提供器（sk_sp、TArray、SkSpan、AutoTArray）
- 使用 `-x` 标志进行正则表达式匹配以支持模板类型
- 所有注册在 "skia" 类别下（`-w skia`），最后通过 `type category enable skia` 激活

### SkFixed 格式化
使用内联 Python 脚本将 `SkFixed`（16.16 定点数）同时显示为整数值和浮点值。公式为 `value / 65536.0`，其中 `value` 是 32 位整数的原始值。例如，`SkFixed` 值 131072 会显示为 `131072 (2.0)`。

### 使用方法

要启用此调试扩展，在 LLDB 调试会话中执行：
```
command script import /path/to/skia/platform_tools/debugging/lldb/skia.py
```

或在 `~/.lldbinit` 文件中添加上述命令以自动加载。加载后，所有支持的 Skia 类型将自动获得增强的可视化效果。

### 正则表达式匹配模式

类型匹配使用以下正则表达式：
- `^sk_sp<.+>$` - 匹配所有 `sk_sp` 模板实例化
- `^skia_private::S?TArray<.+>$` - 匹配 TArray 和 STArray
- `^SkSpan<.+>$` - 匹配所有 SkSpan 实例化
- `^skia_private::AutoS?TArray<.+>$` - 匹配 AutoTArray 和 AutoSTArray

## 依赖关系

- **`lldb` 模块**: LLDB Python 脚本接口（SBData、SBError 等）
- **Skia 内部数据结构布局**: 依赖 `SkString`、`SkTArray`、`sk_sp` 等类型的内存布局
- **libc++ 实现细节**: `AutoTArray_SynthProvider` 依赖 `std::unique_ptr` 内部的 `__ptr_.__value_` 访问路径

## 设计模式与设计决策

- **策略模式**: 每种 Skia 类型对应一个独立的 SynthProvider 类，通过正则匹配自动选择
- **类别化管理**: 所有可视化规则归入 "skia" 类别，可通过 `type category enable/disable skia` 整体控制
- **防御性编程**: 所有数据访问操作都包裹在 try-except 块中，防止调试器因数据损坏而崩溃
- **元素数量限制**: 容器类型限制最大显示 10000 个元素，防止大数组导致调试器无响应
- **自动初始化**: 支持通过 `~/.lldbinit` 配置自动加载，无需每次调试时手动导入

## 性能考量

- 合成提供器采用惰性求值，仅在用户展开变量时才计算子元素
- 每个子元素通过 `CreateChildAtOffset` 直接定位内存，避免遍历整个数组
- `num_children()` 方法将元素数量上限设为 10000，防止超大数组导致 UI 卡死
- `update()` 方法缓存类型信息和指针，避免重复的类型解析开销
- `SkString_SummaryProvider` 使用 `GetPointeeData` 一次性读取整个字符串内容，减少调试器与被调试进程之间的通信次数
- 正则表达式模式匹配（`-x` 标志）在类型注册时编译一次，后续匹配开销极小
- `sk_sp_SynthProvider` 的实现最为轻量，仅转发 `fPtr` 的子元素查询，无额外内存分配

### 已知限制

- `AutoTArray_SynthProvider` 依赖 libc++ 的 `std::unique_ptr` 内部结构（`__ptr_.__value_`），使用其他标准库实现（如 libstdc++）时可能需要调整
- `SkString_SummaryProvider` 假设 `SkString` 使用 `sk_sp<Rec>` 内部存储，如果内部实现变更可能需要更新
- 所有 SynthProvider 的 `try-except` 块会静默捕获异常，调试数据损坏的对象时可能返回不准确的结果而非报错

## 相关文件

- `include/core/SkString.h` - SkString 类型定义
- `include/private/base/SkTArray.h` - TArray/STArray 类型定义
- `include/core/SkSpan.h` - SkSpan 类型定义
- `include/core/SkRefCnt.h` - sk_sp 智能指针定义
- `include/private/base/SkFixed.h` - SkFixed 定点数类型定义
- `platform_tools/debugging/` - 调试工具目录
- `tools/debugger/` - Skia Debugger 应用程序

### 与其他调试工具的比较

Skia 项目还提供了其他调试和分析工具：
- **Skia Debugger**: 基于 GUI 的 SKP 文件调试器，可逐步回放绘图操作
- **Skia Viewer**: 交互式的 SKP 查看器，支持实时修改渲染参数
- **perf.skia.org**: 在线性能监控面板，跟踪渲染性能回归

本 LLDB 扩展填补了源码级调试中的可视化空白，使开发者能够在断点处直接检查 Skia 数据结构的内容，而无需手动展开指针链。

### 兼容性说明

- 该脚本设计用于与 Apple 的 LLDB 和 LLVM 项目的 LLDB 配合使用
- 对 libc++ 的 `std::unique_ptr` 内部布局有硬编码依赖，不同版本可能需要调整
- 在 Xcode 的 LLDB 和命令行 LLDB 中均可使用
