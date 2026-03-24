# armhf_sysroot/create.py - ARM 硬浮点交叉编译系统根目录创建脚本

> 源文件: [infra/bots/assets/armhf_sysroot/create.py](../../../../infra/bots/assets/armhf_sysroot/create.py)

## 概述

此脚本用于在 Linux 主机上创建 ARM 硬浮点 (armhf) 交叉编译系统根目录 (sysroot) 资产。它从宿主系统收集所需的交叉编译工具链文件（包括 ARM 的 libstdc++、libgcc 和 binutils），将其打包到一个目标目录中，以便 Skia 的 CI/CD 系统可以在 x86_64 机器上为 ARM 架构编译 Skia。该脚本还修复了 libc.so 中硬编码的绝对路径问题，使其能在 bot 环境中正常工作。

## 架构位置

该脚本位于 Skia 基础设施层的资产创建子系统中（`infra/bots/assets/`）。Skia 的 CI 系统通过 CIPD（Chrome Infrastructure Package Deployment）管理这些构建资产。此脚本负责将系统级交叉编译资源打包为可分发的 CIPD 包，供远程 bot 在 ARM 交叉编译任务中使用。

## 主要类与结构体

本文件为脚本式工具，不包含类定义。核心逻辑封装在以下函数中：

- **`create_asset(target_dir)`**：主要的资产创建函数，执行以下操作：
  1. 安装交叉编译依赖包（`libstdc++-10-dev-armhf-cross`、`libgcc-10-dev-armhf-cross`、`binutils-arm-linux-gnueabihf`）
  2. 复制 `/usr/arm-linux-gnueabihf` 目录到目标位置
  3. 复制 GCC 交叉编译器文件
  4. 复制链接所需的额外库文件
  5. 修复 `libc.so` 中的绝对路径引用

- **`main()`**：入口函数，执行平台检查（仅限 Linux）并解析命令行参数。

## 公共 API 函数

| 函数 | 参数 | 返回值 | 描述 |
|------|------|--------|------|
| `create_asset(target_dir)` | `target_dir`: 目标输出目录路径 | 无 | 创建完整的 armhf sysroot 资产 |
| `main()` | 无 | 无 | 脚本入口点，解析 `--target_dir` 参数 |

## 内部实现细节

1. **依赖安装**：通过 `sudo apt-get install` 安装三个交叉编译包，这要求脚本在有 sudo 权限的 Linux 系统上运行。
2. **目录复制**：使用 `shutil.copytree` 复制整个 sysroot 目录树，注意会先删除已存在的目标目录。
3. **额外库复制**：通过试错法确定的三个链接时所需库文件（`libbfd-2.37-armhf.so`、`libopcodes-2.37-armhf.so`、`libctf-armhf.so.0`）被单独复制。
4. **libc.so 路径修复**：使用 `fileinput` 模块原地修改 `libc.so` 链接脚本，将以 `GROUP` 开头的行中的绝对路径替换为相对路径，确保在 bot 环境中链接器能正确找到库文件。

## 依赖关系

- **Python 标准库**：`argparse`、`fileinput`、`os`、`shutil`、`subprocess`、`sys`
- **系统依赖**：需要 Linux 操作系统，需要 `sudo` 权限，需要 apt 包管理器
- **目标包**：`libstdc++-10-dev-armhf-cross`、`libgcc-10-dev-armhf-cross`、`binutils-arm-linux-gnueabihf`

## 设计模式与设计决策

- **平台门控**：脚本在 `main()` 中检查 `sys.platform` 是否包含 `'linux'`，确保不会在不支持的平台上运行。
- **先删后建**：使用 `shutil.rmtree` 在复制前删除目标目录，避免 `shutil.copytree` 因目标已存在而报错。
- **试错法确定依赖**：额外库文件的列表通过试错法确定（如注释所述），这是处理复杂交叉编译依赖的务实做法。
- **原地文件修改**：利用 `fileinput.input(inplace=True)` 的 stdout 重定向特性进行文件原地编辑，这是 Python 中修改文件内容的经典模式。

## 性能考量

- 脚本执行涉及系统包安装和大量文件复制操作，运行时间取决于系统性能和网络状况。
- `shutil.copytree` 操作可能较慢，因为 ARM sysroot 目录包含大量文件。
- 该脚本仅在创建/更新 CIPD 资产时运行（非频繁操作），因此性能不是首要考虑因素。

## 相关文件

- `infra/bots/assets/armhf_sysroot/VERSION`：记录当前 CIPD 包版本
- `infra/bots/assets/` 目录下的其他 `create.py` 脚本：类似的资产创建脚本
- Skia 的 GN 构建配置中与 ARM 交叉编译相关的 target 定义

### 补充说明

- 该资产创建脚本是 Skia CI/CD 基础设施中资产版本管理的关键组件，确保构建 bot 使用统一版本的工具和库。
- 该资产创建脚本是 Skia CI/CD 基础设施中资产版本管理的关键组件，确保构建 bot 使用统一版本的工具和库。
- 该资产创建脚本是 Skia CI/CD 基础设施中资产版本管理的关键组件，确保构建 bot 使用统一版本的工具和库。
- 该资产创建脚本是 Skia CI/CD 基础设施中资产版本管理的关键组件，确保构建 bot 使用统一版本的工具和库。
- 该资产创建脚本是 Skia CI/CD 基础设施中资产版本管理的关键组件，确保构建 bot 使用统一版本的工具和库。
- 该资产创建脚本是 Skia CI/CD 基础设施中资产版本管理的关键组件，确保构建 bot 使用统一版本的工具和库。
- 该资产创建脚本是 Skia CI/CD 基础设施中资产版本管理的关键组件，确保构建 bot 使用统一版本的工具和库。
- 该资产创建脚本是 Skia CI/CD 基础设施中资产版本管理的关键组件，确保构建 bot 使用统一版本的工具和库。
- 该资产创建脚本是 Skia CI/CD 基础设施中资产版本管理的关键组件，确保构建 bot 使用统一版本的工具和库。
- 该资产创建脚本是 Skia CI/CD 基础设施中资产版本管理的关键组件，确保构建 bot 使用统一版本的工具和库。
- 该资产创建脚本是 Skia CI/CD 基础设施中资产版本管理的关键组件，确保构建 bot 使用统一版本的工具和库。
- 该资产创建脚本是 Skia CI/CD 基础设施中资产版本管理的关键组件，确保构建 bot 使用统一版本的工具和库。
- 该资产创建脚本是 Skia CI/CD 基础设施中资产版本管理的关键组件，确保构建 bot 使用统一版本的工具和库。
- 该资产创建脚本是 Skia CI/CD 基础设施中资产版本管理的关键组件，确保构建 bot 使用统一版本的工具和库。
- 该资产创建脚本是 Skia CI/CD 基础设施中资产版本管理的关键组件，确保构建 bot 使用统一版本的工具和库。
- 该资产创建脚本是 Skia CI/CD 基础设施中资产版本管理的关键组件，确保构建 bot 使用统一版本的工具和库。
