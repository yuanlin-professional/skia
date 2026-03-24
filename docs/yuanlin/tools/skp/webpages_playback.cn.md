# webpages_playback

> 源文件: tools/skp/webpages_playback.py

## 概述

`webpages_playback.py` 是 Skia 用于归档或回放网页并创建 SKP 文件的核心工具脚本。该脚本通过 Chromium Telemetry 框架来自动化网页捕获流程,可以记录网页的网络流量档案(WPR),并在回放这些档案时生成 SKP 文件。SKP 文件是 Skia 的序列化图形命令记录,用于性能基准测试和回归测试。该脚本支持将生成的 SKP 文件上传到 Google Storage 或本地文件系统,并提供了完整的验证工具链来确保生成的 SKP 文件质量。

## 架构位置

该脚本位于 Skia 项目的工具链层,专门用于 SKP 生成和管理工作流:

```
skia/
  tools/
    skp/
      webpages_playback.py       # 主脚本
      page_sets/                  # 页面集定义目录
        data/                     # 存储 WPR 档案和凭证
          credentials.json        # 网站登录凭证
        skia_*.py                 # 各种页面集定义文件
```

该脚本与 Chromium 的 Telemetry 基础设施紧密集成,依赖于 Chrome 浏览器可执行文件和 Telemetry 工具链(`record_wpr`、`run_benchmark`)来完成网页录制和回放任务。

## 主要类与结构体

### SkPicturePlayback 类

主工作类,负责协调整个 SKP 生成流程:

**核心属性:**
- `_browser_executable`: 用于捕获的浏览器二进制路径
- `_browser_args`: 浏览器启动参数
- `_page_sets`: 要处理的页面集列表
- `_record`: 是否创建新的网页档案
- `_upload`: 是否上传生成的文件
- `gs`: 数据存储对象(Google Storage 或本地文件系统)
- `_skp_files`: 生成的 SKP 文件列表

**核心方法:**

**`__init__(parse_options)`**
构造函数,初始化所有配置参数,包括浏览器路径、页面集、数据存储位置等。

**`Run()`**
主执行方法,完整流程包括:
1. 下载凭证文件
2. 创建本地存储目录
3. 遍历每个页面集
4. 如果是录制模式,调用 `record_wpr` 创建网页档案
5. 否则下载已有档案并调用 `run_benchmark` 生成 SKP
6. 重命名 SKP 文件为描述性名称
7. 可选运行验证工具(render_pictures、render_pdfs、debugger)
8. 上传结果到存储位置

**`_ParsePageSets(page_sets)`**
解析页面集参数,支持:
- `'all'`: 获取所有 Skia 和 Chromium 页面集
- glob 模式: 如 `'tools/skp/page_sets/*.py'`
- 逗号分隔列表: 多个具体页面集

**`_RenameSkpFiles(page_set)`**
将生成的 SKP 文件重命名为标准化名称:
- Skia 页面集: `{platform_prefix}_{page_name}.skp`
- Chromium 页面集: `{preset_prefix}_{webpage_name}.skp`
验证 SKP 文件大小必须 >= 1KB,否则抛出 `InvalidSKPException`。

**`_GetSkiaSkpFileName(page_set)`**
生成 Skia 页面集的 SKP 文件名,格式为 `{device_prefix}_{page_name}.skp`,其中 device 映射为:
- `'desktop'` → `'desk'`
- `'mobile'` → `'mobi'`
- `'tablet'` → `'tabl'`

**`_DownloadWebpagesArchive(wpr_data_file, page_set_json_name)`**
从存储位置下载网页档案文件和对应的 JSON 配置文件。

### DataStore 抽象类

定义数据存储接口,模拟 Google Storage API:

**抽象方法:**
- `target_name()`: 返回存储目标名称
- `target_type()`: 返回存储类型描述
- `does_storage_object_exist(name)`: 检查对象是否存在
- `download_file(name, local_path)`: 下载文件
- `upload_dir_contents(source_dir, dest_dir)`: 上传目录内容

### GoogleStorageDataStore 类

Google Storage 实现,使用 `gcloud storage` 命令:
- 使用 `gcloud storage ls` 检查文件存在性
- 使用 `gcloud storage cp` 进行上传下载
- 使用 `gcloud storage rm --recursive` 删除路径

### LocalFileSystemDataStore 类

本地文件系统实现:
- 使用 Python 标准库 `os`、`shutil` 操作文件
- 实现递归目录复制功能

