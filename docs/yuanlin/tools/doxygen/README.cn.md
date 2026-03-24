# Skia Doxygen 文档生成工具

## 概述

`tools/doxygen` 包含 Skia 使用 Doxygen 自动生成 API 文档所需的配置文件和资源。Doxygen 是业界标准的 C++ 文档生成工具，能从源码注释中提取 API 文档并生成 HTML 格式的参考手册。该目录提供了完整的 Doxygen 配置，包括自定义样式表、页脚模板和主页内容。

## 目录结构

```
tools/doxygen/
├── README.md              # 英文使用说明
├── Doxyfile               # 完整 Doxygen 配置文件（约 109KB）
├── ProdDoxyfile           # 生产环境精简配置
├── customdoxygen.css      # 自定义 CSS 样式表
├── footer.html            # HTML 页脚模板
├── logo.png               # Skia 标志图片
└── mainpage/
    └── mainpage.dox       # 文档主页内容定义
```

## 配置文件说明

### Doxyfile

Doxygen 的主配置文件，定义了文档生成的所有参数：

- **输入源**: 扫描 `include/` 和 `src/` 目录的源文件
- **输出位置**: 生成结果写入 `/tmp/doxygen`
- **文件过滤**: 处理 `.h`、`.cpp` 等 C++ 源文件
- **交叉引用**: 启用类继承图、调用关系图等
- **外观定制**: 使用自定义 CSS 和页脚模板

### ProdDoxyfile

生产环境的精简配置，包含 Doxyfile 并覆盖特定设置，用于 CI/CD 环境中的自动化文档生成。

### customdoxygen.css

自定义样式表，调整 Doxygen 默认主题以匹配 Skia 项目的视觉风格，包括：

- 页面布局和导航栏样式
- 代码高亮配色
- 类图和关系图的显示样式

### mainpage/mainpage.dox

定义文档首页内容，通常包含：

- 项目简介
- 快速入门指南
- 模块概览和导航链接

## 使用方法

### 生成文档

```bash
# 在 tools/doxygen 目录下运行
cd tools/doxygen
doxygen Doxyfile
```

### 查看文档

```bash
# 启动本地 HTTP 服务器
cd /tmp/doxygen/html
python3 -m http.server 8000

# 在浏览器中访问
# http://localhost:8000
```

### 实时监控更新

使用 `entr` 工具在文件保存时自动重新生成文档：

```bash
cd tools/doxygen
find ../../include/ ../../src/ . | entr doxygen ./Doxyfile
```

### 安装 Doxygen

```bash
# Linux (Debian/Ubuntu)
sudo apt install doxygen

# macOS
brew install doxygen
```

## 生成内容

Doxygen 会生成以下内容：

- **类参考**: 每个类的详细 API 文档
- **命名空间**: 按命名空间组织的 API 索引
- **文件列表**: 源文件和头文件的文档
- **继承关系图**: 类的继承层次可视化
- **调用图**: 函数调用关系图（如果启用 Graphviz）

## 与其他模块的关系

- **include/**: Doxygen 扫描的主要头文件目录
- **src/**: Doxygen 扫描的实现文件目录
- **site/**: Skia 网站文档（手工编写的指南和教程）
