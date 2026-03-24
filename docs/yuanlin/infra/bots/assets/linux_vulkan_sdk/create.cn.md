# create.py

> 源文件: infra/bots/assets/linux_vulkan_sdk/create.py

## 概述

`create.py` 用于创建 Linux Vulkan SDK 资产，从 LunarG 官网下载完整的 Vulkan SDK 并验证其完整性。Vulkan 是现代跨平台图形和计算 API，Skia 使用它实现高性能的 GPU 渲染后端。

## 架构位置

该资产为 Skia 的 Vulkan 后端提供开发和运行时支持，包括 Vulkan 加载器、验证层、头文件和工具。

## 主要类与结构体

函数式编程风格，无类定义。

### 全局常量
```python
SDK_VERSION='1.4.321.1'
SDK_SHA256='f22a3625bd4d7a32e7a0d926ace16d5278c149e938dac63cecc00537626cbf73'
SDK_URL=('https://sdk.lunarg.com/sdk/download/%s/linux/'
         'vulkansdk-linux-x86_64-%s.tar.xz' % (SDK_VERSION, SDK_VERSION))
```

## 公共 API 函数

### create_asset(target_dir)

```python
def create_asset(target_dir):
    """从 LunarG 下载 Vulkan SDK 并验证"""
```

**功能**：
1. **下载 SDK**
```python
subprocess.check_call(['curl', '-L', SDK_URL, '--output', tarball])
```
使用 `curl -L` 跟随重定向下载。

2. **SHA256 验证**
```python
with open(tarball, 'rb') as f:
    actual_hash = hashlib.sha256(f.read()).hexdigest()
if actual_hash != SDK_SHA256:
    raise Exception('SHA256 mismatch...')
```
计算文件哈希并与预期值比较，确保下载完整且未被篡改。

3. **提取 SDK**
```python
subprocess.check_call(['tar', '--extract', '--verbose',
                       '--file=%s' % tarball,
                       '--directory=%s' % target_dir,
                       '--strip-components=2',
                       '%s/x86_64' % SDK_VERSION])
```
- 使用 `--strip-components=2` 跳过前两层目录
- 只提取 `<SDK_VERSION>/x86_64/` 目录的内容
- 直接解压到 `target_dir`，避免嵌套目录

### main()
限制只在 Linux 平台运行，解析参数并调用 `create_asset()`。

## 内部实现细节

### SDK 目录结构优化

原始 tarball 结构：
```
vulkansdk-linux-x86_64-1.4.321.1.tar.xz
└── 1.4.321.1/
    ├── x86_64/                   # 目标内容
    │   ├── bin/
    │   ├── lib/
    │   ├── include/
    │   └── ...
    └── documentation/            # 不需要
```

使用 `--strip-components=2` 后：
```
<target_dir>/
├── bin/                          # Vulkan 工具
│   ├── vulkaninfo
│   ├── vkconfig
│   └── ...
├── lib/                          # 库文件
│   ├── libvulkan.so.1
│   ├── libVkLayer_*.so          # 验证层
│   └── ...
├── include/                      # 头文件
│   └── vulkan/
│       ├── vulkan.h
│       └── ...
└── share/                        # 共享数据
    └── vulkan/
        └── explicit_layer.d/     # 层配置
```

### 安全性验证

使用 SHA256 哈希验证：
- **防止下载损坏**：检测网络传输错误
- **防止篡改**：确保文件未被恶意修改
- **版本确认**：确保下载的是预期版本

### 版本管理

硬编码 SDK 版本和哈希：
- **可重复性**：确保每次创建相同的资产
- **稳定性**：避免自动更新导致的构建问题
- **更新流程**：
  1. 访问 LunarG 网站检查新版本
  2. 下载并计算 SHA256（`sha256sum vulkansdk-linux-x86_64-*.tar.xz`）
  3. 更新脚本中的 `SDK_VERSION` 和 `SDK_SHA256`

## 依赖关系

### 系统依赖
- **curl**: 支持 HTTPS 和重定向的下载工具
- **tar**: 支持 xz 压缩的解压工具
- **Linux 系统**: 脚本强制要求（`sys.platform` 检查）

### Python 依赖
- 标准库：`argparse`, `hashlib`, `os`, `subprocess`, `sys`
- Skia 模块：`utils`（提供 `tmp_dir` 上下文管理器）

### 外部资源
- **LunarG Vulkan SDK**: 官方 Vulkan 开发套件（~300 MB）

## 设计模式与设计决策

### 安全下载模式
结合 HTTPS、SHA256 验证和官方源，确保资产的完整性和可信度。

### 平台限制
只允许在 Linux 运行：
- SDK 包是 Linux 特定的
- 避免在错误平台上运行导致混淆

### 临时目录使用
在临时目录中下载和验证，只在成功后提取到目标位置，确保失败不会产生不完整的输出。

### 路径优化
使用 `--strip-components` 避免嵌套目录，简化资产结构。

## 性能考量

### 下载时间
- **文件大小**: ~300 MB（压缩后）
- **网络速度影响**:
  - 100 Mbps: 25-30 秒
  - 10 Mbps: 4-5 分钟

### 哈希计算
- **算法**: SHA256
- **时间**: 2-5 秒（取决于磁盘速度）
- **内存**: 读取整个文件到内存（~300 MB）

### 解压时间
- **xz 解压**: 30-60 秒（CPU 密集）
- **解压后大小**: ~1.5 GB

### 总执行时间
- **最佳情况**: 1-2 分钟
- **典型情况**: 3-5 分钟
- **最差情况**: 10 分钟（慢速网络）

### 磁盘空间
- 下载的 tarball: ~300 MB
- 解压后的 SDK: ~1.5 GB
- 临时空间峰值: ~1.8 GB

## 相关文件

### LunarG 资源
- **官方网站**: `https://vulkan.lunarg.com/`
- **SDK 下载**: `https://vulkan.lunarg.com/sdk/home`
- **文档**: `https://vulkan.lunarg.com/doc/sdk`

### Skia Vulkan 后端
- **`src/gpu/ganesh/vk/`**: Skia 的 Vulkan 后端实现
- **`include/gpu/vk/`**: Vulkan 相关公共头文件
- **`gn/gpu.gni`**: Vulkan 构建配置

### 构建系统
- **`infra/bots/gen_tasks_logic/gen_tasks_logic.go`**: 使用 Vulkan 的任务定义
- **`gn/skia/BUILD.gn`**: Skia 构建配置（启用 Vulkan 后端）

### 相关资产
- **`mesa_intel_driver_linux/`**: Intel Mesa Vulkan 驱动
- **`clang_linux/`**: Linux Clang 编译器（构建 Vulkan 代码）
