# milestone

> 源文件
> - tools/milestone.py

## 概述

milestone 是一个命令行工具脚本,用于更新 Skia 的里程碑版本号。该脚本自动修改 `SkMilestone.h` 头文件,将其中定义的 `SK_MILESTONE` 宏更新为指定的版本号。这个工具简化了版本更新流程,确保版本号修改的一致性和正确性。

脚本提供了完整的使用说明,指导开发者完成从拉取代码、更新版本到提交的完整工作流程。

## 架构位置

milestone 脚本位于工具目录根级别,作为版本管理工具链的一部分:

```
skia/
├── tools/
│   ├── milestone.py           # 版本更新脚本
│   └── 其他工具
├── include/
│   └── core/
│       └── SkMilestone.h      # 被修改的目标文件
└── .git/                      # Git 仓库
```

该脚本在发布流程中的位置:
1. 准备新版本发布
2. **运行 milestone.py 更新版本号**
3. 提交并推送更改
4. 触发构建和发布流程

## 主要类与结构体

该脚本是一个简单的过程式脚本,不包含类定义。主要组成部分:

### 全局变量

**milestone_file**
- 值: `'include/core/SkMilestone.h'`
- 用途: 定义需要修改的目标文件路径

**usage**
- 类型: 多行字符串
- 用途: 提供完整的使用说明,包括 Git 工作流程

**text**
- 类型: 文件模板字符串
- 用途: 生成新的头文件内容,包含版权信息和宏定义

## 公共 API 函数

### 命令行接口

```bash
python tools/milestone.py MILESTONE_NUMBER
```

**参数**:
- `MILESTONE_NUMBER`: 正整数,表示新的里程碑版本号

**使用示例**:
```bash
# 更新到版本 100
python tools/milestone.py 100
```

**完整工作流程**:
```bash
git fetch
git checkout -b change_milestone origin/main
python tools/milestone.py 100
git add include/core/SkMilestone.h
git commit -m "Update Skia milestone."
git cl land
```

### 脚本执行流程

1. **参数验证**: 检查命令行参数是否为正整数
2. **切换目录**: 切换到仓库根目录
3. **生成内容**: 使用模板生成新的头文件内容
4. **写入文件**: 覆盖原有的 SkMilestone.h
5. **输出确认**: 将新文件内容输出到标准输出

## 内部实现细节

### 参数解析和验证

```python
try:
    milestone = int(sys.argv[1])
    assert milestone > 0
except (IndexError, ValueError, AssertionError):
    sys.stderr.write(usage % (sys.argv[0], milestone_file))
    exit(1)
```

**验证逻辑**:
- 捕获 `IndexError`: 没有提供参数
- 捕获 `ValueError`: 参数无法转换为整数
- 捕获 `AssertionError`: 数字不是正数

**错误处理**: 将使用说明输出到 stderr 并以状态码 1 退出

### 目录定位

```python
os.chdir(os.path.join(os.path.dirname(__file__), os.pardir))
```

**逻辑**:
1. `__file__`: 脚本的绝对路径
2. `os.path.dirname(__file__)`: 脚本所在目录 (tools/)
3. `os.pardir`: 父目录符号 (..)
4. 结果: 切换到仓库根目录

**必要性**: 确保相对路径 `include/core/SkMilestone.h` 正确解析

### 文件内容模板

```python
text = '''/*
 * Copyright 2016 Google Inc.
 *
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */
#ifndef SK_MILESTONE
#define SK_MILESTONE %d
#endif
'''
```

**模板特点**:
- 包含完整的版权声明
- 使用 `#ifndef` 头文件保护
- 通过 `%d` 格式化占位符插入版本号

### 文件写入和验证

```python
with open(milestone_file, 'w') as o:
    o.write(text % milestone)

with open(milestone_file, 'r') as f:
    sys.stdout.write(f.read())
```

**两步操作**:
1. 写入: 将格式化后的内容写入文件
2. 读取并输出: 读回文件内容到 stdout,用于人工确认

**设计考虑**: 输出到 stdout 让用户可以立即看到更改结果

## 依赖关系

### Python 标准库
- `os`: 文件路径操作和目录切换
- `sys`: 命令行参数和标准输入输出

### 外部依赖
- **Git**: 使用说明中包含 Git 命令
- **code review 工具**: `git cl land` 需要 depot_tools

### 被修改文件
- `include/core/SkMilestone.h`: 版本号定义文件

### 依赖工具
- Skia 构建系统会读取 `SK_MILESTONE` 宏
- 版本信息可能被用于库标识和日志记录

## 设计模式与设计决策

### 简单直接的设计

脚本采用最简单的实现方式:
- 不使用模板引擎
- 不使用 JSON/YAML 配置文件
- 直接字符串替换

**理由**:
- 任务简单,不需要复杂抽象
- 依赖最少,Python 标准库即可
- 易于理解和维护

### 完整的使用说明

在脚本中嵌入完整的工作流程说明:
- 降低使用门槛
- 确保正确的 Git 操作流程
- 减少文档分散

### 原子性操作

脚本设计为完全替换文件内容:
- 不进行部分修改
- 避免解析现有文件的复杂性
- 确保文件格式一致性

**权衡**: 如果其他人修改了文件格式(如添加注释),这些修改会丢失

### 立即反馈

将更新后的文件内容输出到 stdout:
- 用户可以立即验证更改
- 适合自动化流程的日志记录
- 帮助调试和确认

## 性能考量

### 脚本性能

该脚本性能影响可忽略:
- 操作单个小文件(< 1KB)
- I/O 操作最小化
- 无复杂计算

### 执行时间

预期执行时间 < 100ms:
- Python 启动: ~50ms
- 文件操作: ~10ms
- 字符串格式化: < 1ms

### 优化空间

无需优化,因为:
- 不在热路径上
- 手动触发,不频繁执行
- 性能已足够好

## 相关文件

### 被修改的文件
- `include/core/SkMilestone.h`: 里程碑版本号定义

**SkMilestone.h 内容示例**:
```cpp
/*
 * Copyright 2016 Google Inc.
 *
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */
#ifndef SK_MILESTONE
#define SK_MILESTONE 100
#endif
```

### 依赖此版本号的代码

版本号的使用者:
- 构建配置脚本
- 库版本标识
- 兼容性检查代码
- 日志和诊断信息

### 发布流程相关

- `RELEASE_NOTES.md`: 发布说明
- CI/CD 配置: 可能触发版本相关的构建
- 打标签脚本: 可能读取版本号

### 使用示例

**更新到版本 101**:
```bash
$ python tools/milestone.py 101
/*
 * Copyright 2016 Google Inc.
 *
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */
#ifndef SK_MILESTONE
#define SK_MILESTONE 101
#endif
```

**错误示例 - 无参数**:
```bash
$ python tools/milestone.py

usage:
  git fetch
  git checkout -b change_milestone origin/main
  python tools/milestone.py MILESTONE_NUMBER
  git add include/core/SkMilestone.h
  git commit -m "Update Skia milestone."
  git cl land
```

**错误示例 - 无效参数**:
```bash
$ python tools/milestone.py -5

usage:
  git fetch
  git checkout -b change_milestone origin/main
  python tools/milestone.py MILESTONE_NUMBER
  git add include/core/SkMilestone.h
  git commit -m "Update Skia milestone."
  git cl land
```

milestone 脚本虽然简单,但在 Skia 的版本管理流程中扮演重要角色。它的设计体现了"做一件事并做好"的 Unix 哲学,专注于更新版本号这一个任务,并提供清晰的使用指导。
