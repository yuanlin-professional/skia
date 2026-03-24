# jni_skqp.cpp - SkQP Android JNI 桥接层

> 源文件: `tools/skqp/src/jni_skqp.cpp`

## 概述

`jni_skqp.cpp` 实现了 SkQP（Skia Quality Program）测试框架的 JNI（Java Native Interface）桥接层。该文件将 C++ 实现的 SkQP 测试引擎暴露给 Android Java 层的 `org.skia.skqp.SkQP` 类，使得 SkQP 能够作为 Android CTS（Compatibility Test Suite）的一部分在 Android 设备上运行。

核心功能包括：初始化测试引擎并加载 Android Asset 中的测试资源、执行单元测试并返回错误信息、生成测试报告。

## 架构位置

```
SkQP Android 应用
├── Java 层
│   └── org.skia.skqp.SkQP         <-- Java 类，调用 native 方法
├── JNI 桥接层
│   └── jni_skqp.cpp                <-- 本文件：JNI 函数实现
└── C++ 核心层
    └── tools/skqp/src/skqp.h/.cpp  <-- SkQP 测试引擎
```

## 主要类与结构体

### `AndroidAssetManager`
继承自 `SkQPAssetManager` 的 Android 资源管理器，通过 Android NDK 的 `AAssetManager` API 读取 APK 中打包的测试资源。

```cpp
struct AndroidAssetManager : public SkQPAssetManager {
    sk_sp<SkData> open(const char* path) override;
    std::vector<std::string> iterateDir(const char* directory, const char* extension) override;
};
```

- `open(path)`: 从 Android Asset 中读取指定路径的文件并返回 `SkData`
- `iterateDir(directory, extension)`: 遍历指定目录下所有具有特定扩展名的文件

### 全局状态

```cpp
static AndroidAssetManager gAndroidAssetManager;  // 资源管理器单例
static std::mutex gMutex;                          // 线程安全互斥锁
static SkQP gSkQP;                                 // SkQP 测试引擎单例
static AAssetManager* sAAssetManager;              // Android Asset 管理器指针
```

## 公共 API 函数

### JNI 导出函数

#### `Java_org_skia_skqp_SkQP_nInit`
```cpp
void Java_org_skia_skqp_SkQP_nInit(JNIEnv*, jobject, jobject assetManager, jstring dataDir);
```
初始化 SkQP 测试引擎。接收 Android `AssetManager` 和报告输出目录路径。初始化后将可用的单元测试列表和 SkSL 错误测试信息设置到 Java 对象的字段中。

#### `Java_org_skia_skqp_SkQP_nExecuteUnitTest`
```cpp
jobjectArray Java_org_skia_skqp_SkQP_nExecuteUnitTest(JNIEnv*, jobject, jint index);
```
执行指定索引的单元测试。返回错误信息的字符串数组，如果测试通过则返回 `nullptr`。

#### `Java_org_skia_skqp_SkQP_nMakeReport`
```cpp
void Java_org_skia_skqp_SkQP_nMakeReport(JNIEnv*, jobject);
```
生成测试报告，将结果写入初始化时指定的输出目录。

## 内部实现细节

### Asset 数据读取

`open_asset_data()` 函数通过 Android NDK 的 `AAssetManager` API 读取资源：

```cpp
static sk_sp<SkData> open_asset_data(const char* path) {
    AAsset* asset = AAssetManager_open(sAAssetManager, path, AASSET_MODE_STREAMING);
    size_t size = SkToSizeT(AAsset_getLength(asset));
    data = SkData::MakeUninitialized(size);
    AAsset_read(asset, data->writable_data(), size);
    AAsset_close(asset);
    return data;
}
```

此函数同时被注册为 `gResourceFactory`，使得 Skia 的 `tools/Resources` 框架也能通过 Android Asset 读取测试资源。

### JNI 辅助函数

- `make_java_string_array(env, size)`: 创建 Java `String[]` 数组
- `set_string_array_element(env, array, str, index)`: 设置数组元素
- `to_java_string_array(env, vector, stringizeFn)`: 模板函数，将 C++ `std::vector` 转换为 Java 字符串数组，支持自定义的字符串化函数
- `to_string(env, jString)`: 将 Java `jstring` 转换为 C++ `std::string`

