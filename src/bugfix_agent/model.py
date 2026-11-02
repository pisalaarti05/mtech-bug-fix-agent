"""Optional Hugging Face adapter for a quantized causal language model."""
from __future__ import annotations
import time

class HuggingFaceModel:
    """Load a selected model in 4-bit NF4 mode for a CUDA Colab GPU."""
    def __init__(self, model_id: str, max_new_tokens: int = 700, max_input_tokens: int = 8192):
        if not model_id:
            raise ValueError("Choose a model ID after the Colab feasibility pilot.")
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        except ImportError as exc:
            raise RuntimeError("Model support is missing. Install with: pip install -e '.[model]'") from exc
        if not torch.cuda.is_available():
            raise RuntimeError("This model configuration needs a CUDA GPU. In Colab, select Runtime > Change runtime type > T4 GPU.")
        self.model_id = model_id
        self.max_new_tokens = max_new_tokens
        self.max_input_tokens = max_input_tokens
        self._torch = torch
        self._tokenizer = AutoTokenizer.from_pretrained(model_id)
        quantization = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
        load_started = time.perf_counter()
        self._model = AutoModelForCausalLM.from_pretrained(
            model_id,
            quantization_config=quantization,
            torch_dtype=torch.float16,
            device_map="auto",
        )
        self._model.eval()
        self.revision = getattr(self._model.config, "_commit_hash", None)
        self.load_seconds = round(time.perf_counter() - load_started, 3)
        self.last_usage: dict[str, int | float] = {}

    def generate(self, prompt: str) -> str:
        messages = [{"role": "user", "content": prompt}]
        formatted = self._tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        encoded = self._tokenizer(
            formatted,
            return_tensors="pt",
            truncation=True,
            max_length=self.max_input_tokens,
        ).to(self._model.device)
        input_tokens = int(encoded["input_ids"].shape[-1])
        started = time.perf_counter()
        with self._torch.inference_mode():
            output = self._model.generate(
                **encoded,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
                pad_token_id=self._tokenizer.eos_token_id,
            )
        elapsed = time.perf_counter() - started
        generated_tokens = output[0, input_tokens:]
        self.last_usage = {
            "input_tokens": input_tokens,
            "output_tokens": int(generated_tokens.shape[-1]),
            "generation_seconds": round(elapsed, 3),
        }
        return self._tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()
