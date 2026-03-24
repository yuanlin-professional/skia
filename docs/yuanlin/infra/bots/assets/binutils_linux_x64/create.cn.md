# binutils Linux x64 资产创建脚本

> 源文件: infra/bots/assets/binutils_linux_x64/create.py

## 概述

这是一个从 Debian 软件包中提取特定 binutils 工具的资产创建脚本。binutils 是一套二进制工具集合，包含链接器、汇编器、目标文件处理工具等。该脚本专门从 Debian Buster 仓库下载 x86-64 架构的 binutils 包，提取其中的 `strip` 工具用于去除二进制文件中的调试符号和其他不必要信息，以减小文件体积。

## 架构位置

该脚本位于 `infra/bots/assets/binutils_linux_x64/` 目录，是 Skia 基础设施工具链资产的一部分。提取的 `strip` 工具用于：
- 优化构建产物大小
- 去除调试符号生成发布版本
- 减小 CI 构建缓存体积
- 加速部署和分发

选择 Debian Buster（旧稳定版）的包是为了减少动态库依赖，提升兼容性。

## 主要类与结构体

脚本使用函数式编程风格，依赖标准库和 Skia 工具模块：

- **argparse**: 命令行参数解析
- **glob**: 文件名模式匹配（导入但未使用）
- **os**: 路径操作
- **shutil**: 文件复制操作
- **subprocess**: 外部命令执行
- **sys**: 系统路径操作
- **utils**: Skia 基础设施工具模块

### 模块级常量

```python
URL = 'https://ftp.debian.org/debian/pool/main/b/binutils/binutils-x86-64-linux-gnu_2.31.1-16_amd64.deb'
SHA256 = 'c1da1cffff8a024b5eca0a6795558d9e0ec88fbd24fe059490dc665dc5cac92f'

to_copy = {
  'x86_64-linux-gnu-strip': 'strip',
}
```

**URL**: Debian Buster 的 binutils 包下载地址
**SHA256**: 包文件的校验和，确保完整性和安全性
**to_copy**: 映射关系，定义要提取的文件及其重命名

## 公共 API 函数

### `create_asset(target_dir)`

核心资产创建函数，执行下载、验证、解包和提取流程。

**参数**:
- `target_dir` (str): 存放提取文件的目标目录

**执行流程**:
1. 在临时目录中下载 .deb 包
2. 验证 SHA256 校验和
3. 使用 ar 命令解包 .deb 文件
4. 使用 tar 解压 data.tar.xz
5. 从指定路径复制需要的二进制文件到目标目录
6. 临时目录自动清理

**关键实现**:
```python
with utils.tmp_dir():
    subprocess.check_call(['wget', '--output-document=binutils.deb', '--quiet', URL])

    # 验证校验和
    output = subprocess.check_output(['sha256sum', 'binutils.deb'], encoding='utf-8')
    actual_hash = output.split(' ')[0]
    if actual_hash != SHA256:
        raise Exception('SHA256 does not match (%s != %s)' % (actual_hash, SHA256))

    # .deb 是 ar 归档文件
    subprocess.check_call(['ar', 'x', 'binutils.deb'])
    subprocess.check_call(['tar', '-xf', 'data.tar.xz'])

    # 复制并重命名文件
    for (orig, copy) in to_copy.items():
        shutil.copy(os.path.join('usr', 'bin', orig),
                    os.path.join(target_dir, copy))
```

### `main()`

脚本入口函数，负责参数解析和函数调用。

**命令行参数**:
- `--target_dir, -t`: 必需参数，指定资产输出目录

## 内部实现细节

### Debian 包结构

.deb 文件是 Debian/Ubuntu 软件包格式，实际是一个 ar 归档文件，包含：
- **debian-binary**: 版本信息
- **control.tar.xz**: 包元数据和控制脚本
- **data.tar.xz**: 实际的文件内容

脚本使用标准 Unix 工具解包：
```bash
ar x binutils.deb  # 解包 ar 归档
tar -xf data.tar.xz  # 解压数据部分
```

### 文件路径映射

Debian 包中的 binutils 工具使用带架构前缀的名称：
- 包内: `usr/bin/x86_64-linux-gnu-strip`
- 资产: `strip`

这种映射使得工具名称更简洁，符合常规命名惯例。

### 选择 Debian Buster 的原因

注释说明使用 Buster（Debian 10）而非更新版本的原因：
```python
# https://packages.debian.org/buster/amd64/binutils-x86-64-linux-gnu/download
# The older version from buster has fewer dynamic library dependencies.
```

**优势**:
- **依赖更少**: 旧版本链接的动态库更少，兼容性更好
- **部署简单**: 在不同 Linux 发行版上更容易运行
- **稳定性**: 成熟的稳定版本，经过充分测试

### SHA256 校验机制

