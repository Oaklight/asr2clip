# 本地 ASR 服务器

asr2clip 包含一个可选的本地 ASR 服务器，基于 [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) 实现完全离线的语音识别。

## 安装

使用 `local_asr` 可选依赖安装：

```bash
pip install "asr2clip[local_asr]"
```

## 下载模型

首次使用前，预下载 SenseVoice 模型：

```bash
asr2clip --download-model
```

模型默认存储在 `~/.cache/asr2clip/models/` 目录下。

## 启动服务器

可以通过两种方式启动服务器：

```bash
# 使用专用命令
asr2clip-serve

# 或使用 --serve 标志
asr2clip --serve
```

服务器默认在 `http://localhost:8000` 启动，提供 OpenAI 兼容的 `/v1/audio/transcriptions` 端点。

### 服务器选项

| 选项 | 默认值 | 说明 |
|------|--------|------|
| `--host` | `127.0.0.1` | 服务器绑定地址 |
| `--port` | `8000` | 服务器绑定端口 |
| `--model-dir` | 自动 | ASR 模型目录路径 |
| `--num-threads` | `4` | 推理线程数 |

```bash
# 在自定义地址和端口启动
asr2clip --serve --host 0.0.0.0 --port 9000

# 使用指定模型目录
asr2clip --serve --model-dir /path/to/models
```

## 配置

将 asr2clip 指向本地服务器：

```yaml
api_base_url: "http://localhost:8000/v1/"
api_key: "not-used"
model_name: "sensevoice-small"
```

## 使用方式

```bash
# 在一个终端启动服务器
asr2clip --serve

# 在另一个终端使用本地服务器
asr2clip -c local_config.yaml

# 或直接转录文件
asr2clip -c local_config.yaml -i recording.mp3
```

## 特性

- **完全离线** — 无需互联网连接
- **OpenAI 兼容 API** — 可作为云端 ASR 服务的直接替代
- **自动下载模型** — 首次使用时自动下载模型
- **多模型支持** — 通过 sherpa-onnx 配置 ASR 模型
- **集成 CLI** — 使用 `asr2clip --serve` 启动服务器，无需单独命令
