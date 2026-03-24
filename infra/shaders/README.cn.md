本目录包含为托管在 shaders.skia.org 的 Skia 着色器 (Shader) 创建最终 Docker 镜像的构建规则。

此构建规则将必要的 Skia 工件 (Artifact)（CanvasKit）插入到在 Skia 基础设施仓库中创建的中间 Docker 镜像中，该中间镜像位于 https://skia.googlesource.com/buildbot/+/refs/heads/main/shaders/BUILD.bazel。
最终的 Docker 镜像随后被上传到 Artifact Registry，并使用 Louhi 部署到 skia.org。