---
title: "使用 pprof 对 Skia 进行性能分析"
linkTitle: "性能分析 (Profiling)"

---

Skia 二进制文件（如 `nanobench` 和 `dm`）可以被检测以生成与 [pprof](https://github.com/google/pprof) 可视化工具兼容的 [CPU](https://github.com/gperftools/gperftools/blob/07c5e9226bda1720bdf783a11f5df0f515e3c9d3/docs/cpuprofile.adoc) 和 [堆 (Heap) 性能分析](https://github.com/gperftools/gperftools/blob/07c5e9226bda1720bdf783a11f5df0f515e3c9d3/docs/tcmalloc.adoc)数据。

<img src=../pprof_webview.png width=846 height=176 alt="A pprof weblist showing lines of code and time spent on each line." />

前提条件
-------------

### 安装性能分析器
安装 gperftool 头文件（用于编译）和共享库（用于链接）。这包括 `libprofiler.so`（用于 CPU）和 `libtcmalloc.so`（用于堆）。

    # 在 Debian/Ubuntu 上：
    $ sudo apt-get install libgoogle-perftools-dev


### 安装可视化工具
Google 员工已经有 `pprof` 分析工具，但外部用户可以执行以下操作来安装 `google-pprof`（可能还需要创建别名将其称为 `pprof`）。

    # 在 Debian/Ubuntu 上：
    $ sudo apt-get install google-perftools

术语
-----------

分析性能数据时，你会看到两个主要指标：

*   **扁平 (Flat)**：**严格在**该特定函数内花费的时间（或内存）。较高的扁平时间表示该函数自身逻辑中存在瓶颈（例如，一个耗时的循环）。
*   **累积 (Cumulative)**：在该函数*加上它调用的所有函数*中花费的总时间（或分配的内存）。累积时间高但扁平时间低表示瓶颈在该函数的某个子函数中。

使用性能分析支持进行构建
-------------------------------

要启用性能分析检测，在你的 `args.gn` 中设置 `skia_use_pprof=true`。使用 `-Og` 可能有助于在不牺牲优化性能优势的情况下获得准确的行级归因。

    # out/Profile 中的 args.gn 示例
    is_debug = false
    skia_use_pprof = true
    extra_cflags = ["-Og"]

然后构建你的目标：

    $ ninja -C out/Profile nanobench

这会链接 CPU 检测器（它会反复暂停程序并记录程序运行的位置，将样本聚合到性能数据中）和堆检测器（跟踪所有分配和释放）。

在 Nanobench 中创建性能分析数据
------------------------------

使用 `skia_use_pprof` 构建时，`nanobench` 提供了启用分析器以产生输出的标志。

## CPU 性能分析

使用 `--cpuprofile` 标志指定输出文件名。通常增加运行持续时间以获取更多样本会很有用。

    $ ./out/Profile/nanobench --match <bench_name> --cpuprofile <output.prof> --ms 1000

## 堆性能分析

使用 `--memprofile` 标志指定输出前缀。堆分析器将在程序运行期间和结束时生成快照。

    $ ./out/Profile/nanobench --match <bench_name> --memprofile <output.heap>
    ...
    Dumping heap profile to output.heap.0001.heap
    ...
    Dumping heap profile to output.heap.0002.heap

分析
--------

使用 `pprof` 工具可视化结果。

## Web 界面

### 图形视图（使用 GraphViz）

CPU 图形显示每个函数在调用栈上花费的时间。这有助于识别潜在的瓶颈。

<img src=../pprof_cpu_web.png width=500 height=600 alt="A graphviz graph showing time spent in different functions." />

    $ pprof -web ./out/Profile/nanobench <output.prof>

alloc_space 堆图显示整个运行过程中每个函数在堆上分配了多少内存（即使内存已被释放）。这可以识别多余的内存分配位置。

<img src=../pprof_mem_web.png width=500 height=400 alt="A graphviz graph showing allocations from different functions." />

    $ pprof -alloc_space -web ./out/Profile/nanobench output.heap.0005.heap

不使用 `-alloc_space` 时，只会显示存活字节（未释放的内存）。你可以使用任何堆文件，但查看最新的文件可能最有用。


### 带注释的源代码

`pprof` 可以显示每行代码花费了多少时间，甚至可以分解汇编指令。由于指令重排序，这并不完美（请参阅下面的提示）。大量堆分配也可能混淆性能归因。

<img src=../pprof_cpu_weblist.png width=565 height=293 alt="A pprof weblist showing lines of code and time spent on each line. One line is expanded to show the assembly instructions" />

    $ pprof -weblist <function> ./out/Profile/nanobench <output.prof>
    # 选择你想要放大查看的函数。你可以不提供函数名（或函数正则表达式）
    # 来运行命令，但这会非常嘈杂。

`-weblist` 对堆性能数据的工作方式类似。通过使用 `-alloc_space`，你将看到给定行分配了多少总内存。

<img src=../pprof_mem_weblist.png width=794 height=1083 alt="A pprof weblist showing total allocations on a few of the lines in a function." />

    $ pprof -alloc_space -weblist <function> ./out/Profile/nanobench output.heap.0005.heap

### 火焰图 (Flame Graphs)

作为 Web 图形的替代视图，可以显示火焰图。Google 员工可以将其创建并上传到[内部工具](http://pprof/?id=aaaf3cb7d1c0c1f3dc033d5068d06e29)（更方便与同事/bug 共享）。

<img src=../pprof_cpu_flame.png width=951 height=308 alt="A flame graph showing which functions the CPU spent the most time with." />

    $ pprof -flame ./out/Profile/nanobench <output.prof>
    $ pprof -alloc_space -flame ./out/Profile/nanobench output.heap.0005.heap

## 命令行

如果你不想使用 Web UI，可以直接在终端进行快速分析。

### 顶部函数
查看"扁平"时间花费最多的地方。

    `$ pprof -top ./out/Profile/nanobench <output.prof>`

查看哪些函数负责最多的内存分配（总计）。

    $ pprof -alloc_space -top ./out/Profile/nanobench output.heap.0005.heap

查看哪些函数分配了最多的*对象*（而非字节）。

    $ pprof -alloc_objects -top ./out/Profile/nanobench output.heap.0005.heap

### 带注释的源代码
打印特定函数的带注释源代码。

    $ pprof -list <function_name> ./out/Profile/nanobench <output.prof>
    $ pprof -alloc_space -list <function_name> ./out/Profile/nanobench output.heap.0005.heap
    $ pprof -alloc_objects -list <function_name> ./out/Profile/nanobench output.heap.0005.heap

## 比较性能数据（差异比较）

比较两个性能数据文件是验证优化或查找内存泄漏的最佳方式。有关更多信息，请参阅[官方文档](https://github.com/google/pprof/blob/a15ffb7f9dccb95074ad153aef0f1fcbb01e61e3/doc/README.md#comparing-profiles)。

提示
----

*   **指令漂移 (Instruction Drifting)**：如果样本出现在错误的行上（例如，一个不应该花费时间的 `if` 语句），这可能是由于编译器重排序指令导致的。使用 `-Og` 可以最小化此问题。
