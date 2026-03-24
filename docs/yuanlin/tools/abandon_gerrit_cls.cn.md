# abandon_gerrit_cls - Gerrit CL 批量废弃工具

> 源文件: `tools/abandon_gerrit_cls.py`

## 概述

`abandon_gerrit_cls.py` 是一个 Python 辅助脚本,用于批量废弃 Gerrit 上的 CL(Change List)。它封装了 Go 语言实现的 `abandon_gerrit_cls` 工具,支持按最后修改时间过滤需要废弃的 CL。

## 架构位置

属于 Skia 工具链中的代码审查管理工具。

## 公共 API 函数

- **`run_abandon_cls(args)`**: 安装并运行 Go 实现的 abandon_gerrit_cls
- **`main()`**: 解析命令行参数并调用执行

## 内部实现细节

- 参数: `--gerrit-instance`(默认 skia-review)、`--abandon-reason`、`--last-modified-before-days`
- 通过 `go.mod_download()` 和 `go.install()` 安装 Go 工具

## 依赖关系

- Go 工具链, `infra/go` 模块中的 `abandon_gerrit_cls`

## 设计模式与设计决策

Python 封装 Go 工具,提供更友好的命令行接口。

## 性能考量

批量操作,性能取决于 CL 数量和 Gerrit API 响应速度。

## 相关文件

- `infra/` 目录下的 Go 基础设施代码
