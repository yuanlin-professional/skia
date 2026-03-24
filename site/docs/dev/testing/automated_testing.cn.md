
---
title: "Skia 自动化测试"
linkTitle: "Skia 自动化测试"

---


概述
--------

Skia 使用 [Swarming](https://github.com/luci/luci-py/blob/main/appengine/swarming/doc/Design.md)
来完成自动化测试的主要工作。它将任务分发出去——这些任务可能包括编译代码、运行测试或其他各种工作——分配给我们的机器人 (bots)，这些机器人是位于我们本地实验室、Chrome Infra 实验室或 GCE 中的虚拟或物理机器。

[Skia 任务调度器](http://go/skia-task-scheduler) 决定什么任务应该在什么机器人上、在什么时间运行。有关相对任务优先级如何确定的详细说明，请参阅该链接。一个*任务 (task)* 对应一个 Swarming 任务。一个*作业 (job)* 由一个或多个*任务*组成的有向无环图构成。当所有组成任务都成功完成时，作业即为完成；当任何组成任务失败时，作业即被视为失败。调度器可能会在其设定的限制内自动重试任务。作业不会被重试。多个作业可以共享同一个任务，例如，在两个不同 Android 设备上运行的测试使用相同的编译代码。

每个 Skia 仓库都有一个 `infra/bots/tasks.json` 文件，定义了该仓库的作业和任务。大多数作业会在每次提交时运行，但也可以指定每日和每周的作业。为方便起见，大多数仓库还有一个 `gen_tasks.go`，用于生成 `tasks.json`。你需要[安装 Go](https://golang.org/doc/install)。从仓库根目录执行：

	$ go run infra/bots/gen_tasks.go

每次修改 `gen_tasks.go` 或每次[资产](https://skia.googlesource.com/skia/+/main/infra/bots/assets/README.md)发生变更时，都需要运行 `gen_tasks.go`。还有一个测试模式，仅用于验证 `tasks.json` 文件是否为最新：

	$ go run infra/bots/gen_tasks.go --test



试用作业 (Try Jobs)
--------

Skia 的 trybots 允许在变更合入仓库之前对其进行测试和验证。你需要有触发试用作业的权限；如果你需要权限，请联系提交者。将你的 CL 上传到 [Gerrit](https://skia-review.googlesource.com/) 后，你可以为 `tasks.json` 中列出的任何作业触发试用作业，可以通过 Gerrit UI、使用 `git cl try`，例如：

    git cl try -B skia.primary -b Some-Tryjob-Name

或使用 `bin/try`，这是 `git cl try` 的一个小型封装工具，有助于选择试用作业。从 Skia 检出目录执行：

    bin/try --list

你也可以使用正则表达式搜索：

    bin/try "Test.*Pixel.*Release"


状态视图 (Status View)
------------

状态视图显示一个表格，X 轴是按测试类型和平台分组的任务，Y 轴是提交记录。单元格根据每次提交的任务状态着色：

* 绿色：成功
* 橙色：失败
* 紫色：故障（基础设施问题）
* 黑色边框，无填充：任务进行中
* 空白：给定版本尚未开始任何任务

提交按作者列出，提交所在的分支显示在最左侧。紫色结果会覆盖橙色结果。

要查看更多详情，你可以点击单个单元格以获取任务摘要。你也可以点击每列顶部的白色条来查看同名近期任务的摘要。

状态页面有几个过滤器，可用于仅显示任务规格的子集：

* 有趣的 (Interesting)：在可见提交窗口内同时有成功和失败的任务规格。
* 失败 (Failures)：在可见提交窗口内有失败的任务规格。
* 评论 (Comments)：有评论的任务规格。
* 无评论的失败 (Failing w/o comment)：在可见提交窗口内有失败但没有评论的任务规格。
* 全部 (All)：显示所有任务。
* 搜索 (Search)：输入搜索字符串。可以使用子字符串和正则表达式，遵循 Javascript String Match() 规则：
  http://www.w3schools.com/jsref/jsref_match.asp

<a name="adding-new-jobs"></a>
添加新作业
---------------

如果你想添加作业来构建或测试新配置，请提交一个[新机器人请求][new bot request]。

如果你知道新作业需要新硬件，或者你不确定哪些现有机器人应该运行新作业，请分配给 jcgregorio。一旦 Infra 团队分配了硬件，我们会分配回给你来完成流程。

通常可以复制一个现有作业并进行修改来实现你的目标。你需要将新作业添加到 [infra/bots/jobs.json][jobs json]。在某些情况下，你需要修改配方 (recipes)：

* 如果有新的 GN 标志或编译器选项：
  [infra/bots/recipe_modules/build][build recipe module]，通常是 default.py。
* 如果有 dm 标志的修改：[infra/bots/recipes/test.py][test py]
* 如果有 nanobench 标志的修改：
  [infra/bots/recipes/perf.py][perf py]

修改以上任何文件后，在 infra/bots 目录中运行 `make train` 来更新生成的文件。上传 CL，然后运行 `git cl try -B skia.primary -b <job name>` 来运行新作业。（提交后，新作业将在 Housekeeper-Nightly-UpdateMetaConfig 任务的下一次成功运行后出现在 PolyGerrit UI 中。）

[new bot request]:
    https://bugs.chromium.org/p/skia/issues/entry?template=New+Bot+Request
[jobs json]: https://skia.googlesource.com/skia/+/main/infra/bots/jobs.json
[build recipe module]:
    https://skia.googlesource.com/skia/+/refs/heads/main/infra/bots/recipe_modules/build/
[test py]:
    https://skia.googlesource.com/skia/+/main/infra/bots/recipes/test.py
[perf py]:
    https://skia.googlesource.com/skia/+/main/infra/bots/recipes/perf.py


Skia 任务详情
--------------------

[infra/bots/gen_tasks.go][gen_tasks] 读取配置文件：

* [infra/bots/jobs.json][jobs json]
* [infra/bots/cfg.json][cfg json]
* [infra/bots/recipe_modules/builder_name_schema/builder_name_schema.json][builder_name_schema]

根据 jobs.json 中的每个作业名称，gen_tasks 决定生成哪些任务（process 函数）。各种辅助函数返回作业直接依赖的任务名称。

在 gen_tasks 中，任务用 TaskSpec 指定。TaskSpec 指定了如何生成和触发 Swarming 任务。

大多数 Skia 任务使用 Kitchen 运行配方。kitchenTask 函数的参数指定了将运行配方的 TaskSpec 的最常见参数。有关配方的更多信息，请参阅 [infra/bots/recipes/README.md][recipes README] 和 [infra/bots/recipe_modules/README.md][recipe_modules README]。

Swarming 任务根据 TaskSpec 的多个参数生成：

* Isolate：指定隔离文件。隔离文件指定了在运行任务之前放置在机器人上的仓库文件。（对于非 Kitchen 任务，隔离文件还指定要运行的命令。）[更多信息][isolate user guide]。
* Command：要运行的命令，如果未在 Isolate 中指定。（通常这是一个运行配方的样板 Kitchen 命令；见下文。）
* CipdPackages：指定将在运行任务之前放置在机器人上的 CIPD 包的 ID。更多信息请参阅 infra/bots/assets/README.md。
* Dependencies：指定此任务所依赖的其他任务的名称。这些任务的输出将在运行此任务之前放置在机器人上。
* Dimensions：指定哪种机器人应该运行此任务。请向 Infra 团队咨询如何设置。
* ExecutionTimeout：任务被终止之前允许运行的总时间。
* IoTimeout：任务在没有向 stdout/stderr 输出任何内容的情况下可以运行的时间，超过后将被终止。
* Expiration：大多数情况下会被忽略。如果任务恰好在没有可以运行它的机器人时被调度，它将在此时间内保持待处理状态，然后被取消。

如果你需要做更复杂的事情，或者你不确定如何添加和配置新作业，请向 borenet@、rmistry@ 或 jcgregorio@ 寻求帮助。

[gen_tasks]:
	https://skia.googlesource.com/skia/+/main/infra/bots/gen_tasks.go
[cfg json]:
	https://skia.googlesource.com/skia/+/main/infra/bots/cfg.json
[builder_name_schema]:
	https://skia.googlesource.com/skia/+/main/infra/bots/recipe_modules/builder_name_schema/builder_name_schema.json
[recipes README]:
    https://skia.googlesource.com/skia/+/main/infra/bots/recipes/README.md
[recipe_modules README]:
    https://skia.googlesource.com/skia/+/main/infra/bots/recipe_modules/README.md
[isolate user guide]:
    https://chromium.googlesource.com/infra/luci/luci-py/+/main/appengine/isolate/doc/client/Isolate-User-Guide.md
