# app/services/audio_pipeline.py
"""
Telephony Audio Pipeline - обработка аудио для GSM телефонии.

Конвертация XTTS аудио (24kHz float32) в формат для SIM7600G-H GSM модема.
"""

from typing import Generator, Optional

import numpy as np


class TelephonyAudioPipeline:
    """
    Pipeline для обработки аудио в телефонных системах.

    GSM Audio спецификации:
    - Sample rate: 8000 Hz
    - Bit depth: 16-bit signed PCM
    - Channels: 1 (mono)
    - Frame size: 20ms (160 samples)

    Оптимизирован для минимальной латентности.
    """

    # GSM константы
    GSM_SAMPLE_RATE = 8000
    GSM_FRAME_SAMPLES = 160  # 20ms @ 8kHz
    GSM_FRAME_BYTES = GSM_FRAME_SAMPLES * 2  # 16-bit = 2 bytes per sample

    def __init__(
        self,
        source_sample_rate: int = 24000,
        target_sample_rate: int = 8000,
        frame_duration_ms: int = 20,
    ):
        """
        Args:
            source_sample_rate: Частота XTTS (по умолчанию 24kHz)
            target_sample_rate: Целевая частота (по умолчанию 8kHz для GSM)
            frame_duration_ms: Длительность фрейма в мс (20ms для GSM)
        """
        self.source_rate = source_sample_rate
        self.target_rate = target_sample_rate
        self.frame_samples = int(target_sample_rate * frame_duration_ms / 1000)

        # Буфер для накопления неполных фреймов
        self._buffer = np.array([], dtype=np.float32)

    def resample(self, audio: np.ndarray, source_rate: int) -> np.ndarray:
        """
        Resample аудио к целевой частоте.

        Args:
            audio: float32 аудио массив
            source_rate: исходная частота

        Returns:
            Resampled float32 массив
        """
        if source_rate == self.target_rate:
            return audio

        # Используем scipy для качественного resampling
        try:
            from scipy import signal

            # Вычисляем соотношение
            ratio = self.target_rate / source_rate
            target_len = int(len(audio) * ratio)

            # Resample
            resampled = signal.resample(audio, target_len)
            return resampled.astype(np.float32)
        except ImportError:
            # Fallback на линейную интерполяцию
            ratio = self.target_rate / source_rate
            target_len = int(len(audio) * ratio)
            indices = np.linspace(0, len(audio) - 1, target_len)
            return np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)

    def float_to_pcm16(self, audio: np.ndarray) -> bytes:
        """
        Конвертация float32 [-1, 1] в PCM16 bytes.

        Args:
            audio: float32 массив

        Returns:
            bytes в формате signed 16-bit little-endian
        """
        # Clip to [-1, 1] и scale to int16 range
        audio_clipped = np.clip(audio, -1.0, 1.0)
        audio_int16 = (audio_clipped * 32767).astype(np.int16)
        return audio_int16.tobytes()

    def pcm16_to_float(self, data: bytes) -> np.ndarray:
        """
        Конвертация PCM16 bytes в float32.

        Args:
            data: bytes в формате signed 16-bit little-endian

        Returns:
            float32 массив [-1, 1]
        """
        audio_int16 = np.frombuffer(data, dtype=np.int16)
        return (audio_int16 / 32767.0).astype(np.float32)

    def process_chunk(
        self,
        audio: np.ndarray,
        source_rate: int,
        output_format: str = "pcm16",
    ) -> bytes:
        """
        Обработка одного аудио чанка.

        Args:
            audio: float32 аудио
            source_rate: исходная частота
            output_format: "pcm16" или "float32"

        Returns:
            bytes готовые для отправки
        """
        # Resample если нужно
        if source_rate != self.target_rate:
            audio = self.resample(audio, source_rate)

        # Конвертируем в нужный формат
        if output_format == "pcm16":
            return self.float_to_pcm16(audio)
        else:
            return audio.tobytes()

    def generate_gsm_frames(
        self,
        audio_chunks: Generator[tuple[np.ndarray, int], None, None],
        output_format: str = "pcm16",
    ) -> Generator[bytes, None, None]:
        """
        Генератор GSM-совместимых фреймов из потока XTTS чанков.

        Буферизует аудио и выдаёт строго 20ms фреймы (160 samples @ 8kHz).
        Это критично для GSM модема.

        Args:
            audio_chunks: генератор (audio, sample_rate) от XTTS
            output_format: "pcm16" или "float32"

        Yields:
            bytes фреймы по 320 байт (160 samples * 2 bytes)
        """
        for audio_chunk, source_rate in audio_chunks:
            # Resample к 8kHz
            if source_rate != self.target_rate:
                audio_chunk = self.resample(audio_chunk, source_rate)

            # Добавляем в буфер
            self._buffer = np.concatenate([self._buffer, audio_chunk])

            # Выдаём полные фреймы
            while len(self._buffer) >= self.frame_samples:
                frame = self._buffer[: self.frame_samples]
                self._buffer = self._buffer[self.frame_samples :]

                if output_format == "pcm16":
                    yield self.float_to_pcm16(frame)
                else:
                    yield frame.tobytes()

        # Выдаём последний неполный фрейм с padding
        if len(self._buffer) > 0:
            # Pad до полного фрейма
            padding = np.zeros(self.frame_samples - len(self._buffer), dtype=np.float32)
            frame = np.concatenate([self._buffer, padding])
            self._buffer = np.array([], dtype=np.float32)

            if output_format == "pcm16":
                yield self.float_to_pcm16(frame)
            else:
                yield frame.tobytes()

    def encode_g711_alaw(self, audio: np.ndarray) -> bytes:
        """
        Кодирование в G.711 A-law (стандарт европейской телефонии).

        Сжатие: 16-bit → 8-bit с логарифмической компандацией.
        Используется для PCM линий в PSTN.

        Args:
            audio: float32 массив

        Returns:
            bytes в формате A-law (1 byte per sample)
        """
        # Сначала в int16
        audio_int16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)

        # A-law lookup table
        def alaw_encode_sample(sample: int) -> int:
            """Encode single sample to A-law"""
            sign = 0x80 if sample >= 0 else 0x00
            sample = min(abs(sample), 32635)

            if sample < 256:
                encoded = sample >> 4
            else:
                # Найти сегмент
                segment = 1
                tmp = sample >> 8
                while tmp > 0:
                    segment += 1
                    tmp >>= 1

                encoded = (segment << 4) | ((sample >> (segment + 3)) & 0x0F)

            return (encoded | sign) ^ 0x55

        # Кодируем все samples
        encoded = bytes([alaw_encode_sample(s) for s in audio_int16])
        return encoded

    def reset(self):
        """Сброс внутреннего буфера."""
        self._buffer = np.array([], dtype=np.float32)


