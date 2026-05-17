#!/usr/bin/env python3
"""一次性产出"投递包"到 ~/music-site/release-package/, 包含:
1. 3000x3000 高清封面 (Lanczos 升采样)
2. 9 首歌的标准元数据 CSV
3. 每首歌的 EN-only + CN-only LRC 文件 (网易/QQ 接受格式)
4. 中文区"安全替代标题/描述"清单 (避开 国内审核 红线)
5. README + AI 披露文案模板
"""

from __future__ import annotations

import csv
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from PIL import Image
from mutagen.mp4 import MP4

ROOT = Path.home() / "music-site"
PUBLIC = ROOT / "public"
PKG = ROOT / "release-package"

BILINGUAL_SEP = "||"


@dataclass
class Track:
    n: int                      # 曲序
    title: str                  # 国际版正式曲名
    audio_filename: str         # 文件名 (在 public/audio/<slug>/)
    lrc_filename: str           # LRC 文件名
    title_cn_safe: str          # 中文区安全替代曲名


@dataclass
class Album:
    slug: str
    title: str
    subtitle: str
    cover_filename: str
    year: int
    artist: str
    genre_primary: str
    genre_secondary: str
    tracks: list[Track]
    title_cn_safe: str          # 中文区替代专辑名
    description_intl: str       # 国际版专辑描述
    description_cn_safe: str    # 中文区安全描述


ALBUMS: list[Album] = [
    Album(
        slug="lumen-ad-revelationem",
        title="Lumen ad Revelationem",
        subtitle="A Candlemas Liturgical Drama — The Song of Simeon",
        cover_filename="lumen-ad-revelationem.jpg",
        year=2026,
        artist="JiangJingyi",
        genre_primary="Classical Crossover",
        genre_secondary="Sacred / Choral",
        title_cn_safe="守候之光",
        description_intl=(
            "A bilingual sacred song cycle inspired by the Canticle of Simeon (Luke 2:25–35). "
            "Five movements weaving liturgical Latin titles, English verse, and Chinese reflection, "
            "produced with SUNO Pro under commercial license. Curated and arranged by JiangJingyi."
        ),
        description_cn_safe=(
            "中英双语古典声乐组曲。五个乐章以中世纪礼仪戏剧形制为结构原型,"
            "以光、等候、记忆为核心意象,融合西方古典声乐与东方文学化的中文译唱。"
            "由 JiangJingyi 策划、整理、定稿,生成式 AI 辅助创作。"
        ),
        tracks=[
            Track(1, "Movement I — Canticle of Waiting",
                  "01-movement-i-canticle-of-waiting.m4a",
                  "01-movement-i-canticle-of-waiting.lrc",
                  "第一乐章 · 等候之歌"),
            Track(2, "Movement II — Nunc Dimittis",
                  "02-movement-ii-nunc-dimittis.m4a",
                  "02-movement-ii-nunc-dimittis.lrc",
                  "第二乐章 · 安然之歌"),
            Track(3, "Ere Thou Art Named",
                  "03-ere-thou-art-named.m4a",
                  "03-ere-thou-art-named.lrc",
                  "命名之前 · 摇篮曲"),
            Track(4, "Adventus Tacitus — The Silent Coming",
                  "04-adventus-tacitus-the-silent-coming.m4a",
                  "04-adventus-tacitus-the-silent-coming.lrc",
                  "第四乐章 · 寂静之至"),
            Track(5, "Canticum Annae",
                  "05-canticum-annae.m4a",
                  "05-canticum-annae.lrc",
                  "第五乐章 · 守望之歌"),
        ],
    ),
    Album(
        slug="la-colomba-grigia-ep",
        title="La Colomba Grigia (The Grey Dove) — EP",
        subtitle="Four Variations on a Single Lament",
        cover_filename="la-colomba-grigia-ep.jpg",
        year=2026,
        artist="JiangJingyi",
        genre_primary="World",
        genre_secondary="Classical Crossover",
        title_cn_safe="灰鸽 · La Colomba",
        description_intl=(
            "Four variations on a single lament — from sacred plainchant to troubadour ballad. "
            "A bilingual song cycle on memory, departure, and the fixed star that does not sink. "
            "Produced with SUNO Pro under commercial license. Curated and arranged by JiangJingyi."
        ),
        description_cn_safe=(
            "同一支挽歌的四种变奏 —— 由古朴的合咏到游吟诗人民谣。"
            "中英双语,主题为记忆、离别与那颗不肯沉落的星。"
            "由 JiangJingyi 策划、整理、定稿,生成式 AI 辅助创作。"
        ),
        tracks=[
            Track(1, "La Colomba Grigia: Choral Lament",
                  "01-la-colomba-grigia-gregorian-choral-lament.m4a",
                  "01-la-colomba-grigia-gregorian-choral-lament.lrc",
                  "灰鸽 · 合咏挽歌"),
            Track(2, "La Colomba Grigia: Solo Chant",
                  "02-la-colomba-grigia-gregorian-solo-chant.m4a",
                  "02-la-colomba-grigia-gregorian-solo-chant.lrc",
                  "灰鸽 · 独唱版"),
            Track(3, "La Colomba Grigia: Troubadour Ballad (Embellished)",
                  "03-la-colomba-grigia-troubadour-ballad-embellished-ve.m4a",
                  "03-la-colomba-grigia-troubadour-ballad-embellished-ve.lrc",
                  "灰鸽 · 游吟诗人民谣(华彩版)"),
            Track(4, "La Colomba Grigia: Troubadour Ballad",
                  "04-la-colomba-grigia-troubadour-ballad.m4a",
                  "04-la-colomba-grigia-troubadour-ballad.lrc",
                  "灰鸽 · 游吟诗人民谣"),
        ],
    ),
]


