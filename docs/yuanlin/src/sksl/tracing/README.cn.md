# SkSL Tracing - 着色器调试追踪系统

## 概述

`src/sksl/tracing` 目录实现了 SkSL (Skia Shading Language) 的调试追踪系统。该系统允许开发者像调试普通 C++ 代码一样调试 SkSL 着色器程序，支持单步执行、断点设置、调用栈查看和变量检查等标准调试功能。追踪系统通过在着色器执行期间记录操作序列来实现，这些操作序列随后可以被 `SkSLDebugTracePlayer` 回放和分析。

调试追踪的工作原理是：在 SkSL 编译为 Raster Pipeline 时，代码生成器会在着色器代码中注入追踪操作（trace ops）。这些操作在着色器实际执行时被触发，记录行号变化、变量赋值、函数进入/退出以及作用域变化等事件。所有事件被序列化到一个 `TraceInfo` 数组中，形成完整的执行轨迹。

该系统的核心组件包括三部分：`TraceHook` 定义了追踪事件的回调接口，由 Raster Pipeline 代码生成器在执行时调用；`DebugTracePriv` 存储完整的调试信息，包括变量槽位（slot）映射、函数信息、源代码和追踪事件序列；`SkSLDebugTracePlayer` 是追踪回放引擎，将原始追踪事件转化为用户友好的调试体验，支持 step、step over、step out 和 run 等调试操作。

该系统主要用于 Skia 的调试器工具（如 sksl-minify debugger 和 Skia 的内部调试工具），帮助着色器开发者理解程序的执行逻辑，定位着色器中的错误。追踪功能仅在 Raster Pipeline 后端可用，因为 GPU 后端的着色器在 GPU 上并行执行，无法进行逐像素的单步调试。

## 架构图

```
                 SkSL 编译器
                      |
                      v
         RasterPipelineCodeGenerator
         (注入追踪操作到 RP 指令流)
                      |
                      v
              RP::Program 执行
                      |
            +----+----+----+----+
            |    |    |    |    |
            v    v    v    v    v
          line  var  enter exit scope
          事件  事件  事件  事件  事件
            |    |    |    |    |
            +----+----+----+----+
                      |
                      v
               TraceHook (回调接口)
                      |
                      v
               Tracer (默认实现)
                      |
                      v
              DebugTracePriv
           +---------------------+
           | fSlotInfo[]         |  变量槽位调试信息
           | fUniformInfo[]      |  Uniform 槽位信息
           | fFuncInfo[]         |  函数调试信息
           | fTraceInfo[]        |  追踪事件序列
           | fSource[]           |  源代码行
           | fTraceCoord         |  追踪像素坐标
           +---------------------+
                      |
                      v
           SkSLDebugTracePlayer
           +---------------------+
           | step()              |  单步执行
           | stepOver()          |  单步跳过
           | stepOut()           |  跳出当前函数
           | run()               |  运行到断点
           | setBreakpoints()    |  设置断点
           | getCallStack()      |  获取调用栈
           | getLocalVariables() |  获取局部变量
           | getGlobalVariables()|  获取全局变量
           +---------------------+
                      |
                      v
              调试器 UI / 测试
```

## 目录结构

```
src/sksl/tracing/
|-- BUILD.bazel                    # Bazel 构建配置
|
|-- SkSLTraceHook.h                # 追踪钩子抽象接口定义
|-- SkSLTraceHook.cpp              # Tracer 默认实现
|
|-- SkSLDebugTracePriv.h           # 调试追踪数据存储（核心数据结构）
|-- SkSLDebugTracePriv.cpp         # 调试追踪数据操作（dump、值解释等）
|
|-- SkSLDebugTracePlayer.h         # 追踪回放引擎声明
|-- SkSLDebugTracePlayer.cpp       # 追踪回放引擎实现
```

## 关键类与函数

### TraceHook 抽象接口 (`SkSLTraceHook.h`)

