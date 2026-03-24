# create.py

> 源文件: infra/bots/assets/cmake_linux/create.py

## 概述

`create.py` 是用于创建 Linux 平台 CMake 构建工具资产的脚本。该脚本从 CMake 官方 GitHub Releases 下载预编译的 Linux 二进制包，并提取必要的 `bin` 和 `share` 目录。

## 架构位置

```
infra/bots/assets/cmake_linux/
├── create.py                     # 本文件：下载 CMake
└── README.md                     # 资产说明
```

该资产为 Skia 的构建系统提供 CMake 工具，用于构建某些第三方依赖（如 ANGLE、Dawn 等）。

## 主要类与结构体

函数式编程风格，无类定义。

## 公共 API 函数

### create_asset(target_dir)

```python
def create_asset(target_dir):
    """从 CMake 官方下载并提取必要文件"""
    with utils.tmp_dir():
        subprocess.check_call(['wget', URL, '--output-document=cmake.tar.gz'])
        subprocess.check_call(['tar', '--extract', '--gunzip', '--file', 'cmake.tar.gz'])
        cmake_dir = 'cmake-%s-linux-x86_64' % VERSION
        for d in ['bin', 'share']:
            subprocess.check_call(['mv', os.path.join(cmake_dir, d), target_dir])
```

**功能**：
1. 在临时目录中下载 CMake tarball
2. 解压归档文件
3. 将 `bin` 和 `share` 目录移动到目标位置
4. 临时目录自动清理（通过 `utils.tmp_dir` 上下文管理器）

**参数**：
- `target_dir` (str): 输出目录

**关键设计**：
- 只提取 `bin` 和 `share` 目录，忽略文档等不必要文件
- 使用临时目录避免污染工作目录

### main()

```python
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--target_dir', '-t', required=True)
    args = parser.parse_args()
    create_asset(args.target_dir)
```

## 内部实现细节

### 版本配置

```python
VERSION = '3.31.8'
URL = ('https://github.com/Kitware/CMake/releases/download/v%s/'
       'cmake-%s-linux-x86_64.tar.gz') % (VERSION, VERSION)
```

- **CMake 版本**：3.31.8（截至脚本编写时的最新稳定版）
- **下载源**：CMake 官方 GitHub Releases
- **平台**：linux-x86_64（64 位 Intel/AMD Linux）
- **格式**：tar.gz 压缩归档

### 目录结构优化

CMake 官方发布包包含完整的目录结构：
```
cmake-3.31.8-linux-x86_64/
├── bin/          # 可执行文件（需要）
├── share/        # 模块和文档（需要模块）
├── doc/          # 文档（不需要）
└── man/          # 手册页（不需要）
```

脚本只提取必要的 `bin` 和 `share` 目录，减少资产大小：
- **bin/**：包含 `cmake`、`ctest`、`cpack` 等可执行文件
- **share/**：包含 CMake 模块（`.cmake` 文件）和模板

### 临时目录模式

使用 `utils.tmp_dir()` 上下文管理器：
```python
with utils.tmp_dir():
    # 下载和解压在临时目录中进行
    # 退出时自动清理
```

优势：
- 自动清理临时文件
- 避免污染当前工作目录
- 异常安全（即使发生错误也会清理）

## 依赖关系

### 系统依赖

1. **wget**：下载工具（Linux 通常预装）
2. **tar**：归档解压（Linux 标准工具）
3. **网络连接**：访问 GitHub Releases

### Python 依赖

- **`argparse`、`os`、`subprocess`、`sys`**（标准库）
- **`utils`**：Skia 工具模块
  - `tmp_dir`: 临时目录上下文管理器

### 外部文件依赖

- CMake 官方发布包（约 50 MB）

## 设计模式与设计决策

### 下载官方二进制

选择下载官方预编译包而非从源代码编译：
1. **构建复杂度**：CMake 的构建依赖（需要已有的 CMake 或 bootstrap）
2. **构建时间**：编译 CMake 需要 10-20 分钟
3. **官方保证**：Kitware 官方构建，质量有保证
4. **简化依赖**：不需要 C++ 编译器和开发库

### 选择性提取

只提取必要的 `bin` 和 `share` 目录：
- **减小资产大小**：从 ~80 MB 减少到 ~50 MB
- **加快下载和解压**：减少不必要的文件传输
- **CI 效率**：在 CI 环境中更快部署

### 版本固定

硬编码 CMake 版本号：
- **可重复性**：确保每次创建相同的资产
- **稳定性**：避免意外的版本升级破坏构建
- **更新控制**：手动测试新版本后再更新

### 临时目录使用

在临时目录中进行下载和解压：
- **清洁**：不留下中间文件
- **安全**：自动清理防止磁盘填满
- **隔离**：避免与其他操作冲突

## 性能考量

### 下载时间

- **文件大小**：约 50 MB
- **网络速度影响**：
  - 100 Mbps：4-5 秒
  - 10 Mbps：40-60 秒

### 解压时间

- **tar.gz 解压**：2-5 秒
- **文件数量**：约 1000+ 个文件

### 目录移动

- **操作**：`mv` 命令（快速，仅更新元数据）
- **时间**：< 1 秒

### 总执行时间

- **最佳情况**：10-15 秒（快速网络）
- **典型情况**：30-60 秒
- **最差情况**：2-3 分钟（慢速网络）

### 磁盘空间

- 下载的 tarball：~50 MB
- 解压后完整目录：~80 MB
- 提取后的资产：~50 MB（只包含 bin 和 share）
- 临时空间峰值：~130 MB
- 清理后：~50 MB

## 相关文件

### 同目录文件

- **`README.md`**: CMake 版本和使用说明

### 相似资产

- **`cmake_win/create.py`**: Windows 版本的 CMake 资产
- **`cmake_mac/create.py`**: macOS 版本的 CMake 资产

### 工具模块

- **`infra/bots/utils.py`**: Skia 工具模块
  - `tmp_dir`: 临时目录上下文管理器

### 使用位置

- **Dawn 构建**：`third_party/externals/dawn/` 使用 CMake 构建
- **ANGLE 构建**：部分 ANGLE 组件使用 CMake
- **构建脚本**：`infra/bots/recipes/` 中的 recipe 使用该资产

### CMake 官方

- **官方网站**：`https://cmake.org/`
- **GitHub Releases**：`https://github.com/Kitware/CMake/releases`
- **文档**：`https://cmake.org/documentation/`

### 构建系统

- **`infra/bots/gen_tasks_logic/gen_tasks_logic.go`**: 定义需要 CMake 的任务
- **`DEPS`**: 可能包含 CMake 版本信息