class StreamingAudioBuffer:
    """
    Кольцевой буфер для streaming аудио с минимальной латентностью.

    Используется для сглаживания потока между TTS и телефонией.
    """

    def __init__(self, max_duration_ms: int = 500, sample_rate: int = 8000):
        """
        Args:
            max_duration_ms: максимальная длительность буфера в мс
            sample_rate: частота дискретизации
        """
        self.max_samples = int(sample_rate * max_duration_ms / 1000)
        self.sample_rate = sample_rate
        self._buffer = np.zeros(self.max_samples, dtype=np.float32)
        self._write_pos = 0
        self._read_pos = 0
        self._available = 0

    def write(self, audio: np.ndarray) -> int:
        """
        Записать аудио в буфер.

        Args:
            audio: float32 массив

        Returns:
            Количество записанных samples
        """
        samples_to_write = min(len(audio), self.max_samples - self._available)

        if samples_to_write <= 0:
            return 0

        # Записываем с учётом кольцевого буфера
        end_pos = (self._write_pos + samples_to_write) % self.max_samples
        if end_pos > self._write_pos:
            self._buffer[self._write_pos : end_pos] = audio[:samples_to_write]
        else:
            first_part = self.max_samples - self._write_pos
            self._buffer[self._write_pos :] = audio[:first_part]
            self._buffer[:end_pos] = audio[first_part:samples_to_write]

        self._write_pos = end_pos
        self._available += samples_to_write
        return samples_to_write

    def read(self, num_samples: int) -> Optional[np.ndarray]:
        """
        Прочитать аудио из буфера.

        Args:
            num_samples: количество samples для чтения

        Returns:
            float32 массив или None если недостаточно данных
        """
        if self._available < num_samples:
            return None

        result = np.zeros(num_samples, dtype=np.float32)
        end_pos = (self._read_pos + num_samples) % self.max_samples

        if end_pos > self._read_pos:
            result[:] = self._buffer[self._read_pos : end_pos]
        else:
            first_part = self.max_samples - self._read_pos
            result[:first_part] = self._buffer[self._read_pos :]
            result[first_part:] = self._buffer[:end_pos]

        self._read_pos = end_pos
        self._available -= num_samples
        return result

    @property
    def available_samples(self) -> int:
        """Количество доступных для чтения samples."""
        return self._available

    @property
    def available_ms(self) -> float:
        """Количество доступного аудио в мс."""
        return self._available / self.sample_rate * 1000

    def clear(self):
        """Очистить буфер."""
        self._write_pos = 0
        self._read_pos = 0
        self._available = 0