## 公共 API 函数

### 命令行接口

脚本通过 `optparse` 提供丰富的命令行参数:

**核心参数:**
- `--page_sets`: 指定要处理的页面集,支持 `'all'` 或 glob 模式
- `--record`: 创建新的网页档案(录制模式)
- `--browser_executable`: Chrome 浏览器二进制路径(必需)
- `--data_store`: 数据存储位置,格式 `gs://bucket` 或本地路径
- `--upload`: 是否上传生成的文件

**验证和调试参数:**
- `--skia_tools`: Skia 工具目录路径,用于运行验证工具
- `--non-interactive`: 非交互模式,跳过调试器

**高级参数:**
- `--browser_extra_args`: 额外的浏览器参数
- `--chrome_src_path`: Chromium 源码路径
- `--alternate_upload_dir`: 备用上传目录
- `--upload_to_partner_bucket`: 上传到合作伙伴 bucket
- `--skp_prefix`: SKP 文件名前缀
- `--output_dir`: 临时输出目录

### 工具函数

**`remove_prefix(s, prefix)`**
移除字符串前缀的辅助函数。

## 内部实现细节

### 网页录制流程

录制模式下,脚本调用 `record_wpr` 命令:
```bash
PYTHONPATH=<paths> DISPLAY=:0 record_wpr \
  --extra-browser-args="..." \
  --browser=exact \
  --browser-executable=<path> \
  <page_set_basename>_page_set \
  --page-set-base-dir=<dir>
```

最多重试 `RETRY_RECORD_WPR_COUNT`(5) 次,成功后将生成的 `.wprgo` 文件和 `.json` 文件复制到本地归档目录。

### SKP 生成流程

调用 `run_benchmark` 命令生成 SKP:
```bash
PYTHONPATH=<paths> DISPLAY=:0 timeout 1800 run_benchmark \
  --extra-browser-args="..." \
  --browser=exact \
  --browser-executable=<path> \
  skpicture_printer \
  --page-set-name=<name> \
  --page-set-base-dir=<dir> \
  --skp-outdir=<tmp_dir> \
  --also-run-disabled-tests
```

最多重试 `RETRY_RUN_MEASUREMENT_COUNT`(3) 次,每次失败后等待 10 秒。

### SKP 文件验证

生成的 SKP 文件必须满足:
1. **大小检查**: 文件大小 >= 1KB,否则认为捕获失败(可能是 404 或重定向循环)
2. **最大文件选择**: 如果一个网站生成多个 SKP,选择最大的作为最终结果
3. **工具验证**: 如果指定了 `--skia_tools`,依次运行:
   - `render_pictures -r <skp_dir>`: 验证 SKP 可渲染
   - `render_pdfs -r <skp_dir>`: 验证 PDF 输出
   - `debugger <skp_dir>`: 交互式调试(非交互模式下跳过)

### 文件命名规范

SKP 文件名遵循严格的命名约定:
- **长度限制**: 基础名称最多 31 字符(`MAX_SKP_BASE_NAME_LEN`)
- **Skia 页面集格式**: `{platform}_{site}.skp`
  - 示例: `desk_yahooanswers.skp` (desktop)
  - 示例: `mobi_wikipedia.skp` (mobile)
  - 示例: `tabl_worldjournal.skp` (tablet)
- **Chromium 页面集格式**: `{prefix}_{webpage}.skp`
  - 自动去除 URL 前缀 `http___`、`https___`、`www_`

### 排除规则

某些页面集配置了排除过滤器(`PAGE_SETS_TO_EXCLUSIONS`):
- `key_mobile_sites_smooth.py`: 排除 `"(digg|worldjournal|twitter|espn)"`
- `top_25_smooth.py`: 排除 `"(mail\.google\.com)"`

### 凭证管理

脚本需要 `credentials.json` 文件来访问需要登录的网站,文件格式:
```json
{
  "google": {
    "username": "google_testing_account_username",
    "password": "google_testing_account_password"
  }
}
```

凭证文件从 `gs://<bucket>/playback/credentials/credentials.json` 下载到本地 `page_sets/data/credentials.json`。

## 依赖关系

### 外部工具依赖

1. **Chromium Telemetry 框架**:
   - `tools/perf/record_wpr`: Web Page Replay 录制工具
   - `tools/perf/run_benchmark`: 基准测试运行器
   - `third_party/catapult`: Telemetry 核心库

