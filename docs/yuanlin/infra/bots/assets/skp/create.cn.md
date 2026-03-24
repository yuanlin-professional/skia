# create.py - SKP 测试资源创建脚本

> 源文件: [infra/bots/assets/skp/create.py](https://github.com/aspect-build/aspect-cli/blob/main/infra/bots/assets/skp/create.py)

## 概述

`create.py` 是 Skia SKP（Skia Picture）测试资源的核心创建脚本。SKP 是 Skia 的序列化绘图指令格式，用于性能基准测试和渲染回归检测。该脚本从三个不同来源收集 SKP 文件：Flutter 的 SKP 生成工具、通过 Chrome 浏览器录制网页渲染指令、以及从 Google Cloud Storage 下载的私有 SKP 文件。对于私有 SKP，脚本还使用 Skia 的 `dm` 工具更新其内部版本号以保持兼容性。整个脚本约 210 行，包含复杂的进程管理、错误处理和文件操作逻辑。

## 架构位置

该脚本在 SKP 资源创建流程中处于核心位置，是实际执行资源生成工作的模块。

```
SKP 资源创建架构:

create_and_upload.py
    └── sk asset upload
        └── create.py (本文件)
            ├── [来源1] Flutter SKP 生成器
            │   └── flutter/tests/skp_generator/build.sh
            ├── [来源2] 网页录制
            │   └── tools/skp/webpages_playback.py
            │       └── Chrome 浏览器
            └── [来源3] 私有 SKP
                ├── gs://skia-skps/private/skps (下载)
                └── dm --config skp (版本更新)
```

## 主要类与结构体

本脚本无类定义。关键常量和环境变量：

| 常量/变量 | 值 | 说明 |
|-----------|-----|------|
| `BROWSER_EXECUTABLE_ENV_VAR` | `SKP_BROWSER_EXECUTABLE` | 浏览器路径环境变量 |
| `CHROME_SRC_PATH_ENV_VAR` | `SKP_CHROME_SRC_PATH` | Chrome 源码路径环境变量 |
| `UPLOAD_TO_PARTNER_BUCKET_ENV_VAR` | `SKP_UPLOAD_TO_PARTNER_BUCKET` | 是否上传到合作伙伴桶 |
| `DM_PATH_ENV_VAR` | `DM_PATH` | Skia DM 工具路径环境变量 |
| `SKIA_TOOLS` | `tools/` 目录路径 | Skia 工具目录 |
| `PRIVATE_SKPS_GS` | `gs://skia-skps/private/skps` | 私有 SKP 的 GCS 路径 |

## 公共 API 函数

### `create_asset(chrome_src_path, browser_executable, target_dir, upload_to_partner_bucket, dm_path)`

SKP 资源创建的主函数。

**参数**：
- `chrome_src_path` (str): Chromium 源代码路径
- `browser_executable` (str): Chrome 浏览器可执行文件路径
- `target_dir` (str): 资源输出目录
- `upload_to_partner_bucket` (bool): 是否上传到合作伙伴 GCS 桶
- `dm_path` (str): Skia DM 测试工具路径

### `get_flutter_skps(target_dir)`

从 Flutter 的 SKP 生成工具创建 SKP 文件。

**参数**：
- `target_dir` (str): SKP 输出目录

### `getenv(key)`

获取环境变量值的辅助函数，变量不存在时输出错误信息并退出。

### `main()`

命令行入口，从环境变量获取配置参数并调用 `create_asset`。

## 内部实现细节

### 来源 1：Flutter SKP 生成

```python
def get_flutter_skps(target_dir):
    utils.git_clone('https://github.com/flutter/tests.git', '.')
    os.chdir('skp_generator')
    subprocess.check_call(['bash', 'build.sh'])
```

克隆 Flutter 的 tests 仓库，运行 `skp_generator/build.sh` 生成 SKP。生成后对文件名进行清理，将非字母数字字符替换为下划线，避免文件系统兼容性问题。

### 来源 2：Chrome 网页录制

使用 `webpages_playback.py` 脚本驱动 Chrome 浏览器访问 `tools/skp/page_sets/` 中定义的网页，录制渲染指令为 SKP 文件。在 CI 环境中（`CHROME_HEADLESS`），会启动 Xvfb 虚拟显示服务器。

关键流程：
1. 如果是 headless 环境，启动 Xvfb (`sudo Xvfb :0 -screen 0 1280x1024x24`)
2. 运行 `webpages_playback.py` 录制所有页面集
3. 在 `finally` 块中进行全面的进程清理

### 进程清理逻辑

脚本包含详细的进程清理机制，处理以下场景：
- Xvfb 进程的正常终止（`Popen.kill()`）和备用终止（`sudo kill -9`）
- 残留浏览器进程的检测和终止（通过 `ps ax` 扫描）
- 残留 Xvfb 进程的检测和终止
- 排除当前 Python 进程以避免自杀

### 来源 3：私有 SKP 版本更新

```python
subprocess.check_call([
    dm_path,
    '--config', 'skp',
    '-w', new_skps_dir,
    '--skps', old_skps_dir,
    '--src', 'skp'])
```

通过 DM 工具"回放"旧版本 SKP 并重新序列化，确保 SKP 内部版本号保持最新，避免因版本过旧而无法被当前 Skia 库解析。

### DM 输出路径处理

DM 工具的输出遵循 `${dir}/${config}/${source_type}/` 的目录结构，因此实际 SKP 位于 `new_skps_dir/skp/skp/`。文件名会被 DM 添加额外的 `.skp` 后缀（如 `file.skp.skp`），脚本通过替换 `.skp.skp` 为 `.skp` 来修正。

## 依赖关系

### 内部模块

- `infra/bots/utils.py`：提供 `tmp_dir()` 上下文管理器和 `git_clone()` 工具
- `tools/skp/webpages_playback.py`：网页录制工具
- `tools/skp/page_sets/`：网页集合定义

### 外部工具

- Chrome 浏览器：用于网页渲染录制
- `dm`：Skia 的测试/诊断工具，用于 SKP 版本更新
- `gcloud`：Google Cloud SDK，用于从 GCS 下载私有 SKP
- `Xvfb`：X 虚拟帧缓冲区，用于 headless 环境
- `bash`：运行 Flutter SKP 生成器的构建脚本
- `git`：克隆 Flutter tests 仓库

### 网络/存储依赖

- `https://github.com/flutter/tests.git`：Flutter SKP 生成器仓库
- `gs://skia-skps/private/skps`：私有 SKP 文件的 GCS 路径

### 标准库

- `argparse`、`os`、`shutil`、`subprocess`、`sys`、`tempfile`
- `distutils.dir_util.copy_tree`：递归目录复制

## 设计模式与设计决策

### 多源聚合模式

从三个不同来源（Flutter、Chrome 录制、GCS 私有库）收集 SKP，合并到统一的输出目录。这种设计确保了测试覆盖面的全面性。

### 环境变量配置模式

通过环境变量（而非命令行参数）接收配置，因为脚本通过 `sk` 工具间接调用，无法直接传递命令行参数。这是与 `create_and_upload.py` 配合使用的设计决策。

### 防御性进程管理

脚本对 Xvfb 和浏览器进程进行了多层次的清理（正常终止 -> sudo 强制终止 -> ps 扫描强制终止），这种防御性编程风格源于在 CI 环境中长期积累的经验——Telemetry 框架不总是正确清理进程。

### SKP 版本升级策略

通过 DM 工具回放并重新序列化私有 SKP，而非要求手动重新生成，这是一种向后兼容的巧妙策略。随着 SKP 格式的演进，旧版本 SKP 可能无法被新版本 Skia 解析，此机制自动解决了这个问题。

## 性能考量

- **整体执行时间**：该脚本的执行时间可能较长（几十分钟），因为涉及浏览器启动、网页加载和渲染录制
- **Flutter SKP 生成**：需要克隆 Git 仓库并运行构建脚本，耗时取决于网络和编译速度
- **网页录制**：逐个页面录制，受限于浏览器启动时间和页面加载速度
- **DM 版本更新**：对 SKP 进行反序列化-重新序列化操作，CPU 密集但通常较快
- **临时目录管理**：使用 `utils.tmp_dir()` 上下文管理器和 `tempfile.mkdtemp()` 确保临时文件的及时清理
- **进程扫描**：使用 `ps ax` 进行全进程扫描可能在进程数量巨大时较慢，但在 CI 环境中通常不是问题

## 相关文件

- `infra/bots/assets/skp/create_and_upload.py` - 上传协调脚本
- `infra/bots/assets/skp/__init__.py` - Python 包初始化
- `infra/bots/utils.py` - 基础设施工具函数
- `tools/skp/webpages_playback.py` - 网页录制工具
- `tools/skp/page_sets/` - 网页集合定义目录
- `tools/dm/` - DM 测试工具源代码
