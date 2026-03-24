# SkShaper_harfbuzz 实现 - HarfBuzz 文本塑形引擎

> 源文件: `modules/skshaper/src/SkShaper_harfbuzz.cpp`

## 概述

SkShaper_harfbuzz.cpp 是 Skia 文本塑形模块中基于 HarfBuzz 的完整实现，也是功能最完善的塑形后端。该文件实现了三种换行策略的塑形器（ShaperDrivenWrapper、ShapeThenWrap、ShapeDontWrapOrReorder），以及脚本运行迭代器、HarfBuzz 字体回调系统、字体面 LRU 缓存和 BiDi 重排输出。它是连接 Skia 字体系统与 HarfBuzz 排版引擎的桥梁。

## 架构位置

该文件位于 skshaper 模块的实现层，是 SkShaper_harfbuzz.h 声明的函数和 SkShaper 虚方法的具体实现。它依赖 HarfBuzz C 库进行字形塑形，依赖 SkUnicode 进行 BiDi 分析和行断行。

**调用流程**: `SkShaper::shape()` -> `ShaperHarfBuzz::shape()` -> `wrap()` -> `hb_shape()` -> RunHandler 回调

## 主要类与结构体

### `ShaperHarfBuzz`（抽象基类）
HarfBuzz 塑形器的公共基类：
- 持有 `sk_sp<SkUnicode>`、`HBBuffer`、`sk_sp<SkFontMgr>`
- 实现了 SkShaper 的 `shape()` 方法
- 定义了纯虚方法 `wrap()` 由子类实现不同换行策略
- 提供内部 `shape()` 方法对单个文本段进行 HarfBuzz 塑形

### `ShaperDrivenWrapper`
塑形驱动换行策略：
- 边塑形边判断换行，利用 HarfBuzz 的 unsafe-to-break 标记
- 对整个项目（item）先完整塑形生成模型
- 使用断行迭代器找到候选断点
- 优先复用模型结果，仅在断点不在安全位置时重新塑形

### `ShapeThenWrap`
先塑形后换行策略：
- 先对所有运行段完成塑形
- 然后遍历字形序列，根据宽度约束进行换行
- 换行优先级：行断行 > 字素断行
- 最后进行 BiDi 视觉重排和输出

### `ShapeDontWrapOrReorder`
不换行不重排策略：
- 所有文本作为单行处理
- 不进行 BiDi 重排
- 适合已知单行或手动控制布局的场景

### `SkUnicodeHbScriptRunIterator`
基于 HarfBuzz Unicode 函数的脚本运行迭代器：
- 使用 `hb_unicode_script()` 检测每个字符的脚本
- 处理 INHERITED 和 COMMON 脚本的合并

### `RunIteratorQueue`
运行迭代器优先级队列，协调字体、BiDi、脚本和语言四个迭代器的推进：
- 使用 SkTDPQueue 按运行结束位置和优先级排序
- 字体迭代器优先级最低（3），在相同位置时最后处理

### `ShapedGlyph`
塑形后的字形数据：ID、簇索引、偏移、前进量、断行属性标记。

### `ShapedRun`
塑形后的运行数据：UTF-8 范围、字体、BiDi 级别、脚本、语言、字形数组和总前进量。

### `ShapedLine`
一行的所有运行和总前进量。

### `HBLockedFaceCache`
线程安全的 HarfBuzz 字体面 LRU 缓存包装器（容量 100）。

## 公共 API 函数

| 命名空间 | 函数 | 说明 |
|----------|------|------|
| `SkShapers::HB` | `ShaperDrivenWrapper(unicode, fallback)` | 创建塑形驱动换行器 |
| `SkShapers::HB` | `ShapeThenWrap(unicode, fallback)` | 创建先塑形后换行器 |
| `SkShapers::HB` | `ShapeDontWrapOrReorder(unicode, fallback)` | 创建不换行器 |
| `SkShapers::HB` | `ScriptRunIterator(utf8, bytes[, script])` | 创建脚本迭代器 |
| `SkShapers::HB` | `PurgeCaches()` | 清除字体面缓存 |

