# Compile CAS - 编译任务 CAS 规格生成

> 源文件: `infra/bots/gen_tasks_logic/compile_cas.go`

## 概述

`compile_cas.go` 负责生成编译任务所需的 CAS（Content Addressable Storage）规格。它通过分析 Git 仓库中的源文件，构建一个优化的文件路径树，自动合并包含过多子项的目录，生成简洁高效的 CasSpec。

## 架构位置

位于 `infra/bots/gen_tasks_logic/` 包中，被 `GenTasks` 调用以生成 `CAS_COMPILE` 规格。该规格定义了编译任务需要从 CAS 下载的源文件集合。

## 主要类与结构体

- **`node`**: 目录树节点
  - `children map[string]*node`: 子节点映射
  - `name string`: 节点名称
  - `isLeaf bool`: 是否为叶节点（显式包含的路径）
- **`tree`**: 目录树
  - `root *node`: 根节点

## 公共 API 函数

- **`generateCompileCAS(b, cfg)`**: 生成编译 CAS 规格并注册

## 内部实现细节

1. **路径收集** (`getRelevantPaths`):
   - 通过 `git ls-files` 获取所有版本控制文件
   - 使用正则匹配编译相关文件: `.c`, `.cc`, `.cpp`, `.gn`, `.gni`, `.h`, `.mm`, `.storyboard`
   - 追加显式路径: `.bazelrc`, `BUILD.bazel`, `DEPS`, `bin/*`, `resources`, `third_party/externals` 等
2. **路径合并** (`combinePathsThreshold = 3`):
   - 当一个目录直接包含 3 个以上叶节点时，将目录本身提升为叶节点
   - 递归应用，产生更简洁的 CAS 规格
3. **树结构**:
   - `add`: 递归插入路径组件，自动合并超过阈值的目录
   - `entries`: 递归提取所有叶路径，添加 "skia/" 前缀
4. **最终规格**: Root="..", Excludes=git 目录

## 依赖关系

- `go.skia.org/infra/go/cas/rbe`: RBE 排除模式
- `go.skia.org/infra/task_scheduler/go/specs`: CasSpec 定义
- 标准库: `log`, `os/exec`, `path/filepath`, `regexp`, `sort`, `strings`
- 外部工具: `git` (用于 ls-files)

## 设计模式与设计决策

- 树压缩算法: 自动合并高密度目录，减少 CasSpec 条目数量
- 白名单方式: 显式列出需要的文件模式和路径，而非排除不需要的
- `combinePathsThreshold` 阈值可调：目前为 3，平衡细粒度和简洁性
- 根节点特殊处理：根节点不参与合并决策

## 性能考量

- CAS 规格的优化直接影响编译任务的启动时间（下载文件数量和大小）
- 路径合并减少了 CasSpec 的条目数，降低了 CAS 查询复杂度
- `git ls-files` 比文件系统遍历更快，且只包含版本控制的文件

## 相关文件

- `infra/bots/gen_tasks_logic/gen_tasks_logic.go`: 调用 generateCompileCAS
- `infra/bots/gen_tasks_logic/task_builder.go`: 使用 CAS_COMPILE 规格
