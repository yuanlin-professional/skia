# tools - 基础设施工具

## 概述

`tools/` 目录包含 Skia CI 系统所需的基础设施工具二进制文件，主要是 LUCI-Go 工具集在各平台上的预编译版本。

## 目录结构

```
tools/
└── luci-go/
    ├── win64/     # Windows 64位 LUCI-Go 二进制
    ├── mac64/     # macOS 64位 LUCI-Go 二进制
    └── linux64/   # Linux 64位 LUCI-Go 二进制
```

## 关键文件

### luci-go/

包含 LUCI-Go 工具集的平台特定二进制文件。这些工具用于：
- 与 Swarming 任务调度系统交互
- CAS（Content Addressable Storage）操作
- CIPD（Chrome Infrastructure Package Deployment）包管理
- 其他 LUCI 基础设施操作

每个平台子目录（`win64/`、`mac64/`、`linux64/`）包含对应平台的可执行文件。

## 依赖关系

- LUCI 基础设施系统
- 被 `gen_tasks_logic/` 和任务执行流程引用

## 相关文档与参考

- [LUCI-Go 项目](https://chromium.googlesource.com/infra/luci/luci-go/)
