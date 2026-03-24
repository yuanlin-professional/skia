
---
title: "GPU 园丁文档"
linkTitle: "GPU Gardener Documentation"

---


### 目录 ###

*   [GPU 园丁 (Gardener) 做什么？](#what_is_a_gpu_gardener)
*   [跟踪 GPU 园丁工作](#tracking)
*   [查看当前和即将到来的轮值](#view_current_upcoming_rotations)
*   [如何交换轮值班次](#how_to_swap)
*   [GPU 园丁小贴士](#tips)


<a name="what_is_a_gpu_gardener"></a>
GPU 园丁做什么？
----------------------------

GPU 园丁有三项主要工作：

1) 及时处理来自各个 bug 跟踪系统中客户提交的 GPU 相关 bug。这意味着对有明确负责人的 bug 进行分类和指派，以及对没有负责人的 bug 进行调查并可能修复。同时还要对 Skia [状态页面](https://status.skia.org/)上显示的 "OSS-Fuzz" 未分类 bug 进行分类。如有需要，请向[此处](https://github.com/google/oss-fuzz/blob/master/projects/skia/project.yaml)列出的 Skia 成员申请 oss-fuzz bug 的查看权限。


2) 提高 GPU 机器人的可靠性。这包括处理不稳定的图片、崩溃的机器人等。我们总是有处理不完的机器或驱动程序相关问题。我们经常将它们搁置一旁以便有时间做"真正的工作"。当你是园丁时，这就是"真正的工作"。


3) 改进我们的工具。这包括编写新工具和改进现有的测试工具。预期成果包括更快的机器人运行时间、更准确的测试、更快速的测试、呈现新的有用数据以及提高可调试性。


GPU 园丁应该始终优先处理新进来的 bug。园丁剩余的时间应该根据自己的判断在第 2) 项和第 3) 项之间分配。期望园丁在轮值周内尽可能暂停日常工作，专注于园丁任务。在园丁周期间深入研究园丁职责的某一特定方面并尽可能推进是可以的（也是鼓励的），同时要保持对新进 bug 的关注。

请注意，GPU 园丁的工作不包括花费大量时间对图片进行分类、为失败的机器人提交 bug 或监督 DEPS 滚动。当你轮值为通用 Skia 园丁时会有机会做这些。

<a name="tracking"></a>
跟踪 GPU 园丁工作
--------------------------
除了 bug 报告之外，GPU 园丁应该跟踪自己的进展，以便未来的园丁可以在周末时接手任何未完成的工作。

此外，每当园丁弄清楚如何完成某项园丁任务（例如运行一组文档不够完善的 Chromium 测试，或使用巧妙的 OpenGL 技巧来调试棘手的问题）时，应该更新此文档的小贴士部分以帮助未来的园丁。


<a name="view_current_upcoming_rotations"></a>
查看当前和即将到来的轮值
-----------------------------------

GPU 园丁列表在[此处](https://rotations.corp.google.com/rotation/6176639586140160)指定。
[状态页面](https://status.skia.org)上的园丁小部件也会显示当前的园丁。


<a name="how_to_swap"></a>
如何交换轮值班次
---------------------------

如果你需要与他人交换班次（因为生病或休假），请获得你希望交换的人的同意，然后直接通过[轮值页面](https://rotations.corp.google.com/rotation/6176639586140160)进行交换。


<a name="tips"></a>
GPU 园丁小贴士
----------------------

请参见[此文档](https://docs.google.com/a/google.com/document/d/1Q1A5T5js4MdqvD0EKjCgNbUBJfRBMPKR3OZAkc-2Tvc/edit?usp=sharing)。
