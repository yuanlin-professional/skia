# SkNullCanvas

> 源文件: include/utils/SkNullCanvas.h, src/utils/SkNullCanvas.cpp

## 概述

`SkNullCanvas` 是 Skia 图形库中的空画布工具,创建一个不执行任何实际绘制操作的画布对象。该模块的核心价值在于性能测试和基准测试,允许测试者隔离绘制调用的开销,而无需实际的光栅化、GPU 提交或内存写入操作。

实现上,`SkNullCanvas` 通过创建一个没有目标画布的 `SkNWayCanvas` 实例来实现空操作效果。当 N 路画布的目标画布数量为 0 时,所有绘制调用都会被接收但不转发到任何实际设备,从而达到"无操作"的效果。这种极简设计使其成为测量绘制逻辑自身性能的理想工具。

## 架构位置

`SkNullCanvas` 位于 Skia 的实用工具层,作为测试和性能分析工具:

```
性能测试框架 / 基准测试工具
   ↓
SkNullCanvas (工具层 - include/utils, src/utils)
   ↓
SkNWayCanvas (N 路画布,N=0)
   ↓
SkCanvas (画布基类)
```

使用场景:
- 性能基准测试
- 绘制逻辑的单元测试
- 绘制调用开销分析
- 调试和性能剖析

## 主要类与结构体

### SkNullCanvas (函数)

实际上不是一个类,而是一个工厂函数,创建并返回空画布实例。

**返回类型**: `std::unique_ptr<SkCanvas>`

## 公共 API 函数

### SkMakeNullCanvas

```cpp
SK_API std::unique_ptr<SkCanvas> SkMakeNullCanvas();
```

创建一个空画布实例,该画布接受所有绘制调用但不执行任何实际操作。

**返回值**: 指向 `SkCanvas` 的 `std::unique_ptr`,实际类型为 `SkNWayCanvas`(配置为0个目标画布)

**示例用法**:
```cpp
// 性能基准测试
auto canvas = SkMakeNullCanvas();
auto start = std::chrono::high_resolution_clock::now();

// 执行绘制操作
for (int i = 0; i < 1000000; i++) {
    canvas->drawRect(SkRect::MakeXYWH(0, 0, 100, 100), paint);
}

auto end = std::chrono::high_resolution_clock::now();
auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start);
// duration 反映绘制调用自身的开销,不包括实际光栅化
```

## 内部实现细节

### 利用 SkNWayCanvas 的特性

```cpp
std::unique_ptr<SkCanvas> SkMakeNullCanvas() {
    // N 路画布在 N==0 时有效地成为空画布
    return std::unique_ptr<SkCanvas>(new SkNWayCanvas(0, 0));
}
```

**实现原理**:
- `SkNWayCanvas` 设计用于将绘制调用转发到 N 个目标画布
- 当目标画布列表为空(N=0)时,所有绘制方法都会执行基类逻辑但不转发
- 构造函数参数 `(0, 0)` 指定画布尺寸为 0x0

### SkNWayCanvas 的无操作行为

`SkNWayCanvas` 的绘制方法模式:

```cpp
void SkNWayCanvas::onDrawRect(const SkRect& rect, const SkPaint& paint) {
    for (int i = 0; i < fList.size(); ++i) {
        fList[i]->drawRect(rect, paint);
    }
}
```

当 `fList` 为空时,循环体不执行,方法立即返回。

### 极简的开销

- **内存分配**: 仅分配 `SkNWayCanvas` 对象本身(约几百字节)
- **虚函数调用**: 保留虚函数调用开销,用于测量基类逻辑
- **参数传递**: 保留参数复制和传递开销
- **无光栅化**: 完全没有像素写入、GPU 提交等操作

### 尺寸为零的语义

构造参数 `(0, 0)` 指定画布尺寸:

```cpp
new SkNWayCanvas(0, 0)
```

**影响**:
- `getBaseLayerSize()` 返回 `{0, 0}`
- 裁剪区域为空
- 某些绘制优化可能因空裁剪区域而短路

**替代设计**: 可以使用非零尺寸(如 `1920, 1080`)来模拟真实画布,避免因空尺寸导致的特殊代码路径。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkCanvas | 画布基类 |
| SkNWayCanvas | N 路画布实现 |
| std::unique_ptr | 智能指针,管理画布生命周期 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|----------|
| 性能基准测试 | 测量绘制调用开销 |
| 单元测试 | 测试绘制逻辑而不关注输出 |
| 性能剖析工具 | 分离绘制逻辑和光栅化开销 |
| 回归测试 | 验证绘制调用不崩溃 |

