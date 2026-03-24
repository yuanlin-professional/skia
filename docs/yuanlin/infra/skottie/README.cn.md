# skottie - Skottie 应用 Docker 镜像

## 概述

`skottie/` 目录包含 Skia Skottie 应用 (skottie.skia.org) 的 Docker 镜像构建规则。Skottie 是一个在线 Lottie 动画播放和预览工具，使用 CanvasKit 在浏览器中渲染动画。

## 目录结构

```
skottie/
├── Dockerfile   # Docker 镜像定义
├── build.sh     # 构建脚本
└── README.md    # 原始说明文档
```

## 关键文件

### build.sh
构建脚本，将 CanvasKit WASM 构建产物插入中间 Docker 镜像。

## 部署流程

与其他 Web 应用相同的标准 Louhi 部署流程。

## 依赖关系

- CanvasKit WASM 构建产物
- [Skia 基础设施仓库 Skottie 构建](https://skia.googlesource.com/buildbot/+/refs/heads/main/skottie/BUILD.bazel)
- Louhi 部署系统

## 相关文档与参考

- [Skottie](https://skottie.skia.org/)
- [Skottie 模块文档](https://skia.org/docs/user/modules/skottie/)
