# ProcessWorklist

> 源文件: `tools/skslc/ProcessWorklist.h`, `tools/skslc/ProcessWorklist.cpp`

## 概述

`ProcessWorklist` 是 SkSL 编译器（skslc）的批处理工具函数，用于从工作列表文件（worklist）中读取多组命令行参数并批量执行。工作列表文件使用简单的文本格式，每行一个参数，空行分隔不同的命令组。该函数广泛用于批量编译着色器文件，支持并行构建系统和测试框架。

主要功能：
- 解析 `.worklist` 文件格式
- 批量执行命令（通过回调函数）
- 错误聚合和优先级排序
- 简洁的错误报告

## 架构位置

```
skia/
├── tools/
│   └── skslc/
│       ├── ProcessWorklist.h/cpp      # 工作列表处理
│       ├── Main.cpp                   # skslc 主程序
│       └── *.worklist                 # 工作列表文件
├── src/
│   └── sksl/
│       └── SkSLCompiler.h/cpp         # SkSL 编译器核心
└── gn/
    └── sksl.gni                       # 构建配置
```

## 主要类与结构体

### 枚举 `ResultCode`

定义命令执行的结果代码，按严重程度排序。

```cpp
enum class ResultCode {
    kSuccess = 0,              // 成功
    kCompileError = 1,         // 编译错误（预期的，如单元测试）
    kInputError = 2,           // 输入错误（文件不存在等）
    kOutputError = 3,          // 输出错误（写入失败等）
    kConfigurationError = 4,   // 配置错误（参数错误等）
};
```

**设计理念**: 值越大越严重，方便使用 `std::max` 聚合错误。

**特殊语义**: `kCompileError` 严重度最低，因为在单元测试中编译错误是预期行为。

## 公共 API 函数

### `ProcessWorklist`

```cpp
ResultCode ProcessWorklist(
    const char* worklistPath,
    const std::function<ResultCode(SkSpan<std::string> args)>& processCommandFn);
```

从工作列表文件读取命令并批量执行。

**参数**:
- `worklistPath`: 工作列表文件路径（必须以 `.worklist` 结尾）
- `processCommandFn`: 命令处理函数，接收参数数组，返回结果代码

**返回值**: 所有命令的"最差"结果代码（最大值）

**工作列表格式**:
```
arg1
arg2
arg3

arg4
arg5

arg6
```

- 每行一个参数
- 空行分隔不同的命令组
- 文件结尾可以有或没有空行

**解析为命令**:
```
命令 1: ["sksl", "arg1", "arg2", "arg3"]
命令 2: ["sksl", "arg4", "arg5"]
命令 3: ["sksl", "arg6"]
```

注意：第一个参数自动设置为 "sksl"（程序名）。

**实现细节**:

1. **文件扩展名验证**:
```cpp
if (!skstd::ends_with(inputPath, ".worklist")) {
    printf("expected .worklist file, found: %s\n\n", worklistPath);
    return ResultCode::kConfigurationError;
}
```

2. **逐行读取**:
```cpp
std::vector<std::string> args = {"sksl"};
std::ifstream in(worklistPath);
for (std::string line; std::getline(in, line); ) {
    if (in.rdstate()) {
        printf("error reading '%s'\n", worklistPath);
        return ResultCode::kInputError;
    }
    // ...
}
```

3. **参数累积与命令执行**:
```cpp
if (!line.empty()) {
    args.push_back(std::move(line));  // 累积参数
} else {
    if (!args.empty()) {
        ResultCode outcome = processCommandFn(args);  // 执行命令
        resultCode = std::max(resultCode, outcome);   // 聚合错误
        args.resize(1);  // 保留 "sksl"，清除其他参数
    }
}
```

4. **处理文件结尾未完成的命令**:
```cpp
if (args.size() > 1) {
    ResultCode outcome = processCommandFn(args);
    resultCode = std::max(resultCode, outcome);
}
```

5. **返回最差结果**:
```cpp
return resultCode;  // 最大的 ResultCode 值
```

## 内部实现细节

### 参数累积策略

```cpp
std::vector<std::string> args = {"sksl"};  // 永远保留第一个元素
```

使用 `resize(1)` 而非 `clear()` 避免重复添加 "sksl"。

### 错误聚合算法

```cpp
resultCode = std::max(resultCode, outcome);
```

使用数值比较而非复杂的错误合并逻辑，简洁高效。

### 流状态检查

```cpp
if (in.rdstate()) {
    return ResultCode::kInputError;
}
```

检测文件读取错误（权限问题、磁盘故障等）。

### 移动语义优化

```cpp
args.push_back(std::move(line));
```

避免复制字符串，减少内存分配。

## 依赖关系

### 直接依赖

**标准库**:
- `<fstream>`: 文件流
- `<vector>`: 动态数组
- `<functional>`: 函数对象
- `<algorithm>`: `std::max`

