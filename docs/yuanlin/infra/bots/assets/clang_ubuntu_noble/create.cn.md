# create.py

> 源文件: infra/bots/assets/clang_ubuntu_noble/create.py

## 概述

`create.py` 是用于为 Ubuntu Noble（24.04 LTS）创建 Clang 编译器工具链资产的脚本。该脚本使用 Docker 容器化构建环境来编译 Clang，并将编译产物提取到目标目录，以便上传到 CIPD 供 Skia 的持续集成系统使用。

## 架构位置

该脚本位于 Skia 基础设施的 Clang 工具链资产管理目录：

```
infra/bots/assets/clang_ubuntu_noble/
├── create.py                     # 本文件：资产创建脚本
├── Dockerfile                    # Docker 构建配置（编译 Clang）
└── README.md                     # 资产说明文档
```

该资产为 Skia 在 Ubuntu Noble 系统上的构建提供 Clang 编译器，支持最新的 C++20/23 标准和 LLVM 优化。

## 主要类与结构体

该脚本采用函数式编程风格，不包含类定义。核心函数：

### create_asset(target_dir)

负责执行 Docker 镜像构建和文件提取的主要逻辑。

### main()

脚本入口点，处理命令行参数并调用 `create_asset()`。

## 公共 API 函数

### create_asset(target_dir)

```python
def create_asset(target_dir):
    """使用 Docker 构建 Clang 并提取到目标目录"""
```

**功能**：
1. 使用 Dockerfile 构建包含编译好的 Clang 的 Docker 镜像
2. 从镜像中提取编译产物到本地目录
3. 调整文件权限以供 CIPD 打包

**参数**：
- `target_dir` (str): 资产输出目录的绝对路径

**执行步骤**：

#### 步骤 1: 构建 Docker 镜像

```python
args = ['docker', 'build', '-t', 'clang_ubuntu_noble_asset',
        './infra/bots/assets/clang_ubuntu_noble']
subprocess.run(args, check=True, encoding='utf8')
```

- 使用 `docker build` 命令构建镜像
- 镜像标签：`clang_ubuntu_noble_asset`
- 构建上下文：`./infra/bots/assets/clang_ubuntu_noble`
- Dockerfile 中定义的构建过程包括：
  - 下载 LLVM/Clang 源代码
  - 配置 CMake 构建选项
  - 编译 Clang 及相关工具（lld, clang-tidy 等）
  - 将输出安装到 `/tmp/clang_output`

#### 步骤 2: 提取编译产物

```python
os.makedirs(target_dir, exist_ok=True)
args = ['docker', 'run', '--mount', 'type=bind,source=%s,target=/OUT' % target_dir,
        'clang_ubuntu_noble_asset', '/bin/sh', '-c',
        'cp -R /tmp/clang_output/* /OUT && chmod -R a+w /OUT']
subprocess.run(args, check=True, encoding='utf8')
```

- 创建目标目录（如果不存在）
- 运行 Docker 容器，挂载目标目录到 `/OUT`
- 复制 `/tmp/clang_output` 的内容到 `/OUT`
- 修改权限：`chmod -R a+w` 使所有用户可写
  - **必要性**：Docker 容器中的文件默认由 root 拥有，修改权限确保后续操作（删除、打包）不需要 sudo

### main()

```python
def main():
    """主函数：解析参数并创建资产"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--target_dir', '-t', required=True)
    args = parser.parse_args()
    create_asset(args.target_dir)
```

**功能**：标准的命令行脚本入口模式。

**参数**：
- `--target_dir` / `-t`（必需）：输出目录路径

## 内部实现细节

### Docker 容器化构建

使用 Docker 构建的优势：
1. **环境隔离**：不污染主机系统
2. **可重复性**：确保构建环境一致
3. **依赖管理**：所有构建依赖在 Dockerfile 中明确定义
4. **多平台支持**：可在任何支持 Docker 的系统上构建

### 文件权限处理

Docker 容器中的文件默认权限问题：
- 容器中的进程以 root 运行（默认）
- 创建的文件归 root 所有
- 主机上的普通用户无法修改这些文件

解决方案：
```bash
chmod -R a+w /OUT
```
给予所有用户写权限，避免后续的权限错误。

