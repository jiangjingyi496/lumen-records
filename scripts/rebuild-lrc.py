#!/usr/bin/env python3
from __future__ import annotations

"""重新生成 LRC 歌词文件,支持中英双语合并显示。

数据源优先级 (高 → 低):
1. `lyrics-raw/<album-slug>/<track-filename>.txt` 用户手写的中英双语对
   - 格式: 每两行一对(英文行 + 中文行),段间空行表示节落分隔
2. m4a 自带的 ©lyr 元数据 (Apple Music 写入的)
3. 占位 "(暂无歌词)"

输出 LRC 格式:
- 单语行: [00:02.00]Some lyric
- 双语行: [00:02.00]English line||Chinese line
  双竖线是中英分隔符,前端 JS 解析后渲染成两层 (英文为主,中文为辅)
"""

import re
import sys
from dataclasses import dataclass
from pathlib import Path

from mutagen.mp4 import MP4

ROOT = Path.home() / "music-site"
PUBLIC = ROOT / "public"
LYRICS_RAW = ROOT / "lyrics-raw"

BILINGUAL_SEP = "||"  # 与前端 ApplePlayer 约定一致


@dataclass
class TrackJob:
    slug: str            # album slug
    lrc_filename: str    # 输出 LRC 文件名 (track-NN-...lrc)
    audio_filename: str  # site 内的音频文件名 (track-NN-...m4a)
    fallback_audio: str | None = None  # m4a 自带歌词的回退源 (album 内)


# 每首歌的"前奏 / 尾奏"配置 (秒)。键 = lrc 文件名。
# 用于把均匀分布的歌词时间戳"窗口"控制在真实唱段范围内。
# 没列出的歌走 DEFAULT_INTRO / DEFAULT_OUTRO。
DEFAULT_INTRO = 6.0
DEFAULT_OUTRO = 6.0
TRACK_TIMING: dict[str, tuple[float, float]] = {
    # 经验值,Lumen 这种宗教冥想风格前奏偏长
    "01-movement-i-canticle-of-waiting.lrc": (10.0, 8.0),
    "02-movement-ii-nunc-dimittis.lrc": (8.0, 8.0),
    "03-ere-thou-art-named.lrc": (8.0, 6.0),
}


JOBS: list[TrackJob] = [
    # === Lumen (3 tracks after restructure) ===
    TrackJob(
        slug="lumen-ad-revelationem",
        lrc_filename="01-movement-i-canticle-of-waiting.lrc",
        audio_filename="01-movement-i-canticle-of-waiting.m4a",
        fallback_audio="01-movement-i-canticle-of-waiting.m4a",
    ),
    TrackJob(
        slug="lumen-ad-revelationem",
        lrc_filename="02-movement-ii-nunc-dimittis.lrc",
        audio_filename="02-movement-ii-nunc-dimittis.m4a",
        fallback_audio=None,  # WAV-derived; no embedded lyrics
    ),
    TrackJob(
        slug="lumen-ad-revelationem",
        lrc_filename="03-ere-thou-art-named.lrc",
        audio_filename="03-ere-thou-art-named.m4a",
        fallback_audio=None,
    ),
    # === La Colomba EP (4 tracks, all share Choral Lament's lyrics) ===
    TrackJob(
        slug="la-colomba-grigia-ep",
        lrc_filename="01-la-colomba-grigia-gregorian-choral-lament.lrc",
        audio_filename="01-la-colomba-grigia-gregorian-choral-lament.m4a",
        fallback_audio="01-la-colomba-grigia-gregorian-choral-lament.m4a",
    ),
    TrackJob(
        slug="la-colomba-grigia-ep",
        lrc_filename="02-la-colomba-grigia-gregorian-solo-chant.lrc",
        audio_filename="02-la-colomba-grigia-gregorian-solo-chant.m4a",
        fallback_audio="01-la-colomba-grigia-gregorian-choral-lament.m4a",
    ),
    TrackJob(
        slug="la-colomba-grigia-ep",
        lrc_filename="03-la-colomba-grigia-troubadour-ballad-embellished-ve.lrc",
        audio_filename="03-la-colomba-grigia-troubadour-ballad-embellished-ve.m4a",
        fallback_audio="01-la-colomba-grigia-gregorian-choral-lament.m4a",
    ),
    TrackJob(
        slug="la-colomba-grigia-ep",
        lrc_filename="04-la-colomba-grigia-troubadour-ballad.lrc",
        audio_filename="04-la-colomba-grigia-troubadour-ballad.m4a",
        fallback_audio="01-la-colomba-grigia-gregorian-choral-lament.m4a",
    ),
]


# === Bilingual raw file parsing ===

def parse_bilingual_raw(text: str) -> list[tuple[str, str]]:
    """每两行 (EN, CN) 一对;空行分隔节落。
    若节落以单数行结尾(只有 1 句没有配翻译), 不丢弃, 当作 EN-only 单行保留。"""
    pairs: list[tuple[str, str]] = []
    buf: list[str] = []
    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            if len(buf) == 1:
                pairs.append((buf[0], ""))
            buf.clear()
            continue
        buf.append(line)
        if len(buf) == 2:
            pairs.append((buf[0], buf[1]))
            buf.clear()
    if buf:
        pairs.append((buf[0], ""))
    return pairs


# === m4a 自带歌词 (fallback) ===

_LEAD_BRACKET = re.compile(r"^\s*\[[^\]]*\]\s*")
_INLINE_BRACKETS = re.compile(r"\[[^\]]*\]")
_NEWLINE = re.compile(r"[\r\n]+")
_STAGE_DIR_PATTERNS = [
    re.compile(r"^\s*\[.*\]\s*$"),
    re.compile(r"^\s*\(.*\)\s*$"),
    re.compile(r"^\s*（.*）\s*$"),
    re.compile(r"^\s*【.*】\s*$"),
]


