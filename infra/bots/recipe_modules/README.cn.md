Skia 配方模块
===================

本目录包含供配方 (Recipe) 使用的配方模块 (Recipe Module)（参见 infra/bots/recipes）。它们都是 Skia 特有的，部分模块之间存在关联：

  * builder_name_schema - 帮助从任务（以前称为构建器）名称推导预期行为。
  * core - 作为大多数配方的起点：运行设置和同步步骤。
  * ct - 共享的集群遥测 (Cluster Telemetry) 工具。
  * flavor - 允许调用者指定要运行的高级命令，将平台特定的细节留给特定的 flavor 模块处理。
  * infra - 共享的基础设施相关工具。
  * run - 运行命令的工具。
  * swarming - 运行 Swarming 任务的工具。
  * vars - Skia 配方/模块使用的通用全局变量。

当你更改配方模块时，通常需要重新训练模拟测试：

	$ python infra/bots/infra_tests.py --train

或者：

	$ cd infra/bots; make train

每个配方模块包含以下几个文件：

  * api.py - 这是模块的核心内容。
  * \_\_init\_\_.py - 包含一个 DEPS 变量，指示此模块依赖的其他配方模块。
  * example.py - 可选文件，包含演示如何使用该模块的示例，并应包含足够的测试以实现模块 100% 的覆盖率。测试使用上述 recipes test 命令运行。
