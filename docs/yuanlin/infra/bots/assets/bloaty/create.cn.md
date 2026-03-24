# Bloaty 资产创建脚本

> 源文件: infra/bots/assets/bloaty/create.py

## 概述

这是一个用于从源码构建 Bloaty 二进制文件的 Python 脚本。Bloaty（全称 Bloaty McBloatface）是 Google 开发的一个二进制文件大小分析工具，可以深入分析 ELF、Mach-O 等格式的二进制文件，帮助开发者理解程序大小的组成。该脚本负责下载 Bloaty v1.0 源码、编译并打包成 Linux 可执行文件资产。

## 架构位置

该脚本位于 Skia 基础设施的资产管理体系中，路径为 `infra/bots/assets/bloaty/`。它是 Skia CI/CD 系统的一部分，用于准备代码大小分析工具。Bloaty 资产主要用于：

- 分析编译产物的大小组成
- 监控代码库的膨胀趋势
- 优化二进制文件大小
- 生成构建统计报告

该脚本与 `infra/bots/buildstats/` 目录下的构建统计脚本协同工作，为 Skia 的性能监控系统提供支持。

## 主要类与结构体

脚本采用简洁的函数式编程风格，不包含自定义类或复杂数据结构。主要依赖的模块：

- **argparse**: 命令行参数解析
- **os**: 操作系统接口和路径操作
- **shutil**: 高级文件操作
- **subprocess**: 子进程管理和外部命令执行
- **sys**: 系统参数和路径操作
- **utils**: Skia 基础设施的通用工具模块（从 `infra/bots/` 导入）

### 模块级常量

```python
REPO = 'https://github.com/google/bloaty'  # Bloaty 的 GitHub 仓库地址
TAG = 'v1.0'  # 要构建的版本标签
```

## 公共 API 函数

### `create_asset(target_dir)`

核心资产创建函数，负责完整的构建流程。

**参数**:
- `target_dir` (str): 存放最终构建产物的目标目录路径

**执行流程**:
1. 创建临时目录用于构建
2. 从 GitHub 克隆 Bloaty 仓库的指定版本
3. 使用 CMake 配置构建环境
4. 使用 make 并行编译
5. 将编译好的二进制文件移动到目标目录
6. 自动清理临时目录

**实现细节**:
```python
with utils.tmp_dir():  # 使用上下文管理器确保临时目录自动清理
    subprocess.check_call(['git', 'clone', '--depth', '1', '-b', TAG,
                           '--single-branch', REPO])
    os.chdir('bloaty')
    subprocess.check_call(['cmake', '.'])
    subprocess.check_call(['make', '-j'])
    shutil.move('./bloaty', target_dir)
```

该函数使用浅克隆（`--depth 1`）和单分支（`--single-branch`）优化，减少下载量和时间。

### `main()`

脚本入口点，负责参数解析和函数调度。

**命令行参数**:
- `--target_dir, -t`: 必需参数，指定资产输出目录的绝对或相对路径

## 内部实现细节

### Git 克隆优化

脚本使用高度优化的 Git 克隆命令：

```bash
git clone --depth 1 -b v1.0 --single-branch https://github.com/google/bloaty
```

**优化点**:
- `--depth 1`: 浅克隆，只获取最新的提交历史，大幅减少下载量
- `-b TAG`: 直接检出指定标签，避免额外的 checkout 操作
- `--single-branch`: 只获取目标分支，不下载其他分支的引用

这些优化在网络受限或磁盘空间紧张的 CI 环境中特别有价值。

### CMake 构建系统

Bloaty 使用 CMake 作为构建系统。脚本执行：

1. **配置阶段**: `cmake .` 在当前目录生成 Makefile
2. **编译阶段**: `make -j` 使用所有可用 CPU 核心并行编译

`-j` 参数（无数字）让 make 自动检测并使用所有可用的 CPU 核心，最大化编译速度。

### 临时目录管理

脚本使用 `utils.tmp_dir()` 上下文管理器：

**优点**:
- 自动创建和销毁临时目录
- 异常安全：即使构建失败也会清理
- 避免污染工作目录
- 隔离并发构建