def _is_stage_direction(s: str) -> bool:
    return any(p.match(s) for p in _STAGE_DIR_PATTERNS)


def split_m4a_lyrics(raw: str) -> list[str]:
    """从 m4a 提的原始歌词文本切成单语行(Apple Music 用 \\r 换行)。"""
    out: list[str] = []
    for para in _NEWLINE.split(raw):
        s = para.strip()
        if not s or _is_stage_direction(s):
            continue
        s = _LEAD_BRACKET.sub("", s).strip()
        s = _INLINE_BRACKETS.sub("", s).strip()
        if s:
            out.append(s)
    return out


# === LRC 生成 ===

def fmt_timestamp(t: float) -> str:
    mm = int(t // 60)
    ss = t - mm * 60
    return f"[{mm:02d}:{ss:05.2f}]"


def gen_lrc_bilingual(
    pairs: list[tuple[str, str]],
    duration: float,
    title: str,
    artist: str,
    intro: float = DEFAULT_INTRO,
    outro: float = DEFAULT_OUTRO,
) -> str:
    out = [f"[ti:{title}]", f"[ar:{artist}]"]
    if not pairs:
        return "\n".join(out) + "\n"
    start = intro
    end = max(start + 1.0, duration - outro)
    span = end - start
    step = span / max(len(pairs), 1)
    for i, (en, cn) in enumerate(pairs):
        ts = fmt_timestamp(start + i * step)
        line = f"{en}{BILINGUAL_SEP}{cn}" if cn else en
        out.append(f"{ts}{line}")
    return "\n".join(out) + "\n"


def gen_lrc_single(
    lines: list[str],
    duration: float,
    title: str,
    artist: str,
    intro: float = DEFAULT_INTRO,
    outro: float = DEFAULT_OUTRO,
) -> str:
    pairs = [(ln, "") for ln in lines]
    return gen_lrc_bilingual(pairs, duration, title, artist, intro, outro)


# === Helpers ===

def get_audio_duration(audio_path: Path) -> float:
    if not audio_path.exists():
        return 0.0
    try:
        return float(MP4(audio_path).info.length)
    except Exception:
        return 0.0


def read_embedded_lyrics(m4a_path: Path) -> list[str]:
    try:
        mp4 = MP4(m4a_path)
    except Exception:
        return []
    if not mp4.tags:
        return []
    lyr = mp4.tags.get("\xa9lyr", [])
    if not lyr:
        return []
    raw = lyr[0] if isinstance(lyr, list) else str(lyr)
    return split_m4a_lyrics(raw)


def humanize_title(filename_stem: str) -> str:
    # "02-movement-ii-nunc-dimittis" → "Movement Ii Nunc Dimittis" (rough)
    parts = filename_stem.split("-", 1)
    rest = parts[1] if len(parts) > 1 else parts[0]
    return rest.replace("-", " ").title()


# === Main ===

def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="重生成 LRC 歌词文件")
    ap.add_argument(
        "--force",
        action="store_true",
        help="覆盖已存在的 LRC(默认: 保留已存在的, 这样你在调音器里调过的时间戳不会被冲掉)",
    )
    args = ap.parse_args()

    written, placeholder, preserved = 0, 0, 0

    for job in JOBS:
        lrc_path = PUBLIC / "lrc" / job.slug / job.lrc_filename
        audio_path = PUBLIC / "audio" / job.slug / job.audio_filename
        duration = get_audio_duration(audio_path) or 180.0
        title = humanize_title(Path(job.lrc_filename).stem)
        intro, outro = TRACK_TIMING.get(job.lrc_filename, (DEFAULT_INTRO, DEFAULT_OUTRO))

        # 0. 已存在 LRC 且无 --force → 保留 (调音器里改过的不能被覆盖)
        if lrc_path.exists() and not args.force:
            print(f"  · {job.lrc_filename:60s} 已存在 [跳过, 用 --force 强制重建]")
            preserved += 1
            continue

        # 1. 优先用 lyrics-raw 里的中英对
        raw_file = LYRICS_RAW / job.slug / job.lrc_filename.replace(".lrc", ".txt")
        if raw_file.exists():
            text = raw_file.read_text(encoding="utf-8")
            pairs = parse_bilingual_raw(text)
            lrc = gen_lrc_bilingual(pairs, duration, title, "JiangJingyi", intro, outro)
            lrc_path.write_text(lrc, encoding="utf-8")
            print(f"  ✓ {job.lrc_filename:60s} bilingual {len(pairs):3d} 对 [intro={intro:.0f}s outro={outro:.0f}s]")
            written += 1
            continue

        # 2. fallback: 从同专辑 m4a 自带的 ©lyr 取
        if job.fallback_audio:
            fb_path = PUBLIC / "audio" / job.slug / job.fallback_audio
            lines = read_embedded_lyrics(fb_path)
            if lines:
                lrc = gen_lrc_single(lines, duration, title, "JiangJingyi", intro, outro)
                lrc_path.write_text(lrc, encoding="utf-8")
                print(f"  ✓ {job.lrc_filename:60s} single   {len(lines):3d} 行 [intro={intro:.0f}s outro={outro:.0f}s]")
                written += 1
                continue

        # 3. 占位
        ts = fmt_timestamp(0.0)
        placeholder_text = f"[ti:{title}]\n[ar:JiangJingyi]\n{ts}（暂无歌词,后续可补充）\n"
        lrc_path.write_text(placeholder_text, encoding="utf-8")
        print(f"  ○ {job.lrc_filename:60s} 占位")
        placeholder += 1

    print(f"\n写入 {written} 个真实 LRC, {placeholder} 个占位, 保留 {preserved} 个已调过的。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
