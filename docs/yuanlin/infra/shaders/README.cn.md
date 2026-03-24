# shaders - Shaders 应用 Docker 镜像

## 概述

`shaders/` 目录包含 Skia Shaders 应用 (shaders.skia.org) 的 Docker 镜像构建规则。Shaders 应用允许用户在浏览器中编写和预览 SkSL（Skia Shading Language）着色器代码。

## 目录结构

```
shaders/
├── Dockerfile   # Docker 镜像定义
├── build.sh     # 构建脚本
└── README.md    # 原始说明文档
```

## 关键文件

### build.sh
构建脚本，将 CanvasKit WASM 构建产物插入 Skia 基础设施仓库中创建的中间 Docker 镜像。

## 部署流程

1. Skia 基础设施仓库创建中间 Docker 镜像
2. 本目录将 CanvasKit 构建产物插入中间镜像
3. 最终镜像上传到 Artifact Registry
4. 通过 Louhi 部署到 shaders.skia.org

## 依赖关系

- CanvasKit WASM 构建产物
- [Skia 基础设施仓库 Shaders 构建](https://skia.googlesource.com/buildbot/+/refs/heads/main/shaders/BUILD.bazel)
- Louhi 部署系统

## 相关文档与参考

- [Skia Shaders](https://shaders.skia.org/)