## 设计模式与设计决策

### 工厂函数模式

使用全局函数而非类:

```cpp
std::unique_ptr<SkCanvas> SkMakeNullCanvas()  // 工厂函数
```

而非:
```cpp
class SkNullCanvas : public SkCanvas { ... }  // 新类
```

**优点**:
- 简化实现:无需定义新类和重写所有虚函数
- 代码复用:直接利用 `SkNWayCanvas` 的现有逻辑
- 维护简单:只有2行实现代码
- 透明接口:返回标准 `SkCanvas` 指针

### 空对象模式 (Null Object Pattern)

`SkNullCanvas` 是空对象模式的典型应用:

- **正常对象**: 实际绘制的画布(光栅、GPU 等)
- **空对象**: `SkNullCanvas`,接受调用但无操作
- **客户端**: 无需特殊处理,统一使用 `SkCanvas*` 接口

**优点**:
- 避免空指针检查
- 简化客户端代码
- 允许优雅地"禁用"绘制

### 组合优于继承

通过组合 `SkNWayCanvas` 而非继承 `SkCanvas` 实现功能:

**传统方式**:
```cpp
class SkNullCanvas : public SkCanvas {
    void onDrawRect(...) override {}
    void onDrawPath(...) override {}
    // ... 数十个空实现
};
```

**实际方式**:
```cpp
new SkNWayCanvas(0, 0);  // 零配置的组合
```

节省大量样板代码。

### 最小化接口

仅提供工厂函数,不暴露实现细节:

- 用户不需要知道内部使用 `SkNWayCanvas`
- 未来可更改实现而不影响 API
- 接口极简,易于理解和使用

### 智能指针返回

返回 `std::unique_ptr` 而非裸指针:

**优点**:
- 自动内存管理
- 明确所有权转移
- 现代 C++ 最佳实践

## 性能考量

### 测量的是什么

使用 `SkNullCanvas` 时,性能测量包括:

**包含的开销**:
- 虚函数调用(vtable 查找)
- 参数复制(SkPaint、SkRect 等)
- 基类方法执行(矩阵变换、裁剪检查等)
- 循环遍历(虽然列表为空,但循环条件仍检查)

**排除的开销**:
- 实际光栅化
- GPU 命令提交
- 内存写入
- 纹理上传
- Shader 编译

### 基准测试最佳实践

```cpp
// 预热 CPU 缓存
auto canvas = SkMakeNullCanvas();
for (int i = 0; i < 100; i++) {
    canvas->drawRect(rect, paint);
}

// 实际测量
auto start = now();
for (int i = 0; i < iterations; i++) {
    canvas->drawRect(rect, paint);
}
auto elapsed = now() - start;
```

### 与真实画布的对比

```cpp
// 测量空画布开销
auto nullCanvas = SkMakeNullCanvas();
auto nullTime = benchmark(nullCanvas);

// 测量真实画布总开销
auto realCanvas = surface->getCanvas();
auto realTime = benchmark(realCanvas);

// 光栅化开销 = realTime - nullTime
auto rasterTime = realTime - nullTime;
```

### 编译器优化的影响

空画布不会被优化掉:

- 虚函数调用阻止内联和删除死代码
- `SkNWayCanvas` 的循环不会被优化掉(编译器无法证明列表始终为空)

但仍需注意:
- 使用 `-O2` 或更高优化级别
- 避免在循环外测量无关操作
- 使用 `volatile` 或 `DoNotOptimize` 防止编译器优化掉整个循环

### 内存占用

- **SkNWayCanvas 对象**: ~100-200 字节(取决于平台和编译选项)
- **空的画布列表**: 0 字节(vector 为空)
- **总计**: 可忽略不计

适合在内存受限环境中用于测试。

## 相关文件

| 文件路径 | 说明 |
|----------|------|
| include/utils/SkNullCanvas.h | 公共 API 头文件(仅声明工厂函数) |
| src/utils/SkNullCanvas.cpp | 实现文件(仅3行有效代码) |
| include/utils/SkNWayCanvas.h | N 路画布基类 |
| src/utils/SkNWayCanvas.cpp | N 路画布实现 |
| include/core/SkCanvas.h | 画布基类接口 |
