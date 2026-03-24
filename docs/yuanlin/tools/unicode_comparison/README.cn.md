# Skia Unicode 比较工具

## 概述

`tools/unicode_comparison` 提供了一套用于比较不同 Unicode 处理实现（如 ICU、SkUnicode 等）行为差异的工具集。该模块包含 C++ 桥接代码、Go 语言实用程序和 HTML 展示层，能够下载多语言 Wikipedia 文本数据、提取 Unicode 处理信息，并生成可视化的比较表格。

## 目录结构

```
tools/unicode_comparison/
├── README.md              # 英文使用说明
├── cpp/
│   ├── bridge.h           # C++ 到 Go 的桥接头文件
│   └── bridge.cpp         # 桥接实现，调用 SkUnicode API
├── go/
│   ├── Makefile           # Go 工具构建和运行配置
│   ├── bridge/
│   │   └── bridge.go      # Go 端的 C++ 桥接封装
│   ├── download_wiki/
│   │   └── main.go        # Wikipedia 文本下载工具
│   ├── extract_info/
│   │   └── main.go        # Unicode 信息提取工具
│   ├── generate_table/
│   │   └── main.go        # 比较表格生成工具（约 21KB，最大文件）
│   └── helpers/
│       └── helpers.go     # 通用辅助函数
└── html/
    ├── index.html         # 比较结果展示主页
    ├── styles.html        # CSS 样式定义
    ├── scripts.html       # JavaScript 交互逻辑
    └── tbody.html         # 表格内容模板
```

## 核心组件

### C++ 桥接层（cpp/）

提供 SkUnicode 到 Go 的桥接接口：

**bridge.h / bridge.cpp：**
- 封装 Skia 的 SkUnicode API 调用
- 提供 C 兼容的函数接口，供 Go 通过 cgo 调用
- 实现文本分段（segmentation）、行断（line break）等 Unicode 操作

### Go 工具链（go/）

#### download_wiki（Wikipedia 下载器）

```bash
make download_wiki
./download_wiki
```

- 从 Wikipedia API 下载多语言文章文本
- 支持多种语言的 Wikipedia（参见 List_of_Wikipedias）
- 输出纯文本数据用于后续 Unicode 分析
- 可能需要更新 go-wiki 包：`go get -u github.com/trietmn/go-wiki`

#### extract_info（信息提取器）

```bash
make extract_info
./extract_info
```

- 从下载的文本中提取 Unicode 处理信息
- 分析文本的字符属性、断行点、字形边界等
- 生成中间数据文件供比较使用

#### generate_table（表格生成器）

```bash
make generate_table
./generate_table
```

- 对比不同 Unicode 实现的处理结果
- 生成 HTML 格式的比较表格
- 高亮显示不同实现之间的差异
- 这是最大的文件（约 21KB），包含详细的比较逻辑

#### bridge（Go 桥接）

- 使用 cgo 调用 C++ bridge 代码
- 封装 SkUnicode 的 Go 语言接口

#### helpers（辅助函数）

- 通用文件操作、字符串处理等辅助功能

### HTML 展示层（html/）

基于 Web 的比较结果可视化：

- **index.html**: 主页面，组合其他 HTML 片段
- **styles.html**: 表格和页面样式
- **scripts.html**: 交互功能（排序、过滤、高亮差异）
- **tbody.html**: 动态生成的表格内容

## 使用方法

### 完整工作流

```bash
cd tools/unicode_comparison/go

# 1. 下载 Wikipedia 测试数据
make download_wiki

# 2. 提取 Unicode 处理信息
make extract_info

# 3. 生成比较表格
make generate_table

# 4. 在浏览器中查看结果
open ../html/index.html
```

### 使用 Makefile

```bash
cd tools/unicode_comparison/go
make all    # 执行完整流程
```

## 比较维度

该工具可以比较以下 Unicode 处理操作的实现差异：

| 操作 | 说明 |
|------|------|
| 文本分段 | 字符、单词、句子的边界检测 |
| 行断机会 | 文本换行的合法断行位置 |
| 双向文本 | BiDi 算法的方向分析结果 |
| 字符属性 | Unicode 字符分类和属性查询 |

## 与其他模块的关系

- **modules/skunicode/**: SkUnicode 抽象层
- **third_party/icu/**: ICU Unicode 库
- **src/base/SkUTF.h**: Skia 的 UTF 编码工具
- **modules/skshaper/**: 文本整形引擎（依赖 Unicode 处理）
