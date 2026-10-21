
import multiprocessing
import signal
import time


def _audio_worker(connection, filename):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    player = None
    try:
        from ffpyplayer.player import MediaPlayer

        player = MediaPlayer(filename, ff_opts={"vn": True})
        deadline = time.monotonic() + 8
        while player.get_metadata().get("duration") is None:
            if time.monotonic() >= deadline:
                raise RuntimeError(f"Timed out opening audio for {filename}")
            time.sleep(0.005)
        connection.send(("ready", None))
        while True:
            command = connection.recv()
            if command == "close":
                break
            if command == "pts":
                connection.send(("ok", player.get_pts()))
            elif command == "frame":
                _, status = player.get_frame()
                connection.send(("ok", status))
    except EOFError:
        pass
    except Exception as exc:
        connection.send(("error", str(exc)))
    finally:
        if player is not None:
            player.close_player()
        connection.close()


class AudioPlayer:
    def __init__(self, filename):
        context = multiprocessing.get_context("spawn")
        self.connection, child = context.Pipe()
        self.process = context.Process(target=_audio_worker, args=(child, filename))
        self.process.start()
        child.close()
        try:
            self._receive()
        except BaseException:
            self.close_player()
            raise

    def _receive(self):
        if not self.connection.poll(10):
            raise RuntimeError("Audio player stopped responding")
        try:
            status, value = self.connection.recv()
        except (EOFError, OSError) as exc:
            raise RuntimeError("Audio player exited unexpectedly") from exc
        if status == "error":
            raise RuntimeError(f"Audio playback failed: {value}")
        return value

    def _request(self, command):
        try:
            self.connection.send(command)
        except (EOFError, OSError) as exc:
            raise RuntimeError("Audio player exited unexpectedly") from exc
        return self._receive()

    def get_pts(self):
        return self._request("pts")

    def get_frame(self):
        return None, self._request("frame")

    def close_player(self):
        try:
            if self.process.is_alive():
                self.connection.send("close")
        except (EOFError, OSError):
            pass
        finally:
            self.connection.close()
            self.process.join(timeout=2)
            if self.process.is_alive():
                self.process.terminate()
                self.process.join(timeout=2)
                if self.process.is_alive():
                    self.process.kill()
                    self.process.join(timeout=2)
