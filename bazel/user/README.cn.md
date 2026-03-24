如果你希望定义自定义 Bazel 配置（例如自定义构建），请在此文件夹中创建一个名为 buildrc 的文本文件。该文件应遵循 [.bazelrc 约定](https://bazel.build/docs/bazelrc#config)。

用户可以像往常一样将自定义构建放在 $HOME/.bazelrc 文件中，但如果希望避免与其他 Bazel 项目发生冲突，这里是一个更安全的存储位置。
