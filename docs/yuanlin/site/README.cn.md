# site/ - Skia 官方网站源码

## 概述

`site/` 包含 Skia 官方文档网站（skia.org）的源码。网站使用 Hugo 静态网站
生成器和 Docsy 主题构建，提供 Skia 的用户指南、开发者文档、博客等内容。

## 目录结构

```
site/
├── config.toml              # Hugo 站点配置
├── _index.html              # 首页
├── featured-background.png  # 首页背景图
├── search.md                # 搜索页面
├── about/                   # 关于页面
│   ├── _index.md            # 关于 Skia
│   ├── roles.md             # 角色说明
│   └── user/                # 用户相关
├── blog/                    # 博客
│   ├── _index.md            # 博客首页
│   └── news/                # 新闻文章
└── docs/                    # 文档
    ├── _index.md            # 文档首页
    ├── dev/                 # 开发者文档
    └── user/                # 用户文档
```

## 关键文件

### config.toml
Hugo 站点配置，定义了：
- 站点基础信息（标题："Skia"，描述："2D Graphics Library"）
- 主题：Docsy
- Google Analytics ID
- 代码高亮样式（Tango）
- 导航栏和页脚配置
- Mermaid 图表支持

## 构建方式

```bash
# 安装 Hugo（需要 extended 版本）
# 安装 Docsy 主题依赖
cd site
hugo server  # 本地预览
hugo         # 生成静态文件
```

## 依赖关系

- Hugo 静态网站生成器（extended 版本）
- Docsy 主题
- Node.js（Docsy 依赖）

## 相关文档与参考

- Skia 官网: https://skia.org/
- Hugo 文档: https://gohugo.io/
- Docsy 主题: https://www.docsy.dev/
