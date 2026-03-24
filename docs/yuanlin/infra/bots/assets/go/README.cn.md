# go - Go 语言工具链

## 概述

Go 编程语言工具链资源。Skia 的任务生成器和任务驱动程序使用 Go 编写。

## 目录结构

```
go/
├── asset.json  # 资源元数据
├── create.py   # 自动化创建脚本
└── VERSION     # 当前版本号
```

## 依赖关系

- 被所有 Go 语言相关任务使用
- 任务生成（`gen_tasks.go`）和任务驱动编译

## 相关文档与参考

- [Go 官方文档](https://go.dev/doc/)
- `go_win/` - Windows 版本
