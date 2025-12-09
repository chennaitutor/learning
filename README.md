# Talking photo prototype

This repository contains a lightweight Python script that turns a still image
into a short talking-head style clip. Provide an image plus either a spoken
audio track or text to synthesize, and the script will animate a simple mouth
shape and optionally mux the audio into the generated MP4.

> This is a prototype with a toy visual effect—it does **not** perform true lip
> syncing, but it is an easy way to experiment locally without downloading large
> machine learning models.

## Quick start

1. Install the dependencies (Python 3.10+ recommended):

   ```bash
   pip install -r requirements.txt
   ```

2. Generate a clip from an image and an audio file (WAV works best):

   ```bash
   python talking_photo.py my_face.png --audio speech.wav --include-audio --output demo.mp4
   ```

3. Or let the script synthesize speech from text using `pyttsx3`:

   ```bash
   python talking_photo.py my_face.png --text "Hello from the talking photo" --include-audio
   ```

4. If you only want the animated mouth without audio muxed into the video,
   omit the `--include-audio` flag.

The script requires `ffmpeg` on your PATH. On most Linux distributions you can
install it via your system package manager.

## How it works

- The input image is duplicated into a series of frames with a simple rounded
  rectangle drawn where the mouth would be. The shape alternates between two
  open states to mimic speech cadence.
- Audio input is converted to a temporary mono WAV file (or synthesized from
  text) to measure its duration and drive the frame count.
- Frames are stitched into an MP4 with `ffmpeg`, optionally muxing the audio to
  keep the track aligned with the animation.

Feel free to tweak the defaults (frame rate, mouth color) via the CLI flags to
experiment with different looks.
