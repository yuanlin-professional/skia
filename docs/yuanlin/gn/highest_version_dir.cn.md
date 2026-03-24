# highest_version_dir.py

> 源文件: gn/highest_version_dir.py

## 概述

`highest_version_dir.py` 是一个简洁而实用的 Python 工具,用于在指定目录中查找符合特定模式的最高版本子目录。该脚本在 Skia 构建系统中主要用于自动检测和选择最新版本的工具或依赖,如 SDK、编译器或第三方库,确保构建过程使用最新的可用版本。

该工具通过正则表达式匹配目录名,并按字典序排序后返回最高版本,为构建系统提供了版本选择的自动化能力,减少了手动配置的需求。

## 架构位置

`highest_version_dir.py` 在 Skia 构建工具链中的位置:

```
skia/
├── gn/                              # 构建工具目录
│   ├── highest_version_dir.py       # 本脚本 - 版本目录查找器
│   ├── checkdir.py                  # 目录存在性检查
│   └── ...
├── third_party/                     # 可能包含多版本依赖
│   └── externals/
│       └── sdks/                    # 如 Android SDK 多版本
│           ├── 28/
│           ├── 29/
│           └── 30/                  # 会被选中
└── BUILD.gn                         # 构建配置
```

典型应用场景:
- **SDK 版本选择**: 自动选择最新的 Android/iOS SDK
- **工具链检测**: 找到最高版本的编译器或构建工具
- **库版本管理**: 在多个版本的第三方库中选择最新版

## 主要类与结构体

该脚本使用函数式编程风格,不定义类或结构体。

## 公共 API 函数

### 主函数逻辑

```python
dirpath = sys.argv[1]
regex = re.compile(sys.argv[2])

print(sorted(filter(regex.match, os.listdir(dirpath)))[-1])
```

**参数**:
- `sys.argv[1]`: 要搜索的目录路径
- `sys.argv[2]`: 用于匹配子目录名的正则表达式模式

**返回值**: 通过标准输出打印匹配的最高版本目录名(不是完整路径)

**行为**:
1. 列出指定目录的所有内容
2. 使用正则表达式过滤目录名
3. 按字典序排序匹配结果
4. 返回排序后的最后一个(最高版本)

**调用示例**:

```bash
# 查找最高版本的 Android SDK build-tools
python gn/highest_version_dir.py \
    ~/Android/Sdk/build-tools \
    '^[0-9]+\.[0-9]+\.[0-9]+$'
# 输出: 30.0.3

# 查找最新的 NDK 版本
python gn/highest_version_dir.py \
    ~/Android/Sdk/ndk \
    '^[0-9]+\.'
# 输出: 23.1.7779620

# 查找 Xcode 版本
python gn/highest_version_dir.py \
    /Applications \
    '^Xcode_[0-9]+.*'
# 输出: Xcode_13.1.app
```

### GN 构建系统集成

```gn
# 在 BUILD.gn 或 .gni 文件中
declare_args() {
  android_sdk_build_tools_version = exec_script(
    "gn/highest_version_dir.py",
    [
      "$android_sdk_root/build-tools",
      "^[0-9]+\\.[0-9]+\\.[0-9]+$",
    ],
    "trim string"
  )
}

# 使用结果
android_build_tools = "$android_sdk_root/build-tools/$android_sdk_build_tools_version"
```

## 内部实现细节

### 正则表达式匹配

```python
regex = re.compile(sys.argv[2])
filter(regex.match, os.listdir(dirpath))
```

**regex.match() 行为**:
- 从字符串开头开始匹配
- 不需要匹配整个字符串(除非模式包含 `$`)
- 匹配成功返回 Match 对象(真值),失败返回 None(假值)

**示例模式**:
```python
# 匹配纯数字目录(如 SDK API level)
r'^\d+$'

# 匹配语义化版本
r'^\d+\.\d+\.\d+$'

# 匹配带前缀的版本
r'^v\d+\.\d+'

# 匹配 Xcode 版本
r'^Xcode_\d+'
```

### 目录列表获取

```python
os.listdir(dirpath)
```

**返回内容**:
- 目录和文件的名称(不是完整路径)
- 顺序不确定(取决于文件系统)
- 包含所有可见项(不包含 `.` 和 `..`)
- 包含文件,不仅是目录

**潜在问题**: 脚本不验证匹配项是否为目录,如果有同名文件会被包含。

### 排序和选择策略

```python
sorted(filter(...))[-1]
```

**排序规则**:
- 使用字典序(lexicographic order)
- 对于纯数字字符串: "2" > "10" (字符串比较)
- 对于版本号: "1.10" > "1.9" (正确的版本序)

**版本排序示例**:
```python
# 字典序排序结果
sorted(['1', '2', '10', '20'])
# ['1', '10', '2', '20']  # 不是预期的数字序

sorted(['1.0', '1.10', '1.2', '2.0'])
# ['1.0', '1.10', '1.2', '2.0']  # 正确的版本序
```

**选择最后一个**:
```python
[-1]  # 获取列表的最后一个元素
```
假设排序后最后一个是最高版本(适用于大多数版本命名约定)。

### Python 2/3 兼容性

```python
from __future__ import print_function
```

确保在 Python 2 中也使用函数式 `print()`,保持跨版本兼容。

