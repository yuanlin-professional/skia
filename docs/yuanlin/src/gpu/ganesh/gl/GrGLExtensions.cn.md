# GrGLExtensions

> 源文件
> - include/gpu/ganesh/gl/GrGLExtensions.h
> - src/gpu/ganesh/gl/GrGLExtensions.cpp

## 概述

`GrGLExtensions` 类是 Ganesh OpenGL 后端的扩展管理器，负责查询、存储和管理 OpenGL/OpenGL ES/WebGL 以及 EGL 扩展。该类支持多种扩展查询方式（`glGetString` 和 `glGetStringi`），并提供高效的扩展存在性检查，是 Skia GPU 能力检测的核心组件。

该模块在初始化 OpenGL 上下文时被调用，收集所有可用的 OpenGL 扩展，供后续的能力查询（`GrGLCaps`）和功能决策使用。

## 架构位置

该模块位于 Ganesh OpenGL 后端的能力查询层：

```
Skia Graphics Library
└── GPU (Ganesh)
    └── OpenGL Backend
        ├── GrGLInterface         ← 函数指针表
        ├── GrGLExtensions        ← 当前模块（扩展管理）
        ├── GrGLCaps              ← 能力查询（使用扩展信息）
        └── GrGLGpu               ← GPU 实现
```

## 主要类与结构体

### GrGLExtensions

OpenGL 扩展管理类，存储和查询扩展字符串。

**继承关系**: 无继承关系，独立实用类

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fStrings` | `skia_private::TArray<SkString>` | 排序后的扩展名数组 |
| `fInitialized` | `bool` | 初始化状态标志 |

**构造函数与操作符**

| 方法 | 功能描述 |
|------|---------|
| `GrGLExtensions()` | 默认构造函数，创建未初始化的对象 |
| `GrGLExtensions(const GrGLExtensions&)` | 拷贝构造函数 |
| `operator=(const GrGLExtensions&)` | 赋值操作符 |
| `swap(GrGLExtensions*)` | 交换两个对象的内容 |

## 公共 API 函数

### 初始化函数

| 函数签名 | 功能描述 |
|---------|---------|
| `bool init(GrGLStandard standard, GrGLFunction<GrGLGetStringFn> getString, GrGLFunction<GrGLGetStringiFn> getStringi, GrGLFunction<GrGLGetIntegervFn> getIntegerv, GrGLFunction<GrEGLQueryStringFn> queryString = nullptr, GrEGLDisplay eglDisplay = nullptr)` | 从 OpenGL 上下文初始化扩展列表 |

**参数说明**:
- `standard`: OpenGL 标准类型（桌面 GL、ES、WebGL）
- `getString`: `glGetString` 函数指针
- `getStringi`: `glGetStringi` 函数指针（GL 3.0+）
- `getIntegerv`: `glGetIntegerv` 函数指针
- `queryString`: EGL 扩展查询函数（可选）
- `eglDisplay`: EGL 显示句柄（可选）

### 查询函数

| 函数签名 | 功能描述 |
|---------|---------|
| `bool isInitialized() const` | 检查是否已初始化 |
| `bool has(const char[]) const` | 查询是否支持指定扩展 |
| `bool remove(const char[])` | 移除指定扩展（返回是否存在） |
| `void add(const char[])` | 添加扩展到列表 |
| `void reset()` | 清空所有扩展 |
| `void dumpJSON(SkJSONWriter*) const` | 导出为 JSON 格式（调试用） |

## 内部实现细节

### 扩展查询策略

根据 OpenGL 版本选择不同的查询方式：

```cpp
bool indexed = false;
if (GR_IS_GR_GL(standard) || GR_IS_GR_GL_ES(standard)) {
    // GL 和 ES 3.0+ 支持索引查询
    indexed = version >= GR_GL_VER(3, 0);
} else if (GR_IS_GR_WEBGL(standard)) {
    // WebGL 2.0+ 通过 Emscripten 支持索引查询
    indexed = version >= GR_GL_VER(2, 0);
}
```

**索引查询方式（GL 3.0+）**:
```cpp
GrGLint extensionCnt = 0;
getIntegerv(GR_GL_NUM_EXTENSIONS, &extensionCnt);
fStrings.push_back_n(extensionCnt);
for (int i = 0; i < extensionCnt; ++i) {
    const char* ext = (const char*) getStringi(GR_GL_EXTENSIONS, i);
    fStrings[i] = ext;
}
```

**字符串查询方式（GL < 3.0）**:
```cpp
const char* extensions = (const char*) getString(GR_GL_EXTENSIONS);
eat_space_sep_strings(&fStrings, extensions);
```

### EGL 扩展合并

如果提供了 EGL 查询函数，会将 EGL 扩展也添加到列表：

```cpp
if (queryString) {
    const char* extensions = queryString(eglDisplay, GR_EGL_EXTENSIONS);
    eat_space_sep_strings(&fStrings, extensions);
}
```

### 字符串解析

`eat_space_sep_strings()` 函数解析空格分隔的扩展字符串：

```cpp
static void eat_space_sep_strings(TArray<SkString>* out, const char in[]) {
    if (!in) return;
    while (true) {
        // 跳过多个连续空格
        while (' ' == *in) { ++in; }
        // 到达字符串末尾
        if ('\0' == *in) break;
        // 找到一个扩展
        size_t length = strcspn(in, " ");
        out->push_back().set(in, length);
        in += length;
    }
}
```

### 排序与二分查找

初始化后对扩展数组排序，支持高效查找：

```cpp
if (!fStrings.empty()) {
    SkTQSort(fStrings.begin(), fStrings.end(), extension_compare);
}