### 错误处理宏

```cpp
#define jassert(env, cond, ret) do { if (!(cond)) { \
    (env)->ThrowNew((env)->FindClass("java/lang/Exception"), \
                    __FILE__ ": assert(" #cond ") failed."); \
    return ret; } } while (0)
```

该宏在条件不满足时向 Java 层抛出异常并从 native 函数返回。它通过 `__FILE__` 和 `#cond` 预处理器字符串化提供文件名和失败条件的调试信息。`ret` 参数允许在不同返回类型的函数中使用（对于 `void` 函数，传入空参数）。

### 线程安全

所有 JNI 函数在访问全局 `gSkQP` 对象时都使用 `std::lock_guard<std::mutex>` 进行保护。代码注释中也承认全局变量的设计不理想，建议未来由 Java 对象管理指针和并发控制。

## 依赖关系

- **Android NDK**：`<jni.h>`, `<android/asset_manager.h>`, `<android/asset_manager_jni.h>`
- **Skia 核心**：`SkStream`, `SkData`
- **Skia 工具**：`SkOSPath`, `ResourceFactory`
- **SkQP 框架**：`tools/skqp/src/skqp.h`
- **C++ 标准库**：`<mutex>`, `<sys/stat.h>`

## 设计模式与设计决策

1. **桥接模式（Bridge Pattern）**：JNI 层作为 Java 和 C++ 之间的桥接，将 Android 平台的资源访问机制适配到 SkQP 的 `SkQPAssetManager` 接口。

2. **全局单例**：`gSkQP` 和 `gAndroidAssetManager` 使用全局变量，简化了 JNI 调用的状态管理。源码注释表明这是一个已知的技术债务。

3. **工厂函数注册**：通过 `gResourceFactory = &open_asset_data` 将 Android Asset 读取注册为 Skia 资源工厂，使得所有使用 `tools/Resources` 框架的代码都能透明地从 APK Asset 读取数据。

4. **防御性编程**：`jassert` 宏在每个可能失败的 JNI 操作后进行检查，确保异常被正确传播到 Java 层。

## 性能考量

- **流式读取模式**：使用 `AASSET_MODE_STREAMING` 打开 Asset 文件，适合较大文件的读取。
- **全局互斥锁**：使用单一互斥锁保护所有 SkQP 操作，简单但可能在多线程场景下成为瓶颈。对于 CTS 测试场景，这通常不是问题，因为测试按顺序执行。
- **JNI 本地引用管理**：在 `set_string_array_element` 中使用 `DeleteLocalRef` 及时释放 JNI 本地引用，避免在循环中超出本地引用表限制。
- **全局引用**：`nExecuteUnitTest` 返回的数组使用 `NewGlobalRef`，需要 Java 层负责释放。
- **模板函数优化**：`to_java_string_array` 使用模板接受不同类型的容器和字符串化函数，编译时生成特化版本，避免运行时的虚函数开销。
- **SkData 的引用计数**：`open_asset_data` 返回 `sk_sp<SkData>`（引用计数智能指针），确保 Asset 数据在不再使用时自动释放。
- **一次性初始化**：`nInit` 中的所有初始化操作（测试列表获取、Java 字段设置）在互斥锁保护下一次完成，后续测试执行不需要重复初始化。

## 相关文件

- `tools/skqp/src/skqp.h` - SkQP 核心测试引擎定义（`SkQP` 类、`SkQPAssetManager` 接口）
- `tools/skqp/src/skqp_main.cpp` - 命令行版本入口（非 Android）
- `tools/ResourceFactory.h` - Skia 资源工厂接口（`gResourceFactory` 全局变量）
- `platform_tools/android/apps/skqp/src/main/java/org/skia/skqp/SkQP.java` - 对应的 Java 类（定义 mUnitTests 等字段）
- `tools/skqp/create_apk.py` - APK 构建脚本
- `tools/skqp/src/skqp_GpuTestProcs.cpp` - GPU 测试过程实现
- `src/utils/SkOSPath.h` - 路径拼接工具（`SkOSPath::Join`）
- `include/core/SkStream.h` - 数据流接口
- `include/private/base/SkTo.h` - 类型安全的转换工具（`SkToSizeT`, `SkToInt`）
