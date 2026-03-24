# fuzz/ - Skia 模糊测试（Fuzz Testing）目录

## 概述

`fuzz/` 目录是 Skia 图形库的模糊测试（fuzzing）核心目录，包含约 30 个 fuzzer 实现文件。模糊测试是一种自动化软件测试技术，通过向目标程序输入随机或半随机的数据来发现崩溃、内存错误、未定义行为等问题。

Skia 的 fuzzer 分为两大类：**二进制 fuzzer**（如图像解码器 fuzzer，输入是突变的图像文件）和 **API fuzzer**（输入是随机字节流，被转换为 API 调用序列）。二进制 fuzzer 主要针对 Skia 的数据解析路径（编解码器、SkSL 编译器、反序列化器等），而 API fuzzer 主要针对 Skia 的绘图 API（Canvas、Path、渐变等）。

核心类 `Fuzz`（定义在 `Fuzz.h` 中）是所有 fuzzer 的数据提供者，它从输入字节流中按顺序提取各种类型的值。`FuzzMain.cpp` 提供了一个统一的 fuzzer 可执行文件入口，通过 `--type` 参数选择要运行的 fuzzer 类型。`oss_fuzz/` 子目录包含为 OSS-Fuzz 持续模糊测试平台量身定制的独立 fuzzer 入口文件。

