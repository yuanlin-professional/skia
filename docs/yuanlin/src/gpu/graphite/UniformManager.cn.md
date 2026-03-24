# UniformManager

> 源文件: src/gpu/graphite/UniformManager.h, src/gpu/graphite/UniformManager.cpp

## 概述

`UniformManager` 是 Skia Graphite 渲染架构中负责 uniform 数据管理和写入的核心类。该类提供了类型安全的 API 用于向 GPU uniform 缓冲区写入各种数据类型（标量、向量、矩阵等），并自动处理内存布局、对齐和偏移计算。它支持多种布局（std140、std430、Metal）并通过 `UniformOffsetCalculator` 确保数据按照 GPU 规范正确对齐。

## 架构位置

```
Graphite Uniform 系统：
  ├── Uniform（uniform 定义）
  ├── UniformManager（uniform 写入器）★
  ├── UniformOffsetCalculator（偏移计算器）
  └── UniformDataBlock（数据块容器）
```

## 主要类与结构体

### UniformManager 类

```cpp
class UniformManager {
public:
    UniformManager(Layout layout);

    // 单值写入
    void write(const SkM44& mat);
    void write(const SkMatrix& mat);
    void write(const SkV4& vec);
    void write(const SkV2& vec);
    void write(const SkRect& rect);
    void write(SkPoint pt);
    void write(float f);
    void write(int i);
    // 数组写入
    void writeArray(SkSpan<const SkColor4f> colors);
    void writeArray(SkSpan<const float> floats);
    // 半精度浮点
    void writeHalf(const SkM44& mat);
    void writeHalfArray(SkSpan<const float> floats);

    // 数据访问
    UniformDataBlock finishUniformDataBlock();
    size_t size() const;
    const void* data() const;

    // 重置
    void reset();
    void resetWithNewLayout(Layout layout);

private:
    UniformOffsetCalculator fOffsetCalculator;
    SkTDArray<char> fStorage;
    bool fWrotePaintColor = false;
};
```

## 公共 API 函数

### 构造函数

```cpp
UniformManager(Layout layout);
```

创建指定布局的 uniform 管理器（std140、std430 或 Metal）。

### 写入方法

**矩阵写入**:
```cpp
void write(const SkM44& mat);  // 4x4矩阵
void write(const SkMatrix& mat);  // 3x3矩阵
```

**向量写入**:
```cpp
void write(const SkV4& vec);  // 4D向量
void write(const SkV2& vec);  // 2D向量
void write(const SkRect& rect);  // 4个float
void write(SkPoint pt);  // 2个float
```

**标量写入**:
```cpp
void write(float f);
void write(int i);
```

**数组写入**:
```cpp
void writeArray(SkSpan<const SkColor4f> colors);  // 颜色数组
void writeArray(SkSpan<const float> floats);  // float数组
```

**半精度浮点**:
```cpp
void writeHalf(const SkM44& mat);  // 16位浮点矩阵
void writeHalfArray(SkSpan<const float> floats);  // 16位浮点数组
```

### 数据访问

```cpp
UniformDataBlock finishUniformDataBlock();  // 完成并返回数据块
size_t size() const;  // 当前数据大小
const void* data() const;  // 原始数据指针
```

### 重置

```cpp
void reset();  // 清空数据，保留布局
void resetWithNewLayout(Layout layout);  // 清空并更换布局
```

## 内部实现细节

### 对齐和布局

`UniformOffsetCalculator` 根据布局规则计算偏移：
- **std140**: OpenGL/Vulkan 标准布局
- **std430**: 紧凑布局（SSBO）
- **Metal**: Metal 特定布局

### 数据存储

```cpp
SkTDArray<char> fStorage;  // 动态字节数组
```

### 写入流程

1. 计算对齐偏移（`fOffsetCalculator.advanceOffset()`）
2. 扩展存储空间（`fStorage.append()`）
3. 写入数据（`memcpy` 或手动复制）
4. 更新偏移位置

### 特殊处理

**Paint Color 去重**:
```cpp
bool fWrotePaintColor = false;  // 避免重复写入paintColor
```

**半精度转换**:
```cpp
void writeHalf(const SkM44& mat) {
    for (int i = 0; i < 16; ++i) {
        uint16_t half = SkFloatToHalf(mat.rc(i/4, i%4));
        fStorage.append(2, reinterpret_cast<const char*>(&half));
    }
}
```

## 依赖关系

### 内部依赖

| 依赖类 | 用途 |
|--------|------|
| `UniformOffsetCalculator` | 计算对齐偏移 |
| `UniformDataBlock` | 数据块容器 |
| `Uniform` | Uniform 定义 |
| `Layout` | 布局枚举 |

### 被依赖情况

| 依赖者 | 用途 |
|--------|------|
| `ShaderInfo` | 生成 uniform 声明 |
| `PaintParams` | 写入绘制参数 |
| `RenderStep` | 写入步骤 uniform |

## 设计模式与设计决策

### 构建器模式

逐步写入数据，最后调用 `finishUniformDataBlock()` 完成。

### 类型安全

为每种类型提供专用的 `write()` 重载，避免类型错误。

### 自动对齐

`UniformOffsetCalculator` 自动处理对齐，用户无需手动计算偏移。

### 关键设计决策

1. **动态扩展**: 使用 `SkTDArray` 避免预分配
2. **布局抽象**: 支持多种 GPU uniform 布局规范
3. **半精度支持**: 优化移动设备带宽
4. **Paint Color 去重**: 避免重复写入常见 uniform

## 性能考量

### 内存管理

1. **动态分配**: `SkTDArray` 按需扩展
2. **数据拷贝**: 写入时拷贝数据到内部缓冲区
3. **对齐填充**: 可能产生填充字节

### 带宽优化

1. **半精度浮点**: 减少一半的内存传输
2. **紧凑布局**: std430 比 std140 更节省空间

## 相关文件

| 文件路径 | 作用 |
|----------|------|
| `src/gpu/graphite/Uniform.h` | Uniform 定义 |
| `src/gpu/graphite/UniformDataBlock.h` | 数据块容器 |
| `src/gpu/graphite/ShaderInfo.h` | Uniform 声明生成 |
| `src/gpu/graphite/PaintParams.h` | 绘制参数管理 |
