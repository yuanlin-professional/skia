# SkYUVAInfoLocation

> 源文件: src/core/SkYUVAInfoLocation.h

## 概述

SkYUVAInfoLocation 是 Skia 中用于描述 YUVA 通道在多平面图像中位置的辅助模块。该模块定义了 `SkYUVAInfo::YUVALocation` 结构体,用于指定 Y、U、V 和可选的 A 通道分别位于哪个平面的哪个颜色通道中。它还提供了验证位置配置有效性的静态方法,确保通道映射的正确性和一致性。该模块是连接 SkYUVAInfo 抽象配置与实际像素数据布局的关键桥梁。

## 架构位置

SkYUVAInfoLocation 位于 Skia 核心层的图像表示子系统:

```
src/core/
  └── SkYUVAInfoLocation.h     # YUVA 位置定义（本模块）
include/core/
  ├── SkYUVAInfo.h              # YUVA 配置信息
  └── SkYUVAPixmaps.h           # YUVA 像素映射
```

该模块为 GPU 纹理采样和像素数据解析提供位置映射。

## 主要类与结构体

### SkYUVAInfo::YUVALocation 结构体

| 结构体 | 继承关系 | 关键成员变量 | 说明 |
|--------|---------|------------|------|
| `YUVALocation` | 无 | `int fPlane`<br>`SkColorChannel fChannel` | YUVA 通道位置描述符 |

#### 成员说明

```cpp
struct YUVALocation {
    int fPlane = -1;                       // 平面索引 (-1 表示不存在)
    SkColorChannel fChannel = SkColorChannel::kA;  // 通道枚举

    bool operator==(const YUVALocation& that) const;
    bool operator!=(const YUVALocation& that) const;

    // 验证位置数组的有效性
    static bool AreValidLocations(const SkYUVAInfo::YUVALocations& locations,
                                  int* numPlanes = nullptr);
};
```

### SkYUVAInfo::YUVALocations 类型

```cpp
// SkYUVAInfo.h 中定义
using YUVALocations = std::array<YUVALocation, kYUVAChannelCount>;
// kYUVAChannelCount = 4 (Y, U, V, A)
```

## 公共 API 函数

### 比较操作符

```cpp
bool operator==(const YUVALocation& that) const {
    return fPlane == that.fPlane && fChannel == that.fChannel;
}

bool operator!=(const YUVALocation& that) const {
    return !(*this == that);
}
```

### 验证方法

```cpp
static bool AreValidLocations(
    const SkYUVAInfo::YUVALocations& locations,
    int* numPlanes = nullptr
);
```

功能: 检查 YUVALocations 数组是否有效

参数:
- `locations`: 包含 4 个 YUVALocation 的数组（Y, U, V, A）
- `numPlanes`: 可选输出参数,返回实际使用的平面数量

返回: `true` 表示配置有效,`false` 表示无效

## 内部实现细节

### AreValidLocations 实现

```cpp
static bool AreValidLocations(const SkYUVAInfo::YUVALocations& locations,
                              int* numPlanes) {
    int maxSlotUsed = -1;
    bool used[SkYUVAInfo::kMaxPlanes] = {};  // 最多 4 个平面
    bool valid = true;

    // 遍历 Y, U, V, A 四个通道
    for (int i = 0; i < SkYUVAInfo::kYUVAChannelCount; ++i) {
        if (locations[i].fPlane < 0) {
            // 平面索引为负: 通道不存在
            if (i != SkYUVAInfo::YUVAChannels::kA) {
                valid = false;  // 只有 A 通道可以省略
            }
        } else if (locations[i].fPlane >= SkYUVAInfo::kMaxPlanes) {
            valid = false;  // 平面索引超出范围 (>= 4)
        } else {
            maxSlotUsed = std::max(locations[i].fPlane, maxSlotUsed);
            used[i] = true;
        }
    }

    // 验证平面编号连续性（从 0 开始无间隙）
    for (int i = 0; i <= maxSlotUsed; ++i) {
        if (!used[i]) {
            valid = false;  // 存在间隙
        }
    }

    // 返回平面数量
    if (numPlanes) {
        *numPlanes = valid ? maxSlotUsed + 1 : 0;
    }

    return valid;
}
```

### 验证规则

1. **Y、U、V 通道必须存在**
   - `fPlane` 不能为负数
   - A 通道可选（fPlane = -1 表示无 alpha）

2. **平面索引范围**
   - 有效范围: [0, kMaxPlanes) = [0, 4)
   - 超出范围视为无效

3. **平面编号连续性**
   - 使用的平面必须从 0 开始连续编号
   - 例如: 使用平面 0 和 2 但跳过 1 是无效的
   - 有效示例: {0, 1, 2}, {0, 1}, {0}
   - 无效示例: {0, 2}, {1, 2}