Skia 通过 [OSS-Fuzz](https://github.com/google/oss-fuzz) 进行持续模糊测试，使用 libFuzzer、AFL、Honggfuzz 等多个模糊测试引擎。OSS-Fuzz 在发现问题时会自动在 [Chromium Bug Tracker](https://bugs.chromium.org/p/oss-fuzz/issues/list?q=label:Proj-skia) 上提交和关闭 bug。

## 架构图

```
+------------------------------------------------------------------+
|                     Fuzzing 基础设施                               |
|  +------------------------------------------------------------+  |
|  |                   FuzzMain.cpp (统一入口)                    |  |
|  |  --type api --name <fuzzer_name> --bytes <input_file>       |  |
|  +------------------------------------------------------------+  |
|                              |                                    |
|  +------------------------------------------------------------+  |
|  |                   Fuzz 类 (数据提供者)                       |  |
|  |  next<T>()  |  nextRange()  |  nextEnum()  |  nextN()      |  |
|  +------------------------------------------------------------+  |
|                              |                                    |
|  +------------------------------------------------------------+  |
|  |              DEF_FUZZ 注册的 Fuzzer                          |  |
|  |  +------------------+  +------------------+                 |  |
|  |  | 二进制 Fuzzer    |  | API Fuzzer       |                 |  |
|  |  | (图像解码等)     |  | (Canvas/Path等)  |                 |  |
|  |  +------------------+  +------------------+                 |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
                              |
              +---------------+---------------+
              |                               |
+-------------v-----------+   +---------------v-----------+
| fuzz/oss_fuzz/          |   | OSS-Fuzz 平台             |
| 独立 fuzzer 入口        |    | (libFuzzer/AFL/Honggfuzz) |
| (LLVMFuzzerTestOneInput)|   | 持续运行 + 自动报告      |
+-------------------------+   +---------------------------+
```

## 目录结构

```
fuzz/
├── README.md                      # 官方说明文档
├── Fuzz.h                         # Fuzz 核心类定义
├── Fuzz.cpp                       # Fuzz 类实现
├── FuzzMain.cpp                   # 统一 fuzzer 入口
├── FuzzCommon.h                   # 通用 fuzzing 工具函数
├── FuzzCommon.cpp                 # 工具函数实现
├── FuzzCanvasHelpers.h / .cpp     # Canvas fuzzing 辅助函数
│
├── [API Fuzzer]
│   ├── FuzzCanvas.cpp             # SkCanvas API fuzzer
│   ├── FuzzPath.cpp               # SkPath 路径 fuzzer
│   ├── FuzzParsePath.cpp          # SVG 路径解析 fuzzer
│   ├── FuzzPathMeasure.cpp        # 路径测量 fuzzer
│   ├── FuzzPathop.cpp             # 路径运算 fuzzer
│   ├── FuzzGradients.cpp          # 渐变效果 fuzzer
│   ├── FuzzDrawFunctions.cpp      # 绘制函数 fuzzer
│   ├── FuzzRRect.cpp              # 圆角矩形 fuzzer
│   ├── FuzzRegionOp.cpp           # 区域运算 fuzzer
│   ├── FuzzPolyUtils.cpp          # 多边形工具 fuzzer
│   ├── FuzzTriangulation.cpp      # 三角化 fuzzer
│   ├── FuzzCubicRoots.cpp         # 三次方程求根 fuzzer
│   ├── FuzzQuadRoots.cpp          # 二次方程求根 fuzzer
│   └── FuzzGrStyledShape.cpp      # 样式化形状 fuzzer
│
├── [编解码 Fuzzer]
│   └── FuzzEncoders.cpp           # 图像编码器 fuzzer
│
├── [序列化 Fuzzer]
│   ├── FuzzCreateDDL.cpp          # DDL 创建 fuzzer
│   └── FuzzDDLThreading.cpp       # DDL 多线程 fuzzer
│
├── [文本 Fuzzer]
│   └── FuzzSkParagraph.cpp        # 段落排版 fuzzer
│
├── [GPU Fuzzer]
│   └── FuzzPrecompile.cpp         # Graphite 预编译 fuzzer
│
├── coverage/                      # 覆盖率相关 (空)
│
└── oss_fuzz/                      # OSS-Fuzz 独立入口
    ├── FuzzAndroidCodec.cpp       # Android 编解码 fuzzer
    ├── FuzzAnimatedImage.cpp      # 动画图像 fuzzer
    ├── FuzzImage.cpp              # 图像解码 fuzzer
    ├── FuzzIncrementalImage.cpp   # 增量图像解码 fuzzer
    ├── FuzzBMPRustDecoder.cpp     # BMP Rust 解码器 fuzzer
    ├── FuzzColorspace.cpp         # 色彩空间 fuzzer
    ├── FuzzCOLRv1.cpp             # COLRv1 字体表 fuzzer
    ├── FuzzJSON.cpp               # JSON 解析 fuzzer
    ├── FuzzSVG.cpp                # SVG 解析 fuzzer
    ├── FuzzSKP.cpp                # SKP 文件 fuzzer
    ├── FuzzTextBlobDeserialize.cpp # TextBlob 反序列化 fuzzer
    ├── FuzzPathDeserialize.cpp    # Path 反序列化 fuzzer
    ├── FuzzRegionDeserialize.cpp  # Region 反序列化 fuzzer
    ├── FuzzImageFilterDeserialize.cpp # ImageFilter 反序列化 fuzzer
    ├── FuzzSkDescriptorDeserialize.cpp # Descriptor 反序列化
    ├── FuzzSkMeshSpecification.cpp # Mesh 规范 fuzzer
    ├── FuzzSkRuntimeEffect.cpp    # RuntimeEffect fuzzer
    ├── FuzzSkRuntimeBlender.cpp   # RuntimeBlender fuzzer
    ├── FuzzSkRuntimeColorFilter.cpp # RuntimeColorFilter fuzzer
    ├── FuzzSKSL2GLSL.cpp         # SkSL -> GLSL 编译 fuzzer
    ├── FuzzSKSL2Metal.cpp        # SkSL -> Metal 编译 fuzzer
    ├── FuzzSKSL2Pipeline.cpp     # SkSL -> Pipeline 编译 fuzzer
    ├── FuzzSKSL2SPIRV.cpp        # SkSL -> SPIR-V 编译 fuzzer
    ├── FuzzSKSL2WGSL.cpp         # SkSL -> WGSL 编译 fuzzer
    ├── FuzzPNGEncoder.cpp         # PNG 编码器 fuzzer
    ├── FuzzPNGRustEncoder.cpp     # PNG Rust 编码器 fuzzer
    ├── FuzzJPEGEncoder.cpp        # JPEG 编码器 fuzzer
    ├── FuzzWEBPEncoder.cpp        # WebP 编码器 fuzzer
    └── ...                        # 更多 fuzzer 入口
```

## 关键类与函数

### Fuzz 类（Fuzz.h）

```cpp
class Fuzz {
public:
    explicit Fuzz(const uint8_t* data, size_t size);

    size_t size() const;            // 总数据大小
    bool exhausted() const;         // 数据是否已耗尽
    void deplete();                 // 标记所有数据已消耗
    size_t remainingSize() const;   // 剩余数据大小
    const uint8_t* remainingData() const; // 剩余数据指针

    // 数据提取方法
    template <typename T> void next(T* t);           // 提取单个值
    template <typename Arg, typename... Args>
    void next(Arg* first, Args... rest);             // 提取多个值
    template <typename T> void nextRange(T*, Min, Max); // 范围限制提取
    template <typename T> void nextEnum(T* ptr, T max); // 枚举提取
    template <typename T> void nextN(T* ptr, int n);    // 批量提取

    void next(bool* b);            // 特化: bool
    void next(SkRegion* region);   // 特化: Region
    bool nextBool();               // 便捷方法
    void nextRange(float* f, float min, float max); // 特化: float

    void signalBug();              // 报告发现 bug (SIGSEGV)
};
```

### Fuzzable 结构体与注册宏

```cpp
struct Fuzzable {
    const char* name;       // fuzzer 名称
    void (*fn)(Fuzz*);      // fuzzer 函数指针
};

// 注册宏
#define DEF_FUZZ(name, f) \
    void fuzz_##name(Fuzz*); \
    sk_tools::Registry<Fuzzable> register_##name({#name, fuzz_##name}); \
    void fuzz_##name(Fuzz* f)
```

### FuzzCommon.h 工具函数

| 函数 | 说明 |
|------|------|
| `FuzzNicePath(Fuzz*, SkPathBuilder*, int maxOps)` | 生成合法浮点值的随机路径 |
| `FuzzEvilPath(Fuzz*, int last_verb)` | 生成可能包含 NaN/Inf 的恶意路径 |
| `FuzzNiceRRect(Fuzz*, SkRRect*)` | 生成合法的随机圆角矩形 |
| `FuzzNiceMatrix(Fuzz*, SkMatrix*)` | 生成合法的随机矩阵 |
| `FuzzNiceRegion(Fuzz*, SkRegion*, int maxN)` | 生成合法的随机区域 |
| `FuzzCreateValidInputsForRuntimeEffect(...)` | 为 RuntimeEffect 创建有效输入 |

### FuzzMain.cpp 支持的类型

```
--type 参数支持的值:
  android_codec              # Android 编解码
  animated_image_decode      # 动画图像解码
  api                        # API fuzzer (需配合 --name)
  color_deserialize          # 色彩空间反序列化
  colrv1                     # COLRv1 字体表
  filter_fuzz                # 图像滤镜 (兼容 Chrome)
  image_decode               # 图像解码
  image_decode_incremental   # 增量图像解码
  json                       # JSON 解析
  path_deserialize           # 路径反序列化
  region_deserialize         # 区域反序列化
  skdescriptor_deserialize   # 描述符反序列化
  skmeshspecialization       # Mesh 规范
  skottie_json               # Skottie 动画 (可选)
  skp                        # SKP 文件
  skruntimeblender           # RuntimeBlender
  skruntimecolorfilter       # RuntimeColorFilter
  skruntimeeffect            # RuntimeEffect
  sksl2glsl                  # SkSL -> GLSL
  sksl2metal                 # SkSL -> Metal
  sksl2pipeline              # SkSL -> Pipeline
  sksl2spirv                 # SkSL -> SPIR-V
  sksl2wgsl                  # SkSL -> WGSL
  svg_dom                    # SVG DOM
  textblob                   # TextBlob 反序列化
```

## 依赖关系

```
fuzz/ 依赖关系:
├── include/core/SkData.h            (数据容器)
├── include/core/SkCanvas.h          (Canvas API)
├── include/core/SkPath.h            (路径)
├── include/core/SkImage.h           (图像)
├── include/core/SkRegion.h          (区域)
├── include/codec/SkCodec.h          (编解码器)
├── include/effects/SkRuntimeEffect.h (运行时效果)
├── tools/Registry.h                 (注册表模板)
├── tools/flags/CommandLineFlags.h   (命令行参数)
└── tools/fonts/FontToolUtils.h      (字体工具)

外部系统:
├── OSS-Fuzz (https://github.com/google/oss-fuzz)
├── libFuzzer (LLVM fuzzing 引擎)
├── AFL-Fuzz (American Fuzzy Lop)
└── Honggfuzz
```

## 设计模式分析

### 1. 注册表模式

与测试和基准测试框架一致，fuzzer 使用 `DEF_FUZZ` 宏注册到全局 `sk_tools::Registry<Fuzzable>`。`FuzzMain.cpp` 遍历注册表找到对应名称的 fuzzer。

### 2. 流式数据消费模式

`Fuzz` 类实现了一个确定性的字节流消费器。对于相同的输入字节，`Fuzz` 类保证在所有平台上产生相同的 API 调用序列。注意编译器对函数参数的求值顺序不同（GCC vs Clang），因此 API 设计为通过指针参数传出值而非返回值。

### 3. 种子语料库模式

二进制 fuzzer（如图像解码器）使用种子语料库（seed corpus）提供初始输入样本。模糊测试引擎在这些种子的基础上进行突变，生成新的测试输入。

### 4. 双打包模式

Fuzzer 以两种方式打包：
- **统一可执行文件**（`fuzz`）：包含所有 fuzzer，通过命令行参数选择，方便本地复现
- **独立可执行文件**（`oss_fuzz/` 中的文件）：每个 fuzzer 一个文件，适合 libFuzzer 集成

## 数据流

```
模糊测试执行流程:

1. 统一入口模式 (本地复现)
   fuzz --type api --name ParsePath --bytes crash-input.bin
          |
          v
   读取输入文件 -> sk_sp<SkData>
          |
          v
   根据 --type 分发到对应处理函数
          |
          v
   fuzz_api() -> 遍历 Registry 找到 "ParsePath"
          |
          v
   创建 Fuzz 对象 -> 调用 fuzz_ParsePath(Fuzz*)
          |
          v
   Fuzzer 从 Fuzz 对象提取数据 -> 调用 Skia API
          |
          v
   正常退出 或 触发 bug (crash/ASAN/UBSAN)

2. OSS-Fuzz 模式 (持续运行)
   libFuzzer 引擎生成输入字节
          |
          v
   LLVMFuzzerTestOneInput(data, size)
          |
          v
   创建 Fuzz 对象 -> 调用特定 fuzzer
          |
          v
   libFuzzer 收集覆盖率信息 -> 引导下一轮突变
          |
          +-- 发现 crash --> OSS-Fuzz 自动提交 bug
          |
          +-- 正常 --> 继续突变探索
```

## 相关文档与参考

- `fuzz/README.md` - 官方 Fuzzing 说明文档
- `fuzz/Fuzz.h` - Fuzz 核心类定义
- `fuzz/FuzzCommon.h` - 通用 fuzzing 工具
- `fuzz/FuzzMain.cpp` - 统一入口程序
- `fuzz/oss_fuzz/` - OSS-Fuzz 独立入口文件
- [OSS-Fuzz Skia 项目](https://github.com/google/oss-fuzz/tree/master/projects/skia)
- [Skia Fuzzing 文档](https://skia.org/docs/dev/testing/fuzz/)
- [libFuzzer 文档](https://llvm.org/docs/LibFuzzer.html)