## 内部实现细节

### HarfBuzz 字体回调系统
通过 `hb_font_funcs_t` 注册自定义回调，将 HarfBuzz 的字体查询委托给 SkFont：

| 回调 | 说明 |
|------|------|
| `skhb_glyph` | Unicode 到字形 ID 映射 |
| `skhb_nominal_glyphs` | 批量字形映射（优化） |
| `skhb_glyph_h_advance` | 单个字形水平前进量 |
| `skhb_glyph_h_advances` | 批量水平前进量（优化） |
| `skhb_glyph_extents` | 字形边界框（用于标记定位） |

### HarfBuzz 字体创建
两层字体体系：
1. **TypefaceFont** (`create_typeface_hb_font`): 从 SkTypeface 创建，使用 OpenType 字体函数，缓存在 LRU 中
2. **SubFont** (`create_sub_hb_font`): 从 SkFont 创建子字体，附加 Skia 的自定义回调函数和缩放

### HarfBuzz 面创建（`create_hb_face`）
1. 优先从流数据创建（`hb_face_create`），验证字形数量
2. 回退到表查询创建（`hb_face_create_for_tables`），通过回调函数按需加载字体表
3. 设置 upem（units per em）

### 塑形核心流程（`ShaperHarfBuzz::shape`）
1. 配置 HB buffer：cluster level 设为 MONOTONE_CHARACTERS
2. 添加前后上下文（precontext/postcontext）以改善边界塑形
3. 逐字符填充 buffer，使用 UTF-8 偏移作为 cluster 索引
4. 设置方向、脚本和语言
5. 从缓存获取 HBFont，应用 OpenType 特性
6. 调用 `hb_shape()` 执行塑形
7. RTL 文本逆序 buffer 恢复逻辑顺序
8. 提取字形信息：ID、cluster、偏移、前进量、边界框、unsafe-to-break

### BiDi 视觉重排（`emit` 函数）
1. 收集各运行的 BiDi 级别
2. 调用 `SkUnicode::reorderVisual` 计算视觉到逻辑的映射
3. 按视觉顺序遍历运行，通过 RunHandler 输出
4. 字形在每个运行内按 LTR 输出（PDF 读取器兼容）

### ShaperDrivenWrapper 的模型复用优化
1. 对整个项目完整塑形一次（生成模型）
2. 在模型中标记安全断点（`fUnsafeToBreak == false` 的位置）
3. 候选断点优先从模型中查找字形范围和前进量
4. 仅当候选断点不在安全位置时才重新塑形
5. 命中模型时直接 memcpy 字形数据

### 坐标系转换
HarfBuzz 使用 16.16 定点数和 y-up 坐标系：
- `skhb_position`: SkScalar -> 16.16 定点
- `SkScalarFromHBPosX/Y`: 16.16 定点 -> SkScalar（Y 取反）

## 依赖关系

- **hb.h / hb-ot.h**: HarfBuzz C 库
- **SkUnicode**: BiDi 分析、行/字素断行
- **SkFont / SkTypeface / SkFontMgr**: Skia 字体系统
- **SkLRUCache**: HarfBuzz 字体面缓存
- **SkTDPQueue**: 运行迭代器优先级队列
- **SkUTF**: UTF-8 编码工具
- **SkMutex**: 线程安全

## 设计模式与设计决策

1. **模板方法模式**: ShaperHarfBuzz 定义 `shape()` 流程框架，子类通过 `wrap()` 实现不同换行策略。
2. **两层字体缓存**: TypefaceFont 按 SkTypefaceID 缓存（LRU 100），SubFont 每次按 SkFont 创建（轻量）。
3. **批量优化回调**: `skhb_nominal_glyphs` 和 `skhb_glyph_h_advances` 利用批量 API 降低单个调用开销。
4. **模型复用**: ShaperDrivenWrapper 中的模型优化避免了对已塑形文本的重复处理。
5. **前后上下文**: 向 HarfBuzz 提供断行点前后的文本上下文，改善边界处的字形选择。

## 性能考量

