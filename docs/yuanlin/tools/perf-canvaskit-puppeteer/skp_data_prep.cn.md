# CanvasKit SKP 数据对比分析工具

> 源文件: `tools/perf-canvaskit-puppeteer/skp_data_prep.js`

## 概述

此文件是一个命令行数据分析工具，用于比较 CanvasKit 的 SIMD（Single Instruction, Multiple Data）构建版本和标准 Release 构建版本在 SKP 文件渲染方面的性能差异。它读取两种构建的性能输出 JSON 数据，计算每个 SKP 文件的帧时间平均值和中位数，并以表格形式展示对比结果。

## 架构位置

此文件是 CanvasKit 性能分析工具链中的后处理组件。

- 所属模块：`tools/perf-canvaskit-puppeteer/`
- 角色：离线数据分析工具
- 输入：`make skps_release_and_SIMD` 命令的 JSON 输出
- 输出：控制台表格形式的性能对比报告

## 主要类与结构体

此文件无类定义，使用过程式编程风格。

### 核心数据结构
- **`SIMD_DATA`**：从 `simd_out.json` 读取的 SIMD 构建性能数据
- **`RELEASE_DATA`**：从 `release_out.json` 读取的标准构建性能数据
- **`comparisonData`**：包含每个 SKP 的对比数据的数组

### 对比数据对象结构
```
{
  skp_name: string,
  frames_average_difference: number,
  frames_median_difference: number,
  simd_frames_median: number,
  simd_frames_average: number,
  release_frames_average: number,
  release_frames_median: number
}
```

## 公共 API 函数

### 统计函数
| 函数 | 描述 |
|------|------|
| `averageFromArray(array)` | 计算数组元素的算术平均值 |
| `medianFromArray(array)` | 计算数组元素的中位数 |
| `tableDataFromComparisonDataObject(obj)` | 将对比数据转换为控制台表格格式 |

## 内部实现细节

### 数据处理流程
1. 读取 `simd_out.json` 和 `release_out.json`
2. 合并两个数据集的 SKP 名称到 Set 中
3. 对每个同时存在于两个数据集中的 SKP：
   - 提取 `total_frame_ms` 数组
   - 计算平均帧时间和中位数帧时间
   - 计算差异值（Release - SIMD，正值表示 SIMD 更快）
4. 输出三个表格：
   - 所有 SKP 的综合平均值
   - SIMD 表现最好的 3 个 SKP
   - SIMD 表现最差的 3 个 SKP

### 输出格式
使用 `console.table()` 输出格式化表格，包含列：
- `.SKP name`：SKP 文件名
- `release CanvasKit build (ms)`：标准构建帧时间
- `experimental_simd CanvasKit build (ms)`：SIMD 构建帧时间
- `difference (ms)`：差异值

## 依赖关系

- **fs**：文件系统读取
- 输入文件：`simd_out.json`、`release_out.json`（由 `make skps_release_and_SIMD` 生成）

## 设计模式与设计决策

- **离线分析**：不在测试运行时执行分析，而是对已保存的数据进行后处理
- **关注差异**：按中位数差异排序，突出 SIMD 优化效果最显著和最不显著的场景
- **双指标**：同时计算平均值和中位数，平均值反映总体趋势，中位数抵抗异常值

## 性能考量

- 使用中位数而非平均值作为主要排序指标，更能反映稳态性能
- SIMD 优化对不同 SKP 的效果差异巨大，Top 3 和 Bottom 3 分析有助于定位优化瓶颈
- 帧时间以毫秒为单位，精确到小数点后两位

## 相关文件

- `tools/perf-canvaskit-puppeteer/perf-canvaskit-with-puppeteer.js` - 生成输入数据的驱动程序
- `tools/perf-canvaskit-puppeteer/benchmark.js` - 帧时间收集框架

### 输出表格示例

程序输出三个格式化表格：

**表格 1：综合平均值**
包含所有 SKP 文件的帧时间平均值和中位数的汇总统计。

**表格 2：SIMD 最佳表现（Top 3）**
按中位数帧时间差异降序排列，展示 SIMD 构建相对于标准构建改善最大的 3 个 SKP 文件。

**表格 3：SIMD 最差表现（Bottom 3）**
按中位数帧时间差异升序排列，展示 SIMD 构建改善最小（或退化）的 3 个 SKP 文件。

### 数据处理注意事项

- `medianFromArray` 会修改原始数组（就地排序），但由于每个数组只使用一次，这不会导致问题
- 仅比较同时存在于两个数据集中的 SKP 文件，缺失的 SKP 会被跳过
- 差异值计算为 `release - simd`，正值表示 SIMD 更快

### 典型使用流程

1. 运行 `make skps_release_and_SIMD` 生成两组性能数据
2. 确保当前目录下存在 `simd_out.json` 和 `release_out.json`
3. 运行 `node skp_data_prep.js` 查看对比结果
4. 分析 Top 3 和 Bottom 3 识别优化机会

### 局限性

- 仅支持两种构建的对比，不支持多版本比较
- 输入文件名硬编码，不支持命令行指定
- 不生成持久化报告，仅输出到控制台
- 统计分析相对简单（仅平均值和中位数），未包含标准差或置信区间