```cpp
class TraceHook {
public:
    virtual ~TraceHook() = default;
    virtual void line(int lineNum) = 0;       // 执行到某行
    virtual void var(int slot, int32_t val) = 0;  // 变量赋值
    virtual void enter(int fnIdx) = 0;        // 进入函数
    virtual void exit(int fnIdx) = 0;         // 退出函数
    virtual void scope(int delta) = 0;        // 作用域变化（+1 进入，-1 离开）
};
```

`TraceHook` 是追踪系统的核心抽象接口，定义了五种追踪事件。Raster Pipeline 代码生成器在生成着色器代码时，会在适当的位置插入对这些方法的调用。每种事件对应一种运行时行为：

- `line(lineNum)`: 执行流到达源代码的新行号
- `var(slot, val)`: 某个变量槽位被写入了新值
- `enter(fnIdx)`: 进入一个函数（压栈）
- `exit(fnIdx)`: 退出一个函数（弹栈）
- `scope(delta)`: 作用域深度变化（如进入/离开一个代码块 `{}`）

### Tracer 默认实现 (`SkSLTraceHook.h/cpp`)

```cpp
class Tracer : public TraceHook {
public:
    static std::unique_ptr<Tracer> Make(std::vector<TraceInfo>* traceInfo);
    void line(int lineNum) override;
    void var(int slot, int32_t val) override;
    void enter(int fnIdx) override;
    void exit(int fnIdx) override;
    void scope(int delta) override;
private:
    std::vector<TraceInfo>* fTraceInfo;  // 指向外部的追踪事件存储
};
```

`Tracer` 是 `TraceHook` 的标准实现。每个回调方法只做一件事：将事件序列化为 `TraceInfo` 结构并追加到 `fTraceInfo` 向量中。这种设计使追踪开销最小化——运行时仅做一次 `push_back` 操作，所有分析工作延迟到回放阶段。

### TraceInfo 事件结构 (`SkSLDebugTracePriv.h`)

```cpp
struct TraceInfo {
    enum class Op {
        kLine,   // data: [行号, 未使用]
        kVar,    // data: [槽位索引, 值的位表示]
        kEnter,  // data: [函数索引, 未使用]
        kExit,   // data: [函数索引, 未使用]
        kScope,  // data: [作用域变化量, 未使用]
    };
    Op op;
    int32_t data[2];  // 两个 32 位整数参数
};
```

`TraceInfo` 是追踪事件的紧凑表示。每个事件仅占 12 字节（4 字节 op + 8 字节 data），确保大量追踪事件的内存开销可控。`data` 数组的含义由 `op` 类型决定。

### SlotDebugInfo 变量槽位信息 (`SkSLDebugTracePriv.h`)

```cpp
struct SlotDebugInfo {
    std::string name;        // 完整变量名（如 "myArray[3].myStruct.myVector"）
    uint8_t columns = 1;     // 列数（标量 = 1，向量 = N，矩阵 = N）
    uint8_t rows = 1;        // 行数（标量/向量 = 1，矩阵 = M）
    uint8_t componentIndex;  // 组件索引（如 vec4.z = 2）
    int groupIndex = 0;      // 复合类型中的分组索引
    Type::NumberKind numberKind;  // 数值类型：float/int/uint/bool
    int line = 0;            // 变量在源代码中的声明位置
    Position pos = {};       // 精确的源位置
    int fnReturnValue = -1;  // 1 = 函数返回值槽位，-1 = 普通变量
};
```

`SlotDebugInfo` 为每个变量槽位提供丰富的调试元数据。在 Raster Pipeline 中，所有变量被展平为标量槽位（slot）。例如一个 `vec3` 变量占据 3 个连续的 slot，每个 slot 对应一个分量。`groupIndex` 用于将属于同一变量的多个 slot 关联在一起，以便在变量写入时更新整个变量组的写入时间戳。

### FunctionDebugInfo (`SkSLDebugTracePriv.h`)

```cpp
struct FunctionDebugInfo {
    std::string name;  // 完整函数声明（如 "float myFunction(half4 color)"）
};
```

