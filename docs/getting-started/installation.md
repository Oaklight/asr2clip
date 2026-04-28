# 安装

## 系统依赖

安装 asr2clip 之前，请确保以下系统依赖可用：

| 依赖 | 用途 | Linux | macOS | Windows |
|------|------|-------|-------|---------|
| **ffmpeg** | 音频格式转换 | `apt install ffmpeg` | `brew install ffmpeg` | [下载](https://ffmpeg.org/download.html) |
| **PortAudio** | 音频录制 | `apt install libportaudio2` | `brew install portaudio` | 随 sounddevice 安装 |
| **剪贴板** | 复制到剪贴板 | `apt install xclip` (X11) 或 `wl-clipboard` (Wayland) | 内置 | 内置 |

## 使用 pip 或 pipx 安装（推荐）

```bash
# 使用 pip 安装
pip install asr2clip

# 或使用 pipx 安装（推荐用于隔离环境）
pipx install asr2clip

# 升级到最新版本
pip install --upgrade asr2clip
```

## 从源码安装

```bash
git clone https://github.com/Oaklight/asr2clip.git
cd asr2clip
pip install -e .
```

## 可选：本地 ASR 服务器

安装本地 ASR 服务器（基于 sherpa-onnx 的离线转录）：

```bash
pip install "asr2clip[local_asr]"
```
