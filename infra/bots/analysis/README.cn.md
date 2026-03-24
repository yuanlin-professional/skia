# 作业分析

一组分析 `jobs.json` 以查找我们测试中可能存在的空白的脚本。

## 要求

要运行这些脚本，你需要在机器上安装 `jq` 和 `mlr`。

    $ sudo apt install jq miller

## 运行

Makefile 包含可以针对数据运行的常用查询。

例如，要查找我们当前未运行性能测试 (Perf) 的所有 cpu_or_gpu_values，你可以运行：

    $ make missing_perf_jobs

更多关于可以对 CSV 文件进行的查询类型的详细信息，请参见 https://miller.readthedocs.io/en/latest/reference-dsl.html。
