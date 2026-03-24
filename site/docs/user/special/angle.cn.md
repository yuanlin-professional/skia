
---
title: "ANGLE"
linkTitle: "ANGLE"

---


简介
------------

ANGLE 将 OpenGL ES 2 或 3 调用转换为 DirectX 9、11 或 OpenGL 调用。本文档
说明如何在 Windows 或 Linux 上使用 ANGLE 代替原生 OpenGL 后端。

详细信息
-------

`gclient sync` 会下载 ANGLE 的源代码以及 Skia 的其他仅测试依赖项。

要针对 ANGLE 构建 Skia 测试工具，在你的
`args.gn` 文件中添加 `skia_use_angle = true`（或运行 `gn args` 编辑它）。

运行工具时，使用 `--config angle_<backend>_<frontend>`，例如

    out/Debug/dm --src gm --config angle_d3d11_es2
    out/Release/nanobench --config angle_gl_es2

