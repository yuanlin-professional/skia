# bazel_build.py - GN-Bazel 构建桥接脚本

> 源文件: `gn/bazel_build.py`

## 概述

`bazel_build.py` 是 Skia 构建系统中的一个 Python 桥接脚本，使 GN 构建系统能够调用 Bazel 构建特定的目标，并将 Bazel 生成的输出文件复制到 GN 期望的输出目录中。这实现了 GN 和 Bazel 两种构建系统的互操作。

该脚本主要用于 Skia 从 GN 向 Bazel 迁移过程中的混合构建场景。某些组件（如 Rust FFI 绑定）可能由 Bazel 构建，而主构建系统仍使用 GN，本脚本负责协调两者。

## 架构位置

```
Skia 混合构建系统
├── gn/
│   ├── bazel_build.py    <-- 本文件：GN-Bazel 桥接脚本
│   └── BUILD.gn 文件     <-- GN 构建定义（调用此脚本的 action）
├── BUILD.bazel           <-- Bazel 构建定义
├── bazel-bin/            <-- Bazel 输出目录
└── out/                  <-- GN 输出目录
```

## 主要类与结构体

无。此脚本是纯过程式的命令行工具。

## 公共 API 函数

脚本通过命令行参数调用：

```
python bazel_build.py <targets_and_args_and_outputs...>
```

参数分为三类（通过前缀区分）：
1. **Bazel 目标**（以 `//` 或 `@` 开头）：要构建的 Bazel 目标
2. **Bazel 参数**（以 `--` 开头）：传递给 `bazelisk build` 的额外参数
3. **输出文件**（其他）：需要从 Bazel 输出目录复制到 GN 输出目录的文件

输出文件支持两种格式：
- `bazel-bin/path/to/file`：复制到 GN 输出目录的根目录
- `bazel-bin/path/to/file=dest/path`：复制到指定的目标路径

## 内部实现细节

### 参数解析

```python
targets = []
outputs = {}
bazel_args = []
for arg in sys.argv[1:]:
    if arg.startswith("//") or arg.startswith("@"):
        targets.append(arg)
    elif arg.startswith("--"):
        bazel_args.append(arg)
    else:
        if "=" in arg:
            bazel_file, output_path = arg.split("=")
            outputs[bazel_file] = output_path
        else:
            outputs[arg] = os.path.basename(arg)
```

通过前缀启发式分类参数，无需显式的参数分隔符。

### Bazel 构建调用

```python
subprocess.run(["bazelisk", "build"] + targets + bazel_args, check=True)
```

使用 `bazelisk`（Bazel 版本管理器）而非直接调用 `bazel`，确保使用正确的 Bazel 版本。所有目标在单次 Bazel 调用中构建。

### 智能文件复制

```python
if not os.path.exists(expected_output):
    shutil.copyfile(bazel_file, expected_output)
    os.chmod(expected_output, 0o755)
else:
    created_hash = hashlib.sha256(open(bazel_file, 'rb').read()).hexdigest()
    existing_hash = hashlib.sha256(open(expected_output, 'rb').read()).hexdigest()
    if created_hash != existing_hash:
        os.remove(expected_output)
        shutil.copyfile(bazel_file, expected_output)
        os.chmod(expected_output, 0o755)
```

关键优化：如果目标文件已存在且内容相同（通过 SHA-256 哈希比较），则跳过复制。这是因为 GN 使用文件时间戳判断是否需要重新构建，不必要的文件覆盖会导致时间戳更新，触发下游目标的不必要重建。

## 依赖关系

- **Python 标准库**：`hashlib`, `os`, `shutil`, `subprocess`, `sys`
- **外部工具**：`bazelisk`（Bazel 版本管理器，需要在 PATH 中）

## 设计模式与设计决策

1. **桥接模式（Bridge Pattern）**：脚本作为 GN 和 Bazel 两个构建系统之间的桥梁，将 GN 的构建请求转换为 Bazel 构建调用，并将结果映射回 GN 的文件系统布局。

2. **内容寻址复制**：通过 SHA-256 哈希比较避免不必要的文件覆盖，防止 GN 的时间戳机制触发不必要的重建。这是一个关键的性能优化。

3. **单次 Bazel 调用**：所有目标在一次 `bazelisk build` 调用中构建，利用 Bazel 的并行构建能力，避免多次 Bazel 启动的开销。

4. **灵活的输出映射**：支持通过 `=` 指定源和目标的路径映射，或使用默认的基础名称映射，适应不同的目录结构需求。

5. **可执行权限**：复制后的文件被设置为 `0o755` 权限，确保可执行文件可以直接运行。

## 性能考量

- **SHA-256 增量检查**：对已存在的文件进行哈希比较而非无条件覆盖，显著减少了 GN 的不必要重建。这对于大型项目的增量构建尤为重要。
- **单次 Bazel 调用**：Bazel 的启动成本较高（加载工作区、分析阶段等），合并所有目标到一次调用中可以节省数秒的启动时间。
- **Bazelisk 代理**：使用 `bazelisk` 而非直接 `bazel`，会增加一次版本检查的开销，但确保了构建的可重现性。
- **文件 I/O**：对于大文件，SHA-256 哈希计算可能有一定开销，但通常比不必要的 Ninja 重建要快得多。

## 相关文件

- `BUILD.bazel` - Skia 根目录的 Bazel 构建定义
- `.bazelrc` - Bazel 配置文件
- `.bazelversion` - 指定 Bazel 版本
- `gn/BUILD.gn` - 可能包含调用此脚本的 GN action
