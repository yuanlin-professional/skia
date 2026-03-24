---
title: '正确性测试 (Correctness Testing)'
linkTitle: '正确性测试 (Correctness Testing)'
---

Skia 正确性测试主要由名为 DM 的工具提供支持。这是构建和运行 DM 的快速入门指南。

<!--?prettify lang=sh?-->

    python3 tools/git-sync-deps
    bin/gn gen out/Debug
    ninja -C out/Debug dm
    out/Debug/dm -v -w dm_output

运行时，你可能会注意到 CPU 使用率在一段时间内达到 100%，然后在运行结束时逐渐降低到 1 或 2 个活跃核心。这是有意为之的。DM 是高度多线程的，但某些工作，特别是 GPU 支持的工作，仍然被迫在单线程上运行。如果你愿意，可以使用 `--threads N` 将 DM 限制为 N 个线程。这在 CPU 相对于 RAM 更充裕的机器上有时会很有帮助。

DM 运行时，你应该会看到大量类似这样的输出。

```
Skipping nonrendering: Don't understand 'nonrendering'.
Skipping angle: Don't understand 'angle'.
Skipping nvprmsaa4: Could not create a surface.
492 srcs * 3 sinks + 382 tests == 1858 tasks

(  25MB  1857) 1.36ms   8888 image mandrill_132x132_12x12.astc-5-subsets
(  25MB  1856) 1.41ms   8888 image mandrill_132x132_6x6.astc-5-subsets
(  25MB  1855) 1.35ms   8888 image mandrill_132x130_6x5.astc-5-subsets
(  25MB  1854) 1.41ms   8888 image mandrill_132x130_12x10.astc-5-subsets
(  25MB  1853) 151µs    8888 image mandrill_130x132_10x6.astc-5-subsets
(  25MB  1852) 154µs    8888 image mandrill_130x130_5x5.astc-5-subsets
                                  ...
( 748MB     5) 9.43ms   unit test GLInterfaceValidation
( 748MB     4) 30.3ms   unit test HalfFloatTextureTest
( 748MB     3) 31.2ms   unit test FloatingPointTextureTest
( 748MB     2) 32.9ms   unit test DeferredCanvas_GPU
( 748MB     1) 49.4ms   unit test ClipCache
( 748MB     0) 37.2ms   unit test Blur
```

不要惊慌。

随着你对 DM 越来越熟悉，这些输出可能会有点烦人。如果从命令行中移除 -v，DM 将在单行上旋转进度，而不是为每个状态更新打印新行。

不必担心启动时的 "Skipping something: Here's why." 行。DM 支持许多测试配置，并非所有配置都适用于所有机器。这些行只是一种提示，主要是为了以防 DM 无法运行你可能期望的某些配置。

也不用担心 "skps: Couldn't read skps." 消息，默认情况下你不会有这些文件，没有它们也可以。如果你希望同时使用它们进行测试，可以单独下载。

下一行是 DM 即将执行的工作概览。

```
492 srcs * 3 sinks + 382 tests == 1858 tasks
```

DM 找到了 382 个单元测试（从 tests/ 链接的代码）和 492 个其他绘制源。这些绘制源可能是 GM 集成测试（从 gm/ 链接的代码）、图像文件（来自 `--images`，默认为 "resources"）或 .skp 文件（来自 `--skps`，默认为 "skps"）。你可以使用 `--src`（默认值为 "tests gm image skp"）控制 DM 将使用的源类型。

DM 找到了 3 种可用的方式来绘制这 492 个源。这由 `--config` 控制。默认值取决于操作系统。在 Linux 上，默认值为 "8888 gl nonrendering"。DM 跳过了 nonrendering，留下两个可用配置：8888 和 gl。这两个名称代表使用 Skia 绘制的不同方式：

- 8888：使用软件后端绘制到 32 位 RGBA 位图中
- gl：使用 OpenGL 后端 (Ganesh) 绘制到 32 位 RGBA 位图中

有时 DM 将这些称为配置 (configs)，有时称为接收器 (sinks)。抱歉。有许多可能的配置，但通常我们最关注 8888 和 gl。

DM 总是尝试将所有源绘制到所有接收器中，这就是为什么我们将 492 乘以 3。单元测试并不真正适合这种源-接收器模型，所以它们独立存在。几千个任务是相当正常的。让我们看一下其中一个任务的状态行。

