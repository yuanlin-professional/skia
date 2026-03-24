# skdiff_main.cpp - Skia 图像差异比较工具

> 源文件: `tools/skdiff/skdiff_main.cpp`

## 概述

`skdiff_main.cpp` 是 Skia 图像差异比较工具的主程序入口。该工具用于比较两个目录中同名图像文件的差异，生成差异图像并输出 HTML 报告。它是 Skia 图像质量回归测试流水线中的核心组件，通常用于比较基线（baseline）图像和变体（variant）图像之间的像素差异。

工具接受三个目录参数：基线目录（baseDir）、比较目录（comparisonDir）和输出目录（outputDir），遍历前两个目录中的同名文件，逐对进行像素级比较，并将结果差异图像和 `index.html` 写入输出目录。

## 架构位置

```
Skia 工具链
├── tools/
│   ├── skdiff/            <-- 图像差异比较工具
│   │   ├── skdiff.h       <-- 核心数据结构定义（DiffRecord, DiffResource 等）
│   │   ├── skdiff_html.h  <-- HTML 报告生成
│   │   ├── skdiff_utils.h <-- 工具函数（图像读取、解码等）
│   │   └── skdiff_main.cpp <-- 本文件：主程序入口
│   └── ...
```

此工具是独立的命令行可执行程序，不属于 Skia 核心库，而是 Skia 测试/工具链的一部分。

## 主要类与结构体

### `DiffSummary`
差异比较的汇总统计结构体，是本文件中最核心的数据结构。

```cpp
struct DiffSummary {
    uint32_t fNumMatches;           // 完全匹配的文件对数
    uint32_t fNumMismatches;        // 不匹配的文件对数
    uint32_t fMaxMismatchV;         // 最大颜色通道差异值
    float fMaxMismatchPercent;      // 最大不匹配像素占比
    FileArray fResultsOfType[DiffRecord::kResultCount];          // 按结果类型分类的文件
    FileArray fStatusOfType[DiffResource::kStatusCount][...];    // 按状态分类的文件
    StringArray fFailedBaseNames[DiffRecord::kResultCount];      // 失败的基础文件名
};
```

关键方法：
- `add(const DiffRecord& drp)`: 将一条比较记录加入汇总
- `print(...)`: 输出汇总报告到 stdout
- `printfFailingBaseNames(...)`: 输出失败的文件基础名

### `AutoReleasePixels`
RAII 风格的辅助类，在析构时自动释放 `DiffRecord` 中四个位图的像素引用，防止内存泄漏。

```cpp
class AutoReleasePixels {
public:
    AutoReleasePixels(DiffRecord* drp);
    ~AutoReleasePixels();  // 将 base/comparison/difference/white 的 pixelRef 置空
};
```

## 公共 API 函数

### `main(int argc, char** argv)`
程序入口，解析命令行参数并驱动整个比较流程。

支持的命令行参数：
| 参数 | 说明 |
|------|------|
| `--failonresult <result>` | 指定某种结果类型会导致非零退出码 |
| `--failonstatus <base> <comp>` | 指定某种状态组合会导致非零退出码 |
| `--listfilenames` | 在 stdout 中列出每种结果类型的所有文件名 |
| `--match <substring>` | 仅比较文件名包含指定子串的文件 |
| `--nocolorspace` | 忽略图像色彩空间 |
| `--nodiffs` | 不生成差异图像和 HTML，仅输出报告 |
| `--nomatch <substring>` | 排除文件名包含指定子串的文件 |
| `--norecurse` | 不递归进入子目录 |
| `--sortbymaxmismatch` | 按最大颜色通道差异排序 |
| `--sortbymismatch` | 按平均颜色通道差异排序 |
| `--threshold <n>` | 仅报告颜色通道差异大于 n 的情况 |
| `--weighted` | 按加权像素差异排序 |

返回值：匹配失败的文件对数量（上限 255）。

## 内部实现细节

### 核心比较流程

`create_diff_images()` 是执行实际比较的核心函数，其签名包含大量参数以支持灵活的配置：

```cpp
static void create_diff_images(DiffMetricProc dmp,
                                const int colorThreshold,
                                bool ignoreColorSpace,
                                RecordArray* differences,
                                const SkString& baseDir,
                                const SkString& comparisonDir,
                                const SkString& outputDir,
                                const StringArray& matchSubstrings,
                                const StringArray& nomatchSubstrings,
                                bool recurseIntoSubdirs,
                                bool getBounds,
                                bool verbose,
                                DiffSummary* summary);
```

执行步骤：
1. **文件收集**：分别从 baseDir 和 comparisonDir 收集文件列表
2. **排序**：对两个文件列表按文件名排序（使用 `qsort` + `compare_file_name_metrics`）
3. **输出目录创建**：如果 outputDir 非空则创建目录
4. **双指针合并遍历**：类似归并排序的双指针方式遍历两个排序列表
   - 如果文件仅在 baseDir 中存在 -> `kCouldNotCompare_Result`
   - 如果文件仅在 comparisonDir 中存在 -> `kCouldNotCompare_Result`
   - 如果两个目录都有同名文件：
     - 先读取文件数据（`read_file`）
     - 进行二进制比较（`are_buffers_equal`），完全相同则 `kEqualBits_Result`
     - 否则解码为位图（`get_bitmap`），进行像素级比较并生成差异图像
