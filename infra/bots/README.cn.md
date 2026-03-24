Skia 基础设施
===================

本目录包含基础设施 (Infrastructure) 相关元素。


任务与作业
--------------

本目录中的文件定义了一个在每次 Skia 提交时运行的任务有向无环图 (DAG)。任务是一个小型、独立的单元，通过 Swarming 在机器池中的机器上运行。任务可以链接在一起，例如一个任务编译测试二进制文件，另一个任务实际运行它们。

作业 (Job) 是相关任务的集合，有助于定义 DAG 的子部分，例如用作试运行作业 (Try Job)。每个作业被定义为 DAG 的一个入口点。

本目录中的 tasks.json 文件是仓库的任务和作业列表。请注意，tasks.json 从不手动编辑，而是通过 gen_task.go 和下面列举的输入文件生成的。[任务调度器 (Task Scheduler)](https://skia.googlesource.com/buildbot/+/main/task_scheduler/README.md) 在每次提交时读取 tasks.json 文件以确定要运行哪些作业。为方便起见，提供了 gen_tasks.go 来生成 tasks.json，同时也用于测试其语法正确性、检测循环和孤立任务。请始终编辑 gen_tasks.go 或以下输入 JSON 文件之一，而不是直接编辑 tasks.json：

  * cfg.json - gen_tasks.go 的基本配置信息。
  * jobs.json - 所有要运行的作业列表。编辑此文件以添加或移除机器人 (Bot)。

每当 gen_tasks.go、上述任何 JSON 文件或资产 (Asset) 发生更改时，你需要运行 gen_tasks.go 来重新生成 tasks.json：

	$ go run infra/bots/gen_tasks.go

或者：

	$ make -C infra/bots train

还有一个测试模式，用于执行一致性检查并验证 tasks.json 未被更改：

	$ go run infra/bots/gen_tasks.go --test

或者：

	$ make -C infra/bots test


添加新作业后，你可能想在合入更改之前测试它是否能成功运行。然而，由添加新作业的代码更改所产生的 Gerrit CL 不会自动运行它。它也不会在 Gerrit 界面的可用试运行作业列表中出现。

为了在合入更改之前触发它运行，你可以使用 SK 命令行工具。更多信息请参阅 [SK CLI 工具文档](https://chromium.googlesource.com/skia/+/HEAD/site/docs/dev/tools/sk.md)。

如果你还没有从 skia 目录获取它，可以运行以下命令：

	$ ./bin/fetch-sk

要启动作业，你必须登录 luci-auth。

	$ luci-auth login

然后你可以使用 `sk try` 来发起此更改的作业：

	$ ./bin/sk try [name of job]

例如，如果你想运行 "Test-Mac14-Clang-MacMini9.1-GPU-AppleM1-arm64-Debug-All"，命令将是：

	$ ./bin/sk try Test-Mac14-Clang-MacMini9.1-GPU-AppleM1-arm64-Debug-All

此更改的 Gerrit 审查页面界面现在应该会显示作业的状态。

配方
-------

配方 (Recipe) 是 Skia 基础设施用于在 Swarming 任务中执行工作的框架。主要元素包括：

  * recipes.py - 用于运行和测试配方。
  * recipes - 这些是每种任务类型的入口点，例如编译或运行测试。
  * recipe_modules - 配方使用的共享模块。
  * .recipe_deps - 配方和模块可以依赖其他仓库的模块。recipes.py 脚本会在此目录中自动同步这些依赖项。


隔离文件
-------------

这些文件决定了当 Swarming 任务被触发时，仓库的哪些部分会被传输到机器人。[隔离工具 (Isolate Tool)](https://github.com/luci/luci-py/tree/main/appengine/isolate/doc) 对每个文件进行哈希处理，并将上传任何新的/更改过的文件。机器人维护一个缓存，以便它们可以高效地只下载它们没有的文件。


资产
------

基础设施使用的工件 (Artifact) 在此进行版本管理，同时提供了重新创建/上传/下载它们的脚本。更多信息请参阅该目录中的 README。每当机器人使用的资产发生更改时，你需要重新运行 gen_tasks.go。


工具
-----

其他各类基础设施相关工具，例如 isolate 和 CIPD 二进制文件。


CT
--

用于在集群遥测 (Cluster Telemetry) 中运行 Skia 任务的辅助工具。
