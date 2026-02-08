#!/usr/bin/env python3
"""
Benchmark скрипт для streaming TTS.

Измеряет:
- Time-to-first-audio (TTFA)
- Total synthesis time
- Real-time factor (RTF)
- Chunk statistics

Запуск:
    python scripts/benchmark_streaming_tts.py [--text "Текст для синтеза"] [--iterations 5]
"""

import argparse
import statistics
import sys
import time
from pathlib import Path


# Добавляем корень проекта в path
sys.path.insert(0, str(Path(__file__).parent.parent))


def benchmark_streaming(
    text: str,
    voice_folder: str = "./Анна",
    iterations: int = 5,
    stream_chunk_size: int = 20,
    target_sample_rate: int = 8000,
):
    """Бенчмарк streaming синтеза."""
    from voice_clone_service import VoiceCloneService

    print(f"\n{'=' * 60}")
    print("XTTS v2 Streaming TTS Benchmark")
    print(f"{'=' * 60}")
    print(f"Text: {text[:50]}{'...' if len(text) > 50 else ''}")
    print(f"Voice: {voice_folder}")
    print(f"Stream chunk size: {stream_chunk_size}")
    print(f"Target sample rate: {target_sample_rate} Hz")
    print(f"Iterations: {iterations}")
    print(f"{'=' * 60}\n")

    # Инициализируем сервис
    print("Loading XTTS model...")
    load_start = time.time()
    service = VoiceCloneService(voice_folder=voice_folder)
    load_time = time.time() - load_start
    print(f"Model loaded in {load_time:.1f}s\n")

    # Прогрев
    print("Warmup run...")
    warmup_text = "Привет, это тестовое сообщение."
    for chunk, sr in service.synthesize_streaming(warmup_text, stream_chunk_size=30):
        pass
    print("Warmup complete.\n")

    # Результаты
    ttfa_times = []
    total_times = []
    chunk_counts = []
    audio_durations = []

    for i in range(iterations):
        print(f"Iteration {i + 1}/{iterations}...", end=" ", flush=True)

        first_chunk_time = None
        start_time = time.time()
        chunks = []
        total_samples = 0

        # Capture start_time for closure (fix B023)
        _start_time = start_time

        def on_first(_start=_start_time):
            nonlocal first_chunk_time
            first_chunk_time = (time.time() - _start) * 1000

        for chunk, sr in service.synthesize_streaming(
            text,
            stream_chunk_size=stream_chunk_size,
            target_sample_rate=target_sample_rate,
            on_first_chunk=on_first,
        ):
            chunks.append(chunk)
            total_samples += len(chunk)

        total_time = (time.time() - start_time) * 1000  # мс
        audio_duration = total_samples / target_sample_rate * 1000  # мс

        ttfa_times.append(first_chunk_time)
        total_times.append(total_time)
        chunk_counts.append(len(chunks))
        audio_durations.append(audio_duration)

        print(
            f"TTFA: {first_chunk_time:.0f}ms, Total: {total_time:.0f}ms, "
            f"Audio: {audio_duration:.0f}ms, Chunks: {len(chunks)}"
        )

    # Статистика
    print(f"\n{'=' * 60}")
    print("RESULTS")
    print(f"{'=' * 60}")

    def print_stats(name: str, values: list, unit: str = "ms"):
        mean = statistics.mean(values)
        stdev = statistics.stdev(values) if len(values) > 1 else 0
        p95 = sorted(values)[int(len(values) * 0.95)] if len(values) >= 5 else max(values)
        print(f"{name:25} mean={mean:7.1f}{unit}  std={stdev:5.1f}{unit}  p95={p95:7.1f}{unit}")

    print_stats("Time-to-first-audio:", ttfa_times)
    print_stats("Total synthesis time:", total_times)
    print_stats("Audio duration:", audio_durations)

    # RTF (Real-Time Factor)
    rtfs = [t / d for t, d in zip(total_times, audio_durations, strict=False)]
    rtf_mean = statistics.mean(rtfs)
    print(f"{'Real-Time Factor (RTF)':25} mean={rtf_mean:7.2f}x  (lower is better, <1 = real-time)")

    print(f"{'Chunks per synthesis:':25} mean={statistics.mean(chunk_counts):7.1f}")

    # Оценка для телефонии
    print(f"\n{'=' * 60}")
    print("TELEPHONY ASSESSMENT")
    print(f"{'=' * 60}")

    ttfa_mean = statistics.mean(ttfa_times)
    if ttfa_mean < 500:
        print(f"✅ TTFA {ttfa_mean:.0f}ms - EXCELLENT for live telephony")
    elif ttfa_mean < 1000:
        print(f"⚠️  TTFA {ttfa_mean:.0f}ms - ACCEPTABLE, may feel slightly delayed")
    else:
        print(f"❌ TTFA {ttfa_mean:.0f}ms - TOO SLOW for live conversation")

    if rtf_mean < 0.5:
        print(f"✅ RTF {rtf_mean:.2f}x - EXCELLENT, synthesizes 2x faster than real-time")
    elif rtf_mean < 1.0:
        print(f"✅ RTF {rtf_mean:.2f}x - GOOD, can keep up with real-time playback")
    else:
        print(f"❌ RTF {rtf_mean:.2f}x - TOO SLOW, will buffer/lag during playback")

    return {
        "ttfa_mean": ttfa_mean,
        "ttfa_p95": sorted(ttfa_times)[int(len(ttfa_times) * 0.95)]
        if len(ttfa_times) >= 5
        else max(ttfa_times),
        "total_mean": statistics.mean(total_times),
        "rtf_mean": rtf_mean,
    }