### 文件移动策略

使用 `shutil.move()` 而非 `shutil.copy()` 的原因：
- 更高效：在同一文件系统内是重命名操作
- 自动清理：源文件被移走，无需额外删除
- 原子性：减少中间状态

## 依赖关系

### 构建时依赖

- **Git**: 版本控制工具，用于克隆仓库
- **CMake**: 跨平台构建系统生成器，版本需支持 Bloaty 要求
- **Make**: GNU Make 或兼容实现，用于执行构建
- **C++ 编译器**: GCC 或 Clang，用于编译 Bloaty 源码
- **标准 C++ 库**: Bloaty 使用 C++11 或更高标准

### Python 依赖

- **Python 标准库**: argparse, os, shutil, subprocess, sys
- **Skia utils 模块**: `infra/bots/utils.py` 提供的工具函数

### 运行时依赖

编译产生的 Bloaty 二进制文件可能动态链接到：
- libc/libc++
- libstdc++
- libm (数学库)
- libz (zlib 压缩库)

具体依赖取决于构建系统的配置。

## 设计模式与设计决策

### 上下文管理器模式

使用 `utils.tmp_dir()` 上下文管理器是一个重要的设计决策：

```python
with utils.tmp_dir():
    # 所有构建操作在临时目录中进行
    # 退出时自动清理
```

这种模式提供了：
- **资源管理**: 自动清理保证不泄漏磁盘空间
- **异常安全**: 即使发生错误也执行清理
- **代码简洁**: 无需显式的 try-finally 块

### 版本固定策略

脚本固定构建 v1.0 版本，而非追踪最新版本。这种策略的好处：

- **可重现性**: 相同的脚本总是产生相同的资产
- **稳定性**: 避免上游更新带来的意外破坏
- **测试可控**: 版本变更需要显式修改和测试

### 最小化输出

脚本只保留最终的二进制文件，不包含：
- 源代码
- 中间对象文件
- 构建系统生成文件
- 测试文件

这种设计保持资产包的轻量化，加快下载和部署速度。

### 原地构建

使用 `cmake .` 在源码目录内构建，而非创建单独的构建目录。这种选择的考量：
- **简单性**: 减少目录跳转和路径管理
- **临时性**: 整个目录都会被清理，无需担心污染
- **效率**: 减少文件复制

## 性能考量

### 编译时间

Bloaty 是一个 C++ 项目，编译时间取决于：
- **CPU 性能**: 使用 `make -j` 充分利用多核
- **I/O 性能**: SSD 比机械硬盘快得多
- **内存大小**: 并行编译需要足够内存

典型的现代机器上，编译时间约为 1-3 分钟。

### 网络下载

克隆仓库的时间取决于网络带宽。使用浅克隆大约节省 80% 的下载量。v1.0 版本的浅克隆大小约为 1-2 MB。

### 磁盘使用

- **构建时**: 约 50-100 MB（源码 + 构建产物）
- **最终资产**: 约 5-10 MB（单个二进制文件）

临时目录的自动清理确保不会积累垃圾文件。

### 优化技巧

1. **并行编译**: `make -j` 自动检测 CPU 核心数
2. **浅克隆**: 减少 Git 下载量
3. **单分支**: 避免下载不必要的分支
4. **原地构建**: 减少文件复制开销

## 相关文件

- **`infra/bots/assets/bloaty/VERSION`**: 资产版本标识文件
- **`infra/bots/assets/bloaty/download.py`**: 从资产服务下载的脚本
- **`infra/bots/assets/bloaty/upload.py`**: 上传资产到服务的脚本
- **`infra/bots/utils.py`**: 通用工具函数库，提供 `tmp_dir()` 等
- **`infra/bots/buildstats/`**: 使用 Bloaty 分析构建产物的脚本集合
- **`infra/bots/task_drivers/codesize/`**: 代码大小监控任务驱动

该脚本是 Skia 资产管理工作流的一部分，通常与上传脚本配合使用，将构建好的资产发布到 CIPD（Chrome Infrastructure Package Deployment）系统，供 CI 任务使用。
