# VulkanExtensions

> 源文件：
> - include/gpu/vk/VulkanExtensions.h
> - src/gpu/vk/VulkanExtensions.cpp

## 概述

`VulkanExtensions` 是 Skia Vulkan 后端中用于快速查询 Vulkan 扩展是否存在的辅助类。它接收实例扩展和设备扩展的字符串数组，构建一个排序的数据结构，并提供高效的查询接口来检查特定扩展是否可用及其规范版本。

该类的主要目的是将线性的扩展名称列表转换为可二分查找的有序数组，提升扩展查询性能，特别是在需要多次查询扩展可用性的场景下。

## 架构位置

该类位于 Skia GPU 后端的 Vulkan 实现层：

```
skia/
├── include/gpu/vk/          # Vulkan 公共接口
│   └── VulkanExtensions.h
└── src/gpu/vk/              # Vulkan 实现
    └── VulkanExtensions.cpp
```

该类是 Skia Vulkan 后端的基础设施组件，在 Vulkan 上下文初始化时使用，为其他模块提供扩展查询服务。

## 主要类与结构体

### VulkanExtensions

公共 API 类，负责管理和查询 Vulkan 扩展信息。

**继承关系：**
- 无继承关系

**关键成员变量：**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fExtensions` | `skia_private::TArray<Info>` | 存储扩展信息的排序数组 |

### VulkanExtensions::Info

嵌套的扩展信息结构体，存储每个扩展的名称和版本。

**关键成员变量：**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fName` | `SkString` | 扩展名称字符串 |
| `fSpecVersion` | `uint32_t` | 扩展的规范版本号 |

### VulkanExtensions::Info::Less

嵌套的比较器结构体，用于二分查找和排序操作。

**关键函数：**

| 函数签名 | 说明 |
|---------|------|
| `bool operator()(const Info& a, const SkString& b) const` | 比较 Info 和 SkString |
| `bool operator()(const SkString& a, const Info& b) const` | 比较 SkString 和 Info |

## 公共 API 函数

### 构造与初始化

| 函数签名 | 说明 |
|---------|------|
| `VulkanExtensions()` | 默认构造函数，创建空的扩展集合 |
| `void init(VulkanGetProc, VkInstance, VkPhysicalDevice, uint32_t, const char* const*, uint32_t, const char* const*)` | 初始化扩展列表，合并实例和设备扩展 |

**init 函数参数说明：**
- `VulkanGetProc`：Vulkan 函数加载器
- `VkInstance`：Vulkan 实例句柄
- `VkPhysicalDevice`：物理设备句柄
- `uint32_t instanceExtensionCount`：实例扩展数量
- `const char* const* instanceExtensions`：实例扩展名称数组
- `uint32_t deviceExtensionCount`：设备扩展数量
- `const char* const* deviceExtensions`：设备扩展名称数组

### 查询接口

| 函数签名 | 说明 |
|---------|------|
| `bool hasExtension(const char ext[], uint32_t minVersion) const` | 检查指定扩展是否存在且版本不低于 minVersion |

### 调试接口

| 函数签名 | 说明 |
|---------|------|
| `void dump() const` | 在调试模式下打印所有扩展及其版本（仅 SK_DEBUG） |

## 内部实现细节

### 初始化流程

`init()` 函数的实现分为以下步骤：

1. **合并扩展列表**：
   - 遍历实例扩展数组，使用 `find_info()` 检查扩展是否已存在
   - 如果不存在，创建 `Info` 对象并添加到 `fExtensions` 数组
   - 每次添加后使用 `SkTQSort()` 对数组排序，保持有序状态
   - 对设备扩展执行相同操作

2. **查询版本信息**：
   - 调用 `getSpecVersions()` 从 Vulkan 驱动查询每个扩展的实际规范版本
   - 使用 `vkEnumerateInstanceExtensionProperties` 查询实例扩展版本
   - 使用 `vkEnumerateDeviceExtensionProperties` 查询设备扩展版本
   - 更新 `fExtensions` 中对应扩展的 `fSpecVersion` 字段

### 扩展查找算法

`find_info()` 函数实现高效的扩展名称查找：

```cpp
static int find_info(const TArray<VulkanExtensions::Info>& infos, const char ext[]) {
    if (infos.empty()) {
        return -1;
    }
    SkString extensionStr(ext);
    VulkanExtensions::Info::Less less;
    int idx = SkTSearch<VulkanExtensions::Info, SkString, VulkanExtensions::Info::Less>(
            &infos.front(), infos.size(), extensionStr, sizeof(VulkanExtensions::Info),
            less);
    return idx;
}
```

- 使用 `SkTSearch` 模板函数执行二分查找
- 时间复杂度：O(log n)
- 返回值：找到返回索引，未找到返回负数

### 排序策略

使用 `SkTQSort` 对扩展数组进行快速排序：

```cpp
inline bool extension_compare(const VulkanExtensions::Info& a, const VulkanExtensions::Info& b) {
    return strcmp(a.fName.c_str(), b.fName.c_str()) < 0;
}
```

- 按扩展名称的字典序排序
- 每次插入新扩展后立即重新排序
- 保证查询时数组始终有序

### 版本查询实现

`getSpecVersions()` 函数使用 Vulkan API 查询扩展版本：

1. **实例扩展版本**：
   - 调用 `vkEnumerateInstanceExtensionProperties(nullptr, &count, nullptr)` 获取数量
   - 分配 `VkExtensionProperties` 数组
   - 再次调用获取完整信息
   - 遍历结果，使用 `find_info()` 匹配并更新版本