### DebugTracePriv 调试追踪存储 (`SkSLDebugTracePriv.h`)

```cpp
class DebugTracePriv : public DebugTrace {
public:
    void setTraceCoord(const SkIPoint& coord);  // 设置追踪的像素坐标
    void setSource(const std::string& source);  // 设置 SkSL 源代码
    void dump(SkWStream* o) const override;     // 生成人类可读的追踪转储

    std::string getSlotComponentSuffix(int slotIndex) const;  // 获取分量后缀（".x"、"[2][1]"）
    std::string getSlotValue(int slotIndex, int32_t value) const;   // 值到文本
    double interpretValueBits(int slotIndex, int32_t valueBits) const;  // 位模式到数值
    std::string slotValueToString(int slotIndex, double value) const;   // 数值到文本

    SkIPoint fTraceCoord;                    // 追踪坐标
    std::vector<SlotDebugInfo> fUniformInfo; // Uniform 变量信息
    std::vector<SlotDebugInfo> fSlotInfo;    // 所有变量槽位信息
    std::vector<FunctionDebugInfo> fFuncInfo;// 函数信息
    std::vector<TraceInfo> fTraceInfo;       // 追踪事件序列
    std::vector<std::string> fSource;        // 源代码行
    std::unique_ptr<TraceHook> fTraceHook;   // 追踪钩子（代码生成时自动创建）
};
```

`DebugTracePriv` 是调试追踪数据的中央存储。它继承自公共 API `DebugTrace`，提供了值解释的核心功能：

- `interpretValueBits()`: 根据槽位的 `numberKind` 将 `int32_t` 位模式重新解释为 `float`、`uint` 或有符号 `int`
- `getSlotComponentSuffix()`: 为向量分量生成 `.x`/`.y`/`.z`/`.w` 后缀，为矩阵分量生成 `[col][row]` 后缀
- `dump()`: 生成完整的追踪转储，包括槽位定义、函数列表和缩进的追踪事件日志

### SkSLDebugTracePlayer 追踪回放引擎 (`SkSLDebugTracePlayer.h`)

```cpp
class SkSLDebugTracePlayer {
public:
    // 调试控制
    void reset(sk_sp<DebugTracePriv> trace);   // 重置到追踪起点
    void step();           // 单步执行（到下一行）
    void stepOver();       // 单步跳过（跳过函数调用）
    void stepOut();        // 跳出当前函数
    void run();            // 运行到下一个断点

    // 断点管理
    void setBreakpoints(std::unordered_set<int> breakpointLines);
    void addBreakpoint(int line);
    void removeBreakpoint(int line);

    // 状态查询
    bool traceHasCompleted() const;
    bool atBreakpoint() const;
    int32_t getCurrentLine() const;
    int32_t getCurrentLineInStackFrame(int stackFrameIndex) const;
    std::vector<int> getCallStack() const;
    int getStackDepth() const;

    // 变量查看
    struct VariableData {
        int fSlotIndex;   // 槽位索引
        bool fDirty;      // 自上次步进后是否被修改
        double fValue;    // 经过类型转换的值
    };
    std::vector<VariableData> getLocalVariables(int stackFrameIndex) const;
    std::vector<VariableData> getGlobalVariables() const;

    // 行号统计
    const LineNumberMap& getLineNumbersReached() const;

private:
    struct StackFrame {
        int32_t fFunction;     // 函数索引
        int32_t fLine;         // 当前行号
        SkBitSet fDisplayMask; // 该栈帧中可见的变量槽位
    };
    struct Slot {
        int32_t fValue;        // 当前值
        int fScope;            // 所在作用域深度
        size_t fWriteTime;     // 最近写入时间（游标位置）
    };

    bool execute(size_t position);  // 执行单个追踪事件
    void tidyState();               // 清理步间临时状态
    void updateVariableWriteTime(int slotIdx, size_t writeTime);  // 更新变量组写入时间
};
```

`SkSLDebugTracePlayer` 是整个追踪系统面向用户的核心类。它通过维护以下状态来模拟着色器的逐步执行：

