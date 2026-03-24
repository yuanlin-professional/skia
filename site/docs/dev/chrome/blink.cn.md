
---
title: "Blink 布局测试"
linkTitle: "Blink layout tests"

---

如何提交会改变 Blink 布局测试 (Layout Test) 结果的 Skia 更改。
有关运行 Blink 布局测试的更多详情，请参阅 https://chromium.googlesource.com/chromium/src/+/HEAD/docs/testing/web_tests.md。

关于布局测试的一般提示
-------------------------------
* 布局测试有两种类型："比较两个 HTML 页面" 和 "比较 HTML 页面与 .png 文件"。
  重新基线化 (Rebaseline) 时，大部分工作来自于为第二种类型重新生成 .png 文件。第一种类型的文件类似 `third_party/blink/web_tests/.../something.html`，并有一个同级伴随文件 `.../something-expected.html`。
  ([示例](https://source.chromium.org/chromium/chromium/src/+/main:third_party/blink/web_tests/fast/forms/text/input-appearance-autocomplete-very-long-value.html;drc=f68d6358bed8ebfc88a0198d6cda50256620c71d);
  [伴随 html](https://source.chromium.org/chromium/chromium/src/+/main:third_party/blink/web_tests/fast/forms/text/input-appearance-autocomplete-very-long-value-expected.html;drc=f68d6358bed8ebfc88a0198d6cda50256620c71d))
  第二种类型没有伴随 html 文件，但可能有一个伴随的 .png 文件，或者在其他目录中有多个 .png 文件（当 html 在其他平台或设置上应渲染不同时）。
  ([示例](https://source.chromium.org/chromium/chromium/src/+/main:third_party/blink/web_tests/dark-mode/images/opt-out-svg-gradient.html;drc=44ad10338113aab1779d81df359aca34da89daf3);
  [期望 png](https://source.chromium.org/chromium/chromium/src/+/main:third_party/blink/web_tests/virtual/dark-mode-default/dark-mode/images/opt-out-svg-gradient-expected.png;l=1;drc=ec59d7b96e81ccc0e3dc497697e23304d7259b09))
  对于第二种类型，如果您需要查看重新基线化历史等信息，使用 <https://cs.chromium.org> 是一个好方法。

* 两种类型的布局测试都可以通过向测试文件添加 meta HTML 标签来进行模糊匹配 (Fuzzy Matching)。
  `<meta name="fuzzy" content="maxDifference=0-4; totalPixels=0-100" />`

* 一些非布局测试（也称为像素测试 (Pixel Test)）会因为渲染更改而失败，因为它们有自己已检入的图像。查看失败测试的日志，这些日志应该会输出期望图像和实际图像的 base64 编码 png。打开一个浏览器标签页，使用开发者工具创建一个 `<img src="[base64]" />` 并填入实际的 base64 数据，然后右键保存图像作为新的期望数据。
  ([示例](https://source.chromium.org/chromium/chromium/src/+/main:chrome/browser/ui/views/accessibility/accessibility_focus_highlight_browsertest.cc;l=238;drc=a48632411d7e7263e8fd4d273d24a80f668b73ec);
   [期望 png](https://source.chromium.org/chromium/chromium/src/+/main:chrome/test/data/accessibility/focus_highlight_appearance.png;l=1;drc=1e2dbf6a77e2f7264da0097a3cd4158c249a75b8))

* 一些测试比较 [Skia 和 PyCairo](https://source.chromium.org/chromium/chromium/src/+/main:third_party/blink/web_tests/external/wpt/html/canvas/tools/README.md)。
  由于 Skia 与 Cairo 做出不同的选择，最好增加这些测试的模糊容差。查找生成测试的 .yaml 文件中的 `fuzzy` 条目，然后重新生成（或者直接使用查找替换）。

* 失败的 CQ 测试通常有 "Show Reproduction Instructions" 可用于本地运行。这有助于验证模糊容差。请务必使用 [--gtest_filter](https://github.com/google/googletest/blob/main/docs/advanced.md#running-a-subset-of-the-tests) 来限制测试范围以加快迭代速度。

影响大量测试结果的更改
--------------------------------------------------
当"大量"或"许多"意味着超过约 20 个时，在 Chromium 中重新基线化是一个较复杂的过程。

1. 向 Skia 代码添加一个暂存定义 (Staging Define)，允许客户端在编译时选择使用旧代码路径。如果只有 Chromium 需要重新基线化，使用 `if !defined(SK_USE_LEGACY_xxx)` 可能更容易设置。如果需要跨多个客户端暂存，`if defined(SK_USE_NEW_xxx)` 更好，可以让客户端逐个"选择加入"。
   ([示例 CL](https://crrev.com/c/6316987))
2. 告诉 Chromium 通过在其 `SkUserConfig.h`（或如果仅影响特定构建，则在 `//skia/BUILD.gn`）中使用暂存定义来使用旧代码路径。
   ([示例 CL](https://crrev.com/c/6316987))
3. 提交并等待自动滚动器将 Skia 滚动合入 Chromium。
   ([示例 CL](http://review.skia.org/953516) [自动滚动 CL](https://crrev.com/c/6324680))
4. 创建 Chromium CL 以使用新代码路径（通过删除定义）并更新期望值。
   遵循[重新基线化步骤](https://chromium.googlesource.com/chromium/src/+/HEAD/docs/testing/web_test_expectations.md#How-to-rebaseline)来更新使用参考图像的布局测试。
   对于其他类型的测试（包括 .html 和 -expected.html 类型），请参考上述提示手动更新它们。要更新图像，由于其他同时进行的更改或不稳定的测试，您可能需要重复"同步"、"运行试运行作业"和"从中重新基线化图像"的流程几次。可以随意为任何不稳定的测试添加 `<meta name="fuzzy"` 标签。

   ([示例 CL](https://crrev.com/c/6328778))
5. 从 Skia 中删除暂存定义。
   ([示例 CL](http://review.skia.org/960516))

影响少量布局测试结果的更改
---------------------------------------------------------
影响少于约 20 个布局测试的更改可以不使用暂存定义，按以下步骤重新基线化：

1. 准备您的 Skia 更改。运行 `Chromium-Canary` 试运行作业并记下哪些布局测试将变红。
2. 在包含您更改的 Skia 自动滚动之前，手动向 Blink LayoutTests/TestExpectations [文件](https://chromium.googlesource.com/chromium/src/+/main/third_party/blink/web_tests/TestExpectations) 推送更改，将预期因您的更改而失败的测试标记如下：
   ```
   foo/bar/test-name.html [ Failure Pass ]  # Needs rebaseline
   ```
   有一个 `Skia roll test suppressions` 部分可以使用（以避免与其他更改冲突）。
3. 将您的代码检入 Skia 仓库。
4. 等待 Skia 滚动成功合入。
5. 在您的 Chromium 检出目录中，创建一个新分支
  （例如 `git co main && gclient sync -D && git cl new-branch update-expectations`）。
  遵循[重新基线化步骤](https://chromium.googlesource.com/chromium/src/+/HEAD/docs/testing/web_test_expectations.md#How-to-rebaseline)并从 `TestExpectations` 中删除抑制项。
