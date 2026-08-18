import json
import time
from pathlib import Path

import ollama


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
METRICS_AND_ERRORS_DIR = BASE_DIR / "metrics_and_errors"

MODEL = "qwen3.5:9b"

INPUT_FILE = DATA_DIR / "tools_preprocessed.jsonl"
OUTPUT_FILE = DATA_DIR / "tools_enriched.jsonl"
METRICS_FILE = METRICS_AND_ERRORS_DIR / "tools_enrichment_metrics.jsonl"
ERROR_FILE = METRICS_AND_ERRORS_DIR / "tools_enrichment_errors.jsonl"
PROMPT_FILE = BASE_DIR / "prompt.md"

OLLAMA_HOST = "http://localhost:4378"


def load_prompt() -> str:
    return PROMPT_FILE.read_text(encoding="utf-8")


def build_prompt(tool: dict) -> str:
    return f"""
Enrich the following Galaxy tool according to the system instructions.

TOOL:
{json.dumps(tool, indent=2, ensure_ascii=False)}

Return only the required JSON object.
"""


def enrich_tool(
    client: ollama.Client,
    system_prompt: str,
    tool: dict,
) -> tuple[dict, dict]:
    request_started = time.perf_counter()

    response = client.chat(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": build_prompt(tool),
            },
        ],
        format="json",
        options={
            "temperature": 0,
        },
        think=False
    )

    request_elapsed_sec = time.perf_counter() - request_started

    content = response["message"]["content"]

    result = json.loads(content)

    if not isinstance(result, dict):
        raise ValueError("LLM response is not a JSON object")

    # Ollama durations are returned in nanoseconds.
    total_duration = response.get("total_duration", 0)
    load_duration = response.get("load_duration", 0)
    prompt_eval_duration = response.get("prompt_eval_duration", 0)
    eval_duration = response.get("eval_duration", 0)

    total_duration_sec = total_duration / 1e9
    load_duration_sec = load_duration / 1e9
    prompt_eval_duration_sec = prompt_eval_duration / 1e9
    eval_duration_sec = eval_duration / 1e9

    # Estimate the part that is actually spent on model compute.
    ollama_compute_sec = (
        load_duration_sec
        + prompt_eval_duration_sec
        + eval_duration_sec
    )
    extra_wait_sec = request_elapsed_sec - total_duration_sec

    print("=== Timing breakdown ===")
    print(f"Python wall time:      {request_elapsed_sec:.2f}s")
    print(f"Ollama total:          {total_duration_sec:.2f}s")
    print(f"Ollama compute:        {ollama_compute_sec:.2f}s")
    print(f"Unaccounted gap:       {extra_wait_sec:.2f}s")
    print("========================")

    prompt_eval_count = response.get("prompt_eval_count", 0)
    eval_count = response.get("eval_count", 0)

    metrics = {
        "request_wall_time_sec": request_elapsed_sec,
        "total_duration_sec": total_duration_sec,
        "load_duration_sec": load_duration_sec,
        "prompt_eval_duration_sec": prompt_eval_duration_sec,
        "eval_duration_sec": eval_duration_sec,
        "ollama_compute_sec": ollama_compute_sec,
        "extra_wait_sec": extra_wait_sec,

        "prompt_tokens": prompt_eval_count,
        "output_tokens": eval_count,

        "prompt_tokens_per_sec": (
            prompt_eval_count / prompt_eval_duration_sec
            if prompt_eval_duration_sec > 0
            else 0
        ),

        "output_tokens_per_sec": (
            eval_count / eval_duration_sec
            if eval_duration_sec > 0
            else 0
        ),
    }

    return result, metrics


