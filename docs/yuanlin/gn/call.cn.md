# call.py

> 源文件: gn/call.py

## 概述

`call.py` 是 Skia 构建系统中最简洁的工具脚本之一,提供了一个极简的命令执行包装器。该脚本的唯一功能是将命令行参数传递给 `subprocess.check_call()` 执行,并在命令失败时传播错误。虽然功能单一,但它在 GN 构建系统中扮演着重要的桥梁角色,允许构建规则以统一的方式调用各种外部工具和脚本。

这个工具的设计哲学体现了 Unix "做一件事并做好"的原则,通过提供最小但可靠的功能,成为构建系统中的通用命令执行器。

## 架构位置

`call.py` 在 Skia 构建工具链中的位置:

```
skia/
├── gn/                              # GN 构建脚本目录
│   ├── call.py                      # 本脚本 - 通用命令包装器
│   ├── checkdir.py                  # 目录检查工具
│   ├── find_headers.py              # 头文件收集器
│   └── ...                          # 其他专用工具
├── BUILD.gn                         # 主构建配置
└── tools/                           # 各种外部工具
```

在构建流程中的角色:
- **位置**: 工具层,提供基础执行能力
- **用途**: 从 GN action 调用任意命令
- **特点**: 通用、无状态、错误透明传播

## 主要类与结构体

该脚本不定义任何类或结构体,完全基于函数调用实现。

## 公共 API 函数

### 命令行接口

```python
subprocess.check_call(sys.argv[1:])
```

**参数**:
- `sys.argv[1:]`: 命令行的所有参数(除脚本名外)
  - 第一个参数:要执行的命令
  - 后续参数:传递给该命令的参数

**行为**:
- 执行指定的命令
- 等待命令完成
- 如果命令返回非零退出码,抛出 `CalledProcessError`
- 如果命令成功(返回 0),脚本正常退出

**返回值**: 无显式返回值,通过退出码表示成功或失败

**调用示例**:

```bash
# 执行简单命令
python gn/call.py ls -la

# 执行 Git 命令
python gn/call.py git status

# 编译一个文件
python gn/call.py gcc -o output input.c -Wall

# 运行测试
python gn/call.py ./run_tests --verbose

# 复制文件
python gn/call.py cp source.txt dest.txt
```

### GN 构建系统集成

```gn
# 在 BUILD.gn 中使用
action("run_custom_tool") {
  script = "gn/call.py"
  args = [
    "tools/custom_generator",
    "--input", rebase_path("input.dat"),
    "--output", rebase_path("$target_gen_dir/output.h"),
  ]
  inputs = [ "input.dat" ]
  outputs = [ "$target_gen_dir/output.h" ]
}
```

**为什么使用 call.py 而不是直接调用工具?**
- GN 的 `script` 字段期望 Python 脚本
- 某些工具不是 Python 脚本(如 shell 脚本、编译的二进制)
- `call.py` 提供统一的调用接口

## 内部实现细节

### subprocess.check_call() 行为

```python
subprocess.check_call(sys.argv[1:])
```

**函数特性**:
- **同步执行**: 阻塞直到命令完成
- **错误检测**: 检查退出码,非零抛出异常
- **标准流继承**: 子进程的 stdout/stderr 直接输出到父进程
- **环境继承**: 子进程继承当前进程的环境变量
- **工作目录**: 子进程使用当前工作目录

### 参数传递机制

```python
sys.argv[1:]  # 切片操作,跳过脚本名
```

**示例转换**:
```bash
# 命令行输入:
python gn/call.py echo "Hello World"

# sys.argv 内容:
['gn/call.py', 'echo', 'Hello World']

# sys.argv[1:] 传递给 check_call:
['echo', 'Hello World']

# 实际执行:
echo "Hello World"
```

### 错误处理

**异常传播**:
```python
# 没有 try-except,异常自动向上传播
subprocess.check_call(...)
```

**失败场景**:
1. **命令不存在**: 抛出 `FileNotFoundError` (Python 3) 或 `OSError` (Python 2)
2. **命令执行失败**: 抛出 `CalledProcessError`,包含退出码
3. **权限不足**: 抛出 `PermissionError`

**构建系统响应**:
- GN/Ninja 捕获异常
- 将构建标记为失败
- 显示错误信息和命令
- 停止依赖此目标的后续构建

### Python 2/3 兼容性

该脚本在 Python 2 和 3 中行为一致:
- `subprocess.check_call` 在两个版本中都存在
- `sys.argv` 是标准接口
- 没有使用版本特定的语法

## 依赖关系

### Python 标准库

```python
import subprocess  # 子进程管理
import sys         # 命令行参数访问
```

**无外部依赖**: 脚本完全基于 Python 标准库,确保最大兼容性。