# === 1. 升采样封面 ===

def upscale_cover(album: Album) -> Path:
    src = PUBLIC / "covers" / album.cover_filename
    dst_dir = PKG / album.slug
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / "cover-3000.jpg"

    img = Image.open(src).convert("RGB")
    # 先 center-crop 成正方形
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    img = img.crop((left, top, left + side, top + side))
    # 再 Lanczos 升采到 3000x3000
    img = img.resize((3000, 3000), Image.LANCZOS)
    img.save(dst, format="JPEG", quality=92, optimize=True, progressive=True)
    return dst


# === 2. 拆 LRC 为 EN-only + CN-only ===

LRC_LINE_RE = re.compile(r"^(\[\d{1,2}:\d{1,2}(?:\.\d+)?\])(.*)$")


def split_bilingual_lrc(src: Path) -> tuple[str, str, str]:
    """读取我的 EN||CN 格式 LRC, 返回 (en_lrc, cn_lrc, plain_text)。"""
    en_lines: list[str] = []
    cn_lines: list[str] = []
    plain_lines: list[str] = []

    raw = src.read_text(encoding="utf-8")
    for line in raw.split("\n"):
        m = LRC_LINE_RE.match(line)
        if not m:
            # [ti:..] [ar:..] 这些 metadata header 行直接保留到两个 LRC
            if line.startswith("[") and not line.strip().endswith("]"):
                continue
            if line.startswith("[ti:") or line.startswith("[ar:") or line.startswith("[al:"):
                en_lines.append(line)
                cn_lines.append(line)
            continue
        ts, body = m.group(1), m.group(2).strip()
        if BILINGUAL_SEP in body:
            en, cn = body.split(BILINGUAL_SEP, 1)
            en, cn = en.strip(), cn.strip()
            en_lines.append(f"{ts}{en}")
            cn_lines.append(f"{ts}{cn}")
            plain_lines.append(en)
            plain_lines.append(cn)
        else:
            # 单语行,只放进 EN
            en_lines.append(f"{ts}{body}")
            plain_lines.append(body)

    en_lrc = "\n".join(en_lines) + "\n"
    cn_lrc = "\n".join(cn_lines) + "\n"
    plain = "\n".join(plain_lines) + "\n"
    return en_lrc, cn_lrc, plain


