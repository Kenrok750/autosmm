import os
import json
from datetime import datetime
import re

from agent.config import OUTPUT_DIR

class RunStorage:
    def __init__(self, base_dir=OUTPUT_DIR):
        self.base_dir = base_dir
        self.run_dir = None
        self.state_file = None
        self.state = {
            "status": "initialized",
            "iterations": [],
            "best_score": 0.0,
            "best_video_path": None,
        }

    def init_run(self, input_url: str):
        os.makedirs(self.base_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # simple safe slug
        slug = re.sub(r'[^a-zA-Z0-9]', '_', input_url)[:20]

        self.run_dir = os.path.join(self.base_dir, f"{timestamp}_{slug}")
        os.makedirs(self.run_dir, exist_ok=True)

        # Create subdirectories
        for sub in ["prompts", "videos", "evaluations", "screenshots", "traces"]:
            os.makedirs(os.path.join(self.run_dir, sub), exist_ok=True)

        self.state_file = os.path.join(self.run_dir, "run_state.json")

        # Save initial input
        input_file = os.path.join(self.run_dir, "input.json")
        with open(input_file, "w", encoding="utf-8") as f:
            json.dump({"original_url": input_url, "timestamp": timestamp}, f, indent=4)

        self.state["status"] = "running"
        self._save_state()

    def _save_state(self):
        if self.state_file:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=4)

    def record_iteration(self, iteration: int, prompt: str, video_path: str, eval_json: dict):
        iteration_data = {
            "iteration": iteration,
            "prompt": prompt,
            "video_path": video_path,
            "evaluation": eval_json
        }
        self.state["iterations"].append(iteration_data)

        if eval_json and "score" in eval_json:
            try:
                score = float(eval_json["score"])
                if score > self.state["best_score"]:
                    self.state["best_score"] = score
                    self.state["best_video_path"] = video_path
            except ValueError:
                pass

        self._save_state()

    def save_prompt(self, filename: str, content: str):
        path = os.path.join(self.run_dir, "prompts", filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def save_evaluation(self, filename: str, content: dict):
        path = os.path.join(self.run_dir, "evaluations", filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(content, f, indent=4, ensure_ascii=False)
        return path

    def get_video_path(self, iteration: int) -> str:
        return os.path.join(self.run_dir, "videos", f"iter_{iteration:02d}.mp4")

    def get_screenshot_path(self, filename: str) -> str:
        return os.path.join(self.run_dir, "screenshots", filename)

    def update_status(self, status: str):
        self.state["status"] = status
        self._save_state()