def benchmark_batch(
    text: str,
    voice_folder: str = "./Анна",
    iterations: int = 5,
):
    """Бенчмарк batch синтеза для сравнения."""
    from voice_clone_service import VoiceCloneService

    print(f"\n{'=' * 60}")
    print("XTTS v2 Batch TTS Benchmark (for comparison)")
    print(f"{'=' * 60}")

    service = VoiceCloneService(voice_folder=voice_folder)

    # Прогрев
    service.synthesize("Тест.", language="ru")

    times = []
    for i in range(iterations):
        print(f"Iteration {i + 1}/{iterations}...", end=" ", flush=True)
        start = time.time()
        audio, sr = service.synthesize(text, language="ru")
        elapsed = (time.time() - start) * 1000
        audio_duration = len(audio) / sr * 1000
        times.append(elapsed)
        print(f"Time: {elapsed:.0f}ms, Audio: {audio_duration:.0f}ms")

    print(f"\nBatch synthesis mean: {statistics.mean(times):.0f}ms")
    return statistics.mean(times)


def main():
    parser = argparse.ArgumentParser(description="Benchmark streaming TTS")
    parser.add_argument(
        "--text",
        default="Здравствуйте! Я ваш виртуальный секретарь. Чем могу помочь?",
        help="Text to synthesize",
    )
    parser.add_argument("--voice", default="./Анна", help="Voice folder path")
    parser.add_argument("--iterations", type=int, default=5, help="Number of iterations")
    parser.add_argument("--chunk-size", type=int, default=20, help="XTTS stream chunk size")
    parser.add_argument("--sample-rate", type=int, default=8000, help="Target sample rate")
    parser.add_argument("--compare-batch", action="store_true", help="Also benchmark batch mode")

    args = parser.parse_args()

    # Streaming benchmark
    streaming_results = benchmark_streaming(
        text=args.text,
        voice_folder=args.voice,
        iterations=args.iterations,
        stream_chunk_size=args.chunk_size,
        target_sample_rate=args.sample_rate,
    )

    # Optional batch comparison
    if args.compare_batch:
        batch_mean = benchmark_batch(
            text=args.text,
            voice_folder=args.voice,
            iterations=args.iterations,
        )
        print(f"\n{'=' * 60}")
        print("COMPARISON")
        print(f"{'=' * 60}")
        print(f"Streaming TTFA: {streaming_results['ttfa_mean']:.0f}ms")
        print(f"Batch total:    {batch_mean:.0f}ms")
        print(
            f"Improvement:    {batch_mean / streaming_results['ttfa_mean']:.1f}x faster first audio"
        )


if __name__ == "__main__":
    main()
