# modules - Skia 模块系统

## 概述

`modules/` 目录包含 Skia 图形库的所有可选功能模块。这些模块构建在 Skia 核心之上,提供了高级功能如动画渲染、文本排版、矢量图形解析、色彩管理等。每个模块可以作为独立的构建目标按需编译,使用者可以根据自己的需求选择性地集成所需模块。

Skia 的模块化架构遵循关注点分离原则:核心库 (`src/` 和 `include/`) 提供基础的 2D 图形绘制能力,而模块系统扩展了更丰富的上层功能。模块之间存在层次化的依赖关系,例如 skottie (Lottie 动画) 依赖于 sksg (场景图)、skresources (资源管理)、skshaper (文本整形) 和 jsonreader (JSON 解析) 等多个基础模块。

模块的构建配置统一采用 GN (`.gn`/`.gni`) 和 Bazel (`.bazel`) 双构建系统支持,确保在不同的构建环境下都能正确编译。大部分模块遵循标准的目录结构:`include/` 存放公共头文件,`src/` 存放实现代码,`tests/` 存放单元测试。

## 架构图

```
                          +------------------+
                          |   Skia Core      |
                          | (src/ + include/)|
                          +--------+---------+
                                   |
          +------------------------+------------------------+
          |            |           |           |            |
          v            v           v           v            v
    +---------+  +---------+  +--------+  +--------+  +---------+
    | skcms   |  | skshaper|  | sksg   |  |skunicode|  |bentley- |
    | (色彩   |  | (文本   |  | (场景  |  |(Unicode)|  |ottmann  |
    | 管理)   |  | 整形)   |  | 图)    |  |         |  |(线段交点)|
    +---------+  +---------+  +--------+  +--------+  +---------+
                      |           |
          +-----------+-----------+----------+
          |           |                      |
          v           v                      v
    +-----------+ +---------+          +-----------+
    |skresources| |jsonreader|          |skparagraph|
    |(资源管理) | |(JSON    |          |(段落排版) |
    +-----------+ |解析器)  |          +-----------+
          |       +---------+
          |           |
          +-----------+
          |
          v
    +-----------+     +-----------+     +-----------+
    |  skottie  |     |    svg    |     | canvaskit |
    | (Lottie   |     | (SVG     |     | (WASM     |
    | 动画)     |     | 渲染)    |     | 绑定)     |
    +-----------+     +-----------+     +-----------+

    +-----------+     +-----------+     +-----------+
    |audioplayer|     |skplaintext|     |  pathops  |
    |(音频播放) |     |editor     |     |(路径操作) |
    +-----------+     |(文本编辑)|     +-----------+
                      +-----------+
```

## 模块列表

### 渲染与动画模块

| 模块 | 目录 | 说明 |
|------|------|------|
| **skottie** | `modules/skottie/` | Lottie (After Effects) 动画渲染引擎,支持完整的 Lottie JSON 格式 |
| **svg** | `modules/svg/` | SVG 1.1 矢量图形解析与渲染,支持形状、渐变、滤镜、文本等 |
| **sksg** | `modules/sksg/` | 场景图 (Scene Graph) 框架,为 skottie 提供声明式渲染树 |
| **canvaskit** | `modules/canvaskit/` | WebAssembly 绑定,在浏览器中使用 Skia 的完整功能 |

### 文本处理模块

| 模块 | 目录 | 说明 |
|------|------|------|
| **skshaper** | `modules/skshaper/` | 文本整形引擎,封装 HarfBuzz/ICU 等后端 |
| **skparagraph** | `modules/skparagraph/` | 段落级文本排版,支持多样式、BiDi、换行等 |
| **skunicode** | `modules/skunicode/` | Unicode 处理抽象层,提供 BiDi/换行/字形聚类 |
| **skplaintexteditor** | `modules/skplaintexteditor/` | 纯文本编辑器示例,展示 Skia 文本 API 的使用 |