```
(  25MB  1857) 1.36ms   8888 image mandrill_132x132_12x12.astc-5-subsets
   [1]   [2]   [3]      [4]
```

这个状态行告诉我们几件事。

1. DM 曾使用的最大内存量为 25MB。注意这是高水位线，不是当前内存使用量。这主要用于我们在构建机器人上跟踪，其中一些机器人运行时接近系统内存限制。

2. 未完成任务的数量，在本例中有 1857 个，正在运行或等待运行。我们通常每个可用硬件线程运行一个任务，所以在典型的笔记本电脑上可能同时运行 4 或 8 个。有时计数似乎乱序出现，特别是在 DM 启动时；这是无害的，不会影响运行的正确性。

3. 接下来，我们看到此任务花费了 1.36 毫秒运行。通常，此计时器的精度约为 1 微秒。时间纯粹是出于信息目的，便于我们找到慢速测试。

4. 我们运行的测试的配置和名称。我们将测试 "mandrill_132x132_12x12.astc-5-subsets"（一个 "image" 源）绘制到 "8888" 接收器中。

当 DM 完成运行时，你应该能找到一个包含名为 `dm.json` 的文件的目录，以及一些嵌套目录，其中充满了大量图像。

```
$ ls dm_output
8888    dm.json gl

$ find dm_output -name '*.png'
dm_output/8888/gm/3x3bitmaprect.png
dm_output/8888/gm/aaclip.png
dm_output/8888/gm/aarectmodes.png
dm_output/8888/gm/alphagradients.png
dm_output/8888/gm/arcofzorro.png
dm_output/8888/gm/arithmode.png
dm_output/8888/gm/astcbitmap.png
dm_output/8888/gm/bezier_conic_effects.png
dm_output/8888/gm/bezier_cubic_effects.png
dm_output/8888/gm/bezier_quad_effects.png
                ...
```

目录首先按接收器类型（`--config`）嵌套，然后按源类型（`--src`）嵌套。我们刚看的任务 "8888 image mandrill_132x132_12x12.astc-5-subsets" 的图像可以在 `dm_output/8888/image/mandrill_132x132_12x12.astc-5-subsets.png` 找到。

`dm.json` 被我们的自动化测试系统使用，如果你愿意可以忽略它。它包含每个运行测试的列表以及该运行生成的图像的校验和。

### 详情 <a name="digests"></a>

无聊的技术细节：校验和不是 .png 文件的校验和，而是用于创建该 .png 的原始像素的校验和。这意味着两个不同的配置可能产生完全相同的 .png，但它们的校验和不同。

单元测试通过时通常不会输出任何内容，只有状态更新。如果测试失败，DM 将打印出其断言失败信息，在发生时打印一次，然后在所有任务运行完毕后再次汇总打印。这些失败信息也包含在 `dm.json` 文件中。

DM 有一个简单的功能来与之前运行的结果进行比较：

<!--?prettify lang=sh?-->

    ninja -C out/Debug dm
    out/Debug/dm -w good

    # 做一些工作

    ninja -C out/Debug dm
    out/Debug/dm -r good -w bad

使用 `-r` 时，DM 将对任何未产生与 `good` 运行相同图像的测试显示失败。

对于更高级的用法，我建议使用 skdiff：

<!--?prettify lang=sh?-->

    ninja -C out/Debug dm
    out/Debug/dm -w good

    # 做一些工作

    ninja -C out/Debug dm
    out/Debug/dm -w bad

    ninja -C out/Debug skdiff
    mkdir diff
    out/Debug/skdiff good bad diff

    # 在你的 Web 浏览器中打开 diff/index.html

以上是 DM 的基础知识。DM 支持许多其他模式和标志。以下是一些你可能会觉得有用的示例。

<!--?prettify lang=sh?-->

    out/Debug/dm --help        # 打印所有标志、它们的默认值和每个标志的简要说明。
    out/Debug/dm --src tests   # 仅运行单元测试。
    out/Debug/dm --nocpu       # 仅测试 GPU 支持的工作。
    out/Debug/dm --nogpu       # 仅测试 CPU 支持的工作。
    out/Debug/dm --match blur  # 仅运行名称中包含 "blur" 的工作。
    out/Debug/dm --dryRun      # 不实际执行任何操作，只打印我们会做什么。
