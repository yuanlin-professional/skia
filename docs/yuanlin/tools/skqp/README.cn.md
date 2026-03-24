# Skia SKQP 质量保障测试工具

## 概述

`tools/skqp`（Skia Quality Program）是 Android CTS（兼容性测试套件）的组成部分，用于测试 Android 设备的 GPU 以及 OpenGL ES 和 Vulkan 驱动程序。它利用 Skia 现有的单元测试和渲染测试，在目标设备上验证图形驱动的正确性和合规性。SKQP 可以作为 Android APK 运行，也可以作为独立的命令行可执行文件运行。

## 目录结构

```
tools/skqp/
├── README.md                         # 英文使用文档
├── create_apk.py                     # APK 创建脚本
├── make_apk.sh                       # APK 构建 Shell 脚本
├── make_universal_apk                # 通用 APK 构建入口
├── make_universal_apk.py             # 通用 APK 构建 Python 脚本
├── docker_build_universal_apk.sh     # Docker 中构建通用 APK
├── docker_run_apk.sh                 # Docker 中运行 APK
├── run_apk.sh                        # 在设备上运行 APK
├── test_apk.sh                       # 测试 APK 脚本
├── run_skqp_exe                      # 命令行可执行文件运行脚本
├── clean_app.sh                      # 清理应用数据
├── setup_resources                   # 设置测试资源
└── src/
    ├── skqp.h                        # SkQP 核心类声明
    ├── skqp.cpp                      # SkQP 核心实现
    ├── skqp_main.cpp                 # 命令行入口
    ├── skqp_GpuTestProcs.cpp         # GPU 测试过程
    └── jni_skqp.cpp                  # Android JNI 接口
```

## 核心架构

### SkQP 类

```cpp
class SkQP {
public:
    using UnitTest = const skiatest::Test*;

    struct SkSLErrorTest {
        std::string name;
        std::string shaderText;
    };

    void init(SkQPAssetManager* assetManager, const char* reportDirectory);
    std::vector<std::string> executeTest(UnitTest);
    void makeReport();

    const std::vector<UnitTest>& getUnitTests() const;
    const std::vector<SkSLErrorTest>& getSkSLErrorTests() const;
};
```

**核心方法：**

| 方法 | 说明 |
|------|------|
| `init()` | 初始化 Skia 和 SkQP，接收资源管理器和报告目录 |
| `executeTest()` | 执行单个单元测试，返回错误列表 |
| `makeReport()` | 生成 HTML 格式的测试报告 |
| `getUnitTests()` | 获取所有 GPU 单元测试列表 |
| `getSkSLErrorTests()` | 获取所有 SkSL 错误测试列表 |

### SkQPAssetManager

抽象资源管理器接口：

```cpp
class SkQPAssetManager {
public:
    virtual sk_sp<SkData> open(const char* path) = 0;
    virtual std::vector<std::string> iterateDir(const char* directory,
                                                 const char* extension) = 0;
};
```

### JNI 接口（jni_skqp.cpp）

为 Android APK 提供 Java 到 C++ 的桥接层：

- 将 Java 调用转发到 SkQP C++ 核心
- 管理 Android 资产（Assets）的访问
- 处理 Android Instrumentation 测试框架的回调

## 构建和运行

### APK 方式

```bash
# 1. 获取依赖
git clone https://skia.googlesource.com/skia.git
cd skia
git checkout origin/skqp/dev

# 2. 构建 APK
tools/git-sync-deps
tools/skqp/make_universal_apk

# 3. 安装并运行
adb install -r out/skqp/skqp-universal-debug.apk
adb shell am instrument -w org.skia.skqp

# 4. 查看日志
adb logcat TestRunner org.skia.skqp skia "*:S"

# 5. 获取报告
OUTPUT_LOCATION="/storage/emulated/0/Android/data/org.skia.skqp/files/output"
adb pull $OUTPUT_LOCATION /tmp/
# 打开 /tmp/output/skqp_report/report.html
```

### 运行单个测试

```bash
# 运行指定的渲染测试
adb shell am instrument \
  -e class 'org.skia.skqp.SkQPRunner#gles_aarectmodes' \
  -w org.skia.skqp

# 运行指定的单元测试
adb shell am instrument \
  -e class 'org.skia.skqp.SkQPRunner#unitTest_GrSurface' \
  -w org.skia.skqp
```

### 命令行可执行文件方式

```bash
# 构建命令行版本
ninja -C out/skqp/arm skqp

# 推送并运行
python tools/skqp/run_skqp_exe out/skqp/arm
```

## 测试类型

| 测试类型 | 说明 |
|---------|------|
| GPU 单元测试 | Skia GPU 功能的正确性测试 |
| SkSL 错误测试 | SkSL 着色器语言的错误处理验证 |
| 渲染测试 | GPU 渲染结果的视觉正确性验证 |

## 依赖项

- Java JDK 8
- Android NDK
- Android SDK
- depot_tools
- Git 和 Python

## 与其他模块的关系

- **tests/**: SKQP 复用 Skia 的单元测试套件
- **gm/**: 渲染测试基于 GM（Golden Master）测试
- **src/gpu/**: GPU 后端的正确性验证
- **src/sksl/**: SkSL 编译器的错误处理测试