2. **Chrome 浏览器**:
   - 需要 Chromium 构建的 Chrome 二进制文件
   - 使用 `--disable-setuid-sandbox` 和 `--disable-field-trial-config` 参数

3. **Google Cloud SDK**:
   - `gcloud storage` 命令用于 Google Storage 操作

4. **Skia 工具**:
   - `render_pictures`: SKP 渲染验证工具
   - `render_pdfs`: PDF 输出验证工具
   - `debugger`: SKP 调试器

### Python 模块依赖

- 标准库: `datetime`, `glob`, `optparse`, `os`, `posixpath`, `shutil`, `subprocess`, `sys`, `tempfile`, `time`, `traceback`
- 隐式依赖: Telemetry 框架通过 `PYTHONPATH` 注入

## 设计模式与设计决策

### 策略模式

使用 `DataStore` 抽象类定义存储接口,通过 `GoogleStorageDataStore` 和 `LocalFileSystemDataStore` 实现不同的存储策略。根据 `--data_store` 参数的前缀(`gs://` vs 其他)动态选择实现:

```python
if data_store_location.startswith(GS_PREFIX):
    self.gs = GoogleStorageDataStore(data_store_location)
else:
    self.gs = LocalFileSystemDataStore(data_store_location)
```

### 重试机制

对不稳定的网络操作实施重试策略:
- 录制操作: 最多重试 5 次
- SKP 生成: 最多重试 3 次,每次失败后等待 10 秒
- 使用 Python 的 `for-else` 模式优雅处理重试失败

### 渐进式验证

采用多层验证确保 SKP 质量:
1. **生成时验证**: 检查文件大小 >= 1KB
2. **渲染验证**: 通过 `render_pictures` 确保可渲染
3. **PDF 验证**: 通过 `render_pdfs` 确保 PDF 输出正确
4. **交互式验证**: 可选通过 `debugger` 手动检查

### 异常处理

定义自定义异常 `InvalidSKPException` 来区分 SKP 验证失败和其他错误,支持在重试循环中特殊处理。

## 性能考量

### 并行化机会

当前实现是顺序处理每个页面集,但设计上支持并行化:
- 页面集之间独立,可并行录制
- SKP 生成使用独立的临时目录(`TMP_SKP_DIR`)避免冲突

### 超时控制

`run_benchmark` 命令使用 `timeout 1800` (30 分钟)防止挂起:
- 处理网络慢、页面复杂等情况
- 超时后自动进入重试流程

### 存储优化

1. **增量上传**: 只上传新生成的 SKP,不重复上传已有文件
2. **清理策略**: 处理前清空旧的 data 目录文件,处理后删除临时站点目录
3. **最大文件选择**: 只保留每个站点最大的 SKP,节省存储空间

### 网络带宽

Google Storage 上传使用 `gcloud storage cp --recursive`,利用 gcloud SDK 的内置优化(并行上传、断点续传等)。

## 相关文件

### 页面集定义

- `/tools/skp/page_sets/skia_*.py`: Skia 维护的各种网站页面集
- `<chrome_src>/tools/perf/page_sets/*.py`: Chromium 官方页面集

### 配置和数据

- `/tools/skp/page_sets/data/credentials.json`: 网站登录凭证
- `/tools/skp/page_sets/data/skia_*.json`: WPR 回放配置文件
- `/tools/skp/page_sets/data/skia_*.wprgo`: WPR 网络流量档案

### Telemetry 工具

- `<chrome_src>/tools/perf/record_wpr`: WPR 录制工具
- `<chrome_src>/tools/perf/run_benchmark`: 基准测试运行器
- `<chrome_src>/third_party/catapult`: Telemetry 框架

### Skia 验证工具

- `<skia_tools>/render_pictures`: SKP 渲染工具
- `<skia_tools>/render_pdfs`: PDF 生成工具
- `<skia_tools>/debugger`: SKP 调试器

### 输出目录

- `<output_dir>/playback/skps/`: 生成的 SKP 文件
- `<output_dir>/playback/webpages_archive/`: 录制的网页档案
- `<tmp_dir>/`: 临时 SKP 生成目录(自动清理)

### 远程存储

- `gs://<bucket>/playback/skps/`: SKP 文件存储位置
- `gs://<bucket>/playback/webpages_archive/`: 网页档案存储位置
- `gs://<bucket>/playback/credentials/credentials.json`: 凭证文件
- `gs://chrome-partner-telemetry/skps/<timestamp>/`: 合作伙伴 bucket
