# third_party/imgui - Dear ImGui 调试界面

## 概述

`third_party/imgui/` 包含 Dear ImGui 即时模式图形用户界面库的 Skia 构建配置。
ImGui 用于 Skia 的调试工具和 Viewer 应用中，提供交互式的参数调整和可视化界面。

## 目录结构

```
imgui/
└── BUILD.gn             # GN 构建配置
```

## 关键文件

- **BUILD.gn**: 配置 ImGui 的编译选项和 Skia 集成

## 依赖关系

- Dear ImGui 源码（通过 DEPS 拉取）

## 相关文档与参考

- Dear ImGui: https://github.com/ocornut/imgui
- Skia Viewer: `tools/viewer/`
