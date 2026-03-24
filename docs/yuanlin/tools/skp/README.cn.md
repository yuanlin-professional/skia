# Skia SKP 工具

## 概述

`tools/skp` 提供了 SKP（Skia Picture）文件的网页录制和管理工具。该模块的核心功能是使用 Chromium 浏览器录制真实网页的渲染操作为 SKP 文件，这些 SKP 文件随后可用于性能基准测试、视觉回归测试和渲染正确性验证。模块包含一个自动化录制脚本和大量网页页面集（Page Sets）定义。

## 目录结构

```
tools/skp/
├── webpages_playback.py         # 网页录制和回放主脚本
├── generate_page_set.py         # 页面集定义生成工具
├── page_set_template            # 页面集 Python 模板文件
├── page_sets/                   # 页面集定义目录
│   ├── __init__.py              # Python 包初始化
│   ├── skia_amazon_mobile.py    # Amazon 移动版
│   ├── skia_baidu_mobile.py     # 百度移动版
│   ├── skia_cnn_desktop.py      # CNN 桌面版
│   ├── skia_facebook_desktop.py # Facebook 桌面版
│   ├── skia_google*.py          # Google 系列页面
│   ├── skia_wikipedia_*.py      # Wikipedia 页面
│   ├── skia_youtube_*.py        # YouTube 页面
│   ├── ... (共 50+ 页面集)
│   ├── data/
│   │   └── README               # 数据文件说明
│   └── other/                   # 非活跃页面集
│       ├── CRASHING-*.json      # 已知崩溃的页面
│       ├── DOWN-*.json          # 已下线的页面
│       ├── LAYERS-*.json        # 层相关问题的页面
│       ├── OLD-*.json           # 旧版页面集
│       └── POPUP-*.json         # 弹窗问题的页面
```

## 核心组件

### webpages_playback.py

网页录制和 SKP 生成的主脚本，支持两种操作模式：

**录制模式（Archive）：**

```bash
cd skia
python tools/skp/webpages_playback.py \
  --data_store=gs://your-bucket-name \
  --record \
  --page_sets=all \
  --skia_tools=/path/to/out/Debug/ \
  --browser_executable=/path/to/chrome
```

**回放模式（Replay）：**

```bash
python tools/skp/webpages_playback.py \
  --data_store=gs://your-bucket-name \
  --page_sets=all \
  --skia_tools=/path/to/out/Debug/ \
  --browser_executable=/path/to/chrome
```

**主要参数：**

| 参数 | 说明 |
|------|------|
| `--data_store` | 数据存储位置（gs:// 或本地路径） |
| `--record` | 启用录制模式（归档网页） |
| `--page_sets` | 选择页面集（默认 all） |
| `--skia_tools` | Skia 工具二进制目录 |
| `--browser_executable` | Chrome 浏览器路径 |
| `--upload` | 是否上传生成的结果 |
| `--non-interactive` | 非交互模式（CI 使用） |

### 页面集（Page Sets）

每个页面集文件定义一个网页的录制配置：

- **桌面版页面**: `*_desktop.py` - 全尺寸桌面浏览器
- **移动版页面**: `*_mobile.py` - 模拟移动设备视口
- **平板版页面**: `*_tablet.py` - 模拟平板设备视口

**覆盖的网站类别：**

| 类别 | 示例网站 |
|------|---------|
| 搜索引擎 | Google、百度 |
| 社交媒体 | Facebook、Twitter、Reddit |
| 新闻媒体 | CNN、NYTimes、ESPN |
| 视频平台 | YouTube |
| 科技网站 | TechCrunch、The Verge、SlashDot |
| 百科全书 | Wikipedia（多语言） |
| 电商平台 | Amazon、eBay |
| SVG 测试 | 各类 SVG 复杂图形 |
| 性能测试 | MotionMark 测试套件 |

### generate_page_set.py

根据模板自动生成新的页面集定义文件：

```bash
python tools/skp/generate_page_set.py \
  --url "https://example.com" \
  --name "example_desktop" \
  --type desktop
```

### other/ 目录

存放非活跃的页面集，按问题类型分类：

- **CRASHING-**: 会导致浏览器或 Skia 崩溃
- **DOWN-**: 网站已下线或 URL 失效
- **LAYERS-**: 存在层（Layer）相关渲染问题
- **OLD-**: 已被新版本替代的旧配置
- **POPUP-**: 存在弹窗干扰录制

## 工作流程

```
1. 选择页面集（page_sets）
2. 使用 Chrome 浏览器访问指定网页
3. 录制浏览器的渲染操作为 SKP 文件
4. （可选）上传到 Google Cloud Storage
5. 后续工具可下载 SKP 用于基准测试和回归测试
```

## 与其他模块的关系

- **tools/skpbench/**: 使用本模块生成的 SKP 文件进行 Android GPU 性能测试
- **tools/skdiff/**: 比较不同版本生成的 SKP 渲染结果
- **tools/debugger/**: 调试器可加载 SKP 文件进行逐步调试
- **dm**: DM 测试工具使用 SKP 进行回放正确性测试
- **bench/**: nanobench 使用 SKP 进行性能基准测试
