# skdiff_utils

> 源文件
> - tools/skdiff/skdiff_utils.h
> - tools/skdiff/skdiff_utils.cpp

## 概述

`skdiff_utils` 是 Skia 图像差异比较工具（skdiff）的工具函数模块，提供了一组用于图像读取、解码、编码、比较和文件命名的实用函数。该模块封装了图像处理的底层细节，包括文件 I/O、PNG 编解码、像素操作以及差异图像生成等功能。它是 skdiff 工具的基础设施层，被主程序和 HTML 生成器等模块广泛使用。

该模块的主要功能包括：文件读取和缓冲区比较、图像解码和编码、差异文件名生成、差异图像创建和写入等。它提供了简洁的 API 抽象，隐藏了 Skia 编解码器和文件系统操作的复杂性。

## 架构位置

该模块位于 Skia 工具层的图像差异比较工具中：

```
skia/
├── tools/
│   └── skdiff/
│       ├── skdiff.h                   # 差异比较核心接口
│       ├── skdiff.cpp                 # 差异比较核心实现
│       ├── skdiff_utils.h             # 本模块头文件（工具函数）
│       ├── skdiff_utils.cpp           # 本模块实现
│       ├── skdiff_html.h              # HTML 报告生成
│       └── skdiff_main.cpp            # 主程序入口
├── include/
│   ├── core/
│   │   ├── SkBitmap.h                 # 位图类
│   │   ├── SkData.h                   # 数据容器
│   │   └── SkStream.h                 # 流接口
│   ├── codec/
│   │   └── SkPngDecoder.h             # PNG 解码器
│   └── encode/
│       └── SkPngEncoder.h             # PNG 编码器
```

该模块的架构角色：
- **向上**：为 skdiff 主程序和 HTML 生成器提供工具函数
- **向下**：调用 Skia 核心 API（编解码、位图操作、文件 I/O）
- **横向**：与 skdiff.cpp 协同工作

## 主要类与结构体

该模块不定义新类，主要使用 Skia 核心类型：

### SkData

Skia 数据容器，用于表示内存块：
- 不可变数据块
- 引用计数管理
- 可从文件创建

### SkBitmap

Skia 位图类，表示像素数组：
- 包含像素数据和图像信息
- 支持多种颜色类型和格式
- 提供像素访问接口

### DiffResource

定义在 `skdiff.h` 中，表示差异比较资源：
- `SkBitmap fBitmap`：位图数据
- `SkString fFullPath`：完整路径
- `SkString fFilename`：文件名
- `DiffResource::Status fStatus`：资源状态

### DiffRecord

定义在 `skdiff.h` 中，表示差异比较记录：
- `DiffResource fBase`：基准图像
- `DiffResource fComparison`：比较图像
- `DiffResource fDifference`：差异图像
- `DiffResource fWhite`：白色背景差异图像
- `DiffRecord::Result fResult`：比较结果

## 公共 API 函数

### are_buffers_equal

```cpp
bool are_buffers_equal(SkData* skdata1, SkData* skdata2);
```

**功能：** 比较两个数据缓冲区是否完全相同。

**参数：**
- `skdata1`：第一个数据缓冲区
- `skdata2`：第二个数据缓冲区

**返回值：** 如果两个缓冲区非空、大小相同且内容完全一致，返回 `true`

**实现逻辑：**
```cpp
if ((nullptr == skdata1) || (nullptr == skdata2)) return false;
if (skdata1->size() != skdata2->size()) return false;
return (0 == memcmp(skdata1->data(), skdata2->data(), skdata1->size()));
```

**使用场景：** 快速检测两个文件是否完全相同，避免不必要的图像解码。

### read_file

```cpp
sk_sp<SkData> read_file(const char* file_path);
```

**功能：** 读取文件的完整内容到内存。

**参数：**
- `file_path`：文件路径

**返回值：** 成功返回包含文件内容的 `SkData` 智能指针，失败返回 `nullptr`

**实现：** 使用 `SkData::MakeFromFileName()` 读取文件，失败时输出警告。

**使用场景：** 加载图像文件到内存进行解码和比较。

### get_bitmap

```cpp
bool get_bitmap(sk_sp<SkData> fileBits,
                DiffResource& resource,
                bool sizeOnly,
                bool ignoreColorSpace);
```

**功能：** 从文件数据解码图像到位图。

**参数：**
- `fileBits`：文件数据
- `resource`：输出的差异资源对象
- `sizeOnly`：如果为 `true`，仅解码图像尺寸信息
- `ignoreColorSpace`：是否忽略颜色空间转换