**Skia 工具库**:
- `src/base/SkStringView.h`: 字符串视图（`skstd::ends_with`）
- `include/core/SkSpan.h`: 数组视图

### 被依赖情况

- `tools/skslc/Main.cpp`: skslc 主程序
- 构建系统（GN/Bazel）：批量编译着色器
- 测试框架：批量运行测试用例

## 设计模式与设计决策

### 回调函数模式

```cpp
const std::function<ResultCode(SkSpan<std::string> args)>& processCommandFn
```

将命令处理逻辑委托给调用者，`ProcessWorklist` 只负责解析和调度。

**优势**:
- 解耦：工作列表处理与具体命令逻辑分离
- 灵活：可用于不同的批处理场景
- 可测试：易于模拟和测试

### 简单文本格式

工作列表使用纯文本而非 JSON/XML 的原因：
- **易于生成**: 构建脚本简单输出
- **易于编辑**: 手动调试和测试
- **高效解析**: 无需复杂解析器
- **版本控制友好**: 文本差异清晰

### 错误优先级设计

```cpp
enum class ResultCode {
    kSuccess = 0,
    kCompileError = 1,    // 最低优先级
    kInputError = 2,
    kOutputError = 3,
    kConfigurationError = 4,  // 最高优先级
};
```

**编译错误优先级低**的原因：
- 单元测试故意触发编译错误（如负面测试）
- 真正的问题（配置错误、I/O 错误）应该优先报告

### 参数数组视图

```cpp
SkSpan<std::string> args
```

使用 `SkSpan` 而非 `std::vector&` 避免不必要的复制和所有权转移。

## 性能考量

### 文件 I/O 性能

**逐行读取**:
```cpp
for (std::string line; std::getline(in, line); ) {
    // ...
}
```

- 缓冲 I/O：`std::ifstream` 内部使用缓冲区
- 内存分配：每行一次 `std::string` 分配

**典型性能**:
- 小工作列表（< 100 行）：< 1ms
- 中等工作列表（1000 行）：5-10ms
- 大工作列表（10000 行）：50-100ms

解析开销远小于实际命令执行（编译着色器通常需要 10-100ms/个）。

### 字符串移动优化

```cpp
args.push_back(std::move(line));
```

避免复制，特别是对于长路径字符串（可能数百字节）。

### 错误聚合开销

```cpp
resultCode = std::max(resultCode, outcome);
```

整数比较，约 1 纳秒，可忽略。

### 内存使用

**参数向量**: 每个命令约 10 个参数，每个参数约 50 bytes，约 500 bytes/命令。

**峰值内存**: 仅保存当前命令的参数，约 1KB。

## 相关文件

### SkSL 编译器
- `tools/skslc/Main.cpp`: 主程序
- `src/sksl/SkSLCompiler.h/cpp`: 编译器核心

### 工作列表文件
- `gn/sksl.gni`: GN 构建配置
- `*.worklist`: 着色器编译列表

### 使用示例

**创建工作列表** (`shaders.worklist`):
```
input1.sksl
--output=output1.glsl
--stage=fragment

input2.sksl
--output=output2.glsl
--stage=vertex

input3.sksl
--output=output3.glsl
```

**使用 ProcessWorklist**:
```cpp
#include "tools/skslc/ProcessWorklist.h"

ResultCode compileShader(SkSpan<std::string> args) {
    // args[0] = "sksl"
    // args[1] = "input.sksl"
    // args[2] = "--output=output.glsl"
    // ...

    // 调用编译器
    // ...

    return ResultCode::kSuccess;
}

int main(int argc, char** argv) {
    if (argc == 2 && ends_with(argv[1], ".worklist")) {
        ResultCode result = ProcessWorklist(argv[1], compileShader);
        return static_cast<int>(result);
    }

    // 处理单个文件
    // ...
}
```

**实际使用** (skslc):
```bash
# 批量编译
$ skslc shaders.worklist

# 单个文件
$ skslc input.sksl --output=output.glsl
```

### 错误处理示例

```cpp
ResultCode result = ProcessWorklist("test.worklist", [](SkSpan<std::string> args) {
    // 模拟不同错误
    if (args[1] == "missing.sksl") {
        return ResultCode::kInputError;
    }
    if (args[1] == "invalid.sksl") {
        return ResultCode::kCompileError;
    }
    if (args[1] == "readonly_output.sksl") {
        return ResultCode::kOutputError;
    }
    return ResultCode::kSuccess;
});

// result 将是最严重的错误码（kOutputError）
```

### 构建系统集成

**GN 示例**:
```gn
action("compile_shaders") {
  script = "//tools/skslc/skslc"
  args = [ rebase_path("shaders.worklist") ]
  inputs = [ "shaders.worklist", "input1.sksl", "input2.sksl" ]
  outputs = [ "output1.glsl", "output2.glsl" ]
}
```

这种批处理模式允许并行构建系统高效调度编译任务。
