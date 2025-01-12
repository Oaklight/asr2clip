# asr to clipboard 实时语音转文字剪贴板工具

[English](README_en.md)

本工具旨在实时识别语音，将其转换为文字，并自动将文字复制到系统剪贴板。该工具利用 API 服务进行语音识别，并使用 Python 库进行音频捕获和剪贴板管理。

## 前置条件

在开始之前，请确保已准备好了以下内容：

- **Python 3.8 或更高版本**：该工具是用 Python 编写的，因此您需要在系统上安装 Python。
- **API 密钥**：您需要一个语音识别服务的 API 密钥（例如 OpenAI 的 Whisper API 或兼容的语音转文字 (ASR) API，如[siliconflow](https://siliconflow.cn)）。请确保您拥有必要的凭证。

## 安装

1. **克隆仓库**（如果适用）：

```bash
git clone https://github.com/Oaklight/asr_to_clipboard.git
cd asr_to_clipboard
```

2. **安装所需的 Python 包**：

```bash
pip install -r requirements.txt
```

3. **设置 API 密钥**：
   - 在项目的根目录下创建一个 `config.yaml` 文件，已提供了一个示例文件 `config.example.yaml`。
   - 将您的 API 密钥添加到 `config.yaml` 文件中：

```yaml
asr_model:
  api_key: "your_api_key_here"
  api_base_url: "https://api.openai.com/v1" # 如果需要自定义 API 地址
  model_name: "whisper-1" # 默认模型名称
```

4. **Linux 用户注意**：
如果您在 Linux 上使用 `pyperclip` ，请确保安装了 `xclip` 或 `xsel` 。可以通过以下命令安装

```bash
sudo apt-get install xsel # 基础剪贴板功能
sudo apt-get install xclip # 功能更强
```

## 使用方法

1. **运行工具**：

```bash
python asr_to_clipboard.py
```

或者，如果您已经使脚本可执行（通过 `chmod +x asr_to_clipboard.py` ），可以直接运行：

```bash
./asr_to_clipboard.py
```

2. **开始说话**：

   - 工具将开始从麦克风捕获音频。
   - 它将音频发送到 API 进行语音识别。
   - 识别出的文字将自动复制到系统剪贴板。

3. **停止工具**：
   - 按 `Ctrl+C` 停止工具。

## 配置

您可以通过修改 `config.yaml` 文件来自定义工具。例如，您可以根据使用的 API 服务更改 API 端点、音频采样率或其他参数。

## 示例

```bash
$ ./asr_to_clipboard.py --duration 5
Recording for 5 seconds...
Recording complete.
Transcribing audio...
Transcribed Text:
-----------------
1233211234567，这是一个中文测试。
The transcribed text has been copied to the clipboard.
```

## 故障排除

- **音频未捕获**：确保您的麦克风已正确连接并配置。
- **API 错误**：检查您的 API 密钥，并确保您有足够的额度或权限。
- **剪贴板问题**：确保 `pyperclip` 已正确安装并与您的操作系统兼容。Linux 用户需要安装 `xclip` 或 `xsel`。

## 贡献

如果您想为此项目做出贡献，请 fork 仓库并提交 pull request。欢迎任何改进或新功能！

## 许可证

本项目采用 GNU Affero General Public License v3.0 许可证。有关更多详细信息，请参阅 `LICENSE` 文件。
