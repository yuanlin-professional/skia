# create.py - SkParagraph 测试字体资源创建脚本

> 源文件: [infra/bots/assets/skparagraph/create.py](https://github.com/aspect-build/aspect-cli/blob/main/infra/bots/assets/skparagraph/create.py)

## 概述

`create.py` 用于创建 SkParagraph 测试所需的字体资源 CIPD 包。SkParagraph 是 Skia 的段落文本排版模块（`SkParagraphTests.cpp`），其测试对字体的精确度有极高要求——测试中的文本度量值（metrics）与特定字体版本紧密耦合。该脚本从两个 Git 仓库（`textlayout` 和 `skia`）的特定 commit 收集字体文件，并从 Google Fonts 下载一个阿拉伯语字体（NotoNaskhArabic），确保测试使用的字体版本完全可追溯和可重复。

## 架构位置

该脚本属于 Skia 文本排版测试基础设施。

```
infra/bots/assets/
├── skparagraph/
│   └── create.py              # 本文件 - 字体资源创建
└── ...

字体来源:
1. github.com/Rusino/textlayout (fonts/ 目录)
2. skia.googlesource.com/skia (resources/fonts/ 目录)
3. fonts.gstatic.com (NotoNaskhArabic-Regular.ttf)

使用方:
SkParagraphTests.cpp -> 这些字体文件
```

## 主要类与结构体

本脚本无类定义。关键常量：

| 常量 | 值 | 说明 |
|------|-----|------|
| `ARABIC_URL` | Google Fonts gstatic URL | Noto Naskh Arabic 字体下载地址 |
| `ARABIC_SHA256` | `b957e8c71a24e50c...` | 阿拉伯字体的 SHA256 哈希 |

## 公共 API 函数

### `create_asset(target_dir)`

从多个来源收集字体文件到目标目录。

**参数**：
- `target_dir` (str): 资源输出目录路径

**行为**：
1. 克隆 `textlayout` 仓库，检出特定 commit，复制 `fonts/` 目录
2. 克隆 `skia` 仓库，检出特定 commit，复制 `resources/fonts/` 目录
3. 清理不需要的文件（`abc/`、`svg/` 子目录和 `fonts.xml`）
4. 下载 NotoNaskhArabic 字体并进行 SHA256 校验

### `main()`

命令行入口，解析 `--target_dir` / `-t` 参数并调用 `create_asset`。

## 内部实现细节

### 多源字体收集

脚本从三个不同来源收集字体，每个来源都锁定到特定版本：

```python
# 来源 1: textlayout 仓库（特定 commit）
subprocess.call(['git', 'clone', 'https://github.com/Rusino/textlayout'])
subprocess.call(['git', 'checkout', '9c1868e84da1db358807ebff5cf52327e53560a0'])
shutil.copytree("fonts", target_dir, dirs_exist_ok=True)

# 来源 2: Skia 仓库（特定 commit）
subprocess.call(['git', 'clone', 'https://skia.googlesource.com/skia/'])
subprocess.call(['git', 'checkout', '2f82ef6e77774dc4e8e382b2fb6159c58c0f8725'])
shutil.copytree(os.path.join("resources", "fonts"), target_dir, dirs_exist_ok=True)

# 来源 3: Google Fonts（NotoNaskhArabic）
subprocess.call(['wget', '--quiet', '--output-document', target_file, ARABIC_URL])
```

### Git commit 锁定

两个仓库都检出到特定的 commit hash，而非分支或标签，确保字体文件的绝对不可变性。这对 SkParagraph 测试至关重要，因为不同版本的字体可能有微妙的度量差异。

### 文件清理

从 Skia 仓库复制字体后，删除测试不需要的文件：
- `abc/` - 非字体子目录
- `svg/` - SVG 相关文件
- `fonts.xml` - 字体配置文件（测试不需要）

### 阿拉伯语字体来源说明

脚本注释详细说明了 NotoNaskhArabic 字体的获取过程：
- 直接使用 Google Fonts gstatic CDN 链接（完整 `.ttf`，非子集化的 `.woff2`）
- 镜像到 `cdn.skia.org` 作为备份
- `.woff2` 版本被排除，因为它们是 Unicode 范围子集，不适合测试

### dirs_exist_ok 参数

`shutil.copytree` 使用 `dirs_exist_ok=True`（Python 3.8+），允许向已存在的目录中复制文件。两个来源的字体文件可能有重叠，后复制的文件会覆盖先前的同名文件。

## 依赖关系

### 外部工具

- `git`：克隆和检出仓库
- `wget`：下载字体文件
- `sha256sum`：文件完整性校验

### 网络依赖

- `https://github.com/Rusino/textlayout`：textlayout 字体仓库
- `https://skia.googlesource.com/skia/`：Skia 源码仓库
- `fonts.gstatic.com`：Google Fonts CDN
- `cdn.skia.org`：Skia CDN（备份镜像）

### 标准库

- `argparse`、`os`、`subprocess`、`tempfile`、`shutil`

## 设计模式与设计决策

### 精确版本锁定

每个字体来源都锁定到特定的 Git commit 或文件哈希。这种严格的版本控制是因为 SkParagraph 测试的度量值对字体的像素级变化敏感——即使是同一字体的不同版本也可能导致测试失败。

### 多源聚合

从三个不同来源收集字体到统一目录，实现了字体资源的集中管理。`textlayout` 仓库提供了专门的排版测试字体，Skia 仓库提供了通用测试字体，Google Fonts 提供了特定语言的字体。

### 详细的来源文档

脚本注释中详细记录了阿拉伯语字体 URL 的获取方式（通过 DevTools 监控 Google Fonts 下载行为），这种自文档化的做法有助于未来维护者理解和更新字体资源。

### 临时目录工作空间

使用 `tempfile.TemporaryDirectory()` 作为 Git 克隆的工作空间，确保中间文件在操作完成后自动清理。

## 性能考量

- **Git 克隆**：克隆整个 Skia 仓库可能较慢（仓库体积较大），但 `git clone` 默认只获取最新历史
- **两次 Git 操作**：可以考虑使用 `--depth 1` 浅克隆减少数据传输量
- **字体文件体积**：字体文件通常为几 MB 到几十 MB，复制操作较快
- **SHA256 校验**：单个字体文件的校验计算几乎瞬时完成
- **os.chdir 使用**：脚本多次使用 `os.chdir`，这会影响全局工作目录状态

## 相关文件

- `modules/skparagraph/tests/SkParagraphTests.cpp` - 使用这些字体的测试文件
- `resources/fonts/` - Skia 主仓库中的字体资源目录
- `infra/bots/assets/skparagraph/VERSION` - CIPD 资源版本号