**返回值：** 成功返回 `true`，并更新 `resource.fBitmap` 和 `resource.fStatus`

**实现细节：**

1. **创建编解码器**
   ```cpp
   static constexpr const SkCodecs::Decoder decoders[] = {SkPngDecoder::Decoder()};
   auto codec = SkCodec::MakeFromData(std::move(fileBits), decoders);
   ```
   仅支持 PNG 格式。

2. **颜色空间处理**
   ```cpp
   SkImageInfo info = codec->getInfo().makeColorType(kN32_SkColorType);
   if (!ignoreColorSpace) {
       info = info.makeColorSpace(SkColorSpace::MakeSRGB());
   }
   ```
   - `ignoreColorSpace = true`：使用原始颜色空间，逐字节比较
   - `ignoreColorSpace = false`：转换到 sRGB，颜色感知比较

3. **按需解码**
   ```cpp
   if (sizeOnly) return true;
   ```
   可选择仅获取尺寸，避免完整解码开销。

### write_bitmap

```cpp
bool write_bitmap(const SkString& path, const SkBitmap& bitmap);
```

**功能：** 将位图编码为 PNG 并写入文件。

**参数：**
- `path`：输出文件路径
- `bitmap`：要写入的位图

**返回值：** 成功返回 `true`

**实现细节：**

1. **强制不透明**
   ```cpp
   static void force_all_opaque(const SkBitmap& bitmap) {
       for (int y = 0; y < bitmap.height(); y++) {
           for (int x = 0; x < bitmap.width(); x++) {
               *bitmap.getAddr32(x, y) |= (SK_A32_MASK << SK_A32_SHIFT);
           }
       }
   }
   ```
   将所有像素的 Alpha 通道设置为 255（完全不透明），避免 PNG 透明度问题。

2. **编码写入**
   ```cpp
   SkFILEWStream file(path.c_str());
   return SkPngEncoder::Encode(&file, copy.pixmap(), {});
   ```
   使用 Skia 的 PNG 编码器写入文件。

### filename_to_diff_filename

```cpp
SkString filename_to_diff_filename(const SkString& filename);
```

**功能：** 根据输入文件名生成差异图像文件名。

**转换规则：**
- 移除文件扩展名
- 添加 `-diff.png` 后缀
- 将路径分隔符替换为下划线（处理子目录）

**示例：**
- `foo.png` → `foo-diff.png`
- `dir/bar.png` → `dir_bar-diff.png`

### filename_to_white_filename

```cpp
SkString filename_to_white_filename(const SkString& filename);
```

**功能：** 生成白色背景差异图像文件名。

**转换规则：** 类似 `filename_to_diff_filename`，但使用 `-white.png` 后缀。

### create_and_write_diff_image

```cpp
void create_and_write_diff_image(DiffRecord* drp,
                                 DiffMetricProc dmp,
                                 const int colorThreshold,
                                 const SkString& outputDir,
                                 const SkString& filename);
```

**功能：** 计算差异并写入差异图像文件。

**参数：**
- `drp`：差异记录指针（输入/输出）
- `dmp`：差异度量函数指针
- `colorThreshold`：颜色差异阈值
- `outputDir`：输出目录（空则不写入）
- `filename`：文件名

**实现流程：**

1. **尺寸检查**
   ```cpp
   if (w != drp->fComparison.fBitmap.width() || h != drp->fComparison.fBitmap.height()) {
       drp->fResult = DiffRecord::kDifferentSizes_Result;
   }
   ```

2. **分配差异图像**
   ```cpp
   drp->fDifference.fBitmap.allocN32Pixels(w, h);
   drp->fWhite.fBitmap.allocN32Pixels(w, h);
   ```

3. **计算差异**
   ```cpp
   compute_diff(drp, dmp, colorThreshold);
   ```

4. **写入文件**
   ```cpp
   if (DiffRecord::kDifferentPixels_Result == drp->fResult) {
       write_bitmap(drp->fDifference.fFullPath, drp->fDifference.fBitmap);
       write_bitmap(drp->fWhite.fFullPath, drp->fWhite.fBitmap);
   }
   ```

## 内部实现细节

### 字符串替换

```cpp
static SkString replace_all(const SkString &input,
                            const char oldSubstring[],
                            const char newSubstring[]);
```

**功能：** 替换字符串中所有匹配的子串。

**实现：** 使用 `strstr()` 查找并逐段拼接。

