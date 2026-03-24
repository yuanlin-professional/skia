# Rectanizer

> 源文件: src/gpu/Rectanizer.h

## 概述

`Rectanizer` 是 Skia GPU 层的矩形打包算法抽象基类,定义了二维矩形打包的统一接口。该类为 GPU 纹理图集管理提供了通用的矩形分配框架,支持动态添加矩形、查询空间使用率以及重置状态。

具体实现包括 `RectanizerSkyline`(基于天际线算法,高空间利用率)和 `RectanizerPow2`(基于 2 的幂次量化,快速分配)。通过工厂方法模式,调用方无需关心具体算法,只需使用统一的接口。

## 架构位置

`Rectanizer` 位于 GPU 层的资源管理基础设施:

- 命名空间: `skgpu`
- 模块位置: `src/gpu/`
- 类型: 抽象基类
- 设计模式: 工厂模式 + 策略模式
- 应用场景: 字体图集、纹理图集、动态资源打包

该类是矩形打包算法的抽象层,为上层的图集管理器提供算法无关的统一接口。

## 主要类与结构体

### 继承关系

```
Rectanizer (抽象基类)
├── RectanizerSkyline (天际线算法实现)
└── RectanizerPow2 (2 的幂次量化实现)
```

### 关键成员变量

| 成员变量 | 类型 | 访问性 | 说明 |
|---------|------|--------|------|
| `fWidth` | `const int` | private | 打包空间的总宽度 |
| `fHeight` | `const int` | private | 打包空间的总高度 |

## 公共 API 函数

### 构造与析构

```cpp
// 构造函数,指定打包空间大小
Rectanizer(int width, int height);

// 虚析构函数
virtual ~Rectanizer();
```

**参数**:
- `width`: 打包空间的宽度(像素)
- `height`: 打包空间的高度(像素)

**断言**: `width >= 0 && height >= 0`

### 纯虚函数(必须由子类实现)

```cpp
// 重置到初始状态,清空所有已分配区域
virtual void reset() = 0;

// 尝试添加矩形,成功返回 true 并填充位置
virtual bool addRect(int width, int height, SkIPoint16* loc) = 0;

// 返回空间使用率(0.0-1.0)
virtual float percentFull() const = 0;
```

### 具体实现的方法

```cpp
// 获取打包空间的宽度
int width() const { return fWidth; }

// 获取打包空间的高度
int height() const { return fHeight; }

// 添加带边距的矩形
bool addPaddedRect(int width, int height, int16_t padding, SkIPoint16* loc);
```

### 静态工厂方法

```cpp
// 创建 Rectanizer 实例(默认创建 RectanizerSkyline)
static Rectanizer* Factory(int width, int height);
```

## 内部实现细节

### addPaddedRect 实现

```cpp
bool Rectanizer::addPaddedRect(int width, int height, int16_t padding, SkIPoint16* loc) {
    // 1. 尝试分配包含边距的矩形
    if (this->addRect(width + 2*padding, height + 2*padding, loc)) {
        // 2. 调整返回位置,跳过边距
        loc->fX += padding;
        loc->fY += padding;
        return true;
    }
    return false;
}
```

**功能**: 在矩形周围添加边距后进行分配
**用途**: 避免相邻字形的渲染伪影(bleeding)

**示例**:
- 请求: 宽 10,高 10,边距 1
- 实际分配: 宽 12,高 12
- 返回位置: 偏移 +1,+1(内部有效区域)

### Factory 方法实现

```cpp
// 实现在 RectanizerSkyline.cpp
Rectanizer* Rectanizer::Factory(int width, int height) {
    return new RectanizerSkyline(width, height);
}
```

**设计决策**: 默认使用 `RectanizerSkyline`,因为它提供更好的空间利用率。

## 依赖关系

### 依赖的模块

| 模块 | 用途 | 头文件 |
|------|------|--------|
| SkIPoint16 | 16 位坐标点 | `src/core/SkIPoint16.h` |
| SkAssert | 断言检查 | `include/private/base/SkAssert.h` (隐式) |

### 被依赖的模块

| 模块 | 关系 | 说明 |
|------|------|------|
| GrDrawOpAtlas | 使用方 | Ganesh 字形和绘制操作图集 |
| sktext::gpu::StrikeCache | 使用方 | GPU 字形缓存 |
| graphite::AtlasManager | 使用方 | Graphite 图集管理 |
| RectanizerSkyline | 子类 | 天际线算法实现 |
| RectanizerPow2 | 子类 | 2 的幂次算法实现 |

## 设计模式与设计决策

### 1. 策略模式(Strategy Pattern)

`Rectanizer` 定义了矩形打包的策略接口:
- **抽象策略**: `Rectanizer` 基类
- **具体策略**: `RectanizerSkyline`、`RectanizerPow2`
- **上下文**: 图集管理器(AtlasManager)

**优点**:
- 算法可替换
- 算法与使用方解耦
- 易于添加新算法