### 系统工具依赖

**依赖被调用的工具**:
- 脚本本身不依赖特定工具
- 但要求被调用的命令在系统 PATH 中或使用绝对路径
- 工具的可用性由调用者保证

### 与构建系统的关系

```
GN 构建规则
    ↓
action { script = "call.py" }
    ↓
call.py 执行
    ↓
外部工具/脚本运行
    ↓
结果返回给 Ninja
```

## 设计模式与设计决策

### 透明代理模式
脚本作为命令的透明代理:
- 不修改参数
- 不过滤输出
- 不改变退出码
- 不添加额外逻辑

### 最小化设计

**为什么不添加更多功能?**
- **日志记录?** 构建系统已经记录所有命令
- **参数验证?** 由被调用工具负责
- **超时控制?** 由构建系统管理
- **输出捕获?** 某些工具需要交互式输出

保持简单使脚本:
- 易于理解和审计
- 不会成为瓶颈
- 行为可预测

### 错误传播策略

**不捕获异常的原因**:
```python
# 不这样做:
try:
    subprocess.check_call(sys.argv[1:])
except Exception:
    pass  # 或进行自定义处理
```

**正确做法**:
让异常自然传播,确保:
- 构建系统能够检测失败
- 错误信息完整传递
- 调试信息不丢失

### Unix 哲学体现

1. **做一件事**: 仅执行命令
2. **做好这件事**: 可靠的错误处理
3. **协作良好**: 与构建系统无缝集成

## 性能考量

### 执行开销

**进程启动成本**:
- Python 解释器启动: ~30-50ms
- subprocess 创建: ~5-10ms
- 总固定开销: ~35-60ms

**实际命令时间**:
- 对于快速命令(如 `echo`): 开销显著
- 对于慢命令(如编译): 开销可忽略

### 性能优化考虑

**为什么不用 shell 脚本代替?**
```bash
# 等价的 shell 脚本
#!/bin/sh
exec "$@"
```

**选择 Python 的原因**:
- 跨平台一致性(Windows/macOS/Linux)
- GN 本身是 Python 友好的
- Python 在构建环境中总是可用
- 未来可能扩展功能

### 内存占用

**最小内存足迹**:
- Python 解释器基线: ~5-10 MB
- 脚本本身: < 1 KB
- 子进程独立内存空间
- 无内存泄漏风险(立即退出)

### 并发安全性

**完全无状态**:
- 无全局变量
- 无文件系统写入
- 无共享资源
- 可安全并行调用

## 相关文件

### 同类包装器

**Skia 构建系统中的其他包装器**:
- **`gn/checkdir.py`**: 专用于目录检查
- **`gn/highest_version_dir.py`**: 专用于版本目录查找
- **`gn/find_headers.py`**: 专用于头文件收集

**call.py vs 专用工具**:
- `call.py`: 通用,适合一次性或简单任务
- 专用工具: 针对特定场景优化,提供额外功能

### 典型使用场景

**执行测试工具**:
```gn
action("run_unit_tests") {
  script = "gn/call.py"
  args = [ "./out/tests", "--gtest_output=xml:out/test_results.xml" ]
  testonly = true
}
```

**调用代码生成器**:
```gn
action("generate_sources") {
  script = "gn/call.py"
  args = [
    "tools/generate_code.sh",
    rebase_path("$target_gen_dir"),
  ]
}
```

**复制资源文件**:
```gn
action("copy_resources") {
  script = "gn/call.py"
  args = [
    "cp", "-r",
    rebase_path("resources/"),
    rebase_path("$root_out_dir/resources/"),
  ]
}
```

**执行 Git 操作**:
```gn
action("get_git_hash") {
  script = "gn/call.py"
  args = [
    "git", "rev-parse", "HEAD",
  ]
  outputs = [ "$target_gen_dir/git_hash.txt" ]
}
```

### 替代方案

**GN 内置功能**:
```gn
# 某些情况可以使用 exec_script
git_hash = exec_script("git", ["rev-parse", "HEAD"], "trim string")

# 或使用 copy 规则
copy("copy_files") {
  sources = [ "input.txt" ]
  outputs = [ "$target_gen_dir/output.txt" ]
}
```

**直接使用工具**:
```gn
# 如果工具是 Python 脚本
action("custom_action") {
  script = "tools/my_tool.py"  # 无需 call.py
  args = [ "--input", "..." ]
}
```

**何时使用 call.py**:
- 工具不是 Python 脚本
- 需要执行 shell 命令
- 一次性任务,不值得写专用脚本
- 需要跨平台兼容的命令执行

该脚本虽然简单,但提供了构建系统中不可或缺的基础功能。其极简设计确保了可靠性和可预测性,使其成为处理各种临时构建任务的理想工具。
