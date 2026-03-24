* `SkEventTracer::SetInstance` 的 `leakTracer` 参数已被移除，现在的行为等同于 `leakTracer=true`。此前，当 `leakTracer=false` 时，`SkEventTracer` 会在 `atexit` 处理程序中被删除，但这在多线程应用程序退出过程中可能导致竞态条件 (Race Condition)。在退出时泄露该对象实际上具有相同的行为，但避免了竞态问题。
* `SkEventTracer` 新增了一个虚函数 `onExit()`，默认不执行任何操作。该函数将在进程退出时被调用，可用于替代析构函数 (Destructor) 中的任何刷新逻辑。
