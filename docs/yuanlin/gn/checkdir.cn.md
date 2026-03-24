# checkdir.py

> 源文件: gn/checkdir.py

## 概述

`checkdir.py` 是一个极其简洁的 Python 实用工具脚本,用于在 Skia 构建系统中验证目录是否存在。该脚本接收单个目录路径作为参数,检查该路径是否为有效目录,并将布尔结果输出到标准输出。这个工具主要用于 GN 构建脚本中的条件判断,帮助构建系统根据目录存在性做出决策。

尽管功能简单,但该脚本在构建系统中扮演着重要角色,允许 GN 构建规则动态适应不同的源代码树配置和可选依赖的存在性。

## 架构位置

`checkdir.py` 位于 Skia 的构建工具集合中:

```
skia/
├── gn/                          # GN 构建辅助脚本目录
│   ├── checkdir.py              # 本脚本 - 目录检查工具
│   ├── find_headers.py          # 头文件收集器
│   ├── call.py                  # 命令执行包装器
│   └── ...                      # 其他构建工具
├── BUILD.gn                     # 主构建配置文件
└── third_party/                 # 可能检查的第三方依赖目录
    └── externals/               # 外部依赖
```

在构建流程中的作用:
- **触发时机**: GN 配置阶段
- **典型用途**: 检测可选功能的依赖是否存在
- **输出结果**: 布尔值 (True/False) 用于构建条件判断

## 主要类与结构体

该脚本不定义任何类或结构体,完全基于函数式编程风格实现。

## 公共 API 函数

### 主函数逻辑

```python
dirpath, = sys.argv[1:]
print(os.path.isdir(dirpath))
```

**功能**: 检查指定路径是否为目录并输出结果

**参数**:
- `sys.argv[1]`: 待检查的目录路径(字符串)

**返回值**: 无直接返回值,通过标准输出打印:
- `True`: 路径存在且是目录
- `False`: 路径不存在或不是目录

**调用示例**:
```bash
# 在构建脚本中调用
python gn/checkdir.py third_party/externals/freetype
# 输出: True 或 False

# 在 GN 文件中使用
have_freetype = exec_script("gn/checkdir.py",
                            ["third_party/externals/freetype"],
                            "value")
```

### 参数解包细节

```python
dirpath, = sys.argv[1:]
```

**技术要点**:
- 使用解包赋值确保只接受一个参数
- 尾部逗号表示期望单元素序列
- 如果参数数量不匹配会抛出 `ValueError`

**等价写法**:
```python
# 原写法的明确形式
assert len(sys.argv) == 2
dirpath = sys.argv[1]
```

## 内部实现细节

### 核心实现分析

**os.path.isdir() 行为**:
- 返回 `True` 当且仅当路径存在且是目录
- 符号链接会被跟随(指向目录的链接返回 `True`)
- 不会抛出异常,不存在的路径返回 `False`
- 无权限访问时返回 `False`

### Python 2/3 兼容性

```python
from __future__ import print_function
```

**用途**: 确保脚本同时兼容 Python 2 和 Python 3
- Python 2 中 `print` 是语句: `print "text"`
- Python 3 中 `print` 是函数: `print("text")`
- 导入 `print_function` 使 Python 2 也使用函数式语法

### 输出格式

```python
print(os.path.isdir(dirpath))
```

输出为 Python 布尔值的字符串表示:
- Python 输出: `True` 或 `False` (首字母大写)
- Shell 可以解析这些字符串作为命令结果
- GN 使用 `exec_script(..., "value")` 将其解析为布尔值

## 依赖关系

### Python 标准库依赖

```python
import os      # 提供 os.path.isdir()
import sys     # 提供 sys.argv 访问命令行参数
```

**无外部依赖**: 脚本仅依赖 Python 标准库,确保最大兼容性。

### 构建系统集成

**GN 调用方式**:
```gn
# 典型 GN 使用模式
declare_args() {
  skia_use_system_freetype = exec_script("gn/checkdir.py",
                                         ["third_party/freetype"],
                                         "value")
}
```

