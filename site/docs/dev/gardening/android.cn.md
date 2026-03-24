---
title: 'Android 园丁文档'
linkTitle: 'Android Gardener Documentation'
---

### 目录

- [Android 园丁 (Gardener) 做什么？](#what_is_a_android_gardener)
- [Android 自动滚动器](#autoroller_doc)
- [查看当前和即将到来的轮值](#view_current_upcoming_rotations)
- [如何交换轮值班次](#how_to_swap)

<a name="what_is_a_android_gardener"></a> Android 园丁做什么？

---

Android 园丁有两项主要工作：

1. 监控并批准从 Skia 代码库到 Android 源代码树的半自动
   [git 合并](https://googleplex-android-review.git.corp.google.com/#/q/owner:31977622648%2540project.gserviceaccount.com+status:open)。有关如何与自动滚动器交互的详细信息，请参见<a href="#autoroller_doc">此处</a>的自动滚动器文档。

2. 及时处理两个 bug 跟踪系统中与 Android 相关的 bug：
   [Skia](https://bugs.chromium.org/p/skia/issues/list?can=2&q=OpSys%3DAndroid&sort=-id&colspec=ID+Type+Status+Priority+Owner+Summary&cells=tiles)
   和
   [Android](https://buganizer.corp.google.com/issues?q=assignee:skia-android-triage%20status:open)。对于 Skia 的 bug，这意味着对所有当前未分配的 Android bug 进行分类和指派。对于 Android 的 bug，这意味着遵循
   [Android 指南](http://go/android-buganizer) 验证所有 Skia bug 都已经过 TL 分类（如果没有，请联系 djsollen@）。

Android 园丁的工作不包括处理 Perf 和 Gold 中的问题。当你轮值为通用 Skia 园丁时会有机会处理这些问题。

<a name="autoroller_doc"></a> Android 自动滚动器

---

Android 主分支的自动滚动器运行在
[https://skia-autoroll.corp.goog/r/android-master-autoroll](https://skia-autoroll.corp.goog/r/android-master-autoroll)，仅限 Google 员工访问。<br/> 自动滚动器的状态显示在 Skia 的[状态页面](https://status.skia.org/)上。

你可以通过界面将自动滚动器切换到试运行 (dry run) 模式。处于试运行模式时，上传的更改不会自动提交。

你也可以通过界面停止自动滚动器。这在需要调查故障且你不想通过运行不必要的测试浪费 TH 资源时非常有用。

如果自动滚动器在界面中显示错误，请在其
[云日志](https://pantheon.corp.google.com/logs/viewer?project=google.com:skia-buildbots&resource=logging_log%2Fname%2Fandroid-master-autoroll&logName=projects%2Fgoogle.com:skia-buildbots%2Flogs%2Fautoroll)中查找更多详细信息。

如果你需要关于自动滚动器的更多信息，请查看
[skbug.com/40036716](https://bugs.chromium.org/p/skia/issues/detail?id=5538) 或联系
rmistry@ / skiabot@。

我们还有用于发布分支的自动滚动器（同样仅限 Google 员工访问）：

- [https://android-o-roll.skia.org](https://android-o-roll.skia.org)
  （[云日志](https://pantheon.corp.google.com/logs/viewer?project=google.com:skia-buildbots&resource=logging_log%2Fname%2Fandroid-o-autoroll&logName=projects%2Fgoogle.com:skia-buildbots%2Flogs%2Fautoroll)）。

这些滚动器创建的更改需要手动批准。<br/> 发布滚动器创建的更改：

- 包含所有合并更改的作者，以便他们可以关注滚动进度。
- 提取所有形如 'BUG=b/123' 或 'Bug: b/456' 的 buganizer bug，并在合并更改中创建一行 'Bug: 123, 456'。
- 收集所有 'Test: ' 行并将其带入合并更改中。

<a name="view_current_upcoming_rotations"></a> 查看当前和即将到来的轮值

---

Android 园丁列表在[此处](https://rotations.corp.google.com/rotation/5296436538245120)指定。[状态页面](https://status.skia.org)上的园丁小部件也会显示当前的园丁。

<a name="how_to_swap"></a> 如何交换轮值班次

---

如果你需要与他人交换班次（因为生病或休假），请获得你希望交换的人的同意，然后直接通过[轮值页面](https://rotations.corp.google.com/rotation/5296436538245120)进行交换。