def write_lrc_set(album: Album, track: Track) -> None:
    src_lrc = PUBLIC / "lrc" / album.slug / track.lrc_filename
    if not src_lrc.exists():
        print(f"  skip (no lrc): {src_lrc}")
        return
    out_dir = PKG / album.slug
    stem = src_lrc.stem  # e.g. "01-movement-i-canticle-of-waiting"
    en, cn, plain = split_bilingual_lrc(src_lrc)
    (out_dir / f"{stem}.en.lrc").write_text(en, encoding="utf-8")
    (out_dir / f"{stem}.cn.lrc").write_text(cn, encoding="utf-8")
    (out_dir / f"{stem}.txt").write_text(plain, encoding="utf-8")


# === 3. 元数据 CSV ===

CSV_COLUMNS = [
    "album_title_intl",
    "album_title_cn_safe",
    "album_artist",
    "release_date",
    "genre_primary",
    "genre_secondary",
    "label",
    "album_cover_3000_file",
    "track_no",
    "track_title_intl",
    "track_title_cn_safe",
    "track_duration_sec",
    "track_duration_mmss",
    "composer",
    "lyricist",
    "producer",
    "ai_assisted",
    "audio_file",
    "lyrics_lrc_en",
    "lyrics_lrc_cn",
    "lyrics_text_bilingual",
    "isrc",
    "iswc",
    "language",
    "explicit",
]


def get_duration(album: Album, track: Track) -> int:
    p = PUBLIC / "audio" / album.slug / track.audio_filename
    if not p.exists():
        return 0
    try:
        return int(MP4(p).info.length)
    except Exception:
        return 0


def fmt_mmss(sec: int) -> str:
    return f"{sec // 60}:{sec % 60:02d}"


def write_csv() -> Path:
    csv_path = PKG / "metadata.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for album in ALBUMS:
            for track in album.tracks:
                dur = get_duration(album, track)
                stem = Path(track.lrc_filename).stem
                row = {
                    "album_title_intl": album.title,
                    "album_title_cn_safe": album.title_cn_safe,
                    "album_artist": album.artist,
                    "release_date": f"{album.year}-06-01",  # 用户可自己改
                    "genre_primary": album.genre_primary,
                    "genre_secondary": album.genre_secondary,
                    "label": "Self-released (JiangJingyi)",
                    "album_cover_3000_file": f"{album.slug}/cover-3000.jpg",
                    "track_no": track.n,
                    "track_title_intl": track.title,
                    "track_title_cn_safe": track.title_cn_safe,
                    "track_duration_sec": dur,
                    "track_duration_mmss": fmt_mmss(dur),
                    "composer": "JiangJingyi (with AI assistance)",
                    "lyricist": "JiangJingyi (with AI assistance)",
                    "producer": "JiangJingyi · SUNO Pro",
                    "ai_assisted": "Yes",
                    "audio_file": f"public/audio/{album.slug}/{track.audio_filename}",
                    "lyrics_lrc_en": f"{album.slug}/{stem}.en.lrc",
                    "lyrics_lrc_cn": f"{album.slug}/{stem}.cn.lrc",
                    "lyrics_text_bilingual": f"{album.slug}/{stem}.txt",
                    "isrc": "",   # 发行商分配
                    "iswc": "",   # 词曲版权号,可空
                    "language": "English / Chinese",
                    "explicit": "No",
                }
                w.writerow(row)
    return csv_path


# === 4. 中文区安全替代清单 ===