**数据流**:
```
GN 配置文件
    ↓
exec_script() 调用
    ↓
checkdir.py 执行
    ↓
True/False 输出
    ↓
GN 变量赋值
    ↓
条件编译决策
```

## 设计模式与设计决策

### 单一职责原则
脚本仅负责一个功能:目录存在性检查。这种设计使其:
- 易于理解和维护
- 可在多种场景下复用
- 行为可预测且易于测试

### 零配置设计
- 无需配置文件
- 无需环境变量
- 命令行参数即全部输入
- 标准输出即全部输出

### 最小依赖原则
仅使用 Python 标准库,避免了:
- 第三方包安装问题
- 版本兼容性问题
- 构建环境复杂性

### 明确的错误处理策略

**隐式错误处理**:
```python
dirpath, = sys.argv[1:]  # 参数数量错误会自动抛出 ValueError
os.path.isdir(dirpath)   # 路径问题返回 False,不抛出异常
```

**设计理由**:
- 参数错误应该立即失败(构建脚本错误)
- 目录不存在是预期情况(返回 False 供调用者处理)

### 脚本作为可执行工具

```python
#!/usr/bin/env python
```

**Shebang 行作用**:
- 允许脚本作为独立可执行文件运行
- 自动查找系统 Python 解释器
- 支持 `./checkdir.py <path>` 直接调用

## 性能考量

### 执行效率

**极简设计的优势**:
- 脚本启动和执行时间 < 50ms (典型场景)
- 仅一次系统调用(stat/fstat)
- 无文件 I/O 操作
- 无网络访问

**文件系统缓存**:
- `os.path.isdir()` 调用 stat 系统调用
- 操作系统会缓存 inode 信息
- 重复检查同一路径几乎无开销

### 构建系统影响

**GN 配置阶段调用**:
- 仅在 `gn gen` 时执行
- 不在实际编译过程中运行
- 结果被 GN 缓存,无需重复执行

**并行构建友好**:
- 无副作用(纯查询操作)
- 无全局状态修改
- 可安全并行调用

### 内存占用

**最小内存足迹**:
- Python 解释器基线内存(约 5-10 MB)
- 脚本本身代码极小(< 1 KB)
- 无大型数据结构
- 立即退出,无内存泄漏风险

## 相关文件

### 同类工具脚本

- **`gn/call.py`**: 通用命令执行包装器,用于在 GN 中调用其他工具
- **`gn/highest_version_dir.py`**: 查找最高版本的目录,类似的路径查询工具

### 典型调用场景

**检测第三方库**:
```gn
# 检查 Vulkan SDK 是否存在
has_vulkan = exec_script("gn/checkdir.py", ["third_party/vulkan"], "value")
if (has_vulkan) {
  defines += [ "SK_VULKAN_AVAILABLE" ]
}
```

**检测可选工具**:
```gn
# 检查测试资源目录
has_test_resources = exec_script("gn/checkdir.py", ["resources/"], "value")
if (has_test_resources) {
  testonly = true
}
```

**平台特定路径**:
```gn
# 检查 Android SDK 位置
has_android_sdk = exec_script("gn/checkdir.py",
                              [android_sdk_root],
                              "value")
```

### GN 集成文件

- **`BUILD.gn`**: 主构建文件,可能调用此脚本进行条件配置
- **`gn/BUILDCONFIG.gn`**: 全局构建配置
- **`gn/*.gni`**: GN 模板文件,可能使用目录检查

### 替代实现

在某些构建系统中的等价功能:
- **CMake**: `if(IS_DIRECTORY "${path}")`
- **Make**: `[ -d path ] && echo true || echo false`
- **Bazel**: `glob()` 和 `select()` 组合

该脚本虽然简单,但展示了 Unix 哲学"做好一件事"的设计理念,在复杂的构建系统中提供了可靠的基础功能。其简洁性和可靠性使其成为构建工具链中不可或缺的组件。
