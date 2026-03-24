# debugger-app - 调试器应用 Docker 镜像

## 概述

`debugger-app/` 目录包含 Skia 调试器应用 (debugger.skia.org) 的 Docker 镜像构建规则。调试器允许用户在浏览器中加载和逐步调试 SKP（Skia Picture）文件。

## 目录结构

```
debugger-app/
├── Dockerfile   # Docker 镜像定义
├── build.sh     # 构建脚本
└── README.md    # 原始说明文档
```

## 关键文件

### build.sh
构建脚本，将 CanvasKit WASM 构建产物插入中间 Docker 镜像。

## 部署流程

1. Skia 基础设施仓库创建中间 Docker 镜像
2. 本目录将 CanvasKit 构建产物插入中间镜像
3. 最终镜像上传到 Artifact Registry
4. 通过 Louhi 部署到 debugger.skia.org

## 依赖关系

- CanvasKit WASM 构建产物
- [Skia 基础设施仓库 Debugger 构建](https://skia.googlesource.com/buildbot/+/refs/heads/main/debugger-app/BUILD.bazel)
- Louhi 部署系统

## 相关文档与参考

- [Skia Debugger](https://debugger.skia.org/)