5. **尾部处理**：处理一个列表耗尽后另一个列表中的剩余文件
6. **汇总记录**：将每对文件的比较结果添加到 `DiffSummary` 中

### 比较结果分类

`DiffRecord::Result` 枚举定义了五种可能的比较结果：
- `kEqualBits_Result`：二进制完全相同
- `kEqualPixels_Result`：像素完全相同（但二进制可能因元数据不同）
- `kDifferentPixels_Result`：像素存在差异
- `kDifferentSizes_Result`：图像尺寸不同
- `kCouldNotCompare_Result`：无法比较（文件缺失、无法读取或无法解码）

### 文件过滤机制

`get_file_list_subdir()` 递归遍历目录，支持：
- `matchSubstrings`：文件名必须包含的子串集合（OR 关系）
- `nomatchSubstrings`：文件名不能包含的子串集合
- 自动跳过以 `.` 开头的隐藏文件和目录

`add_unique_basename()` 辅助函数从完整文件名中提取不含扩展名的基础名称，并确保唯一性（用于失败报告中的去重）。

### 终端着色

在非 Windows 平台使用 ANSI 转义码为输出着色：
- 红色（`\x1b[31m`）：读取失败、像素不同
- 绿色（`\x1b[32m`）：匹配
- 黄色（`\x1b[33m`）：文件缺失

Windows 平台上这些颜色宏被定义为空字符串。`VERBOSE_STATUS` 宏封装了带颜色的状态输出逻辑。

### 排序策略

`main` 函数中通过函数指针选择排序策略：
```cpp
int (*sortProc)(const void*, const void*) = compare<CompareDiffMetrics>;
```

可选的排序比较器包括：
- `CompareDiffMetrics`：按不匹配像素比例排序（默认）
- `CompareDiffMaxMismatches`：按最大颜色通道差异排序
- `CompareDiffMeanMismatches`：按平均颜色通道差异排序
- `CompareDiffWeighted`：按加权像素差异排序

### get_bounds 功能

当使用 `--nodiffs` 时（generateDiffs=false 但 getBounds=true），仍然需要获取图像的尺寸信息用于报告，但不需要进行像素级比较。`get_bounds()` 函数仅解码图像头部获取尺寸，不读取完整像素数据。

## 依赖关系

- **Skia 核心库**：`SkBitmap`, `SkData`, `SkPixelRef`, `SkStream`
- **Skia 内部模块**：`SkTSearch`, `SkOSFile`, `SkOSPath`
- **工具模块**：`skdiff.h`（DiffRecord 等核心类型）, `skdiff_html.h`（HTML 生成）, `skdiff_utils.h`（图像读取/解码）
- **Skia 私有类型**：`SkTDArray`（动态数组）

## 设计模式与设计决策

1. **双指针归并比较**：利用排序后的文件列表进行高效的双指针遍历，时间复杂度 O(n log n + m log m)，比朴素的双循环嵌套更高效。

2. **分层比较策略**：先进行快速的二进制比较（避免不必要的图像解码），只有在二进制不同时才进行像素级比较。

3. **RAII 像素管理**：`AutoReleasePixels` 确保像素数据在比较完成后立即释放，避免在大批量比较时内存占用过高。

4. **灵活的失败判定**：通过 `--failonresult` 和 `--failonstatus` 参数，用户可以精确控制哪些比较结果应该导致非零退出码。

5. **可插拔的排序策略**：通过函数指针 `sortProc` 支持多种排序方式（按最大差异、平均差异、加权差异等），使用策略模式。

## 性能考量

- **二进制预比较**：通过 `are_buffers_equal` 进行快速二进制比较，避免对相同文件进行昂贵的像素解码和比较操作。
- **即时释放像素**：`AutoReleasePixels` 在每对文件比较完成后立即释放位图像素数据，降低内存峰值使用。
- **qsort 排序**：使用 C 标准库的 `qsort` 进行排序，虽然不如 `std::sort` 类型安全，但在处理 Skia 自有容器时保持了与旧代码的兼容性。
- **退出码截断**：将失败数量限制在 255 以内，避免 Linux 等平台的退出码回绕问题。

## 相关文件

- `tools/skdiff/skdiff.h` - 核心数据结构定义（DiffRecord, DiffResource, DiffMetricProc, RecordArray）
- `tools/skdiff/skdiff_html.h` - HTML 报告生成函数 `print_diff_page`
- `tools/skdiff/skdiff_utils.h` - 工具函数（`read_file`, `get_bitmap`, `create_and_write_diff_image`, `are_buffers_equal`）
- `include/core/SkBitmap.h` - 位图类
- `include/core/SkData.h` - 不可变数据容器
- `include/core/SkPixelRef.h` - 像素引用（AutoReleasePixels 所操作的对象）
- `include/core/SkStream.h` - 流接口
- `include/private/base/SkTDArray.h` - 动态数组模板
- `src/base/SkTSearch.h` - 搜索辅助函数
- `src/core/SkOSFile.h` - 文件系统操作（目录遍历、文件存在性检查）
- `src/utils/SkOSPath.h` - 路径操作工具（路径拼接、分隔符处理）
