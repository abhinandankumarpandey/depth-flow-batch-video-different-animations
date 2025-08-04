# Settings (uncomment profile)
# Minimal distortion
# ISOMETRIC = 0.8
# HEIGHT = 0.1

# Balanced
#ISOMETRIC = 0.6
#HEIGHT = 0.2

# More 3D effect
# ISOMETRIC = 0.4
# HEIGHT = 0.3

import os
from pathlib import Path
from threading import Thread
import random
from depthflow.scene import DepthScene, DepthState
from depthflow.animation import Animation, Target
from broken.externals.depthmap import DepthAnythingV2
from broken.externals.upscaler import NoUpscaler

# Hardcoded folders
INPUT_FOLDER = Path("C:/Users/abhin/OneDrive/Pictures/try-batch")
OUTPUT_FOLDER = Path("C:/Users/abhin/OneDrive/Pictures/try-batch/output")
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

# Settings
ISOMETRIC = 0.6
HEIGHT = 0.2
STEADY = 0.1
FPS = 24
TIME = 6
LOOP = 1
REVERSE = False
INTENSITY = 0.5

# Effects (restored full list for random variety)
USE_RANDOM = [ "orbital",  "zoom", "horizontal" ]  #"Dolly" "circle","vertical"   add these to get random on videos 


class BatchManager:
    def __init__(self):
        self.estimator = DepthAnythingV2()  # Shared estimator
        self.estimator.load_torch()
        self.estimator.load_model()
        self.upscaler = NoUpscaler()
        self.threads = []
        self.concurrency = 1  # Limit to 1 for low VRAM

    def process(self, image, effect, output):
        thread = Thread(target=self._worker, args=(image, effect, output), daemon=True)
        self.threads.append(thread)
        thread.start()

    def _worker(self, image, effect, output):
        scene = DepthScene(backend="headless")
        scene.config.estimator = self.estimator
        scene.set_upscaler(self.upscaler)
        scene.input(image=image)
        
        scene.config.animation.clear()
        scene.state = DepthState()
        
        scene.config.animation.add(Animation.Set(target=Target.Isometric, value=ISOMETRIC))
        scene.config.animation.add(Animation.Set(target=Target.Height, value=HEIGHT))
        scene.config.animation.add(Animation.Set(target=Target.Steady, value=STEADY))
        
        preset_kwargs = {"intensity": INTENSITY, "reverse": REVERSE, "loop": LOOP}
        
        if effect == "Dolly":
            scene.config.animation.add(Animation.Dolly(**preset_kwargs))
        elif effect == "orbital":
            scene.config.animation.add(Animation.Orbital(**preset_kwargs))
        elif effect == "circle":
            scene.config.animation.add(Animation.Circle(**preset_kwargs))
        elif effect == "zoom":
            scene.config.animation.add(Animation.Zoom(**preset_kwargs))
        elif effect == "horizontal":
            scene.config.animation.add(Animation.Horizontal(**preset_kwargs))
        elif effect == "vertical":
            scene.config.animation.add(Animation.Vertical(**preset_kwargs))
        
        print(f"Processing {image} with {effect}")
        scene.main(
            output=output,
            height=1080,  # Cap height to avoid VRAM issues
            ssaa=1,
            fps=FPS,
            time=TIME,
            loops=LOOP,
            turbo=True
        )

    def join(self):
        for thread in self.threads:
            thread.join()

manager = BatchManager()

for file in INPUT_FOLDER.glob("*"):
    if file.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
        effect = random.choice(USE_RANDOM)
        output = OUTPUT_FOLDER / f"{file.stem}_{effect}.mp4"
        manager.process(file, effect, output)

manager.join()