### 基础设施模块

| 模块 | 目录 | 说明 |
|------|------|------|
| **skcms** | `modules/skcms/` | 色彩管理系统,ICC 配置文件解析和颜色空间转换 |
| **skresources** | `modules/skresources/` | 外部资源加载抽象,图像/字体/音频资源管理 |
| **jsonreader** | `modules/jsonreader/` | 高性能 JSON 解析器,64 位紧凑值表示 |
| **audioplayer** | `modules/audioplayer/` | 跨平台音频播放器抽象 (macOS/Android/SFML) |

### 几何算法模块

| 模块 | 目录 | 说明 |
|------|------|------|
| **bentleyottmann** | `modules/bentleyottmann/` | Bentley-Ottmann 线段交点算法及 Myers 算法 |
| **pathops** | `modules/pathops/` | 路径布尔运算 (并集/交集/差集/异或) |

## 模块依赖关系

```
skottie --> sksg, skresources, skshaper, skunicode, jsonreader, audioplayer
svg     --> skresources, skshaper
skparagraph --> skshaper, skunicode
skshaper    --> skunicode
skresources --> (Skia Core: SkCodec, SkImage)
canvaskit   --> skottie, skparagraph, skshaper, skresources, skunicode, pathops
pathops     --> bentleyottmann
skcms       --> (无外部依赖, 独立 C 库)
jsonreader  --> (Skia Core: SkArenaAlloc)
audioplayer --> (平台音频 API)
skplaintexteditor --> skshaper
```

## 构建配置

每个模块通常包含以下构建文件:

| 文件 | 说明 |
|------|------|
| `BUILD.gn` | GN 构建规则定义 |
| `BUILD.bazel` | Bazel 构建规则定义 |
| `<module>.gni` | GNI 源文件列表,供 BUILD.gn 导入 |

### 按需编译示例

在 GN 中,模块可以通过构建参数控制是否编译:

```
# 仅编译核心 + Lottie 动画支持
skia_enable_skottie = true
skia_enable_svg = false
```

## 目录结构总览

```
modules/
+-- audioplayer/       # 音频播放器 (跨平台抽象)
+-- bentleyottmann/    # 线段交点算法
+-- canvaskit/         # WebAssembly 绑定
+-- jsonreader/        # JSON 解析器
+-- pathops/           # 路径布尔运算
+-- skcms/             # 色彩管理系统
+-- skottie/           # Lottie 动画引擎
+-- skparagraph/       # 段落文本排版
+-- skplaintexteditor/ # 纯文本编辑器
+-- skresources/       # 资源管理
+-- sksg/              # 场景图框架
+-- skshaper/          # 文本整形
+-- skunicode/         # Unicode 处理
+-- svg/               # SVG 渲染
```

## 设计模式分析

1. **模块化架构**: 每个模块都是独立的构建单元,通过 GNI/Bazel 配置文件声明其源文件和依赖关系,支持按需编译。

2. **依赖注入**: 模块间通过接口解耦。例如 skottie 通过 `ResourceProvider` 接口与资源加载解耦,svg 模块通过 `SkShapers::Factory` 与文本整形解耦。

3. **层次化设计**: 模块系统呈现清晰的层次结构 -- 底层基础设施模块 (skcms, jsonreader) 不依赖其他模块,中间层模块 (skresources, skshaper) 提供公共服务,顶层模块 (skottie, svg, canvaskit) 组合各层能力。

4. **平台抽象**: audioplayer 和 skunicode 等模块通过抽象接口屏蔽平台差异,支持多种后端实现。

## 相关文档与参考

- Skia 项目主页: https://skia.org/
- Skia 核心 API: `include/core/`
- GN 构建系统: https://gn.googlesource.com/gn/
- Bazel 构建系统: https://bazel.build/
- Lottie 动画格式: https://lottiefiles.github.io/lottie-docs/
- SVG 1.1 规范: https://www.w3.org/TR/SVG11/
