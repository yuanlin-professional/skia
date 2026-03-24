# fiddler-backend - Fiddler 后端 Docker 镜像

## 概述

`fiddler-backend/` 目录包含 Skia Fiddler 后端服务的 Docker 镜像构建配置。Fiddler 是一个在线 Skia 代码编辑和执行工具，用户可以在浏览器中编写和运行 Skia C++ 代码片段。

## 目录结构

```
fiddler-backend/
├── Dockerfile              # Docker 镜像定义
├── create_docker_image.sh  # 镜像创建脚本
└── release_tag.sh          # 发布标签脚本
```

## 关键文件

### Dockerfile
基于 `fiddler-base` 基础镜像构建，主要步骤：
1. 从 Louhi 克隆的 Skia 源代码复制到容器
2. 使用 gclient 同步第三方依赖
3. 删除不需要的大型第三方目录（dawn、emsdk、icu4x 等）
4. 配置 GN 构建参数（使用 EGL、Clang、静态链接）
5. 编译 `fiddle` 目标
6. 清理 .git 目录以减小镜像体积

### 构建参数
关键的 GN 编译选项：
- `skia_use_egl = true` - 使用 EGL 图形接口
- `is_debug = false` - Release 模式
- `skia_enable_fontmgr_fontconfig = true` - 启用 Fontconfig 字体管理

## 依赖关系

- `fiddler-base` Docker 基础镜像
- Louhi 部署系统
- gclient 依赖同步

## 相关文档与参考

- [Skia Fiddler](https://fiddle.skia.org/)
- Skia 基础设施仓库中的 Fiddler 相关代码