### 编译产物结构

提取的 Clang 工具链目录结构（典型）：
```
<target_dir>/
├── bin/                          # 可执行文件
│   ├── clang                     # C/C++ 编译器
│   ├── clang++                   # C++ 编译器（符号链接）
│   ├── lld                       # LLVM 链接器
│   ├── clang-format              # 代码格式化工具
│   └── clang-tidy                # 静态分析工具
├── lib/                          # 库文件
│   ├── libc++.so.1               # LLVM C++ 标准库
│   ├── libc++abi.so.1            # C++ ABI 库
│   └── clang/                    # Clang 资源文件
│       └── 18.0.0/
│           └── include/          # 编译器内置头文件
└── include/                      # 开发头文件
    ├── c++/                      # libc++ 头文件
    └── ...
```

## 依赖关系

### 系统依赖

1. **Docker**（必需）
   - 版本要求：Docker 19.03+
   - 功能：容器化构建环境
   - 检查：`docker --version`

2. **网络连接**
   - 用于：下载 Docker 基础镜像和 LLVM 源代码
   - 带宽需求：~500 MB

### Python 依赖

- **`argparse`**: 命令行参数解析（标准库）
- **`os`**: 文件系统操作（标准库）
- **`subprocess`**: 外部命令执行（标准库）

### 外部文件依赖

- **`Dockerfile`**: 同目录下的 Docker 构建脚本
  - 定义基础镜像（通常为 `ubuntu:noble`）
  - 指定 LLVM 版本和编译选项
  - 包含完整的构建命令序列

## 设计模式与设计决策

### 容器化构建模式

将编译过程封装在 Docker 容器中的优势：
- **清洁构建**：每次从干净的环境开始
- **依赖明确**：所有依赖在 Dockerfile 中声明
- **可调试性**：可以手动运行容器排查问题
- **构建缓存**：Docker 层缓存加速重复构建

### 两阶段执行流程

1. **构建阶段**：在容器内编译（耗时 30-60 分钟）
2. **提取阶段**：将产物复制到主机（耗时 < 1 分钟）

这种分离使得：
- 构建失败不会留下不完整的输出
- 可以独立调试每个阶段

### 权限修复策略

在容器内修改权限而非主机上，避免：
- 需要 sudo 权限
- 复杂的权限管理逻辑
- 跨平台权限差异

## 性能考量

### 构建时间

- **首次构建**：30-60 分钟
  - LLVM 源代码下载：5-10 分钟
  - 编译 Clang：20-45 分钟（取决于 CPU 核心数）
  - 安装和打包：1-2 分钟

- **增量构建**：10-20 分钟（利用 Docker 层缓存）

### 资源消耗

- **磁盘空间**：
  - Docker 镜像：~5 GB
  - 编译产物：~500 MB
  - 临时文件：~10 GB

- **内存**：建议 8 GB+（并行编译）

- **CPU**：利用所有可用核心（CMake 默认行为）

### 优化建议

1. **使用 Docker 构建缓存**：不修改 Dockerfile 时可重用镜像
2. **增加内存**：减少交换空间使用
3. **SSD 存储**：显著提升编译速度

## 相关文件

### 同目录文件

- **`Dockerfile`**: Docker 构建脚本，定义 Clang 编译流程
- **`README.md`**: 资产使用说明和版本信息
- **`create_and_upload.sh`**: 上传到 CIPD 的脚本（如果存在）

### 相似资产脚本

- **`infra/bots/assets/clang_linux/create.py`**: AMD64 Linux 的 Clang 构建
- **`infra/bots/assets/clang_win/create.py`**: Windows 的 Clang 包下载
- **`infra/bots/assets/clang_mac_arm/create.py`**: macOS ARM 的 Clang 包

### 构建配置

- **`infra/bots/gen_tasks_logic/gen_tasks_logic.go`**: 引用该资产的构建任务定义
- **`infra/bots/tasks.json`**: 生成的任务配置文件

### Clang 使用位置

- **`gn/BUILD.gn`**: Skia 的 GN 构建文件，配置 Clang 编译器
- **`gn/toolchain/`**: 工具链定义文件
