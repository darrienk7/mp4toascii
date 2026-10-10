import cv2
import numpy as np
import tomllib
import subprocess
import os
import sys
import time
import questionary
from pathlib import Path
from ffpyplayer.player import MediaPlayer

with open("config.toml", mode="rb") as f:
    config = tomllib.load(f)

VIDEO_DIR = Path(__file__).resolve().parent / "Source Videos"
vids = sorted(p for p in VIDEO_DIR.iterdir() if p.is_file() and p.suffix.lower() in [".mp4", ".avi", ".mov", ".mkv", ".avi", ".webm"])
if not vids:
    raise ValueError("No video paths provided in the configuration.")

repeat = False
while True:
    if not repeat:
        if len(vids) > 1:
            vid = questionary.select("Select a video to play:", choices=[
                questionary.Choice(
                    title = p.stem[:30], value = str(p)) for p in vids]).ask()
        else:
            vid = str(vids[0])

        use_color = questionary.select(
            "Playback",
            choices=["Color", "Grayscale"]
        ).ask()

        use_color = True if use_color == "Color" else False


    ascii_chars = config["ascii_scale"]
    cap = cv2.VideoCapture(vid)
    sound_player = MediaPlayer(vid)

    if not cap.isOpened():
        raise RuntimeError(f"Failed to open {vid}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    subprocess.run(["cls"] if os.name == "nt" else ["clear"], shell=True)
    try:
        while True:
            audio_pts = sound_player.get_pts()
            video_pts = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
            start_time = time.time()
            ret, frame = cap.read()
            if not ret:
                break
            
            if video_pts < audio_pts:
                continue
            while video_pts > audio_pts + 0.01:
                time.sleep(0.005)
                audio_pts = sound_player.get_pts()

            terminal_dimensions = os.get_terminal_size()
            t_width = terminal_dimensions.columns
            t_height = terminal_dimensions.lines
            aspect_ratio = width / height

            target_width = min(t_width, int(t_height * aspect_ratio * 2))
            target_height = max(1, int(target_width / aspect_ratio / 2))

            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if use_color:
                color_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            gray_fit = cv2.resize(gray_frame, (target_width, target_height))
            if use_color:
                color_fit = cv2.resize(color_frame, (target_width, target_height))

            left_padding = max(0, (t_width - target_width) // 2)
            top_padding = max(0, (t_height - target_height) // 2)
            pixels = (gray_fit / 255 * (len(ascii_chars) - 1)).astype(np.int32)
            pixels = (gray_fit / 255 * (len(ascii_chars) - 1)).astype(np.int32)

            if use_color:
                ascii_frame = "\n".join(" " * left_padding + "".join(f"\x1b[38;2;{r};{g};{b}m{ascii_chars[p]}"
                        for p, (r, g, b) in zip(gray_row, color_row)) for gray_row, color_row in zip(pixels, color_fit))
            else:
                ascii_frame = "\n".join(
                    " " * left_padding + "".join(ascii_chars[p] for p in row)
                    for row in pixels)

            ascii_frame = "\n" * top_padding + ascii_frame + "\x1b[0m"
            sys.stdout.write("\x1b[H" + ascii_frame)
            sys.stdout.flush()
            
            audio_frame, val = sound_player.get_frame()
            if val == "eof":
                break
            
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        sound_player.close_player()
        subprocess.run(["cls"] if os.name == "nt" else ["clear"], shell=True)
    
    a = len(vids) > 1
    play_again = questionary.select(
        "Which option?",
        choices = ["Repeat playback", "Choose new song", "Exit"] if a else ["Repeat playback", "Exit"]
    ).ask()
    if play_again == "Exit":
        break
    elif play_again == "Repeat playback":
        repeat = True
    elif play_again == "Choose new song":
        repeat = False

print("Playback stopped.")