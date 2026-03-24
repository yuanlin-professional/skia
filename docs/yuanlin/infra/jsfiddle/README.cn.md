# jsfiddle - JSFiddle Docker 镜像

## 概述

`jsfiddle/` 目录包含 Skia JSFiddle (jsfiddle.skia.org) 的 Docker 镜像构建规则。JSFiddle 允许用户在浏览器中使用 CanvasKit（WebAssembly 版 Skia）编写和运行 JavaScript 代码。

## 目录结构

```
jsfiddle/
├── Dockerfile   # Docker 镜像定义
├── build.sh     # 构建脚本
└── README.md    # 原始说明文档
```

## 关键文件

### build.sh
构建脚本，将 Skia 构建产物（CanvasKit WASM 模块）插入中间 Docker 镜像。

### Dockerfile
定义最终的 Docker 镜像，包含 CanvasKit 和 JSFiddle Web 应用。

## 部署流程

1. 在 Skia 基础设施仓库中创建中间 Docker 镜像
2. 本目录的构建规则将 CanvasKit 构建产物插入中间镜像
3. 最终镜像上传到 Artifact Registry
4. 通过 Louhi 部署到 skia.org

## 依赖关系

- CanvasKit WASM 构建产物
- Skia 基础设施仓库中的 JSFiddle 中间镜像
- Louhi 部署系统
- Artifact Registry

## 相关文档与参考

- [Skia JSFiddle](https://jsfiddle.skia.org/)
- [Skia 基础设施仓库 JSFiddle 构建](https://skia.googlesource.com/buildbot/+/refs/heads/main/jsfiddle/BUILD.bazel)