// 查找使用二分搜索
static int find_string(const TArray<SkString>& strings, const char ext[]) {
    SkString extensionStr(ext);
    int idx = SkTSearch<SkString, extension_compare>(
        &strings.front(),
        strings.size(),
        extensionStr,
        sizeof(SkString));
    return idx;
}
```

### 扩展移除

移除扩展后需要重新排序受影响的部分：

```cpp
bool GrGLExtensions::remove(const char ext[]) {
    int idx = find_string(fStrings, ext);
    if (idx < 0) return false;

    fStrings.removeShuffle(idx);  // 移除元素
    if (idx != fStrings.size()) {
        // 重新排序受影响的部分
        SkTInsertionSort(fStrings.begin() + idx,
                        fStrings.size() - idx,
                        extension_compare);
    }
    return true;
}
```

### 扩展添加

添加扩展时避免重复，并保持排序：

```cpp
void GrGLExtensions::add(const char ext[]) {
    int idx = find_string(fStrings, ext);
    if (idx < 0) {  // 不存在才添加
        fStrings.emplace_back(ext);
        SkTInsertionSort(fStrings.begin(), fStrings.size(), extension_compare);
    }
}
```

### 比较函数

使用字符串比较作为排序键：

```cpp
inline bool extension_compare(const SkString& a, const SkString& b) {
    return strcmp(a.c_str(), b.c_str()) < 0;
}
```

## 依赖关系

### 依赖的模块

| 模块名称 | 依赖原因 |
|---------|---------|
| `GrGLFunctions` | 定义 OpenGL 函数指针类型 |
| `GrGLTypes` | 定义 OpenGL 类型（`GrGLStandard` 等） |
| `SkString` | 存储扩展名字符串 |
| `SkTArray` | 动态数组容器 |
| `SkTSearch` | 二分查找算法 |
| `SkTSort` | 排序算法 |
| `GrGLDefines` | OpenGL 常量定义 |
| `GrGLUtil` | OpenGL 工具函数 |

### 被依赖的模块

| 模块名称 | 使用方式 |
|---------|---------|
| `GrGLCaps` | 查询扩展支持情况以确定能力 |
| `GrGLGpu` | 根据扩展支持启用功能 |
| `GrGLInterface` | 初始化时创建扩展对象 |
| 测试代码 | 模拟扩展支持进行测试 |

## 设计模式与设计决策

### 1. 延迟初始化模式

对象可以先创建，后初始化，支持灵活的使用场景。

### 2. 查询策略模式

根据 OpenGL 版本自动选择最优的扩展查询方式（索引 vs 字符串）。

### 3. 排序与二分查找优化

初始化时一次性排序，后续查询使用 O(log n) 的二分查找。

### 4. 增量修改支持

支持运行时添加和移除扩展，用于测试和特殊场景（如禁用某些扩展）。

### 5. 多源扩展合并

支持同时收集 OpenGL 和 EGL 扩展，统一管理。

### 6. 值语义

支持拷贝和赋值，便于存储和传递。

### 7. 条件编译

调试功能（如 `dumpJSON`）使用条件编译，避免生产代码膨胀。

## 性能考量

### 1. 一次性排序

初始化时排序一次，后续查询无需排序开销。

### 2. 二分查找

扩展查询使用 O(log n) 的二分查找，典型场景下有 100-200 个扩展。

### 3. 字符串去重

添加扩展时自动去重，避免重复存储。

### 4. 插入排序优化

添加/移除扩展时使用插入排序，对于小范围修改效率高。

### 5. 避免动态内存分配

使用 `TArray` 的预分配机制，减少多次扩容。

### 6. 字符串共享

`SkString` 内部使用引用计数，复制时共享数据。

### 7. 内联比较函数

比较函数定义为内联，减少函数调用开销。

## 相关文件

| 文件路径 | 作用 |
|---------|------|
| `include/gpu/ganesh/gl/GrGLFunctions.h` | OpenGL 函数指针类型定义 |
| `include/gpu/ganesh/gl/GrGLTypes.h` | OpenGL 类型定义 |
| `src/gpu/ganesh/gl/GrGLDefines.h` | OpenGL 常量定义 |
| `src/gpu/ganesh/gl/GrGLUtil.h` | OpenGL 工具函数 |
| `src/gpu/ganesh/gl/GrGLCaps.h` | OpenGL 能力查询（使用扩展） |
| `src/gpu/ganesh/gl/GrGLGpu.h` | OpenGL GPU 实现 |
| `include/gpu/ganesh/gl/GrGLInterface.h` | OpenGL 接口封装 |
| `include/core/SkString.h` | 字符串类 |
| `include/private/base/SkTArray.h` | 动态数组 |
| `src/base/SkTSearch.h` | 二分查找算法 |
| `src/base/SkTSort.h` | 排序算法 |
