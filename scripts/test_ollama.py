"""Run: python scripts/test_ollama.py"""
import json, math, subprocess, time
from pathlib import Path
import psutil, requests

URL = "http://localhost:11434"
CHAT_MODEL = "llama3.2:3b"
EMBED_MODEL = "nomic-embed-text"

def ollama_rss_gb():
    total = 0
    for p in psutil.process_iter(["name", "memory_info"]):
        if (p.info["name"] or "").lower().startswith("ollama") and p.info["memory_info"]:
            total += p.info["memory_info"].rss
    return total / 1e9

def embed(texts, prefix="search_document: "):
    r = requests.post(f"{URL}/api/embed",
                      json={"model": EMBED_MODEL, "input": [prefix + t for t in texts]}, timeout=120)
    r.raise_for_status()
    return r.json()["embeddings"]

def cos(a, b):
    return sum(x * y for x, y in zip(a, b)) / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))

def main():
    print("Ollama version:", requests.get(f"{URL}/api/version", timeout=10).json())
    vm = psutil.virtual_memory()
    print(f"System RAM: {vm.total/1e9:.1f} GB total, {vm.available/1e9:.1f} GB available")
    print("Installed models:", [m["name"] for m in requests.get(f"{URL}/api/tags", timeout=10).json()["models"]])

    # ---- chat model ----
    t0 = time.perf_counter()
    r = requests.post(f"{URL}/api/generate", timeout=300, json={
        "model": CHAT_MODEL, "stream": False, "options": {"temperature": 0},
        "prompt": "In two sentences, explain what a power supply unit does."}).json()
    wall = time.perf_counter() - t0
    tps = r["eval_count"] / (r["eval_duration"] / 1e9)
    print("\n--- CHAT MODEL ---\n", r["response"].strip())
    print(f"Wall time: {wall:.2f}s | load: {r['load_duration']/1e9:.2f}s | "
          f"prompt tokens: {r['prompt_eval_count']} | generated tokens: {r['eval_count']} | speed: {tps:.1f} tokens/s")
    mem = ollama_rss_gb()
    print(f"Ollama process RAM (RSS): {mem:.2f} GB  (GPU VRAM is not included)")
    try:
        print(subprocess.run(["ollama", "ps"], capture_output=True, text=True).stdout)
    except FileNotFoundError:
        print("'ollama' not on PATH - skipped `ollama ps`")

    # ---- embedding model ----
    t0 = time.perf_counter()
    vecs = embed(["maximum operating temperature", "maximum heat limit", "banana bread recipe"])
    print("--- EMBEDDING MODEL ---")
    print(f"Dimensions: {len(vecs[0])} | time for 3 texts: {time.perf_counter()-t0:.2f}s")
    print(f"similarity('operating temperature','heat limit') = {cos(vecs[0], vecs[1]):.3f}")
    print(f"similarity('operating temperature','banana bread') = {cos(vecs[0], vecs[2]):.3f}")

    Path("data").mkdir(exist_ok=True)
    Path("data/day1_benchmark.json").write_text(json.dumps({
        "chat_model": CHAT_MODEL, "tokens_per_second": round(tps, 2), "wall_seconds": round(wall, 2),
        "ollama_ram_gb": round(mem, 2), "system_ram_gb": round(vm.total / 1e9, 1),
        "embedding_dims": len(vecs[0])}, indent=2))
    print("Saved data/day1_benchmark.json")

if __name__ == "__main__":
    main()