# SkSurface_Null

> 源文件：src/image/SkSurface_Null.cpp

## 概述

`SkSurface_Null` 是一个特殊的表面实现，它不执行任何实际绘制操作。所有绘制命令都被忽略，像素写入无效，快照返回 `nullptr`。该表面主要用于性能测试、基准测试或需要表面接口但不需要实际输出的场景。

## 主要实现

### SkNullSurface 类

```cpp
class SkNullSurface : public SkSurface_Base {
public:
    SkNullSurface(int width, int height) : SkSurface_Base(width, height, nullptr) {}

    SkSurface_Base::Type type() const override { return SkSurface_Base::Type::kNull; }

protected:
    SkCanvas* onNewCanvas() override {
        return new SkNoDrawCanvas(this->width(), this->height());  // 不绘制的 Canvas
    }

    sk_sp<SkSurface> onNewSurface(const SkImageInfo& info) override {
        return SkSurfaces::Null(info.width(), info.height());  // 返回新的 Null 表面
    }

    sk_sp<SkImage> onNewImageSnapshot(const SkIRect* subsetOrNull) override {
        return nullptr;  // 无快照
    }

    void onWritePixels(const SkPixmap&, int x, int y) override {}  // 忽略写入

    void onDraw(SkCanvas*, SkScalar, SkScalar, const SkSamplingOptions&, const SkPaint*) override {}  // 不绘制

    bool onCopyOnWrite(ContentChangeMode) override { return true; }  // 总是成功

    sk_sp<const SkCapabilities> onCapabilities() override {
        return SkCapabilities::RasterBackend();  // 假装是栅格后端
    }

    SkImageInfo imageInfo() const override {
        return SkImageInfo::MakeUnknown(this->width(), this->height());  // 未知格式
    }
};
```

### 工厂函数

```cpp
namespace SkSurfaces {
sk_sp<SkSurface> Null(int width, int height) {
    if (width < 1 || height < 1) {
        return nullptr;
    }
    return sk_sp<SkSurface>(new SkNullSurface(width, height));
}
}
```

## 使用场景

1. **性能基准测试**：测量绘制命令开销而不包含栅格化时间
2. **API 测试**：验证绘制逻辑而不关心输出
3. **空操作实现**：需要表面接口但不需要输出的场景

## 设计特点

### SkNoDrawCanvas

使用 `SkNoDrawCanvas` 作为 Canvas 实现，该 Canvas 忽略所有绘制命令。

### 零开销

- 无内存分配（除了对象本身）
- 无像素操作
- 无 COW 开销

### 类型标识

`type()` 返回 `Type::kNull`，可通过类型检查识别。

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/image/SkSurface_Base.h` | 基类 | 表面实现基类 |
| `include/utils/SkNoDrawCanvas.h` | Canvas | 不绘制的 Canvas |
| `include/core/SkSurface.h` | API | 表面公共接口 |
