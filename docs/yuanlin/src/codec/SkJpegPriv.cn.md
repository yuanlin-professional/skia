# SkJpegPriv

> 源文件: src/codec/SkJpegPriv.h

## 概述

`SkJpegPriv` 是 Skia JPEG 解码器的私有头文件，定义了与 libjpeg 库交互时所需的错误处理机制。该文件的核心是 `skjpeg_error_mgr` 结构体，它扩展了 libjpeg 的标准错误管理器，提供了基于 `setjmp/longjmp` 的异常安全栈管理功能。这是 C/C++ 混合编程中处理 C 库错误的经典模式，确保 JPEG 解码过程中的错误能够安全地传播到 Skia 的错误处理代码。

## 架构位置

该模块位于 JPEG 解码器的基础设施层：

```
src/codec/
  ├── SkJpegPriv.h              # 本文件（错误管理）
  ├── SkJpegUtility.h           # 工具函数（使用 skjpeg_error_mgr）
  ├── SkJpegCodec.h             # JPEG 解码器主类
  ├── SkJpegSourceMgr.h         # 源管理器
  └── SkCodecPriv.h             # 通用编解码器私有工具
```

作为私有头文件，它被所有与 libjpeg 直接交互的模块包含。

## 主要类与结构体

### skjpeg_error_mgr

继承自 `jpeg_error_mgr` 的错误管理器结构体。

**继承关系：**

```cpp
struct skjpeg_error_mgr : public jpeg_error_mgr {
    // Skia 扩展成员
};
```

**成员变量：**

```cpp
jmp_buf* fStack[4] = {};  // 跳转缓冲区栈（最多 4 层嵌套）
```

**构造函数：**

```cpp
skjpeg_error_mgr() : jpeg_error_mgr({}) {}
```

使用聚合初始化 `{}` 将 `jpeg_error_mgr` 的所有字段置零，避免 MSAN（Memory Sanitizer）误报未初始化内存访问（详见 crbug.com/oss-fuzz/68691）。

**核心方法：**

```cpp
void push(jmp_buf* j);  // 将跳转缓冲区压栈
void pop(jmp_buf* j);   // 将跳转缓冲区出栈
```

### AutoPushJmpBuf (内嵌辅助类)

RAII 风格的跳转缓冲区管理器。

**定义：**

```cpp
class AutoPushJmpBuf {
public:
    explicit AutoPushJmpBuf(skjpeg_error_mgr* mgr);
    ~AutoPushJmpBuf();
    operator jmp_buf&();  // 隐式转换为 jmp_buf&

private:
    skjpeg_error_mgr* const fMgr;
    jmp_buf fJmpBuf;
};
```

**使用模式：**

```cpp
skjpeg_error_mgr errorMgr;
{
    skjpeg_error_mgr::AutoPushJmpBuf jmpBuf(&errorMgr);
    if (setjmp(jmpBuf)) {
        // 错误处理路径
        return;
    }
    // 正常处理路径（可能调用 libjpeg 函数）
}
// jmpBuf 析构时自动出栈
```

## 公共 API 函数

### push

```cpp
void push(jmp_buf* j);
```

将跳转缓冲区压入栈中。栈采用右移逻辑，新元素放在 `fStack[0]`。

**实现：**

```cpp
void push(jmp_buf* j) {
    SkASSERT(fStack[3] == nullptr);  // 栈溢出检测
    fStack[3] = fStack[2];
    fStack[2] = fStack[1];
    fStack[1] = fStack[0];
    fStack[0] = j;
}
```

**前置条件：**
- `fStack[3]` 必须为 `nullptr`（栈未满）
- 违反时触发断言，防止栈溢出

### pop

```cpp
void pop(jmp_buf* j);
```

将跳转缓冲区从栈中弹出。栈采用左移逻辑，恢复之前的状态。

**实现：**

```cpp
void pop(jmp_buf* j) {
    SkASSERT(fStack[0] == j);  // 栈平衡检测
    fStack[0] = fStack[1];
    fStack[1] = fStack[2];
    fStack[2] = fStack[3];
    fStack[3] = nullptr;
}
```

**前置条件：**
- `fStack[0]` 必须等于 `j`（push/pop 配对）
- 违反时触发断言，检测栈不平衡

## 内部实现细节

### 错误处理流程

完整的错误处理流程（在 `SkJpegUtility.cpp` 中实现）：

1. **设置错误管理器**：
   ```cpp
   skjpeg_error_mgr errorMgr;
   jpeg_decompress_struct dinfo;
   dinfo.err = jpeg_std_error(&errorMgr);
   errorMgr.error_exit = skjpeg_err_exit;  // 自定义错误退出函数
   ```

2. **建立跳转点**：
   ```cpp
   skjpeg_error_mgr::AutoPushJmpBuf jmpBuf(&errorMgr);
   if (setjmp(jmpBuf)) {
       // libjpeg 调用了 error_exit，通过 longjmp 跳转到这里
       jpeg_destroy_decompress(&dinfo);
       return kError;
   }
   ```

3. **调用 libjpeg**：
   ```cpp
   jpeg_read_header(&dinfo, TRUE);
   jpeg_start_decompress(&dinfo);
   // 如果发生错误，libjpeg 调用 error_exit → longjmp
   ```

4. **错误跳转实现**（在 `SkJpegUtility.cpp`）：
   ```cpp
   void skjpeg_err_exit(j_common_ptr dinfo) {
       skjpeg_error_mgr* error = static_cast<skjpeg_error_mgr*>(dinfo->err);
       (*error->output_message)(dinfo);
       longjmp(*error->fStack[0], 1);  // 跳转到最近的 setjmp
   }
   ```

