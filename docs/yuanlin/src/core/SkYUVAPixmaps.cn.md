# SkYUVAPixmaps

> 源文件: include/core/SkYUVAPixmaps.h, src/core/SkYUVAPixmaps.cpp

## 概述

SkYUVAPixmaps 是 Skia 中用于描述和管理 YUVA 图像多平面像素数据的核心类。该模块将 SkYUVAInfo（描述 YUV 平面配置）与实际的 SkPixmap 数组结合,提供完整的 YUVA 图像存储方案。支持多种数据类型（8/16 位整数、16 位浮点、10+2 位混合）、不同的平面配置（444、420、422 等）和内存管理模式（自主分配、外部内存、零拷贝封装）。它是 Skia 处理视频帧和 YUV 图像的基础数据结构。

## 架构位置

SkYUVAPixmaps 位于 Skia 核心层的图像表示子系统:

```
include/core/
  ├── SkYUVAInfo.h            # YUVA 配置信息
  ├── SkYUVAPixmaps.h         # YUVA 像素映射（本模块）
  ├── SkPixmap.h              # 单平面像素映射
  └── SkImageInfo.h           # 图像信息基础
src/core/
  └── SkYUVAPixmaps.cpp       # 实现文件
```

该模块连接图像解码器、GPU 纹理上传器和渲染管线。

## 主要类与结构体

### SkYUVAPixmapInfo 类

| 类名 | 继承关系 | 关键成员变量 | 说明 |
|------|---------|------------|------|
| `SkYUVAPixmapInfo` | 无 | `SkYUVAInfo fYUVAInfo`<br>`array<SkImageInfo, kMaxPlanes> fPlaneInfos`<br>`array<size_t, kMaxPlanes> fRowBytes`<br>`DataType fDataType` | 完整描述 YUVA pixmap 而不包含实际数据 |

#### DataType 枚举

| 枚举值 | 说明 |
|--------|------|
| `kUnorm8` | 8 位无符号归一化整数 |
| `kUnorm16` | 16 位无符号归一化整数 |
| `kFloat16` | 16 位（半精度）浮点数 |
| `kUnorm10_Unorm2` | Y/U/V 10 位 + Alpha 2 位 |

#### SupportedDataTypes 内部类

```cpp
class SupportedDataTypes {
    constexpr bool supported(PlaneConfig, DataType) const;
    void enableDataType(DataType, int numChannels);
    static constexpr SupportedDataTypes All();
};
```

功能: 管理支持的数据类型和平面配置组合

### SkYUVAPixmaps 类

| 类名 | 继承关系 | 关键成员变量 | 说明 |
|------|---------|------------|------|
| `SkYUVAPixmaps` | 无 | `array<SkPixmap, kMaxPlanes> fPlanes`<br>`sk_sp<SkData> fData`<br>`SkYUVAInfo fYUVAInfo`<br>`DataType fDataType` | 存储实际像素数据的容器 |

## 公共 API 函数

### SkYUVAPixmapInfo 构造与查询

```cpp
// 构造函数
SkYUVAPixmapInfo(const SkYUVAInfo&,
                 const SkColorType[kMaxPlanes],
                 const size_t rowBytes[kMaxPlanes]);

SkYUVAPixmapInfo(const SkYUVAInfo&, DataType,
                 const size_t rowBytes[kMaxPlanes]);

// 查询方法
const SkYUVAInfo& yuvaInfo() const;
int numPlanes() const;
DataType dataType() const;
size_t rowBytes(int i) const;
const SkImageInfo& planeInfo(int i) const;

// 内存计算
size_t computeTotalBytes(size_t planeSizes[kMaxPlanes] = nullptr) const;

// 初始化 pixmap 数组
bool initPixmapsFromSingleAllocation(void* memory,
                                     SkPixmap pixmaps[kMaxPlanes]) const;
```

### SkYUVAPixmaps 工厂方法

```cpp
// 自动分配内存
static SkYUVAPixmaps Allocate(const SkYUVAPixmapInfo& yuvaPixmapInfo);

// 使用 SkData 作为后端存储
static SkYUVAPixmaps FromData(const SkYUVAPixmapInfo&, sk_sp<SkData>);

// 深拷贝
static SkYUVAPixmaps MakeCopy(const SkYUVAPixmaps& src);

// 外部内存（不拥有所有权）
static SkYUVAPixmaps FromExternalMemory(const SkYUVAPixmapInfo&, void* memory);

// 封装现有 pixmaps（不拥有所有权）
static SkYUVAPixmaps FromExternalPixmaps(const SkYUVAInfo&,
                                         const SkPixmap[kMaxPlanes]);
```

### 查询与转换

```cpp
// 查询
bool isValid() const;
int numPlanes() const;
const SkPixmap& plane(int i) const;
const array<SkPixmap, kMaxPlanes>& planes() const;
bool ownsStorage() const;

// 转换
SkYUVAPixmapInfo pixmapsInfo() const;
SkYUVAInfo::YUVALocations toYUVALocations() const;

// 推荐 RGBA 色彩类型
static SkColorType RecommendedRGBAColorType(DataType);
```

## 内部实现细节

### 数据类型与颜色类型映射

```cpp
static constexpr SkColorType DefaultColorTypeForDataType(DataType dataType,
                                                         int numChannels) {
    switch (numChannels) {
        case 1:
            switch (dataType) {
                case DataType::kUnorm8:  return kGray_8_SkColorType;
                case DataType::kUnorm16: return kA16_unorm_SkColorType;
                case DataType::kFloat16: return kA16_float_SkColorType;
                // ...
            }
        case 2:
            // kR8G8_unorm_SkColorType, kR16G16_unorm_SkColorType, ...
        case 3:
            // kRGBA_8888_SkColorType (忽略 alpha 通道)
        case 4:
            // kRGBA_8888_SkColorType, kRGBA_F16_SkColorType, ...
    }
}
```

