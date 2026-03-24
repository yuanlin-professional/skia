# Doxygen

要生成所有文档，请从本目录运行以下命令：

    doxygen Doxyfile

生成的输出位于

    /tmp/doxygen

要在浏览器中本地查看这些文件，请运行：

    cd /tmp/doxygen/html; python3 -m http.server 8000

然后访问

    http://localhost:8000

如果你希望每次保存时都重新生成文档，可以安装 `entr` 并从本目录运行以下命令：

    find  ../../include/ ../../src/ . | entr doxygen ./Doxyfile

## 安装

在 Linux 桌面上，你可以通过以下方式安装 doxygen 工具：

    sudo apt install doxygen
