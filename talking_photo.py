"""Simple talking photo generator.

This script builds a basic talking-head style video from a still image and an
input audio track (or text that will be synthesized to speech using
``pyttsx3``). It is not intended to be production-grade lip sync, but it gives
an easy way to experiment locally without heavy ML dependencies.
"""

import argparse
import os
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Tuple

from PIL import Image, ImageDraw


FFMPEG_BIN = os.environ.get("FFMPEG", "ffmpeg")


class TalkingPhotoError(Exception):
    """Custom error for talking photo failures."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a simple talking photo video")
    parser.add_argument("image", type=Path, help="Path to the source image")
    audio_group = parser.add_mutually_exclusive_group(required=True)
    audio_group.add_argument("--audio", type=Path, help="Path to an input audio file (wav recommended)")
    audio_group.add_argument("--text", type=str, help="Text to convert to speech using pyttsx3")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("talking_photo.mp4"),
        help="Output video path (mp4)",
    )
    parser.add_argument("--fps", type=int, default=12, help="Frames per second for the animation")
    parser.add_argument(
        "--mouth-color",
        type=str,
        default="#e74c3c",
        help="Color used for the animated mouth overlay",
    )
    parser.add_argument(
        "--include-audio",
        action="store_true",
        help="Mux the provided or generated audio into the output video",
    )
    return parser.parse_args()


def ensure_ffmpeg() -> None:
    try:
        subprocess.run([FFMPEG_BIN, "-version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:  # pragma: no cover - environment specific
        raise TalkingPhotoError("ffmpeg is required but was not found on PATH") from exc


def synthesize_text_to_audio(text: str, target_path: Path) -> None:
    try:
        import pyttsx3
    except ImportError as exc:  # pragma: no cover - import guard
        raise TalkingPhotoError(
            "pyttsx3 is required for text-to-speech; install dependencies or provide an audio file"
        ) from exc

    engine = pyttsx3.init()
    engine.save_to_file(text, str(target_path))
    engine.runAndWait()


def convert_audio_to_wav(source_audio: Path, wav_path: Path) -> None:
    """Convert any ffmpeg-supported audio input to wav for duration checks."""
    cmd = [
        FFMPEG_BIN,
        "-y",
        "-i",
        str(source_audio),
        "-ac",
        "1",
        "-ar",
        "16000",
        str(wav_path),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def audio_duration(audio_path: Path) -> float:
    with wave.open(str(audio_path), "rb") as wav_file:
        frames = wav_file.getnframes()
        rate = wav_file.getframerate()
        return frames / float(rate)


def generate_mouth_box(image_size: Tuple[int, int]) -> Tuple[int, int, int, int]:
    width, height = image_size
    box_width = int(width * 0.25)
    box_height = int(height * 0.12)
    left = (width - box_width) // 2
    top = int(height * 0.7)
    right = left + box_width
    bottom = top + box_height
    return left, top, right, bottom


def draw_frame(base_image: Image.Image, mouth_box: Tuple[int, int, int, int], mouth_color: str, open_factor: float) -> Image.Image:
    frame = base_image.copy()
    left, top, right, bottom = mouth_box
    open_height = int((bottom - top) * open_factor)
    adjusted_bottom = top + open_height

    draw = ImageDraw.Draw(frame)
    draw.rounded_rectangle((left, top, right, adjusted_bottom), radius=12, fill=mouth_color)
    return frame


def build_frames(image_path: Path, wav_path: Path, fps: int, mouth_color: str) -> Tuple[str, int]:
    base_image = Image.open(image_path).convert("RGB")
    duration_seconds = audio_duration(wav_path)
    frame_count = max(1, int(duration_seconds * fps))

    mouth_box = generate_mouth_box(base_image.size)
    temp_dir = tempfile.mkdtemp(prefix="frames_")

    for idx in range(frame_count):
        # Alternate mouth openness to simulate speech cadence.
        open_factor = 0.25 + 0.35 * (1 + (-1) ** idx) / 2  # toggles between two values
        frame = draw_frame(base_image, mouth_box, mouth_color, open_factor)
        frame.save(os.path.join(temp_dir, f"frame{idx:04d}.png"))

    return temp_dir, frame_count


def assemble_video(frames_dir: str, audio_path: Path, fps: int, output: Path, include_audio: bool) -> None:
    frame_pattern = os.path.join(frames_dir, "frame%04d.png")
    cmd = [
        FFMPEG_BIN,
        "-y",
        "-framerate",
        str(fps),
        "-i",
        frame_pattern,
    ]

    if include_audio:
        cmd.extend(["-i", str(audio_path), "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac"])
    else:
        cmd.extend(["-c:v", "libx264", "-pix_fmt", "yuv420p"])

    cmd.append(str(output))
    subprocess.run(cmd, check=True)


def main() -> None:
    args = parse_args()
    ensure_ffmpeg()

    temp_dir = tempfile.mkdtemp(prefix="talking_photo_")
    wav_audio = Path(temp_dir) / "speech.wav"

    try:
        if args.text:
            synthesize_text_to_audio(args.text, wav_audio)
        else:
            convert_audio_to_wav(args.audio, wav_audio)

        frames_dir, _ = build_frames(args.image, wav_audio, args.fps, args.mouth_color)
        assemble_video(frames_dir, wav_audio, args.fps, args.output, args.include_audio)
        print(f"Saved talking photo to {args.output}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        if 'frames_dir' in locals():
            shutil.rmtree(frames_dir, ignore_errors=True)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