4. **最大平面数限制**
   - 最多支持 4 个平面（kMaxPlanes = 4）

### 使用示例

**三平面 YUV420 配置**:
```cpp
SkYUVAInfo::YUVALocations locations;
locations[0] = {0, SkColorChannel::kR};  // Y 在平面 0 的 R 通道
locations[1] = {1, SkColorChannel::kR};  // U 在平面 1 的 R 通道
locations[2] = {2, SkColorChannel::kR};  // V 在平面 2 的 R 通道
locations[3] = {-1, SkColorChannel::kA}; // 无 alpha 通道

int numPlanes;
bool valid = YUVALocation::AreValidLocations(locations, &numPlanes);
// valid = true, numPlanes = 3
```

**单平面 NV12 配置**:
```cpp
locations[0] = {0, SkColorChannel::kR};  // Y 在平面 0 的 R 通道
locations[1] = {1, SkColorChannel::kR};  // U 在平面 1 的 R 通道
locations[2] = {1, SkColorChannel::kG};  // V 在平面 1 的 G 通道（交错）
locations[3] = {-1, SkColorChannel::kA}; // 无 alpha

// valid = true, numPlanes = 2
```

**无效配置示例**:
```cpp
// 示例 1: 跳过平面编号
locations[0] = {0, SkColorChannel::kR};  // Y 在平面 0
locations[1] = {2, SkColorChannel::kR};  // U 在平面 2（跳过 1）
locations[2] = {3, SkColorChannel::kR};  // V 在平面 3
locations[3] = {-1, SkColorChannel::kA};
// valid = false (平面编号不连续)

// 示例 2: Y 通道缺失
locations[0] = {-1, SkColorChannel::kR};  // Y 缺失（不允许）
locations[1] = {0, SkColorChannel::kR};
locations[2] = {1, SkColorChannel::kR};
locations[3] = {-1, SkColorChannel::kA};
// valid = false (Y 通道必须存在)
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `include/core/SkColor.h` | SkColorChannel 枚举定义 |
| `include/core/SkYUVAInfo.h` | 平面配置定义 |
| `<algorithm>` | std::max |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|---------|
| `src/core/SkYUVAPixmaps.cpp` | 计算位置映射 |
| GPU 纹理采样器 | 确定采样坐标 |
| 图像解码器 | 验证输出配置 |

## 设计模式与设计决策

### 值语义设计

**决策**: YUVALocation 使用值语义（POD 结构体）

```cpp
struct YUVALocation {
    int fPlane = -1;
    SkColorChannel fChannel = SkColorChannel::kA;
};
```

**优点**:
- 易于复制和传递
- 无需动态内存分配
- 支持编译时常量
- 清晰的相等比较语义

### 静态验证方法

**决策**: 将验证逻辑作为静态方法而非成员方法

```cpp
static bool AreValidLocations(...);  // 静态方法
```

**原因**:
- 验证整个数组而非单个位置
- 无需修改 YUVALocation 状态
- 符合函数式编程风格

### 负索引表示缺失

**决策**: 使用 `-1` 表示通道不存在

```cpp
int fPlane = -1;  // 默认值表示无此通道
```

**优点**:
- 语义清晰（负数天然表示"无"）
- 避免使用 `std::optional`（减少开销）
- 与 C++ 标准库约定一致（如 string::npos）

### 连续性要求

**决策**: 强制平面编号连续

**原因**:
1. **简化数组访问**: `textures[location.fPlane]` 直接有效
2. **防止资源浪费**: 避免分配未使用的纹理槽
3. **匹配硬件限制**: GPU 纹理单元通常连续编号
4. **易于迭代**: `for (int i = 0; i < numPlanes; ++i)`

## 性能考量

### 轻量级结构

**内存布局**:
```cpp
sizeof(YUVALocation) = sizeof(int) + sizeof(SkColorChannel)
                     = 4 + 4 = 8 字节
```

- 可内联传递
- 寄存器传参
- 无堆分配

### 验证开销

**AreValidLocations 复杂度**:
- 时间: O(kMaxPlanes) = O(4) = O(1)
- 空间: O(kMaxPlanes) = O(4) = O(1)

固定小常数,验证成本可忽略

### 缓存友好性

```cpp
std::array<YUVALocation, 4> locations;
// 连续内存: 4 * 8 = 32 字节
```

单次缓存行加载即可访问全部位置

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/core/SkYUVAInfo.h` | 依赖 | 平面配置定义 |
| `include/core/SkColor.h` | 依赖 | SkColorChannel 枚举 |
| `src/core/SkYUVAPixmaps.cpp` | 使用者 | toYUVALocations 方法 |
| `src/gpu/ganesh/GrYUVtoRGBEffect.cpp` | 使用者 | GPU 着色器采样 |
| `src/codec/SkJpegCodec.cpp` | 使用者 | 解码器输出配置 |