## 依赖关系

### Python 标准库

```python
import os      # os.listdir() 目录列表
import re      # 正则表达式编译和匹配
import sys     # 命令行参数访问
```

**无外部依赖**: 完全基于标准库,确保最大兼容性。

### 与构建系统的数据流

```
文件系统目录结构
    ↓
os.listdir() 列举
    ↓
正则表达式过滤
    ↓
字典序排序
    ↓
选择最高版本
    ↓
GN 变量赋值
    ↓
构建配置决策
```

## 设计模式与设计决策

### 函数式编程风格

```python
sorted(filter(regex.match, os.listdir(dirpath)))[-1]
```

**优势**:
- 单行表达完整逻辑
- 无中间变量
- 易于理解数据流
- 性能优化(Python 内部优化 filter 和 sorted)

### 假设和限制

**隐式假设**:
1. 目录名的字典序与版本顺序一致
2. 存在至少一个匹配的目录
3. 调用者提供正确的正则表达式

**未处理的错误情况**:
```python
# 没有匹配时会抛出 IndexError
sorted([])[-1]  # IndexError: list index out of range

# 目录不存在会抛出 FileNotFoundError
os.listdir('/nonexistent')

# 无效正则表达式会抛出 re.error
re.compile('[invalid')
```

### 简单优于复杂

**为什么不添加更多功能?**
- 不验证是否为目录(调用者责任)
- 不处理版本号特殊排序(依赖命名约定)
- 不提供多个结果或排名

保持简单使脚本:
- 易于理解
- 易于测试
- 行为可预测

### Unix 工具理念

**标准输入/输出**:
- 输入通过命令行参数
- 输出通过 stdout
- 错误通过异常(Python traceback 到 stderr)
- 可与其他工具组合(管道)

## 性能考量

### 执行效率

**操作复杂度**:
- `os.listdir()`: O(n),n 为目录项数
- `filter()`: O(n × m),m 为正则匹配复杂度
- `sorted()`: O(n log n)
- 总体: O(n log n)

**实际性能**:
- 典型目录(10-100 项): < 10ms
- 大型目录(1000+ 项): < 100ms
- 瓶颈通常是文件系统操作,不是算法

### 内存占用

**数据结构大小**:
```python
os.listdir(dirpath)  # 列表,所有目录项名称
filter(...)          # 迭代器(Python 3)或列表(Python 2)
sorted(...)          # 新列表,包含匹配项
```

**内存估算**:
- 100 个目录项,平均名称 20 字符
- 原始列表: ~2 KB
- 过滤后列表: < 2 KB
- 总计: < 10 KB(可忽略)

### 缓存和重复调用

**无缓存机制**:
- 每次调用都重新扫描文件系统
- 如果在构建中多次调用相同参数,会重复工作

**优化建议**(未实现):
```gn
# 在 GN 中缓存结果
_cached_version = exec_script(...)  # 仅调用一次
```

## 相关文件

### 同类工具

**Skia 构建工具**:
- **`checkdir.py`**: 检查目录是否存在
- **`call.py`**: 通用命令执行包装器
- **`find_headers.py`**: 查找头文件

### 典型使用场景

**Android SDK 版本检测**:
```gn
android_sdk_build_tools_version = exec_script(
  "gn/highest_version_dir.py",
  [
    android_sdk_root + "/build-tools",
    "^[0-9]+\\.[0-9]+\\.[0-9]+$",
  ],
  "trim string"
)
```

**NDK 版本选择**:
```gn
android_ndk_version = exec_script(
  "gn/highest_version_dir.py",
  [
    android_ndk_root,
    "^[0-9]+\\.[0-9]",
  ],
  "trim string"
)
```

**Platform Tools 检测**:
```gn
platform_tools_version = exec_script(
  "gn/highest_version_dir.py",
  [ platform_tools_path, "^[0-9]+" ],
  "trim string"
)
```

### 替代实现

**使用 shell 脚本**:
```bash
#!/bin/bash
ls "$1" | grep -E "$2" | sort | tail -n 1
```

**使用 Python 语义化版本库**:
```python
from packaging import version
versions = [d for d in os.listdir(path) if regex.match(d)]
print(max(versions, key=version.parse))
```

**GN 内置方案**(不存在):
```gn
# GN 没有内置的文件系统查询功能
# 必须使用 exec_script 调用外部工具
```

### 改进建议

**更健壮的版本排序**:
```python
import re
import os
import sys

def parse_version(s):
    # 提取数字部分进行数值排序
    return tuple(int(x) for x in re.findall(r'\d+', s))

dirpath = sys.argv[1]
regex = re.compile(sys.argv[2])
matches = [d for d in os.listdir(dirpath) if regex.match(d)]
print(max(matches, key=parse_version))
```

**添加错误处理**:
```python
try:
    result = sorted(filter(regex.match, os.listdir(dirpath)))[-1]
    print(result)
except IndexError:
    print("No matching directories found", file=sys.stderr)
    sys.exit(1)
except FileNotFoundError:
    print(f"Directory not found: {dirpath}", file=sys.stderr)
    sys.exit(1)
```

该脚本虽然简单,但在构建系统中提供了重要的版本自动检测功能,通过智能的目录选择减少了手动配置的负担,提高了构建的灵活性和可维护性。