### 栈深度选择

栈深度设为 4 层的原因：

1. **典型嵌套场景**：
   - 层级 0：主解码循环
   - 层级 1：扫描线解码
   - 层级 2：元数据提取
   - 层级 3：保留/边界情况

2. **实践经验**：
   - Skia 的 JPEG 解码器很少超过 2 层嵌套
   - 4 层提供了安全边界，同时保持内存紧凑（32 字节）

3. **调试支持**：
   - 断言检测栈溢出和不平衡
   - 开发阶段能快速发现错误使用

### AutoPushJmpBuf 的 RAII 保障

**构造函数**：

```cpp
explicit AutoPushJmpBuf(skjpeg_error_mgr* mgr) : fMgr(mgr) {
    fMgr->push(&fJmpBuf);
}
```

在对象创建时自动压栈，即使后续代码抛出异常或返回，析构函数也会执行。

**析构函数**：

```cpp
~AutoPushJmpBuf() {
    fMgr->pop(&fJmpBuf);
}
```

保证栈平衡，避免资源泄漏。

**隐式转换**：

```cpp
operator jmp_buf&() {
    return fJmpBuf;
}
```

使对象可以直接传递给 `setjmp`：
```cpp
AutoPushJmpBuf jmpBuf(&errorMgr);
setjmp(jmpBuf);  // 隐式转换为 jmp_buf&
```

## 依赖关系

**外部依赖：**
- `jpeglib.h`：libjpeg 核心库（通过 `extern "C"` 包含）
- `jerror.h`：libjpeg 错误处理定义
- `setjmp.h`：C 标准库的非局部跳转支持
- `stdio.h`：libjpeg 所需（必须在 jpeglib.h 之前）

**内部依赖：**
- `SkStream.h`：流抽象（虽然本文件不直接使用，但相关模块需要）
- `SkTArray.h`：Skia 数组模板（未直接使用，可能是历史遗留）
- `SkEncodedOrigin.h`：图像方向枚举（同上）

**依赖方：**
- `SkJpegUtility.cpp`：实现 `skjpeg_err_exit` 函数
- `SkJpegCodec.cpp`：JPEG 解码器主类
- `SkJpegSourceMgr.cpp`：源管理器

## 设计模式与设计决策

### 1. RAII (Resource Acquisition Is Initialization)

`AutoPushJmpBuf` 使用 RAII 管理跳转缓冲区生命周期：
- **异常安全**：即使发生 `longjmp`，析构函数也能正确执行（通过栈展开）
- **简化代码**：无需手动调用 `pop`
- **防止泄漏**：编译器保证析构函数调用

### 2. setjmp/longjmp 错误处理

选择 `setjmp/longjmp` 而非 C++ 异常的原因：

**优势**：
- **C 兼容性**：libjpeg 是 C 库，不支持 C++ 异常
- **跨边界安全**：C++ 异常穿越 C 代码未定义行为
- **性能**：正常路径零开销（仅栈变量）

**劣势**：
- **手动管理**：需要显式栈管理
- **限制**：不能跳过 C++ 对象的析构函数（已通过 RAII 解决）

### 3. 栈式管理

使用固定大小数组而非动态分配：
- **性能**：避免堆分配
- **简单性**：无需复杂的内存管理
- **可预测**：栈大小固定，行为确定

### 4. 零初始化

构造函数使用 `jpeg_error_mgr({})` 而非默认构造：
- **MSAN 兼容**：避免未初始化内存访问警告
- **安全性**：确保所有字段有定义值
- **性能**：编译器优化为高效的 `memset`

## 性能考量

### 1. 零开销抽象

在正常路径（无错误）上：
- `AutoPushJmpBuf` 的构造/析构编译为简单的指针操作
- `push/pop` 是内联函数（编译器优化）
- 总开销约 10 条指令（可忽略）

### 2. 错误路径开销

`longjmp` 的开销：
- 恢复寄存器状态：约 50-100 周期
- 栈展开：取决于跳转距离
- 远低于 C++ 异常（数千周期）

### 3. 内存占用

整个 `skjpeg_error_mgr` 结构体大小：
- `jpeg_error_mgr` 基类：约 200 字节
- `fStack[4]`：32 字节（64 位系统）
- 总计：约 232 字节

### 4. 缓存友好性

栈数组紧凑布局，所有 4 个指针在同一缓存行（64 字节）。

## 相关文件

| 文件路径 | 说明 | 关系 |
|---------|------|------|
| `src/codec/SkJpegUtility.h` | JPEG 工具函数 | 声明使用 `skjpeg_error_mgr` 的函数 |
| `src/codec/SkJpegUtility.cpp` | JPEG 工具实现 | 实现 `skjpeg_err_exit` |
| `src/codec/SkJpegCodec.h` | JPEG 解码器 | 使用错误管理器 |
| `src/codec/SkJpegCodec.cpp` | JPEG 解码实现 | 创建和使用 `skjpeg_error_mgr` |
| `jpeglib.h` | libjpeg 库 | 定义 `jpeg_error_mgr` 基类 |
| `jerror.h` | libjpeg 错误定义 | 提供错误码和消息 |
| `setjmp.h` | C 标准库 | 提供 `setjmp/longjmp` |

---

*本文档由 Claude Code 自动生成*