def get_completed_ids() -> set[str]:
    completed = set()

    if not OUTPUT_FILE.exists():
        return completed

    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue

            try:
                tool = json.loads(line)

                if "tool_id" in tool:
                    completed.add(tool["tool_id"])

            except json.JSONDecodeError:
                continue

    return completed


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    METRICS_AND_ERRORS_DIR.mkdir(parents=True, exist_ok=True)

    system_prompt = load_prompt()

    client = ollama.Client(
        host=OLLAMA_HOST,
        timeout=20
    )

    completed_ids = get_completed_ids()

    print(f"Model: {MODEL}")
    print(f"Ollama: {OLLAMA_HOST}")
    print(f"Already completed: {len(completed_ids)}")
    print()

    processed = 0
    failed = 0
    metrics_history: list[dict] = []

    with (
        INPUT_FILE.open("r", encoding="utf-8") as infile,
        OUTPUT_FILE.open("a", encoding="utf-8") as outfile,
        ERROR_FILE.open("a", encoding="utf-8") as errorfile,
        METRICS_FILE.open("a", encoding="utf-8") as metricsfile,
    ):
        for line_number, line in enumerate(infile, start=1):

            if not line.strip():
                continue

            tool = None

            try:
                tool = json.loads(line)

                tool_id = tool.get("tool_id")

                if tool_id in completed_ids:
                    continue

                enriched, metrics = enrich_tool(
                    client,
                    system_prompt,
                    tool,
                )

                output = {
                    **tool,
                    "enrichment": enriched,
                }

                outfile.write(
                    json.dumps(
                        output,
                        ensure_ascii=False,
                    ) + "\n"
                )
                outfile.flush()

                metrics_record = {
                    "tool_id": tool_id,
                    "line": line_number,
                    **metrics,
                }
                metrics_history.append(metrics_record)
                metricsfile.write(
                    json.dumps(
                        metrics_record,
                        ensure_ascii=False,
                    ) + "\n"
                )
                metricsfile.flush()

                completed_ids.add(tool_id)
                processed += 1

                print(
                    f"[{processed}] line={line_number}"
                )
                print(f"  id: {tool_id}")
                print(
                    f"  python wall: "
                    f"{metrics['request_wall_time_sec']:.2f}s"
                )
                print(
                    f"  ollama total: "
                    f"{metrics['total_duration_sec']:.2f}s"
                )
                print(
                    f"  ollama compute: "
                    f"{metrics['ollama_compute_sec']:.2f}s"
                )
                print(
                    f"  unaccounted gap: "
                    f"{metrics['extra_wait_sec']:.2f}s"
                )
                print(
                    f"  prompt: "
                    f"{metrics['prompt_tokens']} tokens "
                    f"@ "
                    f"{metrics['prompt_tokens_per_sec']:.2f} tok/s"
                )
                print(
                    f"  output: "
                    f"{metrics['output_tokens']} tokens "
                    f"@ "
                    f"{metrics['output_tokens_per_sec']:.2f} tok/s"
                )
                print()

            except Exception as e:
                failed += 1

                error = {
                    "line": line_number,
                    "tool_id": (
                        tool.get("tool_id")
                        if isinstance(tool, dict)
                        else None
                    ),
                    "error": str(e),
                }

                errorfile.write(
                    json.dumps(
                        error,
                        ensure_ascii=False,
                    ) + "\n"
                )
                errorfile.flush()

                print(
                    f"[ERROR] line={line_number}: {e}"
                )

    if metrics_history:
        avg_total = sum(
            record["total_duration_sec"]
            for record in metrics_history
        ) / len(metrics_history)
        avg_prompt = sum(
            record["prompt_tokens_per_sec"]
            for record in metrics_history
        ) / len(metrics_history)
        avg_output = sum(
            record["output_tokens_per_sec"]
            for record in metrics_history
        ) / len(metrics_history)

        print("\nSummary")
        print(f"  avg total duration: {avg_total:.2f}s")
        print(f"  avg prompt throughput: {avg_prompt:.2f} tok/s")
        print(f"  avg output throughput: {avg_output:.2f} tok/s")

    print("\nFinished")
    print(f"Processed: {processed}")
    print(f"Failed: {failed}")


if __name__ == "__main__":
    main()