1. **执行游标** (`fCursor`): 当前在 `fTraceInfo` 中的位置
2. **作用域深度** (`fScope`): 当前的代码块嵌套深度
3. **变量槽位数组** (`fSlots`): 所有变量的当前值、作用域和写入时间
4. **调用栈** (`fStack`): 函数调用的栈帧，每帧记录函数ID、当前行号和可见变量掩码
5. **脏标记** (`fDirtyMask`): 记录本次步进中被修改的变量
6. **返回值掩码** (`fReturnValues`): 标识哪些槽位是函数返回值

调试操作的实现逻辑：
- `step()`: 向前执行直到遇到 `kLine` 事件
- `stepOver()`: 向前执行直到在当前栈深度或更浅处遇到 `kLine` 事件
- `stepOut()`: 向前执行直到栈深度小于初始深度（即退出当前函数）
- `run()`: 向前执行直到遇到断点行的 `kLine` 事件

变量离开作用域时（`kScope` delta < 0），`execute()` 会扫描所有槽位，将作用域深度大于当前深度的变量从显示掩码中移除。这确保了用户只能看到当前作用域内的有效变量。

## 依赖关系

```
追踪系统依赖:
+----------------------------------------------------+
| 上游（追踪系统使用的模块）                           |
|   - include/sksl/SkSLDebugTrace.h  公共调试接口     |
|   - src/sksl/ir/SkSLType.h        类型信息         |
|   - src/sksl/SkSLPosition.h       源码位置         |
|   - include/core/SkRefCnt.h       引用计数         |
|   - include/core/SkStream.h       输出流           |
|   - include/core/SkPoint.h        像素坐标         |
|   - src/utils/SkBitSet.h          位集合           |
+----------------------------------------------------+

+----------------------------------------------------+
| 下游（使用追踪系统的模块）                           |
|   - src/sksl/codegen/SkSLRasterPipelineCodeGenerator|
|     在代码生成时注入追踪操作                         |
|   - src/sksl/codegen/SkSLRasterPipelineBuilder      |
|     在程序构建时持有 TraceHook                       |
|   - 调试器工具 / 测试                                |
|     通过 SkSLDebugTracePlayer 进行追踪回放          |
+----------------------------------------------------+
```

## 设计模式分析

### 1. 观察者模式 (Observer Pattern)

`TraceHook` 接口是经典的观察者模式实现。着色器执行引擎（Raster Pipeline）作为被观察者，在执行过程中通知 `TraceHook` 观察者各种事件。`Tracer` 作为具体观察者，将事件记录下来供后续分析。

### 2. 命令模式 (Command Pattern)

`TraceInfo` 事件序列本质上是命令模式的体现。每个 `TraceInfo` 是一个可序列化的命令对象，记录了一次操作的类型和参数。`SkSLDebugTracePlayer::execute()` 方法根据命令类型执行相应的状态变更，实现了命令的延迟执行和回放。

### 3. 记录-回放模式 (Record-Replay Pattern)

整个追踪系统采用记录-回放架构：
- **记录阶段**: `Tracer` 在着色器执行时记录所有事件到 `fTraceInfo`
- **回放阶段**: `SkSLDebugTracePlayer` 按顺序执行事件序列，重建程序状态

这种分离使得追踪数据可以被保存、传输和多次回放，不需要重新执行着色器。

### 4. 位掩码优化

`SkBitSet` 被广泛用于高效跟踪变量可见性（`fDisplayMask`）、脏状态（`fDirtyMask`）和返回值标识（`fReturnValues`）。位操作的 O(1) 复杂度确保了即使在有大量变量槽位的情况下，调试操作也能快速执行。

### 5. 值语义位转换

`DebugTracePriv::interpretValueBits()` 使用 `memcpy` 进行类型双关（type punning），将 `int32_t` 位模式安全地重新解释为 `float` 或 `uint32_t`。这是 C++ 中进行位级类型转换的推荐方式，避免了未定义行为。

