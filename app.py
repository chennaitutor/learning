from pathlib import Path
import tempfile
import shutil

from flask import Flask, render_template_string, request, send_file, after_this_request

from talking_photo import TalkingPhotoError, create_talking_photo

app = Flask(__name__)


FORM_HTML = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Talking Photo</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 2rem; max-width: 720px; }
      form { display: grid; gap: 1rem; }
      label { font-weight: bold; }
      input[type="file"], input[type="text"], input[type="number"] { width: 100%; }
      .field { display: flex; flex-direction: column; }
      .hint { font-size: 0.9rem; color: #555; }
      .error { color: #c0392b; font-weight: bold; }
      button { padding: 0.75rem 1rem; font-size: 1rem; cursor: pointer; }
    </style>
  </head>
  <body>
    <h1>Create a talking photo</h1>
    {% if error %}
      <div class="error">{{ error }}</div>
    {% endif %}
    <form method="post" enctype="multipart/form-data">
      <div class="field">
        <label for="image">Image (required)</label>
        <input type="file" id="image" name="image" accept="image/*" required>
        <div class="hint">Upload a clear face photo (PNG or JPG recommended).</div>
      </div>

      <div class="field">
        <label for="text">Speech text</label>
        <input type="text" id="text" name="text" placeholder="Type what the photo should say">
        <div class="hint">Provide text or upload an audio file below. Exactly one is required.</div>
      </div>

      <div class="field">
        <label for="audio">Audio file</label>
        <input type="file" id="audio" name="audio" accept="audio/*">
        <div class="hint">If provided, this audio will be used instead of the text above.</div>
      </div>

      <div class="field">
        <label for="mouth_color">Mouth color</label>
        <input type="text" id="mouth_color" name="mouth_color" value="#e74c3c" placeholder="#e74c3c">
      </div>

      <div class="field">
        <label for="fps">Frames per second</label>
        <input type="number" id="fps" name="fps" value="12" min="1" max="60">
      </div>

      <div class="field">
        <label><input type="checkbox" name="include_audio" checked> Include audio in the video</label>
      </div>

      <button type="submit">Generate video</button>
    </form>
  </body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def index():
    error = None

    if request.method == "POST":
        image_file = request.files.get("image")
        text_value = (request.form.get("text") or "").strip() or None
        audio_file = request.files.get("audio") if request.files.get("audio") and request.files.get("audio").filename else None
        mouth_color = request.form.get("mouth_color") or "#e74c3c"
        include_audio = bool(request.form.get("include_audio"))

        try:
            fps = int(request.form.get("fps") or 12)
        except ValueError:
            fps = 12

        if not image_file or not image_file.filename:
            error = "Please upload an image to animate."
        elif (text_value is None and audio_file is None) or (text_value and audio_file):
            error = "Please provide either text or an audio file, but not both."
        else:
            temp_dir = Path(tempfile.mkdtemp(prefix="talking_photo_web_"))
            image_path = temp_dir / image_file.filename
            image_file.save(image_path)

            audio_path = None
            if audio_file:
                audio_path = temp_dir / audio_file.filename
                audio_file.save(audio_path)

            output_path = temp_dir / "talking_photo.mp4"

            try:
                video_path = create_talking_photo(
                    image_path,
                    output_path,
                    fps=fps,
                    mouth_color=mouth_color,
                    include_audio=include_audio,
                    text=text_value,
                    audio_path=audio_path,
                )
            except TalkingPhotoError as exc:
                error = str(exc)
                shutil.rmtree(temp_dir, ignore_errors=True)
            else:
                @after_this_request
                def cleanup(response):
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return response

                return send_file(video_path, as_attachment=True, download_name="talking_photo.mp4")

    return render_template_string(FORM_HTML, error=error)


if __name__ == "__main__":
    app.run(debug=True)
