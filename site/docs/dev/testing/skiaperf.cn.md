
---
title: "Skia Perf"
linkTitle: "Skia Perf"

---


[Skia Perf](https://perf.skia.org) 是一个 Web 应用程序，用于分析和查看 Skia 测试基础设施产生的性能指标。

<img src=../Perf.png style="margin-left:30px" align="left" width="800"/> <br clear="left">

Skia 在大量平台和配置上进行测试，每次向 Skia 的提交都会生成超过 400,000 个单独的数值发送到 Perf，主要由性能基准测试结果组成，但也包括内存和覆盖率数据。

Perf 提供聚类 (clustering) 功能，这是一种从大量轨迹集合中挑选趋势和模式的工具。

<img src=../Cluster.png style="margin-left:30px" align="left" width="400"/> <br clear="left">

并且可以在这些趋势发现回归 (regression) 时生成警报：

<img src=../Regression.png style="margin-left:30px" align="left" width="800"/> <br clear="left">


## 计算

Skia Perf 能够对测试数据执行计算，允许你构建有趣的查询。

此查询显示 desk\_wowwiki.skp 的回放时间（毫秒）与操作数的比率：

    ratio(
      ave(fill(filter("name=desk_wowwiki.skp&sub_result=min_ms"))),
      ave(fill(filter("name=desk_wowwiki.skp&sub_result=ops")))
    )

你还可以使用数据来回答诸如每次提交运行了多少测试之类的问题。

    count(filter(""))

有关[可用函数的完整列表](https://perf.skia.org/help/)，请参阅 Skia Perf。
