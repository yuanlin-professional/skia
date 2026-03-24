# create.py - Linux ccache 编译缓存工具资源创建脚本

> 源文件: [infra/bots/assets/ccache_linux/create.py](https://github.com/aspect-build/aspect-cli/blob/main/infra/bots/assets/ccache_linux/create.py)

## 概述

`create.py` 用于创建 Linux 平台上 ccache 编译缓存工具的 CIPD 资源包。ccache 是一个编译器缓存工具，能够缓存 C/C++ 编译结果，在重复编译时显著提升构建速度。该脚本从 GitHub 下载 ccache v3.7.7 的源代码压缩包，然后从源码编译安装到目标目录。编译后的二进制文件被打包上传到 CIPD，供 Skia 的 CI/CD 构建机器使用。

## 架构位置

该脚本属于 Skia 基础设施中的构建工具管理子系统。

```
infra/bots/assets/
├── ccache_linux/
│   └── create.py          # 本文件 - 编译 ccache 并创建资源
└── ...

构建加速链:
ccache (编译缓存) -> GCC/Clang (编译器) -> Skia C++ 源代码
```

ccache 在 Skia 的 CI 构建中用于缓存编译中间结果，特别是在增量构建和重复构建场景中能显著减少编译时间。

## 主要类与结构体

本脚本无类定义。关键常量：

| 常量 | 值 | 说明 |
|------|-----|------|
| `URL` | `https://github.com/.../ccache-3.7.7.tar.gz` | 源代码下载地址 |
| `VERSION` | `ccache-3.7.7` | 版本标识，也是解压后的目录名 |

## 公共 API 函数

### `create_asset(target_dir)`

从源码编译 ccache 并安装到目标目录。

**参数**：
- `target_dir` (str): 资源输出目录路径（会被转换为绝对路径）

**行为**：
1. 将 `target_dir` 转换为绝对路径（`configure --prefix` 要求）
2. 在临时目录中下载源码压缩包
3. 解压并进入源码目录
4. 运行 `./configure --disable-man --prefix=<target_dir>`
5. 运行 `make` 编译
6. 运行 `make install` 安装到目标目录

### `main()`

命令行入口，解析 `--target_dir` / `-t` 参数并调用 `create_asset`。

## 内部实现细节

### 从源码编译流程

```python
with utils.tmp_dir():
    # 下载源码
    subprocess.check_call(["wget", "-O", VERSION + ".tar.gz", URL])
    # 解压
    subprocess.check_call(["tar", "-xzf", VERSION + ".tar.gz"])
    os.chdir(VERSION)
    # 配置、编译、安装
    subprocess.check_call(["./configure", "--disable-man", "--prefix=" + target_dir])
    subprocess.check_call(["make"])
    subprocess.check_call(["make", "install"])
```

### configure 选项说明

- `--disable-man`：禁用手册页生成，减少构建时间和不必要的依赖
- `--prefix=<target_dir>`：指定安装前缀，使 `make install` 将文件安装到目标目录

### 绝对路径要求

`target_dir` 必须转换为绝对路径，因为 `configure --prefix` 不接受相对路径。脚本使用 `os.path.abspath()` 确保这一点。

### 临时目录管理

使用 `utils.tmp_dir()` 上下文管理器创建临时目录进行编译，退出时自动清理。注意脚本使用了 `os.chdir()` 进入临时子目录，这在 `with` 块退出后由 `utils.tmp_dir()` 负责恢复。

## 依赖关系

### 内部模块

- `infra/bots/utils.py`：提供 `tmp_dir()` 上下文管理器

### 外部工具

- `wget`：下载源码压缩包
- `tar`：解压 `.tar.gz` 文件
- `make`：编译源码
- GCC/Clang 等 C 编译器：ccache 源码编译需要
- autoconf/automake 生成的 `configure` 脚本

### 网络依赖

- GitHub Releases：`https://github.com/ccache/ccache/releases/`

### 标准库

- `argparse`、`os`、`subprocess`、`sys`

## 设计模式与设计决策

### 源码编译模式

与其他资源创建脚本（直接下载预编译二进制）不同，ccache 采用从源码编译的方式。这可能是因为：
- ccache v3.7.7 可能未提供预编译的 Linux 二进制文件
- 从源码编译可以优化目标平台的编译选项
- 确保编译环境的一致性

### 无哈希校验

与较新的脚本不同，该脚本未对下载的源码压缩包进行 SHA256 校验。这是一个潜在的安全风险，建议在后续更新中添加。

### 版本固定

ccache 版本硬编码为 v3.7.7，这是一个较旧的版本（2019年发布）。较新的 ccache 4.x 版本使用 CMake 构建系统而非 autotools。

## 性能考量

- 源码编译比下载预编译二进制慢得多，但这是一次性操作（创建 CIPD 包时），不影响日常 CI 运行
- `make` 编译默认使用单线程，可通过添加 `-j` 参数加速，但脚本当前未使用此优化
- `--disable-man` 跳过手册页生成，减少了不必要的构建步骤
- `utils.tmp_dir()` 确保编译产生的中间文件在脚本完成后被清理，不占用磁盘空间

## 相关文件

- `infra/bots/utils.py` - 基础设施工具函数，提供 `tmp_dir()` 等工具
- `infra/bots/assets/ccache_linux/VERSION` - CIPD 资源版本号
- CI 构建配置中引用 ccache 的作业定义
