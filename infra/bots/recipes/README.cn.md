Skia 配方
============

这些是在 Swarming 任务中运行的顶层脚本，用于执行 Skia 的所有自动化测试。

在本地运行配方 (Recipe)：

	$ python infra/bots/recipes.py run --workdir=/tmp/<workdir> <recipe name without .py> key1=value1 key2=value2 ...

每个配方可能有自己的必需属性，必须作为命令中的键/值对输入。

当你更改配方时，通常需要重新训练模拟测试：

	$ python infra/bots/recipes.py test train

或者：

        $ cd infra/bots; make train

测试为每个配方中包含的测试生成期望文件，这些文件说明在给定特定输入集的情况下将运行哪些步骤。在进行更改时，请注意这些文件中的差异，以确保你的更改产生了预期的效果。
