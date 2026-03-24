# create.py

> 源文件: infra/bots/assets/clang_linux/create.py

## 概述

`create.py` 是用于为 AMD64 Linux 系统创建 Clang 编译器工具链资产的脚本。该脚本使用 Docker 容器化构建环境来编译最新版本的 Clang，并将编译产物提取到本地目录供 CIPD 打包和分发。

## 架构位置

```
infra/bots/assets/clang_linux/
├── create.py                     # 本文件：资产创建脚本
├── Dockerfile                    # Docker 构建配置
└── README.md                     # 资产说明
```

该资产为 Skia 在标准 AMD64 Linux 发行版上的构建提供 Clang 编译器支持。

## 主要类与结构体

该脚本采用函数式编程风格，无类定义。

### 核心函数

- **`create_asset(target_dir)`**: 执行 Docker 构建和文件提取
- **`main()`**: 脚本入口点

## 公共 API 函数

### create_asset(target_dir)

```python
def create_asset(target_dir):
    """使用 Docker 构建 Clang 工具链"""
```

**功能**：
1. **构建 Docker 镜像**：执行 `docker build` 编译 Clang
2. **创建输出目录**：确保 `target_dir` 存在
3. **提取编译产物**：从容器复制文件到主机
4. **修复权限**：使文件对所有用户可写

**参数**：
- `target_dir` (str): 编译产物的输出目录

**实现细节**：

```python
# 构建镜像（耗时约 30-60 分钟）
args = ['docker', 'build', '-t', 'clang_linux_asset',
        './infra/bots/assets/clang_linux']
subprocess.run(args, check=True, encoding='utf8')

# 提取产物
print('Copying clang from Docker container into CIPD folder')
os.makedirs(target_dir, exist_ok=True)
args = ['docker', 'run', '--mount', 'type=bind,source=%s,target=/OUT' % target_dir,
        'clang_linux_asset', '/bin/sh', '-c',
        'cp -R /tmp/clang_output/* /OUT && chmod -R a+w /OUT']
subprocess.run(args, check=True, encoding='utf8')
```

**关键设计**：
- 使用绑定挂载（bind mount）将主机目录挂载到容器
- 在容器内执行文件复制，避免 `docker cp` 的限制
- 修改权限解决 Docker 文件所有权问题

### main()

```python
def main():
    """主函数：解析参数并创建资产"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--target_dir', '-t', required=True)
    args = parser.parse_args()
    create_asset(args.target_dir)
```

## 内部实现细节

### Docker 构建流程

Dockerfile 中的典型构建步骤：
1. 基于 Ubuntu/Debian 基础镜像
2. 安装构建依赖（cmake, ninja, gcc, g++）
3. 下载 LLVM/Clang 源代码
4. 配置 CMake（启用优化和必要组件）
5. 编译 Clang（并行构建）
6. 安装到 `/tmp/clang_output`

### 权限问题处理

Docker 容器内的文件权限问题：
- 容器中的进程通常以 root 运行
- 创建的文件归属 `root:root`
- 主机上的普通用户无法修改

解决方案：
```bash
chmod -R a+w /OUT
```
赋予所有用户写权限，确保后续操作（删除、打包、上传）不需要 sudo。

### 构建产物结构

```
<target_dir>/
├── bin/
│   ├── clang                     # C 编译器
│   ├── clang++                   # C++ 编译器
│   ├── lld                       # LLVM 链接器
│   ├── clang-format              # 代码格式化
│   └── clang-tidy                # 静态分析
├── lib/
│   ├── libc++.so.1               # LLVM C++ 标准库
│   ├── libc++abi.so.1            # C++ ABI
│   └── clang/18.0.0/             # 编译器资源
│       └── include/              # 内置头文件
└── include/
    └── c++/v1/                   # libc++ 头文件
```

## 依赖关系

### 系统依赖

1. **Docker**（必需）
   - 版本：19.03+
   - 用于容器化构建
   - 需要 Docker daemon 运行

2. **网络连接**
   - 下载 Docker 基础镜像
   - 下载 LLVM 源代码（~200 MB）

### Python 依赖

- `argparse`、`os`、`subprocess`（标准库）

### Docker 镜像依赖

在 Dockerfile 中定义，通常包括：
- 基础镜像：`ubuntu:22.04` 或类似
- 构建工具：cmake, ninja-build, gcc, g++
- 构建依赖：libxml2-dev, zlib1g-dev

## 设计模式与设计决策

### 容器化构建优势

1. **环境隔离**：不污染主机系统
2. **可重复性**：确保构建环境一致
3. **清洁构建**：每次从干净状态开始
4. **跨平台**：可在任何支持 Docker 的系统上构建

### 两阶段流程

**阶段 1：构建（在容器内）**
- 时间：30-60 分钟
- 空间：~10 GB（容器内）

**阶段 2：提取（到主机）**
- 时间：<1 分钟
- 空间：~500 MB（主机）

分离的优势：
- 构建失败不会产生不完整的输出
- 可以独立调试每个阶段
- 容器内的中间文件自动清理

### 与 clang_win 的对比

| 特性 | clang_linux | clang_win |
|------|------------|-----------|
| 构建方式 | Docker 编译 | 下载预编译包 |
| 执行时间 | 30-60 分钟 | 2-5 分钟 |
| 定制能力 | 高 | 无 |
| 版本控制 | Dockerfile | Chromium URL |
| 跨平台创建 | 任何平台 | 任何平台 |

Linux 选择编译的原因：
- Linux 构建环境更简单
- 可以定制编译选项
- 不依赖外部预编译包的可用性

## 性能考量

### 构建时间

- **首次构建**：30-60 分钟
  - 下载源代码：5 分钟
  - 编译 LLVM/Clang：25-50 分钟
  - 安装：1-2 分钟

- **利用缓存**：10-20 分钟（Docker 层缓存）

### 资源消耗

- **CPU**：利用所有可用核心（通过 `cmake --build . -j$(nproc)`）
- **内存**：建议 8 GB+（并行编译）
- **磁盘**：
  - Docker 镜像：~5 GB
  - 编译产物：~500 MB
  - 临时文件：~10 GB

### 优化策略

1. **多核并行编译**：显著缩短构建时间
2. **Docker 构建缓存**：重用未更改的层
3. **SSD 存储**：提升 I/O 性能
4. **增加内存**：减少交换空间使用

## 相关文件

### 同目录文件

- **`Dockerfile`**: 定义 Clang 的编译步骤和依赖
- **`README.md`**: 资产版本和使用说明

### 相似资产

- **`clang_ubuntu_noble/create.py`**: Ubuntu Noble 专用版本
- **`clang_win/create.py`**: Windows 版本（下载方式）
- **`clang_mac_intel/create.py`**: macOS Intel 版本
- **`clang_mac_arm/create.py`**: macOS ARM 版本

### 构建系统

- **`gn/BUILD.gn`**: Skia GN 构建配置
- **`gn/toolchain/linux_toolchain.gni`**: Linux 工具链定义
- **`infra/bots/gen_tasks_logic/gen_tasks_logic.go`**: CI 任务生成

### LLVM 相关

- **LLVM 官方仓库**：`https://github.com/llvm/llvm-project`
- **Clang 文档**：`https://clang.llvm.org/docs/`
