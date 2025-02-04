# asr2clip 语音转文字剪贴板工具

[English](README.md)

本工具旨在实时识别语音，将其转换为文字，并自动将文字复制到系统剪贴板。该工具利用 API 服务进行语音识别，并使用 Python 库进行音频捕获和剪贴板管理。

## 前置条件

在开始之前，请确保已准备好了以下内容：

- **Python 3.8 或更高版本**：该工具是用 Python 编写的，因此您需要在系统上安装 Python。
- **API 密钥**：您需要一个语音识别服务的 API 密钥（例如 **OpenAI/Whisper** API 或与之兼容的语音转文字 (ASR) API，如**FunAudioLLM/SenseVoiceSmall**，见[硅基流动siliconflow](https://siliconflow.cn/) 或 [xinference](https://inference.readthedocs.io/en/latest/)）。请确保您拥有必要的凭证。

## 安装

### 选项 1: 使用 pip 或 pipx 安装

您可以直接从 PyPI 使用 `pip` 或 `pipx` 安装 `asr2clip`：

```bash
# 使用 pip 安装
pip install asr2clip

# 或者使用 pipx 安装（推荐用于隔离环境）
pipx install asr2clip
```

### 选项 2: 从源码安装

1. **克隆仓库**（如果适用）：

```bash
git clone https://github.com/Oaklight/asr2clip.git
cd asr2clip
```

2. **安装所需的 Python 包**：

```bash
pip install -r requirements.txt
```

### 选项 3: 使用 Conda 安装

如果您使用 Conda，可以使用提供的 `environment.yaml` 文件创建环境：

```bash
conda env create -f environment.yaml
conda activate asr
```

3. **设置 API 密钥**：
   - 在项目的根目录下或您的 `~/.config/` 目录中创建一个 `asr2clip.conf` 文件，已提供了一个示例文件 [`asr2clip.conf.example`](asr2clip.conf.example)。
   - 将您的 API 密钥添加到 `asr2clip.conf` 文件中（YAML 格式）：

```yaml
api_key: your_api_key_here
api_base_url: https://api.openai.com/v1
model_name: whisper-1
```

4. **Linux 用户注意**：
如果您在 Linux 上使用 `pyperclip` ，请确保安装了 `xclip` 或 `xsel` 。可以通过以下命令安装：

```bash
sudo apt-get install xsel # 基础剪贴板功能，对asr2clip无差别
sudo apt-get install xclip # 功能更强，对asr2clip无差别
```

## 使用方法

1. **运行工具**：

```bash
asr2clip
```

2. **开始说话**：
   - 工具将开始从麦克风捕获音频。
   - 它将音频发送到 API 进行语音识别。
   - 识别出的文字将自动复制到系统剪贴板。

3. **停止工具**：
   - 按 `Ctrl+C` 停止工具。

### 命令行选项

- **从文件转录**：
  您可以通过指定文件路径直接转录音频文件。工具支持 `pydub` 支持的所有音频格式（如 MP3、WAV、FLAC、AAC 等）：

```bash
asr2clip --input /path/to/audio/file.mp3
```

- **从 stdin 读取音频数据**：
  您也可以直接将音频数据通过管道输入工具：

```bash
cat /path/to/audio/file.wav | asr2clip --stdin
```

- **设置录音时长**：
  您可以指定录音的时长（秒）：

```bash
asr2clip --duration 10
```

- **输出到文件或 stdout**：
  您可以将转录的文字输出到文件或 stdout，而不是复制到剪贴板。使用 `-o` 或 `--output` 选项：
  - 输出到文件（自动创建文件或目录）：
    ```bash
    asr2clip --output /path/to/output.txt
    ```
  - 输出到 stdout：
    ```bash
    asr2clip --output -
    ```

- **生成配置文件模板**：
  生成一个配置文件模板并退出：

```bash
asr2clip --generate_config
```

- **静默模式**：
  禁用日志输出：

```bash
asr2clip --quiet
```

- **指定配置文件**：
  使用自定义配置文件路径：

```bash
asr2clip --config /path/to/config.conf
```

---

### 示例

```bash
$ ./asr2clip.py --duration 5
Recording for 5 seconds...
Recording complete.
Transcribing audio...
Transcribed Text:
-----------------
1233211234567，这是一个中文测试。
The transcribed text has been copied to the clipboard.
```

---

### 故障排除

- **音频未捕获**：确保您的麦克风已正确连接并配置。
- **API 错误**：检查您的 API 密钥，并确保您有足够的额度或权限。
- **剪贴板问题**：确保 `pyperclip` 已正确安装并与您的操作系统兼容。Linux 用户需要安装 `xclip` 或 `xsel`。
- **文件输出问题**：如果指定的输出文件路径包含不存在的目录，工具将自动创建该目录。请自行注意权限问题。

---

### 贡献

如果您想为此项目做出贡献，请 fork 仓库并提交 pull request。欢迎任何改进或新功能！

---

### 许可证

本项目采用 GNU Affero 通用公共许可证 v3.0。详情请参阅 [LICENSE](LICENSE) 文件。
