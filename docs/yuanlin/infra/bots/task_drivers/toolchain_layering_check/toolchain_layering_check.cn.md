# toolchain_layering_check - 工具链分层检查任务驱动

> 源文件: `infra/bots/task_drivers/toolchain_layering_check/toolchain_layering_check.go`

## 概述

`toolchain_layering_check` 验证 Skia 自定义 Bazel 工具链的 `layering_check` 功能是否正常工作。它首先构建一个目标以确认正常构建成功,然后依次添加不同的非法 include 定义并验证构建确实失败,从而确保头文件依赖分层规则被正确执行。

## 架构位置

属于 Skia CI 的构建验证子系统,确保 Bazel 构建的头文件包含规则正确阻止了非法的传递依赖和私有头文件访问。

## 主要类与结构体

无自定义结构体。使用 `common.BazelFlags` 进行 Bazel 标志管理。

## 公共 API 函数

- **`main()`**: 解析标志、验证正常构建成功、验证非法 include 导致构建失败
- **`bazelBuild()`**: 使用 bazelisk 执行构建
- **`expectFailure()`**: 添加 define 后构建并期望失败,如果未失败则报错

## 内部实现细节

验证以下四种非法 include 场景:
1. `HEADER_INCLUDES_TRANSITIVE_HEADER` - 头文件包含传递依赖的头文件
2. `HEADER_INCLUDES_PRIVATE_HEADER` - 头文件包含私有头文件
3. `SOURCE_INCLUDES_TRANSITIVE_HEADER` - 源文件包含传递依赖的头文件
4. `SOURCE_INCLUDES_PRIVATE_HEADER` - 源文件包含私有头文件

通过 `--copt=-D<DEFINE>=1` 传递编译选项激活测试代码中的非法 include。

## 依赖关系

- `go.skia.org/skia/infra/bots/task_drivers/common` - Bazel 公共工具
- `go.skia.org/infra/task_driver/go/lib/bazel` - Bazel 配置
- Bazelisk - Bazel 版本管理

## 设计模式与设计决策

- **正反验证**: 先验证正常构建成功,再验证非法操作失败,确保测试的有效性
- **条件编译**: 通过 C 预处理器 define 控制测试代码中的非法 include 是否激活

## 性能考量

构建后执行 `BazelCleanIfLowDiskSpace` 在磁盘空间不足时清理 Bazel 缓存。

## 相关文件

- `infra/bots/task_drivers/common/bazel_clean_step.go` - Bazel 缓存清理
- `infra/bots/task_drivers/common/bazel_flags.go` - Bazel 标志定义
