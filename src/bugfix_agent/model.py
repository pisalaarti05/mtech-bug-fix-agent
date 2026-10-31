"""Optional Hugging Face causal language model adapter."""
from __future__ import annotations

class HuggingFaceModel:
    """Load a user-selected model; heavy packages are needed only for inference."""
    def __init__(self, model_id: str, max_new_tokens: int = 700):
        if not model_id:
            raise ValueError("Choose a model ID after the Colab feasibility pilot.")
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError("Model support is missing. Install with: pip install -e '.[model]'") from exc
        self.model_id = model_id
        self.max_new_tokens = max_new_tokens
        self._torch = torch
        self._tokenizer = AutoTokenizer.from_pretrained(model_id)
        self._model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype="auto", device_map="auto")
    def generate(self, prompt: str) -> str:
        encoded = self._tokenizer(prompt, return_tensors="pt").to(self._model.device)
        with self._torch.inference_mode():
            output = self._model.generate(**encoded, max_new_tokens=self.max_new_tokens, do_sample=False, pad_token_id=self._tokenizer.eos_token_id)
        new_tokens = output[0, encoded["input_ids"].shape[1]:]
        return self._tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