**用途：** 将文件名中的路径分隔符替换为下划线，确保差异文件都写入同一目录。

### 派生文件名生成

```cpp
static SkString filename_to_derived_filename(const SkString& filename,
                                             const char *suffix);
```

**功能：** 生成派生文件名的通用函数。

**步骤：**
1. 移除扩展名（查找最后一个 `.`）
2. 添加后缀
3. 替换路径分隔符为下划线

## 依赖关系

### 外部依赖

**Skia 核心组件：**
- `SkBitmap`：位图表示
- `SkData`：数据容器
- `SkStream`：流接口（`SkFILEWStream`）
- `SkPixelRef`：像素数据引用

**编解码器：**
- `SkPngDecoder`：PNG 解码
- `SkPngEncoder`：PNG 编码
- `SkCodec`：编解码器基类

**skdiff 组件：**
- `skdiff.h`：核心数据结构和函数
- `DiffResource`、`DiffRecord` 结构体
- `compute_diff()` 函数

**标准库：**
- `<memory>`：智能指针
- `<cstring>`：`memcmp`、`strlen`、`strstr`、`strrchr`

### 被依赖关系

该模块被以下组件使用：
- `skdiff_main.cpp`：主程序
- `skdiff_html.cpp`：HTML 报告生成器
- 其他需要图像处理的 skdiff 功能

## 设计模式与设计决策

### 设计模式

1. **工具函数模式**
   - 提供独立的工具函数
   - 无状态，易于测试

2. **适配器模式**
   - 封装 Skia API 复杂性
   - 提供简化的接口

### 设计决策

1. **仅支持 PNG 格式**
   ```cpp
   static constexpr const SkCodecs::Decoder decoders[] = {SkPngDecoder::Decoder()};
   ```
   - PNG 无损压缩
   - 广泛支持
   - 差异比较需要精确像素值

2. **强制不透明 Alpha**
   - 避免 PNG 透明度导致的视觉差异
   - 简化差异图像显示

3. **颜色空间可选转换**
   - 支持两种比较模式：
     - 字节级精确比较（忽略颜色空间）
     - 感知级比较（转换到 sRGB）

4. **文件名扁平化**
   - 将子目录路径编码到文件名
   - 所有差异文件输出到同一目录
   - 便于管理和查看

5. **按需解码**
   - `sizeOnly` 参数避免完整解码
   - 快速过滤尺寸不匹配的情况

## 性能考量

### 优势

1. **文件缓冲区比较**
   - `are_buffers_equal()` 快速检测完全相同的文件
   - 避免不必要的解码

2. **按需解码**
   - `sizeOnly` 模式仅解码元数据
   - 减少内存和 CPU 使用

3. **零拷贝读取**
   - `SkData::MakeFromFileName()` 可能使用内存映射
   - 避免额外复制

### 潜在瓶颈

1. **PNG 编解码**
   - PNG 解压缩和压缩相对慢
   - 大图像耗时长

2. **强制不透明循环**
   ```cpp
   for (int y = 0; y < bitmap.height(); y++) {
       for (int x = 0; x < bitmap.width(); x++) {
           *bitmap.getAddr32(x, y) |= (SK_A32_MASK << SK_A32_SHIFT);
       }
   }
   ```
   - 遍历所有像素
   - 可能很慢

3. **文件 I/O**
   - 大量小文件读写
   - 磁盘 I/O 可能成为瓶颈

### 优化建议

- 使用并行解码处理多个文件
- 考虑缓存解码结果
- 批量写入差异图像
- 使用更高效的图像格式（WebP）

## 相关文件

**同模块文件：**
- `tools/skdiff/skdiff.h`：核心差异比较接口
- `tools/skdiff/skdiff.cpp`：核心差异比较实现
- `tools/skdiff/skdiff_html.h`：HTML 报告生成
- `tools/skdiff/skdiff_html.cpp`：HTML 报告实现
- `tools/skdiff/skdiff_main.cpp`：主程序入口

**Skia 核心：**
- `include/core/SkBitmap.h`：位图类
- `include/core/SkData.h`：数据容器
- `include/core/SkStream.h`：流接口
- `include/codec/SkCodec.h`：编解码器基类
- `include/codec/SkPngDecoder.h`：PNG 解码器
- `include/encode/SkPngEncoder.h`：PNG 编码器

**相关工具：**
- `tools/viewer/`：可视化工具
- `dm/`：测试框架
- `tools/Resources.h`：资源加载工具
