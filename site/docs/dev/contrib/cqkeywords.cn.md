
---
title: "提交队列关键字"
linkTitle: "Commit Queue Keywords"

---


有关更多信息，请参阅 [CQ 文档](https://chromium.googlesource.com/chromium/src/+/main/docs/infra/cq.md)。

"Key: Value" 形式的选项必须出现在提交消息 (Commit Message) 的最后一段中才能生效。


Commit
------

如果您正在进行实验性代码工作，不想冒意外通过 CQ 提交更改的风险，可以将其标记为 "Commit: false"。如果包含此选项，CQ 将立即放弃该更改。要通过 CQ 进行试运行 (Dry Run)，请使用 Gerrit 的 [CQ 试运行](https://groups.google.com/a/chromium.org/forum/#!topic/chromium-dev/G5-X0_tfmok)功能。

    Commit: false

CQ 将运行其验证器列表（审查者检查、试运行机器人、代码树检查、预提交检查），然后关闭该问题而不是提交它。


No-Dependency-Checks
--------------------

    No-Dependency-Checks: true

CQ 会拒绝具有未关闭依赖的补丁集 (Patchset)。当一个 CL 依赖于另一个尚未关闭的 CL 时，就存在未关闭的依赖。您可以使用此关键字跳过此检查。


Cq-Include-Trybots
------------------

允许您向 CQ 的默认试运行机器人 (Trybot) 列表中添加任意试运行机器人。CQ 将阻塞直到这些试运行作业通过，就像默认的试运行作业列表一样。

此关键字的值的格式为：

    Cq-Include-Trybots: bucket1:bot1,bot2;bucket2:bot3,bot4

允许多行：

    Cq-Include-Trybots: bucket1:bot1
    Cq-Include-Trybots: bucket1:bot2
    Cq-Include-Trybots: bucket2:bot3
    Cq-Include-Trybots: bucket2:bot4

以下是一些实际示例：

    Cq-Include-Trybots: master.tryserver.chromium.linux:linux_chromium_asan_rel_ng
    Cq-Include-Trybots: skia.primary:Test-Mac12-Clang-MacBookPro16.2-GPU-IntelIrisPlus-x86_64-Debug-All-ANGLE
    Cq-Include-Trybots: luci.skia.skia.primary:Build-Debian9-Clang-x86-devrel-Android_SKQP

    FIXME: what bucket are skia bots in now?


No-Tree-Checks
--------------

如果您想跳过代码树状态检查，使 CQ 在代码树关闭时仍然提交 CL，可以在 CL 描述中添加以下行：

    No-Tree-Checks: true

不建议这样做，因为代码树关闭是有原因的。但在极少数情况下这是可以接受的，主要用于修复构建失败（即您的 CL 将有助于重新打开代码树）。


No-Presubmit
------------

如果您想跳过预提交检查 (Presubmit Check)，请在 CL 描述中添加以下行：

    No-Presubmit: true


No-Try
------

如果您等不及试运行作业的结果，可以在 CL 描述中添加以下行：

    No-Try: true

CQ 将不会为您的更改运行任何试运行作业，并且会在代码树打开后立即提交 CL，前提是预提交检查通过。
