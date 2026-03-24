# analysis - 作业分析工具

## 概述

`analysis/` 目录包含一组用于分析 `jobs.json` 的脚本，帮助发现 Skia CI 测试覆盖中可能存在的空白区域。通过对作业列表进行多维度查询，可以识别缺失的测试配置。

## 目录结构

```
analysis/
├── README.md          # 原始说明文档
├── Makefile           # 常用查询命令
├── axis.sh            # 提取作业名称中的维度轴
├── create-alljobs.sh  # 从 jobs.json 创建分析数据
└── missing.sh         # 查找缺失的测试配置
```

## 关键文件

### Makefile

包含常用查询命令，例如：
- `make missing_perf_jobs` - 查找当前未运行 Perf 测试的 cpu_or_gpu 值

### axis.sh

从作业名称中提取维度轴信息，用于多维度分析。

### create-alljobs.sh

将 `jobs.json` 转换为便于分析的 CSV 格式数据。

### missing.sh

通过对比现有作业覆盖范围，查找可能缺失的测试配置组合。

## 前置要求

运行分析脚本需要安装以下工具：
- `jq` - JSON 命令行处理器
- `mlr`（Miller）- CSV/JSON 数据处理工具

```bash
sudo apt install jq miller
```

## 依赖关系

- `infra/bots/jobs.json` - 作业列表数据源
- 外部工具：`jq`、`mlr`

## 相关文档与参考

- [Miller 文档](https://miller.readthedocs.io/en/latest/reference-dsl.html)
- 父目录中关于 `jobs.json` 的说明
