# d-api 接口文档

**Base URL:** `http://127.0.0.1:8080/api/v1`

> 交互式文档（Swagger UI）：`http://127.0.0.1:8080/docs`

---

## 目录

- [Spotify - 自动接口（推荐）](#spotify---自动接口推荐)
- [Lyrics - 歌词](#lyrics---歌词)
- [Spotify - OAuth 手动流程](#spotify---oauth-手动流程)
- [通用说明](#通用说明)

---

## Spotify - 自动接口（推荐）

> 无需前端传 token，服务端自动管理认证。

### GET `/spotify/auto/me`

获取当前授权用户的 Spotify 个人信息。

**请求参数：** 无

**响应示例：**
```json
{
  "id": "312gpw2wmnsmjb6v5u4y45uglh2e",
  "display_name": "mierhaosi2",
  "email": "mierhaosi2@gmail.com",
  "country": "EG",
  "product": "premium",
  "images": [
    {
      "url": "https://i.scdn.co/image/xxx",
      "height": 300,
      "width": 300
    }
  ],
  "followers": { "total": 0 },
  "external_urls": {
    "spotify": "https://open.spotify.com/user/312gpw2wmnsmjb6v5u4y45uglh2e"
  }
}
```

---

### GET `/spotify/auto/playing`

获取当前正在播放的曲目。

**请求参数：** 无

**响应示例（有歌曲）：**
```json
{
  "is_playing": true,
  "progress_ms": 66459,
  "item": {
    "id": "xxxxxx",
    "name": "I LUV IT (feat. Playboi Carti)",
    "duration_ms": 172000,
    "artists": [
      { "id": "xxx", "name": "Camila Cabello" }
    ],
    "album": {
      "id": "xxx",
      "name": "C,XOXO",
      "images": [
        { "url": "https://i.scdn.co/image/xxx", "height": 640, "width": 640 }
      ]
    },
    "external_urls": {
      "spotify": "https://open.spotify.com/track/xxx"
    }
  }
}
```

**响应示例（未播放）：**
```json
{
  "playing": false,
  "item": null
}
```

---

### GET `/spotify/auto/top-tracks`

获取用户最常听的曲目。

**请求参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `time_range` | string | 否 | `medium_term` | `short_term`（近4周）/ `medium_term`（近6个月）/ `long_term`（全部时间） |
| `limit` | integer | 否 | `20` | 返回数量，范围 1~50 |

**响应示例：**
```json
{
  "items": [
    {
      "id": "xxx",
      "name": "360",
      "artists": [{ "name": "Charli xcx" }],
      "album": {
        "name": "BRAT",
        "images": [{ "url": "https://i.scdn.co/image/xxx", "height": 640, "width": 640 }]
      },
      "duration_ms": 133805,
      "external_urls": { "spotify": "https://open.spotify.com/track/xxx" }
    }
  ],
  "total": 50,
  "limit": 20,
  "offset": 0
}
```

---

### GET `/spotify/auto/recently-played`

获取最近播放记录。

**请求参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `limit` | integer | 否 | `20` | 返回数量，范围 1~50 |

**响应示例：**
```json
{
  "items": [
    {
      "track": {
        "id": "xxx",
        "name": "Rock Music",
        "artists": [{ "name": "Charli xcx" }],
        "album": { "name": "Rock Music", "images": [...] },
        "duration_ms": 115106
      },
      "played_at": "2026-07-16T08:44:55.407Z"
    }
  ],
  "next": "https://api.spotify.com/v1/me/player/recently-played?before=xxx&limit=20"
}
```

---

## Lyrics - 歌词

> 歌词数据来源：[LRCLIB](https://lrclib.net)（免费开源）

### GET `/lyrics/now-playing`

自动获取当前 Spotify 正在播放曲目的歌词。

**请求参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `synced` | boolean | 否 | `true` | `true`=LRC 时间轴格式，`false`=纯文本 |

**响应示例（有歌词）：**
```json
{
  "playing": true,
  "track": "Camila Cabello - I LUV IT (feat. Playboi Carti)",
  "album": "C,XOXO",
  "progress_ms": 66459,
  "has_synced": true,
  "lyrics": "[00:07.32] Supersonic (yeah, ooh)\n[00:08.42] In your orbit (yeah, ah)\n..."
}
```

**响应示例（未播放）：**
```json
{
  "playing": false,
  "lyrics": null
}
```

**响应示例（找不到歌词）：**
```json
{
  "playing": true,
  "track": "xxx - xxx",
  "lyrics": null,
  "message": "未找到歌词"
}
```

> **LRC 格式说明：** `[mm:ss.xx] 歌词内容`，前端可按 `progress_ms` 实时高亮对应行，实现卡拉OK效果。

---

### GET `/lyrics/track`

按歌曲名 + 歌手名查询歌词。

**请求参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `track` | string | **是** | - | 歌曲名 |
| `artist` | string | **是** | - | 歌手名 |
| `album` | string | 否 | `""` | 专辑名（可选，提高匹配精度） |
| `synced` | boolean | 否 | `true` | `true`=LRC 时间轴，`false`=纯文本 |

**请求示例：**
```
GET /lyrics/track?track=party+4+u&artist=Charli+xcx
```

**响应示例：**
```json
{
  "track": "Charli xcx - party 4 u",
  "album": "how i'm feeling now",
  "has_synced": true,
  "lyrics": "[00:12.34] ...\n[00:16.78] ..."
}
```

**错误响应（404）：**
```json
{
  "detail": "未找到「Charli xcx - party 4 u」的歌词"
}
```

---

### GET `/lyrics/search`

关键词搜索歌词库。

**请求参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `q` | string | **是** | - | 搜索关键词（歌名/歌手名等） |
| `limit` | integer | 否 | `5` | 返回数量，范围 1~20 |

**请求示例：**
```
GET /lyrics/search?q=charli+xcx+360&limit=3
```

**响应示例：**
```json
[
  {
    "id": 12345,
    "track_name": "360",
    "artist_name": "Charli xcx",
    "album_name": "BRAT",
    "duration": 133,
    "has_synced": true
  }
]
```

---

## Spotify - OAuth 手动流程

> 仅首次配置时需要，日常使用走「自动接口」即可。

### GET `/spotify/login`

跳转到 Spotify 授权页面（浏览器打开）。

### GET `/callback`

Spotify 授权回调，自动换取 token（浏览器会显示 JSON）。

### GET `/spotify/refresh`

刷新 access_token。

**请求参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `refresh_token` | string | **是** | Spotify refresh_token |

---

## 通用说明

### 状态码

| 状态码 | 说明 |
|--------|------|
| `200` | 请求成功 |
| `400` | 参数错误 / Spotify 授权失败 |
| `404` | 未找到歌词 |
| `500` | 服务端错误 |

### 错误响应格式

```json
{
  "detail": "错误描述"
}
```

### 健康检查

```
GET /health
```

```json
{
  "status": "ok",
  "project": "d-api",
  "debug": true
}
```
