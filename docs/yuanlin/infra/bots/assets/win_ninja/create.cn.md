# create.py - Windows Ninja 构建工具资源创建脚本

> 源文件: [infra/bots/assets/win_ninja/create.py](https://github.com/aspect-build/aspect-cli/blob/main/infra/bots/assets/win_ninja/create.py)

## 概述

`create.py` 是用于创建 Windows 平台上 Ninja 构建工具 CIPD 资源包的 Python 脚本。它从 GitHub 上的 ninja-build 项目下载指定版本的 Windows 二进制发行包（zip 格式），解压到目标目录后清理临时文件。该脚本是 Skia CI/CD 基础设施的一部分，确保所有 Windows 构建机器使用一致的 Ninja 版本。

## 架构位置

该脚本位于 Skia 基础设施资源管理系统中，专门负责 Windows 平台 Ninja 工具的版本管理。

```
infra/bots/assets/
├── win_ninja/
│   ├── create.py      # 本文件 - 创建 Windows Ninja 资源
│   └── VERSION        # 当前 CIPD 资源版本号
├── linux_ninja/       # Linux 平台 Ninja（如存在）
└── ...
```

Ninja 是 Skia 使用的核心构建系统之一，与 GN（Generate Ninja）配合使用来编译 Skia 的 C++ 代码。

## 主要类与结构体

本脚本为简单的过程式脚本，无类定义。关键常量：

| 常量 | 值 | 说明 |
|------|-----|------|
| `VERSION` | `"v1.8.2"` | Ninja 的目标版本号 |
| `URL` | GitHub releases 模板 URL | 下载地址模板，使用 `%s` 插入版本号 |

## 公共 API 函数

### `create_asset(target_dir)`

创建 Ninja 资源包。

**参数**：
- `target_dir` (str): 资源输出目录路径

**行为**：
1. 使用 `curl -L` 下载 Ninja Windows zip 文件（`-L` 跟随重定向）
2. 使用 `unzip` 解压到目标目录
3. 删除临时 zip 文件

### `main()`

命令行入口，解析 `--target_dir` / `-t` 参数并调用 `create_asset`。

## 内部实现细节

### 下载与解压流程

```python
# 1. 下载 - 使用 curl 跟随 GitHub 重定向
subprocess.check_call(["curl", "-L", URL % VERSION, "-o", "ninja-win.zip"])
# 2. 解压 - 直接解压到目标目录
subprocess.check_call(["unzip", "ninja-win.zip", "-d", target_dir])
# 3. 清理 - 删除临时文件
subprocess.check_call(["rm", "ninja-win.zip"])
```

下载的 zip 文件包含单个 `ninja.exe` 可执行文件。脚本通过 `subprocess.check_call` 确保每个步骤成功执行。

### 版本固定

Ninja 版本硬编码为 `v1.8.2`，更新版本时需要手动修改 `VERSION` 常量并重新生成 CIPD 包。

## 依赖关系

### 外部工具

- `curl`：用于下载文件，需要支持 `-L` 选项（跟随重定向）
- `unzip`：用于解压 zip 文件

### 网络依赖

- GitHub Releases：`https://github.com/ninja-build/ninja/releases/` 作为下载源

### 标准库

- `argparse`：命令行参数解析
- `subprocess`：外部命令执行

## 设计模式与设计决策

### 简约设计

脚本极为简洁（36 行），遵循单一职责原则。下载、解压、清理三个步骤线性执行，逻辑清晰。

### 无校验设计

与其他类似脚本（如 `bazelisk` 资源创建脚本）不同，本脚本未进行 SHA256 校验。这可能是因为该脚本编写较早（2017年），或认为 Ninja 来源可信度足够高。

### 临时文件管理

zip 文件下载到当前工作目录后立即清理，避免残留临时文件。但如果中间步骤失败，zip 文件可能残留。

## 性能考量

- 脚本执行速度取决于网络下载速度
- Ninja 的 Windows 发行包体积较小（约几百 KB），下载快速
- 使用 `check_call` 同步执行，无并行优化，但由于步骤有序依赖，无需并行
- 未使用临时目录上下文管理器，如果脚本在解压后清理前崩溃，可能留下临时文件

## 相关文件

- `infra/bots/assets/win_ninja/VERSION` - CIPD 资源版本号
- `infra/bots/assets/linux_ninja/create.py` - Linux 平台 Ninja 创建脚本（如存在）
- `gn/` - GN 构建配置目录，GN 生成 Ninja 构建文件