2. **设备扩展版本**：
   - 类似流程，使用 `vkEnumerateDeviceExtensionProperties`
   - 针对特定物理设备查询

### hasExtension 实现

```cpp
bool VulkanExtensions::hasExtension(const char ext[], uint32_t minVersion) const {
    int idx = find_info(fExtensions, ext);
    return  idx >= 0 && fExtensions[idx].fSpecVersion >= minVersion;
}
```

- 首先使用二分查找定位扩展
- 然后检查版本是否满足最低要求
- 两个条件都满足才返回 true

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `include/core/SkString.h` | 字符串类型 |
| `include/gpu/vk/VulkanTypes.h` | VulkanGetProc 等类型定义 |
| `include/private/base/SkAPI.h` | API 导出宏 |
| `include/private/base/SkDebug.h` | 调试输出 |
| `include/private/base/SkTArray.h` | 动态数组容器 |
| `include/private/gpu/vk/SkiaVulkan.h` | Vulkan 类型和函数声明 |
| `src/base/SkTSearch.h` | 二分查找算法 |
| `src/base/SkTSort.h` | 排序算法 |

### 被依赖的模块

该类主要被以下模块使用：

| 模块 | 使用场景 |
|------|---------|
| `VulkanBackendContext` | 初始化 Vulkan 上下文时查询扩展支持 |
| `VulkanInterface` | 检查扩展可用性 |
| `VulkanCaps` | 根据扩展确定设备能力 |
| 各种 Vulkan 功能模块 | 在使用扩展功能前检查其是否可用 |

## 设计模式与设计决策

### 延迟初始化模式

类使用默认构造函数创建空对象，通过显式调用 `init()` 完成初始化。这种设计允许：
- 对象创建与初始化分离
- 支持对象重用
- 避免构造函数抛出异常

### 查找优化

采用排序数组 + 二分查找的策略，而非哈希表：
- **优点**：内存占用小，缓存友好，适合小到中等规模数据集
- **缺点**：插入时需要重新排序（但初始化只发生一次）
- **权衡**：查询是主要操作，O(log n) 的查询性能可接受

### 不重复原则

初始化时检查扩展是否已存在，避免重复添加：
- 实例扩展和设备扩展可能有重叠（如某些扩展同时在两处暴露）
- 保持扩展列表唯一性，简化后续逻辑

### 版本感知

不仅存储扩展是否存在，还存储其版本号：
- 支持检查特定版本的扩展
- 允许根据扩展版本选择不同的代码路径
- 符合 Vulkan 扩展演进的实际需求

## 性能考量

### 初始化性能

初始化过程涉及多次排序操作：
- 每插入一个扩展就排序一次
- 对于 n 个扩展，总时间复杂度约为 O(n² log n)
- **优化空间**：可以先收集所有扩展，最后排序一次，降至 O(n log n)
- **当前设计理由**：扩展数量通常不多（几十个），初始化只执行一次，性能影响可忽略

### 查询性能

二分查找提供 O(log n) 的查询时间：
- 对于 30 个扩展，最多需要 5 次比较
- 字符串比较是瓶颈，但由于数组有序，可以尽早终止

### 内存开销

- 每个扩展存储一个 `SkString` 和一个 `uint32_t`
- `SkString` 内部可能动态分配内存
- 总体内存占用：约 (字符串长度 + 24 字节) × 扩展数量

### 缓存友好性

排序数组的连续内存布局有利于 CPU 缓存：
- 二分查找过程访问的数据局部性较好
- 相比哈希表的随机访问模式更友好

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/gpu/vk/VulkanBackendContext.h` | 使用 | 后端上下文使用该类管理扩展 |
| `src/gpu/vk/VulkanInterface.h` | 使用 | Vulkan 接口层使用该类 |
| `src/gpu/vk/VulkanCaps.h` | 使用 | 能力检测依赖扩展信息 |
| `include/gpu/vk/VulkanTypes.h` | 依赖 | 类型定义 |
| `include/gpu/vk/VulkanPreferredFeatures.h` | 相关 | 功能管理类，与扩展管理互补 |
| `src/base/SkTSearch.h` | 依赖 | 提供二分查找算法 |
| `src/base/SkTSort.h` | 依赖 | 提供排序算法 |

### 典型使用场景

```cpp
// 1. 创建扩展对象
VulkanExtensions extensions;

// 2. 初始化（在 VulkanBackendContext 创建时）
extensions.init(getProc, instance, physicalDevice,
                instanceExtCount, instanceExts,
                deviceExtCount, deviceExts);

// 3. 查询扩展
if (extensions.hasExtension(VK_KHR_SWAPCHAIN_EXTENSION_NAME, 1)) {
    // 使用 swapchain 扩展
}

// 4. 调试输出（仅 debug 模式）
#ifdef SK_DEBUG
extensions.dump();
#endif
```

### 注意事项

1. **必须先初始化**：调用 `hasExtension()` 前必须先调用 `init()`
2. **实例和物理设备生命周期**：传递给 `init()` 的 VkInstance 和 VkPhysicalDevice 必须在查询版本时有效
3. **扩展名称格式**：使用标准的 Vulkan 扩展名称常量（如 `VK_KHR_*_EXTENSION_NAME`）
4. **版本号含义**：版本号是扩展的规范版本，不是 Vulkan API 版本