### 2. 工厂方法模式(Factory Method)

```cpp
static Rectanizer* Factory(int width, int height);
```

**职责**: 封装对象创建逻辑
**优点**:
- 调用方无需知道具体类型
- 可以在运行时或编译时切换算法
- 统一的创建接口

### 3. 模板方法模式(Template Method)

虽然没有显式的模板方法,但 `addPaddedRect` 展示了类似思想:
- 定义算法框架(添加边距 + 调用 `addRect` + 调整位置)
- 子类实现具体步骤(`addRect`)

### 4. 不可变边界

`fWidth` 和 `fHeight` 声明为 `const`:
```cpp
const int fWidth;
const int fHeight;
```

**设计意图**:
- 打包空间大小在创建后不可改变
- 防止意外修改
- 明确对象的生命周期约束

### 5. 简单的接口设计

基类仅定义 4 个纯虚函数 + 2 个具体方法:
- **纯虚**: `reset`、`addRect`、`percentFull`
- **具体**: `width`、`height`、`addPaddedRect`

**优点**:
- 易于实现
- 易于理解
- 最小化虚函数开销

### 6. 使用原始指针返回位置

```cpp
bool addRect(int width, int height, SkIPoint16* loc);
```

而非返回 `std::optional<SkIPoint16>`:

**原因**:
- 历史代码风格
- 避免额外的内存拷贝
- 性能优先(频繁调用)

## 性能考量

### 1. 虚函数开销

主要接口都是虚函数:
- **调用开销**: 1 次间接跳转(vtable 查找)
- **典型成本**: 几个 CPU 周期
- **优化**: 子类标记为 `final` 可以去虚拟化

### 2. 内存布局

基类大小:
```cpp
sizeof(Rectanizer) = sizeof(void*) + sizeof(int) * 2
                   = 8 + 8 = 16 字节(64 位)
```

加上 vtable 指针,总共约 24 字节。

### 3. addPaddedRect 性能

```cpp
bool addPaddedRect(int width, int height, int16_t padding, SkIPoint16* loc) {
    if (this->addRect(width + 2*padding, height + 2*padding, loc)) {
        loc->fX += padding;
        loc->fY += padding;
        return true;
    }
    return false;
}
```

**开销**:
- 1 次虚函数调用(`addRect`)
- 2 次整数加法
- 2 次整数赋值(如果成功)

可内联,总开销很小。

### 4. 不同算法的性能对比

| 算法 | addRect 复杂度 | 空间利用率 | 适用场景 |
|------|---------------|-----------|---------|
| RectanizerSkyline | O(n^2) 最坏 | 85-95% | 字体图集,长期缓存 |
| RectanizerPow2 | O(1) | 70-85% | 临时分配,快速场景 |

### 5. 边界检查

构造函数中的断言:
```cpp
Rectanizer(int width, int height) : fWidth(width), fHeight(height) {
    SkASSERT(width >= 0);
    SkASSERT(height >= 0);
}
```

Debug 模式下检查,Release 模式下可能被优化掉。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/RectanizerSkyline.h` | 子类 | 天际线算法实现 |
| `src/gpu/RectanizerPow2.h` | 子类 | 2 的幂次算法实现 |
| `src/core/SkIPoint16.h` | 依赖 | 16 位整数点类型 |
| `src/gpu/ganesh/GrDrawOpAtlas.h` | 使用方 | Ganesh 图集管理 |
| `src/text/gpu/StrikeCache.h` | 使用方 | GPU 字形缓存 |
| `src/gpu/graphite/text/AtlasManager.h` | 使用方 | Graphite 图集管理 |
| `tests/RectanizerTest.cpp` | 测试 | 单元测试 |

## 扩展性设计

### 如何添加新算法

实现新的 `Rectanizer` 子类:

```cpp
class RectanizerCustom final : public Rectanizer {
public:
    RectanizerCustom(int w, int h) : Rectanizer(w, h) { reset(); }

    void reset() final override {
        // 实现重置逻辑
    }

    bool addRect(int w, int h, SkIPoint16* loc) final override {
        // 实现分配逻辑
    }

    float percentFull() const final override {
        // 实现利用率计算
    }
};
```

修改工厂方法:
```cpp
Rectanizer* Rectanizer::Factory(int width, int height) {
    // 可以基于宏、配置或运行时参数选择算法
    #ifdef USE_CUSTOM_ALGORITHM
        return new RectanizerCustom(width, height);
    #else
        return new RectanizerSkyline(width, height);
    #endif
}
```

### 未来可能的改进

1. **模板化尺寸**: 支持不同的坐标类型(`int32_t`、`float`)
2. **多图集支持**: 基类支持跨多个图集分配
3. **碎片整理**: 添加 `defragment()` 接口
4. **统计信息**: 添加 `getStats()` 获取详细的分配统计
5. **增量更新**: 支持删除矩形和空间回收
