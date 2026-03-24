# PreshapeTool.cpp

> 源文件: `modules/skottie/utils/PreshapeTool.cpp`

## 概述

`PreshapeTool.cpp` 是一个命令行工具程序，用于对 Lottie/Bodymovin JSON 动画文件中的文本图层进行预排版（preshaping）处理。预排版将文本排版结果（字形 ID、位置等）提前计算并嵌入到输出 JSON 中，使得运行时播放器无需依赖字体管理器和文本排版引擎即可正确渲染文本。这对于缺乏完整文本排版能力的目标平台（如 Web、嵌入式设备）特别有价值。

## 架构位置

该文件位于 `modules/skottie/utils/` 目录下，属于 Skottie 模块的工具程序。在 Skottie 的文本处理管线中，PreshapeTool 是一个离线预处理工具，位于动画创作和运行时播放之间：

```
After Effects -> Bodymovin 导出 -> PreshapeTool (预排版) -> 优化后的 JSON -> 运行时播放
```

## 主要类与结构体

该文件不定义任何类或结构体，仅包含一个 `main()` 函数。

## 公共 API 函数

### `main(int argc, char** argv)`
```cpp
int main(int argc, char** argv);
```
- **功能**: 命令行入口，接受输入和输出文件路径参数。
- **参数**:
  - `-i` / `--input`: 输入的 Lottie JSON 文件路径
  - `-o` / `--output`: 输出的预排版后 JSON 文件路径
- **返回值**: 0 表示成功，非零表示失败。

## 内部实现细节

- **平台字体管理器选择**: 根据编译平台条件性地选择字体管理器：
  - macOS: `SkFontMgr_New_CoreText`
  - Android: `SkFontMgr_New_Android` + FreeType 扫描器
  - Linux: `SkFontMgr_New_FontConfig` + FreeType 扫描器
  - 其他平台: `SkFontMgr_New_Custom_Empty`（空字体管理器）
- **排版工厂**: 使用 `SkShapers::BestAvailable()` 获取当前平台最佳的排版引擎。
- **核心处理流程**:
  1. 解析命令行参数
  2. 初始化 Skia 图形子系统 (`SkGraphics::Init()`)
  3. 读取输入文件到 `SkData`
  4. 创建输出文件流 `SkFILEWStream`
  5. 调用 `skottie_utils::Preshape()` 执行预排版
  6. 写入输出文件

- **错误处理**: 对缺少参数、文件读取失败、文件写入失败和预排版失败四种错误情况分别输出诊断信息并返回非零退出码。

## 依赖关系

- **Skia 核心**: `SkData`, `SkFontMgr`, `SkGraphics`, `SkRefCnt`, `SkStream`
- **`modules/skottie/utils/TextPreshape.h`**: `skottie_utils::Preshape()` 核心预排版函数
- **`modules/skresources/include/SkResources.h`**: 资源提供者
- **`modules/skshaper/utils/FactoryHelpers.h`**: `SkShapers::BestAvailable()` 排版引擎选择
- **`tools/flags/CommandLineFlags.h`**: 命令行参数解析
- **平台字体管理器**: `SkFontMgr_mac_ct.h`, `SkFontMgr_android.h`, `SkFontMgr_fontconfig.h`, `SkFontMgr_empty.h`

## 设计模式与设计决策

- **管道工具模式**: 典型的 Unix 管道工具设计——读入文件、处理、写出文件，单一职责清晰。
- **平台抽象**: 通过预处理器条件编译选择合适的字体管理器，保证跨平台兼容性。
- **委托核心逻辑**: `main()` 仅负责 I/O 和参数解析，核心的预排版逻辑委托给 `skottie_utils::Preshape()` 函数。
- **最佳可用策略**: `SkShapers::BestAvailable()` 自动选择当前构建配置下最好的排版引擎（如 HarfBuzz > CoreText > 基础排版）。

## 性能考量

- 作为离线工具，性能不是首要关注点。预排版是一次性操作，结果可被缓存复用。
- `SkGraphics::Init()` 初始化全局 Skia 状态，包括字体缓存等，确保后续操作的效率。
- 预排版的主要时间消耗在文本排版计算上，取决于动画中文本图层的数量和复杂度。
- 预排版后的 JSON 文件在运行时可以绕过文本排版流程，显著降低了播放端的 CPU 开销和依赖复杂度。
- 输出文件的体积会比输入稍大，因为嵌入了字形 ID 和位置数据，但避免了运行时字体加载的开销。

## 相关文件

- `modules/skottie/utils/TextPreshape.h` -- `Preshape()` 函数声明
- `modules/skottie/include/TextShaper.h` -- Shaper 排版接口
- `modules/skshaper/utils/FactoryHelpers.h` -- 排版引擎选择工具
- `tools/flags/CommandLineFlags.h` -- 命令行参数工具
