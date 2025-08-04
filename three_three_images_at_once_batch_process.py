import os
import random
from pathlib import Path
from threading import Thread, Semaphore

from depthflow.scene import DepthScene, DepthState
from depthflow.animation import Animation, Target
from broken.externals.depthmap import DepthAnythingV2
from broken.externals.upscaler import NoUpscaler

# ───────────────────────────────────────────────────────────────────────────────
# Configuration: adjust these as needed
INPUT_FOLDER  = Path("C:/Users/abhin/OneDrive/Pictures/try-batch")
OUTPUT_FOLDER = Path("C:/Users/abhin/OneDrive/Pictures/try-batch/output")
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)  # create output folder if missing

# Depth / animation parameters
ISOMETRIC = 0.6   # camera isometric tilt
HEIGHT    = 0.2   # how tall the “camera” sits above the scene
STEADY    = 0.1   # camera steadiness (lower = more movement)
FPS       = 24    # frames per second
TIME      = 6     # length of video in seconds
LOOPS     = 1     # number of animation loops
REVERSE   = False # play animation in reverse?
INTENSITY = 0.5   # strength of chosen effect

# Which effects to pick at random per file
USE_RANDOM = [
    "orbital", "zoom", "horizontal",
   "vertical"
]
# ─────────────────────────────────────────────────────────────────────────────── "Dolly", "circle", 

class BatchManager:
    """Manages a pool of threads to process media in small batches."""
    def __init__(self, concurrency: int = 3):
        # Load depth estimator once for all threads
        self.estimator = DepthAnythingV2()
        self.estimator.load_torch()
        self.estimator.load_model()

        # No-op upscaler
        self.upscaler = NoUpscaler()

        # Semaphore limits active threads
        self.concurrency = concurrency
        self.semaphore   = Semaphore(concurrency)
        self.threads     = []

    def _worker(self, image: Path, effect: str, output: Path):
        """Set up scene, select effect, render, then release slot."""
        try:
            # Initialize scene
            scene = DepthScene(backend="headless")
            scene.config.estimator = self.estimator
            scene.set_upscaler(self.upscaler)
            scene.input(image=image)

            # Reset animations
            scene.config.animation.clear()
            scene.state = DepthState()

            # Base camera settings
            scene.config.animation.add(
                Animation.Set(target=Target.Isometric, value=ISOMETRIC)
            )
            scene.config.animation.add(
                Animation.Set(target=Target.Height, value=HEIGHT)
            )
            scene.config.animation.add(
                Animation.Set(target=Target.Steady, value=STEADY)
            )

            # Choose the effect
            preset = {
                "intensity": INTENSITY,
                "reverse":   REVERSE,
                "loop":      LOOPS
            }
            if effect == "orbital":
                scene.config.animation.add(Animation.Orbital(**preset))
            elif effect == "zoom":
                scene.config.animation.add(Animation.Zoom(**preset))
            elif effect == "horizontal":
                scene.config.animation.add(Animation.Horizontal(**preset))
            elif effect == "Dolly":
                scene.config.animation.add(Animation.Dolly(**preset))
            elif effect == "circle":
                scene.config.animation.add(Animation.Circle(**preset))
            elif effect == "vertical":
                scene.config.animation.add(Animation.Vertical(**preset))

            # Run and save
            print(f"▶️ Processing {image.name} with {effect}")
            scene.main(
                output=output,
                height=1080,  # cap height to save VRAM
                ssaa=1,
                fps=FPS,
                time=TIME,
                loops=LOOPS,
                turbo=True
            )
            print(f"✅ Finished {image.name}")

        except Exception as exc:
            print(f"❌ Error processing {image.name}: {exc}")

        finally:
            # Free up slot for next
            self.semaphore.release()

    def _enqueue(self, image: Path, effect: str, output: Path):
        """
        Acquire a semaphore slot (blocks if full),
        then start worker thread.
        """
        self.semaphore.acquire()
        t = Thread(target=self._worker, args=(image, effect, output), daemon=True)
        self.threads.append(t)
        t.start()

    def join(self):
        """Wait for all threads to finish."""
        for t in self.threads:
            t.join()

if __name__ == "__main__":
    # Set concurrency (2 or 3 as your VRAM allows)
    manager = BatchManager(concurrency=3)

    # Enqueue all images
    for img in INPUT_FOLDER.glob("*"):
        if img.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
            effect = random.choice(USE_RANDOM)
            out = OUTPUT_FOLDER / f"{img.stem}_{effect}.mp4"
            manager._enqueue(img, effect, out)

    # Block until done
    manager.join()