## 数据流

```
=== 编译时 ===
SkSL 源代码
   |
   v  SkSL 编译器前端
SkSL IR (Program)
   |
   v  MakeRasterPipelineProgram(program, function, debugTrace, writeTraceOps=true)
   |
   +---> 分析变量声明 -> 填充 DebugTracePriv::fSlotInfo[]
   +---> 分析函数定义 -> 填充 DebugTracePriv::fFuncInfo[]
   +---> 设置源代码   -> DebugTracePriv::setSource()
   +---> 创建 TraceHook -> DebugTracePriv::fTraceHook
   |
   v  代码生成器在指令流中插入追踪操作
RP::Program (含追踪指令)

=== 运行时 ===
RP::Program::appendStages()
   |
   v  对指定像素坐标 (fTraceCoord) 执行着色器
   |
   +---> trace_line 指令 -> TraceHook::line(lineNum)    -> fTraceInfo += {kLine, lineNum, 0}
   +---> trace_var  指令 -> TraceHook::var(slot, val)   -> fTraceInfo += {kVar, slot, val}
   +---> trace_enter指令 -> TraceHook::enter(fnIdx)     -> fTraceInfo += {kEnter, fnIdx, 0}
   +---> trace_exit 指令 -> TraceHook::exit(fnIdx)      -> fTraceInfo += {kExit, fnIdx, 0}
   +---> trace_scope指令 -> TraceHook::scope(delta)     -> fTraceInfo += {kScope, delta, 0}
   |
   v  执行完成
DebugTracePriv (包含完整追踪数据)

=== 回放阶段 ===
SkSLDebugTracePlayer::reset(debugTrace)
   |
   +---> 初始化 fSlots[nslots] = {value=0, scope=MAX, writeTime=0}
   +---> 创建全局栈帧 fStack[0] = {function=-1, line=-1}
   +---> 统计 fLineNumbers[行号] = 到达次数
   |
   v  用户调试操作循环
   |
   +---> step()
   |        |
   |        v  execute(fCursor++)
   |        |
   |        +---> kLine: 更新当前行号，减少 fLineNumbers 计数 -> 返回 true (停止)
   |        +---> kVar:  更新 fSlots[slot].fValue，设置脏标记，
   |        |            更新 fStack 显示掩码 -> 返回 false (继续)
   |        +---> kEnter: 压入新 StackFrame -> 返回 false
   |        +---> kExit:  弹出 StackFrame -> 返回 true (停止)
   |        +---> kScope: 更新 fScope，清理超出作用域的变量 -> 返回 false
   |
   +---> getLocalVariables(stackFrameIndex)
   |        |
   |        v  从 fStack[idx].fDisplayMask 获取可见槽位
   |        v  对每个槽位: interpretValueBits() 转换值
   |        v  按 fWriteTime 降序排列（最近修改的排在前面）
   |
   +---> getCallStack()
            |
            v  返回 fStack[1..N].fFunction 索引数组
```

## 相关文档与参考

- **公共 API**: `include/sksl/SkSLDebugTrace.h` 定义了 `DebugTrace` 公共基类。
- **Raster Pipeline 集成**: `src/sksl/codegen/SkSLRasterPipelineCodeGenerator.cpp` 中的追踪操作注入逻辑。
- **Raster Pipeline 构建器**: `src/sksl/codegen/SkSLRasterPipelineBuilder.h` 中的 `DebugTracePriv` 和 `TraceHook` 成员变量。
- **测试文件**: Skia 测试套件中包含 `SkSLDebugTracePlayerTest` 等测试，验证追踪回放的正确性。
- **位集合工具**: `src/utils/SkBitSet.h` 提供了高效的位集合操作。
- **相关目录**:
  - `src/sksl/codegen/` - Raster Pipeline 代码生成器（追踪操作的注入点）
  - `src/sksl/ir/` - SkSL 中间表示（`Type::NumberKind` 等类型信息）
  - `include/sksl/` - SkSL 公共 API
