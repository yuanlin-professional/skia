# pdf-comparison.py - PDF 输出差异比较工具

> 源文件:
> - `experimental/tools/pdf-comparison.py`

## 概述

pdf-comparison.py 是一个实验性的 Python 工具，用于比较 Skia DM 工具在两个不同 Git 提交之间的 PDF 输出差异。它自动化了完整的比较流程：检出对照分支、构建 Skia、运行 DM 生成 PDF、使用 pdfium_test 光栅化 PDF、使用 image_diff_metric 计算像素差异，并生成交互式 HTML 报告。该工具是 Skia PDF 后端开发者验证代码变更影响的自动化回归测试工具。

## 架构位置

```
experimental/tools/pdf-comparison.py  <── 本工具
    ↓ (调用)
├── git worktree (检出对照提交)
├── gn / ninja (构建 Skia)
├── dm (Skia 绘制管理器, 生成 PDF)
├── pdfium_test (PDF 光栅化)
├── image_diff_metric (图像差异度量)
└── HTML 报告生成
```

位于实验性工具目录，不属于 Skia 的正式构建或测试管道。

## 主要类与结构体

无类定义。本工具为过程式 Python 脚本。

## 公共 API 函数

### 核心函数

| 函数 | 描述 |
|------|------|
| `main(control_commitish)` | 主入口，执行完整的比较流程 |
| `checkout_worktree(checkoutable)` | 使用 git worktree 检出对照分支 |
| `build_skia(directory, executable)` | 配置和构建 Skia 可执行文件 |
| `build_and_run_dm(directory, data_dir)` | 构建 DM 并运行 PDF 生成 |
| `rasterize(path)` | 使用 pdfium_test 将 PDF 光栅化为 PNG |

### 辅助函数

| 函数 | 描述 |
|------|------|
| `shard(fn, arglist)` | 多线程分片执行函数 |
| `shardsum(fn, arglist)` | 分片执行并统计 True 结果数 |
| `is_same(path1, path2)` | 二进制比较两个文件是否相同 |
| `get_common_paths(dirs, ext)` | 获取多个目录中共有的指定扩展名文件 |
| `timeout(deadline, cmd)` | 带超时的子进程执行 |
| `test_exe(cmd)` | 测试可执行文件是否存在且可运行 |
| `sysopen(arg)` | 跨平台打开文件（macOS/Windows/Linux）|

## 内部实现细节

### 完整比较流程

1. **验证环境**: 确认 `ninja` 和 `pdfium_test` 可用
2. **检出对照**: 使用 `git worktree add` 检出要比较的提交
3. **构建与运行**: 分别为当前代码和对照代码构建 DM 并生成 PDF
4. **二进制比较**: 快速过滤掉完全相同的 PDF（字节级比较）
5. **PDF 光栅化**: 使用 pdfium_test 将不同的 PDF 转为 PNG（30 秒超时）
6. **PNG 比较**: 过滤掉光栅化结果相同的 PDF
7. **差异度量**: 使用 image_diff_metric 计算像素差异分数
8. **参考图像生成**: 使用 GPU/8888 后端生成参考图像
9. **HTML 报告**: 生成交互式差异报告，包含 before-after diff、before、after 和参考图

### 环境变量配置

| 环境变量 | 默认值 | 描述 |
|----------|--------|------|
| `PDF_COMPARISON_GN_ARGS` | `''` | 额外的 GN 构建参数 |
| `PDF_COMPARISON_NOGPU` | 未设置 | 设置后使用 8888 替代 GL 作为参考后端 |
| `PDF_COMPARISON_DPI` | `72` | PDF 光栅化 DPI |
| `PDF_COMPARISON_300DPI` | 未设置 | 设置后使用 pdf300 配置 |
| `PDF_COMPARISON_THREADS` | `40` | 并行线程数 |

### 多线程分片

`shard()` 函数将任务列表按模运算均匀分配到 `NUM_THREADS` 个线程中，每个线程顺序执行分配到的任务。

### HTML 报告

报告使用 CSS mix-blend-mode: difference 实现交互式差异可视化：
- 左侧：Before-After 叠加差异（混合模式）
- 中间：Before 和 After 单独显示
- 右侧：参考图像（GPU/8888 渲染结果）

### 排除列表

`BAD_TESTS` 列表排除已知在 PDF 模式下有问题的测试：
- `image-cacherator-from-picture`
- `image-cacherator-from-raster`
- `mixershader`
- `shadermaskfilter_image`
- `tilemode_decal`

## 依赖关系

- **外部工具**: `ninja`（构建工具）、`pdfium_test`（PDF 光栅化器）、`ccache`（可选，编译缓存）
- **Skia 构建产物**: `dm`（绘制管理器）、`image_diff_metric`（图像差异度量）
- **Python 标准库**: `os`、`re`、`shutil`、`subprocess`、`sys`、`tempfile`、`threading`
- **Git**: `git worktree`、`git rev-parse`、`git checkout`

## 设计模式与设计决策

- **渐进式过滤**: 先做二进制比较（最快），再光栅化比较（较慢），最后像素差异度量（最慢），逐步缩小需要详细分析的文件集合
- **多线程并行**: 光栅化和比较操作通过分片并行执行，默认 40 线程
- **临时工作区**: 使用 `tempfile.mkdtemp` 创建临时目录存放所有中间文件
- **自包含报告**: HTML 报告使用相对路径引用图片，可直接在浏览器中打开
- **超时保护**: pdfium_test 执行有 30 秒超时，防止异常 PDF 导致工具挂起
- **ccache 集成**: 构建时自动检测并使用 ccache 加速编译

## 性能考量

- 默认 40 个线程并行处理光栅化和比较，充分利用多核 CPU
- 二进制比较使用 4096 字节块逐块读取，内存高效
- 文件完全相同时立即删除以释放磁盘空间
- `git worktree` 避免了完整 clone 的开销，共享对象数据库
- ccache 支持使跨次运行的编译速度大幅提升

## 相关文件

- `dm/DM.cpp` - Skia 绘制管理器
- `tools/image_diff_metric.cpp` - 图像差异度量工具
- `gn/` - GN 构建系统配置
- `bin/sync` - Skia 依赖同步脚本