CN_SAFE_MD = """# 中文区(网易云 / QQ 音乐)安全发行版

> 用于规避审核敏感词的"国内版"投递清单。海外版(Apple Music / Spotify / DistroKid)请用 `metadata.csv` 里的 `*_intl` 字段。

## ⚠ 关键替换原则
- ❌ 拉丁文宗教术语 (Lumen / Canticum / Adventus / Nunc Dimittis)
- ❌ 直接的圣经/西默盎/弥赛亚/教堂等关键词
- ❌ 流派标签 "宗教 / 圣咏 / Sacred"
- ✅ 用 "古典声乐" / "古风 / 世界音乐 / 中世纪音乐" 替代
- ✅ 用"等候 / 守望 / 光 / 静默"等意象词,不点宗教

## 专辑 1:Lumen ad Revelationem → "守候之光"

| 字段 | 国际版 | 国内安全版 |
|---|---|---|
| 标题 | Lumen ad Revelationem | **守候之光** |
| 副标题 | A Candlemas Liturgical Drama — The Song of Simeon | **古典声乐五部曲** |
| 流派 | Sacred / Choral | **古典 / 世界音乐** |

**国内描述文案**(直接复制粘贴):
> 中英双语古典声乐组曲。五个乐章以中世纪戏剧形制为结构原型,
> 以光、等候、记忆为核心意象,融合西方古典声乐与东方文学化的中文译唱。
> 由 JiangJingyi 策划、整理、定稿,生成式 AI 辅助创作。

**国内曲目重命名**:

1. 第一乐章 · 等候之歌
2. 第二乐章 · 安然之歌
3. 命名之前 · 摇篮曲
4. 第四乐章 · 寂静之至
5. 第五乐章 · 守望之歌

## 专辑 2:La Colomba Grigia → "灰鸽"

| 字段 | 国际版 | 国内安全版 |
|---|---|---|
| 标题 | La Colomba Grigia (The Grey Dove) — EP | **灰鸽 · La Colomba** |
| 副标题 | Four Variations on a Single Lament | **同一首挽歌的四种变奏** |
| 流派 | World / Classical Crossover | **世界音乐 / 民谣** |

**国内描述文案**:
> 同一支挽歌的四种变奏 —— 由古朴的合咏到游吟诗人民谣。
> 中英双语,主题为记忆、离别与那颗不肯沉落的星。
> 由 JiangJingyi 策划、整理、定稿,生成式 AI 辅助创作。

**国内曲目重命名**:

1. 灰鸽 · 合咏挽歌
2. 灰鸽 · 独唱版
3. 灰鸽 · 游吟诗人民谣(华彩版)
4. 灰鸽 · 游吟诗人民谣

## 封面调整建议

- **Lumen 封面**:原图人物 + 教堂十字架明显,**国内版建议另出一张更抽象的封面**(用蜡烛 + 光晕 + 鸽子,去掉十字架与人形)。如果保留原图,**审核失败率较高**。
- **La Colomba 封面**:彩窗里有教堂剪影,但风格化处理,**审核通过率较高**,可以直接用。
"""


# === 5. AI 披露文案模板 ===

AI_DISCLOSURE_MD = """# AI 披露文案模板(各平台直接复制粘贴)

## 标准版(英文,海外平台用)
Music composed and produced with the assistance of generative AI (SUNO Pro, licensed for commercial release). Lyrics co-written with AI tools. All artistic direction, theme, curation, and final selection by JiangJingyi. All commercial rights duly held.

## 标准版(中文,国内平台用)
本作品由生成式 AI 辅助创作(SUNO Pro 商业授权,合法持有发行权)。歌词由 AI 协同创作,作品的艺术方向、主题构思、选材与最终成品由 JiangJingyi 完成。

## 短版(限字段)
AI-assisted composition (SUNO Pro, commercial license). Curated by JiangJingyi.

## 字段勾选
- DistroKid / TuneCore: 上传时勾选 "Contains AI-generated content"
- Apple Music: liner notes 写明
- Spotify: 当前(2026)未强制,但建议勾选
- 网易云 / QQ:在描述里 + 投递备注里都写一遍
"""


# === 6. README ===