- **HBFace 缓存**: 100 条目的 LRU 缓存避免了最昂贵的 HarfBuzz 面创建
- **批量字形/前进量查询**: 减少 Skia->HarfBuzz 的调用次数
- **模型复用（ShaperDrivenWrapper）**: 对长文本段避免重复塑形，从 O(n*m) 降到接近 O(n)
- **cluster level MONOTONE_CHARACTERS**: 确保 cluster 索引单调递增，简化断行判断
- **内存管理**: 使用 AutoSTMalloc 进行栈分配优化小数组

### 三种换行策略的比较

| 特性 | ShaperDrivenWrapper | ShapeThenWrap | ShapeDontWrapOrReorder |
|------|---------------------|---------------|------------------------|
| 塑形时机 | 边塑形边换行 | 全部塑形后换行 | 全部塑形，不换行 |
| 模型复用 | 有（安全断点优化） | 无 | 无 |
| BiDi 重排 | 有（emit 函数） | 有（内置） | 无 |
| 断行方式 | 行断行迭代器 | 行断行+字素断行 | 不断行 |
| 适用场景 | 交互式文本编辑 | 静态文本排版 | 单行文本 |
| 性能特点 | 对长文本更优 | 需要更多内存 | 最简单高效 |

### HarfBuzz 版本兼容性
代码中通过 `SK_HB_VERSION_CHECK` 宏处理不同 HarfBuzz 版本的 API 差异：
- **1.8.6+**: 支持 `hb_font_funcs_set_glyph_h_advances_func` 批量查询
- **2.0.0+**: 支持 `hb_font_funcs_set_nominal_glyphs_func` 批量映射
- **1.5.0+**: 支持 `HB_GLYPH_FLAG_UNSAFE_TO_BREAK` 安全断行标记

### 运行迭代器优先级
RunIteratorQueue 中四个迭代器的优先级（数值越小越先处理）：
- 0: LanguageRunIterator（语言最先消费）
- 1: ScriptRunIterator（脚本其次）
- 2: BiDiRunIterator（BiDi 再次）
- 3: FontRunIterator（字体最后消费，因为字体变化最不频繁）

在同一位置发生多个迭代器边界时，优先级低的先消费，确保字体迭代器能获取正确的 BiDi/脚本信息。

## 相关文件

- `modules/skshaper/include/SkShaper_harfbuzz.h` - 公共接口
- `modules/skshaper/include/SkShaper.h` - SkShaper 基类
- `modules/skshaper/include/SkShaper_skunicode.h` - BiDi 迭代器接口
- `modules/skunicode/include/SkUnicode.h` - Unicode 接口
- `src/core/SkLRUCache.h` - LRU 缓存

## 使用注意事项

1. ShaperHarfBuzz 要求 SkUnicode 非空（新版 API 中 assert 验证）
2. HarfBuzz 字体面缓存为全局静态，跨所有塑形器实例共享
3. `PurgeCaches()` 需要获取全局互斥锁，不应在热路径上频繁调用
4. HarfBuzz buffer 的 cluster level 设为 MONOTONE_CHARACTERS，不支持非单调 cluster
5. 未定义语言时使用 "und"（未定义语言），避免 HB_LANGUAGE_INVALID 引发竞态
6. BOT/EOT 标志被有意禁用，以避免首字符为标记时出现点圈
7. `ShapeDontWrapOrReorder` 不执行 BiDi 重排，混合方向文本不会正确显示
8. 旧版 API（`MakeShaperDrivenWrapper` 等）使用全局静态 SkUnicode 实例
9. HarfBuzz 位置使用 16.16 定点数格式，精度约为 1/65536 像素
10. 字形边界使用 SkPaint 默认设置获取，不包含笔画宽度

### HarfBuzz 字体回调说明
Skia 注册的自定义 HarfBuzz 回调替换了默认的 OpenType 字体函数：
- 字形映射和宽度查询使用 Skia 的 SkFont API，确保与 Skia 渲染一致
- 字形范围查询用于 HarfBuzz 的标记定位回退（当字体无 GPOS 标记锚点时）