设计考虑:
- 3 通道情况使用 4 通道格式（GPU 支持更好）
- 选择 "A" 变体而非 "x" 变体（后端支持更广泛）

### 内存布局

**单一分配模式** (`Allocate` / `FromData`):
```
+----------+----------+----------+----------+
| Plane 0  | Plane 1  | Plane 2  | Plane 3  |
| (Y)      | (U)      | (V)      | (A opt.) |
+----------+----------+----------+----------+
^
fData 指向的连续内存
```

**外部内存模式**:
- `fData` 为 nullptr
- 各 SkPixmap 指向外部管理的内存

### 数据类型验证

```cpp
std::tuple<int, DataType> NumChannelsAndDataType(SkColorType ct) {
    switch (ct) {
        case kGray_8_SkColorType:    return {1, DataType::kUnorm8};
        case kRGBA_8888_SkColorType: return {4, DataType::kUnorm8};
        case kRGBA_F16_SkColorType:  return {4, DataType::kFloat16};
        // ... 拒绝 BGR[A] 格式确保通道顺序一致
        default: return {0, DataType::kUnorm8};
    }
}
```

所有平面必须使用相同的 DataType:
```cpp
ok &= i == 0 || colorTypeDataType == fDataType;
```

### YUVALocations 转换

```cpp
SkYUVAInfo::YUVALocations SkYUVAPixmaps::toYUVALocations() const {
    uint32_t channelFlags[] = {
        SkColorTypeChannelFlags(fPlanes[0].colorType()),
        SkColorTypeChannelFlags(fPlanes[1].colorType()),
        // ...
    };
    return fYUVAInfo.toYUVALocations(channelFlags);
}
```

功能: 将像素映射转换为 GPU 纹理采样位置

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `include/core/SkYUVAInfo.h` | 平面配置和采样描述 |
| `include/core/SkPixmap.h` | 单平面像素访问 |
| `include/core/SkImageInfo.h` | 颜色类型和尺寸 |
| `include/core/SkData.h` | 内存管理 |
| `src/core/SkYUVAInfoLocation.h` | GPU 纹理位置映射 |
| `src/base/SkRectMemcpy.h` | 高效内存复制 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|---------|
| `src/core/SkYUVPlanesCache.cpp` | 缓存 YUV 数据 |
| `src/gpu/ganesh/GrYUVtoRGBEffect.cpp` | GPU 着色器输入 |
| `src/codec/` | 解码器输出格式 |
| `src/image/SkImage_Lazy.cpp` | 懒加载 YUV 图像 |

## 设计模式与设计决策

### 工厂方法模式

**决策**: 提供多种静态工厂方法而非复杂的构造函数

**优点**:
- 明确内存所有权语义
- 支持多种初始化策略
- 易于理解和使用

**方法分类**:
1. `Allocate`: 自动分配（所有权归属）
2. `FromData`: 共享所有权（引用计数）
3. `MakeCopy`: 独立副本
4. `FromExternalMemory`: 外部所有权（借用）
5. `FromExternalPixmaps`: 零拷贝封装

### 不可变性与验证

**构造时验证**:
```cpp
if (!yuvaInfo.isValid()) {
    *this = {};  // 构造无效对象
    return;
}
```

**所有操作假设有效性**:
```cpp
int numPlanes() const { return this->isValid() ? fYUVAInfo.numPlanes() : 0; }
```

优点: 简化错误处理,避免运行时检查

### SupportedDataTypes 设计

**constexpr 查询表**:
```cpp
constexpr SupportedDataTypes SupportedDataTypes::All() {
    SupportedDataTypes combinations;
    // 编译时计算所有合法组合
    combinations.fDataTypeSupport = bits;
    return combinations;
}
```

用途: GPU 后端能力查询（某些组合硬件不支持）

## 性能考量

### 内存对齐

**行字节计算**:
```cpp
if (!rowBytes) {
    tempRowBytes[i] = SkColorTypeBytesPerPixel(colorTypes[i]) *
                      planeDimensions[i].width();
}
```

建议: 使用对齐的行字节（GPU 纹理上传要求）

### 零拷贝优化

**FromExternalPixmaps**:
- 直接封装现有 SkPixmap
- 无数据复制
- 适用于解码器直接输出

### 缓存友好性

**连续内存布局**:
```cpp
char* addr = static_cast<char*>(memory);
for (int i = 0; i < n; ++i) {
    pixmaps[i].reset(fPlaneInfos[i], addr, fRowBytes[i]);
    addr += pixmaps[i].rowBytes() * pixmaps[i].height();
}
```

优点: 提高缓存命中率,减少页表压力

### 推荐 RGBA 类型

```cpp
SkColorType RecommendedRGBAColorType(DataType dataType) {
    switch (dataType) {
        case DataType::kUnorm16: return kRGBA_F16_SkColorType;  // F16 GPU 支持更好
        // ...
    }
}
```

考虑: GPU 纹理格式支持而非精确匹配

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/core/SkYUVAInfo.h` | 依赖 | 平面配置定义 |
| `include/core/SkPixmap.h` | 依赖 | 像素映射基础 |
| `src/core/SkYUVAInfoLocation.h` | 依赖 | GPU 位置映射 |
| `src/core/SkYUVPlanesCache.h` | 使用者 | 缓存管理 |
| `src/gpu/ganesh/GrYUVtoRGBEffect.h` | 使用者 | GPU 着色器 |
| `src/codec/SkJpegCodec.cpp` | 使用者 | JPEG YUV 解码 |
| `include/core/SkImage.h` | 相关 | 图像接口 |