README_MD = """# Release Package · JiangJingyi

一次性产出投递包,包含:

```
release-package/
├── README.md                       # 本文件
├── metadata.csv                    # 9 首歌完整元数据 (UTF-8 with BOM, Excel/Numbers 可直开)
├── localized-cn.md                 # 国内审核安全替代标题/描述清单
├── ai-disclosure.md                # AI 披露文案模板(中英)
├── lumen-ad-revelationem/
│   ├── cover-3000.jpg              # 3000×3000 JPEG,投递规格
│   ├── 01-...en.lrc                # 英文同步歌词
│   ├── 01-...cn.lrc                # 中文同步歌词 (网易"翻译歌词"字段)
│   ├── 01-...txt                   # 中英对照纯文本
│   └── ... 其余 4 首同结构
└── la-colomba-grigia-ep/
    └── ... 4 首同结构
```

## 各平台投递路径

| 平台 | 路径 | 用什么字段 |
|---|---|---|
| 网易云音乐人 | https://music.163.com/musician | 国内版字段 + `.en.lrc`(主歌词) + `.cn.lrc`(翻译歌词) |
| 腾讯音乐人 | https://y.tencentmusic.com | 国内版字段 + 同上 |
| DistroKid | https://distrokid.com | 国际版字段, 上传时勾选 AI-assisted |
| Apple Music for Artists | (via DistroKid) | DistroKid 自动同步 |

## 音频文件位置

WAV / M4A 原文件不在本包内, 路径在 `metadata.csv` 的 `audio_file` 列:
- `public/audio/lumen-ad-revelationem/*.m4a`
- `public/audio/la-colomba-grigia-ep/*.m4a`

上传时如果发行商需要 **WAV** (一般要求 ≥ 16-bit 44.1kHz), 可以用 afconvert 反向把 M4A 转回 WAV:
```bash
afconvert -f WAVE -d LEI16@44100 input.m4a output.wav
```

或者直接用原始 WAV(在 Apple Music 媒体库 `~/Music/Music/Media.localized/Music/Jiangjingyi/` 里有)。

## 国内 vs 海外的差异

- **海外**(Apple / Spotify / YouTube Music 等 150+): 用原标题、原描述、原封面
- **国内**(网易云 / QQ 音乐): 用 `localized-cn.md` 里的"安全版"标题/描述,**Lumen 封面建议重新做**(原图教堂+十字架明显,审核可能不过)

## AI 披露(每个平台都要做)

参见 `ai-disclosure.md`,**任何平台投递时都填**。诚实披露 > 隐瞒。
"""


# === 主流程 ===

def main() -> int:
    PKG.mkdir(parents=True, exist_ok=True)

    print("=== 1. 升采样封面到 3000×3000 ===")
    for album in ALBUMS:
        dst = upscale_cover(album)
        print(f"  ✓ {album.slug} → {dst.relative_to(ROOT)}")

    print("\n=== 2. 拆 LRC 为 EN-only / CN-only / 纯文本 ===")
    total_lrc = 0
    for album in ALBUMS:
        for track in album.tracks:
            write_lrc_set(album, track)
            total_lrc += 1
    print(f"  ✓ 处理 {total_lrc} 首歌, 每首 3 个文件 (.en.lrc / .cn.lrc / .txt)")

    print("\n=== 3. 元数据 CSV ===")
    csv_path = write_csv()
    print(f"  ✓ {csv_path.relative_to(ROOT)}  ({sum(len(a.tracks) for a in ALBUMS)} 行)")

    print("\n=== 4. 中文安全替代清单 ===")
    (PKG / "localized-cn.md").write_text(CN_SAFE_MD, encoding="utf-8")
    print(f"  ✓ {PKG.name}/localized-cn.md")

    print("\n=== 5. AI 披露模板 ===")
    (PKG / "ai-disclosure.md").write_text(AI_DISCLOSURE_MD, encoding="utf-8")
    print(f"  ✓ {PKG.name}/ai-disclosure.md")

    print("\n=== 6. README ===")
    (PKG / "README.md").write_text(README_MD, encoding="utf-8")
    print(f"  ✓ {PKG.name}/README.md")

    # 汇总
    print(f"\n>>> 全部完成。包路径: {PKG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
