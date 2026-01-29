# asr2clip 语音转文字剪贴板工具

[![PyPI version](https://badge.fury.io/py/asr2clip.svg?icon=si%3Apython)](https://badge.fury.io/py/asr2clip)
[![GitHub version](https://badge.fury.io/gh/oaklight%2Fasr2clip.svg?icon=si%3Agithub)](https://badge.fury.io/gh/oaklight%2Fasr2clip)
[![License](https://img.shields.io/github/license/Oaklight/asr2clip)](https://github.com/Oaklight/asr2clip/blob/master/LICENSE)

[English](README.md)

本工具旨在实时识别语音，将其转换为文字，并自动将文字复制到系统剪贴板。该工具利用 API 服务进行语音识别，并使用 Python 库进行音频捕获和剪贴板管理。

## 快速开始

```bash
pip install asr2clip       # 安装
asr2clip --edit            # 创建/编辑配置文件
asr2clip --test            # 测试配置
asr2clip                   # 开始录音和转录
```

## 前置条件

在开始之前，请确保已准备好以下内容：

- **Python 3.8 或更高版本**：该工具是用 Python 编写的。
- **API 密钥**：您需要一个语音识别服务的 API 密钥（例如 **OpenAI/Whisper** API 或兼容的 ASR API，如 [硅基流动](https://siliconflow.cn/) 或 [xinference](https://inference.readthedocs.io/en/latest/) 上的 **FunAudioLLM/SenseVoiceSmall**）。

### 系统依赖

| 依赖 | 用途 | Linux | macOS | Windows |
|------|------|-------|-------|---------|
| **ffmpeg** | 音频格式转换 | `apt install ffmpeg` | `brew install ffmpeg` | [下载](https://ffmpeg.org/download.html) |
| **PortAudio** | 音频录制 | `apt install libportaudio2` | `brew install portaudio` | 随 sounddevice 安装 |
| **剪贴板** | 复制到剪贴板 | `apt install xclip` (X11) 或 `wl-clipboard` (Wayland) | 内置 | 内置 |

## 安装

### 选项 1: 使用 pip 或 pipx 安装（推荐）

```bash
# 使用 pip 安装
pip install asr2clip

# 或使用 pipx 安装（推荐用于隔离环境）
pipx install asr2clip

# 升级到最新版本
pip install --upgrade asr2clip
```

### 选项 2: 从源码安装

```bash
git clone https://github.com/Oaklight/asr2clip.git
cd asr2clip
pip install -e .
```

## 配置

### 快速设置

使用内置编辑器配置 asr2clip 是最简单的方式：

```bash
asr2clip --edit  # 在默认编辑器中打开配置文件
```

如果配置文件不存在，将自动在 `~/.config/asr2clip/config.yaml` 创建。

### 配置文件

配置文件使用 YAML 格式：

```yaml
api_base_url: "https://api.openai.com/v1/"  # 或其他兼容的 API 地址
api_key: "YOUR_API_KEY"                     # API 密钥
model_name: "whisper-1"                     # 或其他兼容的模型
# quiet: false                              # 可选，禁用日志
# audio_device: "pulse"                     # 可选，音频输入设备
```

配置文件搜索位置（按顺序）：
1. `./asr2clip.conf`（当前目录）
2. `~/.config/asr2clip/config.yaml`
3. `~/.config/asr2clip.conf`（旧版）
4. `~/.asr2clip.conf`（旧版）

### 测试配置

使用前，请验证您的设置：

```bash
asr2clip --test
```

这将检查：
- ✓ 剪贴板支持
- ✓ 音频设备功能
- ✓ API 连接

### 音频设备选择

如果默认音频设备不工作，列出可用设备并选择一个：

```bash
asr2clip --list_devices    # 列出所有音频输入设备
asr2clip --device pulse    # 使用指定设备
```

或添加到配置文件：
```yaml
audio_device: "pulse"  # 或设备索引如 12
```

## 使用方法

### 基本用法

```bash
asr2clip                   # 录音直到 Ctrl+C，转录，复制到剪贴板
asr2clip --vad             # 持续录音，语音检测自动转录
asr2clip -i audio.mp3      # 转录音频文件
```

### 命令行选项

```
用法: asr2clip [-h] [-v] [-c FILE] [-q] [-i FILE] [-o FILE] [--test]
               [--list_devices] [--device DEV] [-e] [--generate_config]
               [--print_config] [--vad] [--interval SEC] [--adaptive]
               [--calibrate] [--silence_threshold RMS]
               [--silence_duration SEC] [--no_adaptive]

录音并使用 ASR API 转录到剪贴板

选项:
  -h, --help            显示帮助信息并退出
  -v, --version         显示程序版本号并退出
  -c FILE, --config FILE
                        配置文件路径
  -q, --quiet           安静模式 - 仅输出转录结果和错误
  -i FILE, --input FILE
                        转录音频文件而非录音
  -o FILE, --output FILE
                        将转录结果追加到文件
  --test                测试 API 配置并退出
  --list_devices        列出可用的音频输入设备
  --device DEV          音频输入设备（名称或索引）
  -e, --edit            在编辑器中打开配置文件
  --generate_config     在 ~/.config/asr2clip/config.yaml 创建配置文件
  --print_config        打印配置模板到 stdout
  --vad                 持续录音，启用语音活动检测
  --interval SEC        持续录音，固定间隔转录（秒）
  --adaptive            自适应阈值（使用 --vad 时默认启用）
  --calibrate           从环境噪音校准静音阈值
  --silence_threshold RMS
                        静音阈值（默认：自适应自动调整）
  --silence_duration SEC
                        触发转录的静音时长（默认：1.5）
  --no_adaptive         禁用自适应阈值（使用固定阈值）
```

### 示例

```bash
# 单次录音（按 Ctrl+C 停止）
asr2clip

# 转录音频文件
asr2clip -i recording.mp3

# 保存转录结果到文件
asr2clip -o transcript.txt

# 使用指定音频设备
asr2clip --device pulse
```

### 持续录音模式

适用于会议、讲座等长时间录音场景，使用 `--vad` 或 `--interval`：

```bash
# 持续录音，语音活动检测（静音时自动转录）
asr2clip --vad -o ~/meeting.txt

# 持续录音，固定间隔（每 60 秒转录一次）
asr2clip --interval 60 -o ~/meeting.txt

# 结合 VAD 和最大间隔
asr2clip --vad --interval 120 -o ~/meeting.txt
```

持续模式特点：
- 持续录音
- 自动转录（静音时或达到间隔时）
- 按一次 Ctrl+C 停止（退出前会转录剩余音频）
- 转录结果带时间戳追加到输出文件

### 语音活动检测（VAD）

启用静音检测，在您停止说话时自动转录：

```bash
# 检测到静音时自动转录
asr2clip --daemon --vad

# 校准静音阈值（测量环境噪音）
asr2clip --calibrate

# 启用自适应阈值（实时调整）
asr2clip --daemon --vad --adaptive

# 使用自定义静音设置
asr2clip --daemon --vad --silence_threshold 0.005 --silence_duration 2.0
```

VAD 选项：
- `--vad`：启用语音活动检测
- `--adaptive`：启用自适应阈值，实时根据环境噪音调整
- `--calibrate`：测量环境噪音并建议阈值
- `--silence_threshold`：静音 RMS 阈值（默认：0.01）
- `--silence_duration`：触发转录的静音时长（秒，默认：1.5）

提示：使用 `--adaptive` 可以在录音过程中自动调整阈值：
```bash
asr2clip --daemon --vad --adaptive
```

启用 VAD 后，转录在以下情况触发：
1. 检测到语音（音频高于阈值）
2. 随后是静音（音频低于阈值持续指定时长）

## 故障排除

| 问题 | 解决方案 |
|------|----------|
| 音频未捕获 | 运行 `asr2clip --list_devices` 并选择可用设备 |
| 剪贴板不工作 | 安装 `xclip` (X11) 或 `wl-clipboard` (Wayland) |
| API 错误 | 检查配置中的 API 密钥和端点 |
| 静音音频 | 使用 `--device` 尝试其他音频设备 |

运行 `asr2clip --test` 诊断问题。

## 贡献

如果您想为此项目做出贡献，请 fork 仓库并提交 pull request。欢迎任何改进或新功能！

## 许可证

本项目采用 GNU Affero 通用公共许可证 v3.0。详情请参阅 [LICENSE](LICENSE) 文件。