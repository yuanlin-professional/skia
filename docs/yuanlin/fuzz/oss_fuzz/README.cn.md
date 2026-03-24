# fuzz/oss_fuzz/ - OSS-Fuzz 集成入口

## 概述

`fuzz/oss_fuzz/` 目录包含 Skia 为 [OSS-Fuzz](https://github.com/google/oss-fuzz) 持续模糊测试平台提供的独立 fuzzer 入口文件。每个文件实现了标准的 `LLVMFuzzerTestOneInput` 函数接口，使得每个 fuzzer 可以被 libFuzzer、AFL 等模糊测试引擎直接驱动。

该目录包含约 49 个独立的 fuzzer 入口文件，覆盖了 Skia 的绝大部分可被模糊测试的 API 表面。与 `fuzz/` 根目录中的 `DEF_FUZZ` 注册式 fuzzer 不同，这些文件每个都是一个独立的编译单元，编译后产生一个独立的可执行文件，直接与 libFuzzer 链接。

这些 fuzzer 通过 OSS-Fuzz 基础设施在 Google 的集群上持续运行，每秒执行数百万次测试输入。当发现崩溃、内存泄漏、ASAN/UBSAN/MSAN 报告时，OSS-Fuzz 会自动在 Chromium Bug Tracker 上提交 bug，并在 Skia 团队修复后自动关闭。

fuzzer 分为以下几类：图像格式解码（各种图像格式的解码路径）、数据反序列化（SkPath、SkRegion、TextBlob 等的反序列化）、SkSL 编译器（SkSL 到各后端的编译路径）、编码器（PNG、JPEG、WebP 编码）、运行时效果（RuntimeEffect、RuntimeBlender、RuntimeColorFilter）以及 SVG/JSON 解析。

## 架构图

```
+--------------------------------------------------------------+
|                    OSS-Fuzz 基础设施                          |
|  +----------------------------------------------------------+|
|  |  模糊测试引擎                                             ||
|  |  +-----------+ +----------+ +-----------+                 ||
|  |  | libFuzzer | | AFL-Fuzz | | Honggfuzz |                 ||
|  |  +-----------+ +----------+ +-----------+                 ||
|  +----------------------------------------------------------+|
|                            |                                  |
|  +----------------------------------------------------------+|
|  |  LLVMFuzzerTestOneInput(const uint8_t* data, size_t size)||
|  +----------------------------------------------------------+|
+----------------------------+---------------------------------+
                             |
              +--------------+--------------+
              |              |              |
+-------------v--+ +---------v----+ +------v----------+
| 图像解码       | | 数据反序列化 | | SkSL 编译器     |
| FuzzImage      | | FuzzPath     | | FuzzSKSL2GLSL   |
| FuzzAndroid    | | FuzzRegion   | | FuzzSKSL2Metal  |
| Codec          | | FuzzTextBlob | | FuzzSKSL2SPIRV  |
| FuzzAnimated   | | Deserialize  | | FuzzSKSL2WGSL   |
| Image          | |              | | FuzzSKSL2       |
+----------------+ +--------------+ | Pipeline        |
                                    +-----------------+
```

## 目录结构

```
fuzz/oss_fuzz/
├── [图像解码 Fuzzer]
│   ├── FuzzImage.cpp                  # 通用图像解码
│   ├── FuzzIncrementalImage.cpp       # 增量图像解码
│   ├── FuzzAndroidCodec.cpp           # Android 编解码路径
│   ├── FuzzAnimatedImage.cpp          # 动画图像 (GIF/WebP 动画)
│   ├── FuzzBMPRustDecoder.cpp         # BMP Rust 解码器
│   └── FuzzCOLRv1.cpp                 # COLRv1 彩色字体表
│
├── [图像编码 Fuzzer]
│   ├── FuzzPNGEncoder.cpp             # PNG 编码器
│   ├── FuzzPNGRustEncoder.cpp         # PNG Rust 编码器
│   ├── FuzzJPEGEncoder.cpp            # JPEG 编码器
│   └── FuzzWEBPEncoder.cpp            # WebP 编码器
│
├── [数据反序列化 Fuzzer]
│   ├── FuzzPathDeserialize.cpp        # SkPath 反序列化
│   ├── FuzzRegionDeserialize.cpp      # SkRegion 反序列化
│   ├── FuzzRegionSetPath.cpp          # Region::setPath
│   ├── FuzzTextBlobDeserialize.cpp    # SkTextBlob 反序列化
│   ├── FuzzImageFilterDeserialize.cpp # SkImageFilter 反序列化
│   ├── FuzzSkDescriptorDeserialize.cpp# SkDescriptor 反序列化
│   ├── FuzzSkMeshSpecification.cpp    # SkMesh 规范
│   └── FuzzColorspace.cpp             # 色彩空间反序列化
│
├── [SkSL 编译器 Fuzzer]
│   ├── FuzzSKSL2GLSL.cpp             # SkSL -> GLSL
│   ├── FuzzSKSL2Metal.cpp            # SkSL -> Metal Shading Language
│   ├── FuzzSKSL2Pipeline.cpp         # SkSL -> Pipeline Stage
│   ├── FuzzSKSL2SPIRV.cpp            # SkSL -> SPIR-V
│   └── FuzzSKSL2WGSL.cpp             # SkSL -> WGSL (WebGPU)
│
├── [API Fuzzer]
│   ├── FuzzDrawFunctions.cpp          # 绘制函数
│   ├── FuzzGradients.cpp              # 渐变效果
│   ├── FuzzGrStyledShape.cpp          # Ganesh 样式化形状
│   ├── FuzzParsePath.cpp              # SVG 路径解析
│   ├── FuzzPathMeasure.cpp            # 路径测量
│   ├── FuzzPathop.cpp                 # 路径布尔运算
│   ├── FuzzPolyUtils.cpp              # 多边形工具
│   ├── FuzzTriangulation.cpp          # 三角化
│   ├── FuzzCubicRoots.cpp             # 三次方程求根
│   └── FuzzQuadRoots.cpp              # 二次方程求根
│
├── [运行时效果 Fuzzer]
│   ├── FuzzSkRuntimeEffect.cpp        # RuntimeEffect
│   ├── FuzzSkRuntimeBlender.cpp       # RuntimeBlender
│   └── FuzzSkRuntimeColorFilter.cpp   # RuntimeColorFilter
│
├── [文档/解析 Fuzzer]
│   ├── FuzzSVG.cpp                    # SVG DOM 解析
│   ├── FuzzJSON.cpp                   # JSON 解析
│   └── FuzzSKP.cpp                    # SKP 文件
│
├── [Canvas Fuzzer]
│   ├── FuzzRasterN32Canvas.cpp        # 光栅 N32 Canvas
│   ├── FuzzNullCanvas.cpp             # Null Canvas
│   ├── FuzzMockGPUCanvas.cpp          # Mock GPU Canvas
│   └── FuzzAPISVGCanvas.cpp           # SVG Canvas
│
├── [其他 Fuzzer]
│   ├── FuzzAPIImageFilter.cpp         # ImageFilter API
│   ├── FuzzAPICreateDDL.cpp           # DDL 创建 API
│   ├── FuzzDDLThreading.cpp           # DDL 多线程
│   ├── FuzzSkParagraph.cpp            # 段落排版
│   └── FuzzPrecompile.cpp             # Graphite 预编译
```

## 关键函数

### 标准 libFuzzer 入口

每个文件都实现了以下标准接口：

```cpp
extern "C" int LLVMFuzzerTestOneInput(const uint8_t* data, size_t size) {
    // 创建 Fuzz 对象并调用目标函数
    // 返回 0 表示正常
}
```

### 典型 fuzzer 实现模式

```cpp
// FuzzImage.cpp 示例
#include "fuzz/Fuzz.h"
#include "include/codec/SkCodec.h"

extern "C" int LLVMFuzzerTestOneInput(const uint8_t* data, size_t size) {
    auto codec = SkCodec::MakeFromData(SkData::MakeWithoutCopy(data, size));
    if (!codec) return 0;  // 无效输入，正常退出

    SkBitmap bitmap;
    bitmap.allocPixels(codec->getInfo());
    codec->getPixels(bitmap.pixmap());
    return 0;
}
```

## 依赖关系

```
oss_fuzz/ 依赖:
├── fuzz/Fuzz.h                    (Fuzz 核心类)
├── fuzz/FuzzCommon.h              (通用工具)
├── include/codec/SkCodec.h        (编解码器)
├── include/core/SkData.h          (数据容器)
├── include/core/SkCanvas.h        (Canvas API)
├── include/core/SkPath.h          (路径)
├── include/core/SkImage.h         (图像)
├── include/effects/SkRuntimeEffect.h (运行时效果)
├── src/sksl/SkSLCompiler.h        (SkSL 编译器)
└── modules/svg/                   (SVG 模块)

构建系统集成:
├── OSS-Fuzz Dockerfile            (构建环境)
├── OSS-Fuzz build.sh              (构建脚本)
└── gs://skia-cdn/oss-fuzz/        (种子语料库存储)
```

## 设计模式分析

### 1. 单一入口模式

每个 fuzzer 文件实现单一的 `LLVMFuzzerTestOneInput` 函数，这是 libFuzzer 的标准接口。这种设计使得每个 fuzzer 可以独立编译、独立运行。

### 2. 优雅降级模式

所有 fuzzer 对无效输入都采用优雅降级策略——对于无法解析的输入直接返回 0 而不是触发断言。这确保了 fuzzer 只在发现真正的 bug 时才报告问题。

### 3. 种子语料库驱动

二进制 fuzzer（图像解码、SkSL 编译等）依赖种子语料库提供有效的初始输入。种子语料库存储在 `gs://skia-cdn/oss-fuzz/` 中，在 OSS-Fuzz Docker 构建时下载。

## 数据流

```
OSS-Fuzz 持续运行流程:

1. 构建阶段 (在 Docker 中)
   Dockerfile 拉取 Skia 源码 + 种子语料库
          |
          v
   build.sh 编译 fuzzer 可执行文件
          |
          v
   将 fuzzer + 种子语料库放入 $OUT

2. 运行阶段 (Google 集群)
   libFuzzer 加载种子语料库
          |
          v
   反复突变种子 -> 生成新输入
          |
          v
   LLVMFuzzerTestOneInput(data, size)
          |
          +-- ASAN/UBSAN/MSAN 报告 --> 自动提 bug
          +-- 崩溃/超时/OOM --> 自动提 bug
          +-- 正常 --> 收集覆盖率 -> 引导突变
          |
          v
   语料库持续增长 (edge coverage driven)

3. 报告阶段
   OSS-Fuzz 自动提交 Chromium Bug Tracker issue
          |
          v
   Skia 团队修复 -> 提交修复代码
          |
          v
   OSS-Fuzz 自动验证修复 -> 关闭 issue
```

## 相关文档与参考

- `fuzz/README.md` - 官方 Fuzzing 说明和 OSS-Fuzz 集成指南
- `fuzz/Fuzz.h` - Fuzz 核心类
- [OSS-Fuzz Skia 项目](https://github.com/google/oss-fuzz/tree/master/projects/skia)
- [OSS-Fuzz Skia 统计面板](https://oss-fuzz.com/fuzzer-stats)
- [OSS-Fuzz 覆盖率报告](https://oss-fuzz.com/coverage-report/job/libfuzzer_asan_skia/latest)
- [libFuzzer 文档](https://llvm.org/docs/LibFuzzer.html)
- [创建二进制 Fuzzer 指南](https://docs.google.com/document/d/1QDX0o8yDdmhbjoudNsXc66iuRXRF5XNNqGnzDzX7c2I/edit)
- [创建 API Fuzzer 指南](https://docs.google.com/document/d/1e3ikXO7SwoBsbsi1MF06vydXRlXvYalVORaiUuOXk2Y/edit)
