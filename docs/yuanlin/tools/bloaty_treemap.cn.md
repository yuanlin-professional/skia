# bloaty_treemap - Bloaty 输出树状图可视化

> 源文件: `tools/bloaty_treemap.py`

## 概述

`bloaty_treemap.py` 将 Bloaty 的 TSV 输出转换为交互式 HTML 树状图。使用 Google Charts 的 TreeMap 组件,以文件路径为层次结构、以符号体积为大小进行可视化。通过管道从 stdin 读取 Bloaty 输出。

## 架构位置

属于 Skia 工具链中的构建分析可视化工具。

## 公共 API 函数

- **`main()`**: 生成完整的 HTML 文件(含 Google Charts JavaScript)
- **`add_path(path)`**: 为文件路径建立层次节点

## 内部实现细节

- 输入格式: Bloaty TSV (`compileunits\tsymbols\tvmsize\tfilesize`)
- 跳过以 `[` 开头的元数据条目(段信息、调试信息)
- 处理绝对路径中的 `third_party` 目录
- 重复符号名通过后缀 `_1`, `_2` 等确保唯一性
- 路径节点添加 ` (Path)` 后缀避免与符号名冲突
- 转义 C++ lambda 表达式中的单引号

## 依赖关系

- Google Charts CDN (gstatic.com)

## 设计模式与设计决策

- **管道模式**: 从 stdin 读取,支持 `bloaty ... | bloaty_treemap.py > out.html`
- **路径去重**: 使用 parent_map 字典确保每个路径节点只输出一次

## 性能考量

流式处理,内存使用与唯一路径和符号数量成正比。

## 相关文件

- `infra/bots/buildstats/make_treemap.py` - Docker 化的 treemap 生成
