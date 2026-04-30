# 更新日志

asr2clip 的所有重要变更均记录在此。

## 0.4.0（未发布）

### 新增

- **本地 ASR 服务器** — 基于 [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) 的可选离线转录，提供 OpenAI 兼容 API（`asr2clip-serve` / `asr2clip --serve`）
- **模型注册表** — 基于 YAML 的模型管理（`models.yaml`），支持多种模型类型（sense_voice、whisper、paraformer、transducer），具备懒加载和自动下载功能
- **多模型路由** — API 的 `model` 参数选择使用哪个引擎；模型在首次请求时加载
- **逐请求参数** — `language`、`prompt` 和 `temperature` 传递给引擎（取决于模型是否支持），不支持的参数会被静默接受
- **语言识别器 LRU 缓存** — 按语言缓存识别器实例，支持每次请求不同的语言提示（可配置缓存大小，默认 3 个）
- **SSE 流式传输** — `stream=true` 参数返回 Server-Sent Events（`transcript.text.delta`、`transcript.text.done`、`[DONE]`）
- `--download-model` 选项，预下载默认模型
- `--host` / `--port` / `--config` 选项，配置本地 ASR 服务器
- CI 流水线，包含 ruff、ty、complexipy 检查

### 变更

- **零外部依赖** — 使用内置 YAML 解析器和 HTTP 客户端替代 PyYAML 和 httpx/requests；核心安装仅需 numpy、sounddevice、pydub 和 copykitten
- **剪贴板库** — 使用 [copykitten](https://github.com/koenvervloesem/copykitten)（基于 Rust）替代 pyperclip，无需安装 xclip/wl-clipboard 等外部工具
- **Wayland 剪贴板** — 在 Wayland 会话下，优先使用 `wl-copy` 以正确集成剪贴板管理器（如 KDE Klipper）；在 X11 或 wl-copy 不可用时回退到 copykitten
- 最低 Python 版本从 3.8 提升至 **3.10**

### 修复

- `-i` 参数现在能正确触发文件转录，而不再误入持续录音模式

## 0.3.8

### 新增

- **语音活动检测（VAD）**，通过 `--vad` 标志在静音时自动触发转录
- **多特征 VAD** — 结合 RMS 能量、过零率和语音频段能量比，实现稳健检测
- **自适应阈值** — 实时根据环境噪音调整（使用 `--vad` 时默认启用）
- **环境噪音校准** — `--calibrate` 测量环境噪音并建议阈值
- **持续录音模式** — `--vad` 和 `--interval` 适用于会议、讲座等长时间场景
- **异步转录** — 转录在后台运行，结果按顺序输出
- **超时自动重试** — 可配置重试次数和延迟
- **结构化日志** 支持 ANSI 颜色和彩色状态指示
- **双击 Ctrl+C** 在持续模式下强制退出（单次 Ctrl+C 会先转录剩余音频）
- **自动校准** 启动时测量环境噪音水平

### 变更

- 代码模块化重构，拆分为 audio、config、output、transcribe、vad、utils 模块
- 简化 CLI 并改进配置管理

### 修复

- 修复 WAV 写入时多维音频数组处理
- VAD 确认语音时跳过静音检查

## 0.3.7

### 新增

- `--version` / `-v` 选项，显示程序版本号
- `--edit` / `-e` 选项，在默认编辑器中打开配置文件
- `--test` 命令，全面测试配置（剪贴板、音频、API）
- 音频设备选择，支持 `--list_devices` 和 `--device`

### 变更

- 从 `setup.py` 迁移至 `pyproject.toml`，使用动态版本管理
- 移除未使用的依赖包

## 0.3.6

### 新增

- `-o FILE` / `--output` 选项，将转录结果追加到文件（带时间戳）
- 转录结果输出到 stdout

## 0.3.5

### 新增

- `--generate_config` 和 `--print_config`，管理配置模板
- `org_id` 支持 OpenAI 组织 ID
- 详细日志模式，通过 `-q` / `--quiet` 切换

## 0.3.0

### 新增

- 音频文件转录（`-i FILE`），基于 ffmpeg 的格式转换
- 支持 MP3、WAV、FLAC、OGG 及 ffmpeg 支持的其他格式

### 变更

- 项目从 `asr_to_clipboard` 更名为 `asr2clip`

## 0.2.0

### 新增

- 持续录音模式
- 录音时长选项
- 可配置音频参数

## 0.1.0

### 新增

- 首次发布
- 实时语音录制和转录
- 剪贴板集成
- YAML 配置文件支持
- OpenAI Whisper API 支持