使用 SHA256 而非 MD5 或 SHA1：
- **安全性**: SHA256 是密码学安全的哈希算法
- **防篡改**: 确保下载的包未被修改
- **标准化**: Debian 提供 SHA256 校验和

校验失败时抛出异常，防止使用损坏或被篡改的包。

### 可扩展的提取机制

`to_copy` 字典使得添加更多工具非常简单：
```python
to_copy = {
  'x86_64-linux-gnu-strip': 'strip',
  # 可以轻松添加其他工具
  # 'x86_64-linux-gnu-objdump': 'objdump',
  # 'x86_64-linux-gnu-readelf': 'readelf',
}
```

注释提示："If we need other files, we can add them to this mapping."

## 依赖关系

### 外部工具依赖

- **wget**: 下载 .deb 包
- **sha256sum**: 计算校验和
- **ar**: 解包 .deb 归档（GNU binutils 的一部分）
- **tar**: 解压 .tar.xz 文件
- **xz**: tar 需要 xz 支持解压 .xz 文件

### 运行时依赖

提取的 `strip` 工具在运行时需要：
- **glibc**: C 标准库（Debian Buster 使用 glibc 2.28）
- **Linux 内核**: 内核版本兼容性
- **其他动态库**: 较少（这是选择 Buster 的原因）

### Python 依赖

- **Python 标准库**: argparse, glob, os, shutil, subprocess, sys
- **Skia utils**: `infra/bots/utils.py`

## 设计模式与设计决策

### 字典驱动配置

使用 `to_copy` 字典定义提取规则：
```python
to_copy = {
  'source_name': 'dest_name',
}
```

**优点**:
- **声明式**: 配置与逻辑分离
- **可扩展**: 添加新文件只需修改字典
- **清晰**: 映射关系一目了然

### 从系统包提取

选择从 Debian 包提取而非从源码编译：

**优点**:
- **速度快**: 无需编译，只需下载和解包
- **测试充分**: Debian 包经过严格测试
- **依赖明确**: 包管理器处理依赖关系

**缺点**:
- **定制性差**: 无法自定义编译选项
- **版本固定**: 受 Debian 仓库限制

对于工具类资产，使用系统包是合理选择。

### 最小化策略

只提取需要的文件（strip），不包含：
- 文档
- 头文件
- 其他工具
- 库文件

这种最小化策略：
- 减小资产体积（从 ~5 MB 减至 ~1 MB）
- 加快下载和部署
- 减少潜在的安全风险

### 临时目录隔离

使用 `utils.tmp_dir()` 确保：
- 构建过程不污染工作目录
- 异常安全的清理
- 并发安全

## 性能考量

### 执行时间分解

典型执行时间：
- 下载 .deb 包: 1-5 秒（~2 MB）
- 计算校验和: <0.5 秒
- 解包 ar: <0.1 秒
- 解压 tar: 1-2 秒
- 复制文件: <0.1 秒
- 总计: 2-8 秒

相比从源码编译 binutils（需要 5-10 分钟），这种方法快得多。

### 网络优化

Debian FTP 服务器通常有良好的网络性能，但可以考虑：
- 使用地理位置更近的镜像
- 启用 HTTP/2 或 HTTP/3
- 实现本地缓存

### 磁盘 I/O

.deb 包使用 xz 压缩，压缩率高但解压较慢：
- **xz**: 高压缩率，低速度
- **gzip**: 低压缩率，高速度
- 权衡: 对于 2 MB 文件，xz 解压时间可接受

### 并发安全

`utils.tmp_dir()` 为每次调用创建独立的临时目录，支持并发执行。

## 相关文件

### 资产管理

- **`infra/bots/assets/binutils_linux_x64/VERSION`**: 资产版本标识
- **`infra/bots/assets/binutils_linux_x64/download.py`**: 下载脚本
- **`infra/bots/assets/binutils_linux_x64/upload.py`**: 上传脚本

### 使用场景

- **构建脚本**: 在构建完成后使用 strip 优化二进制文件
- **打包脚本**: 在创建发布包时去除调试符号
- **CI 任务**: 在上传 artifacts 前减小文件体积

### Debian 包信息

- 包页面: https://packages.debian.org/buster/amd64/binutils-x86-64-linux-gnu
- 文件列表: https://packages.debian.org/buster/amd64/binutils-x86-64-linux-gnu/filelist
- Debian binutils 主页: https://packages.debian.org/source/buster/binutils

### strip 工具文档

- GNU binutils 文档: https://sourceware.org/binutils/docs/binutils/strip.html
- man 手册: `man strip`

### 相关工具

Skia 可能还会用到 binutils 的其他工具：
- **objdump**: 显示目标文件信息
- **readelf**: 读取 ELF 文件结构
- **nm**: 列出符号表
- **objcopy**: 复制和转换目标文件

这些工具可以通过扩展 `to_copy` 字典轻松添加到资产中。strip 工具是优化构建产物的关键工具，可以将二进制文件大小减少 20-80%。
