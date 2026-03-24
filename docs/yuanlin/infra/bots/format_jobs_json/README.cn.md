# format_jobs_json - jobs.json 格式化工具

## 概述

`format_jobs_json/` 目录包含一个 Go 程序，用于对 `jobs.json` 文件进行标准化格式化，确保作业列表的一致性和可读性。

## 目录结构

```
format_jobs_json/
└── format_jobs_json.go   # 格式化工具主程序
```

## 关键文件

### format_jobs_json.go

读取 `jobs.json` 文件并以标准格式重新写入，确保：
- JSON 格式的一致性
- 作业名称的排序
- 缩进和空白的标准化

## 使用方法

```bash
go run infra/bots/format_jobs_json/format_jobs_json.go
```

## 依赖关系

- `infra/bots/jobs.json` - 被格式化的目标文件

## 相关文档与参考

- 父目录中关于 `jobs.json` 的说明
