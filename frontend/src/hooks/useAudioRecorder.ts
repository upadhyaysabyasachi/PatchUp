"use client";
import { useState, useRef, useCallback } from "react";

const MAX_RECORDING_MS = 25000; // 25s — Sarvam STT limit is 30s
const TARGET_SAMPLE_RATE = 16000; // Sarvam STT optimal rate

/**
 * Encode raw PCM Float32 samples into a WAV Blob.
 */
function encodeWav(samples: Float32Array, sampleRate: number): Blob {
  const numSamples = samples.length;
  const bytesPerSample = 2;
  const dataLength = numSamples * bytesPerSample;
  const buffer = new ArrayBuffer(44 + dataLength);
  const view = new DataView(buffer);

  const w = (off: number, str: string) => {
    for (let i = 0; i < str.length; i++) view.setUint8(off + i, str.charCodeAt(i));
  };

  w(0, "RIFF");
  view.setUint32(4, 36 + dataLength, true);
  w(8, "WAVE");
  w(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * bytesPerSample, true);
  view.setUint16(32, bytesPerSample, true);
  view.setUint16(34, 16, true); // bits per sample
  w(36, "data");
  view.setUint32(40, dataLength, true);

  for (let i = 0; i < numSamples; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]!));
    view.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }

  return new Blob([buffer], { type: "audio/wav" });
}

/**
 * Records audio directly as raw PCM and produces a WAV blob on stop.
 * Avoids the unreliable WebM → AudioContext.decodeAudioData → WAV pipeline.
 */
export function useAudioRecorder(onAutoStop?: () => void) {
  const [isRecording, setIsRecording] = useState(false);
  const ctxRef = useRef<AudioContext | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const samplesRef = useRef<Float32Array[]>([]);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const recordingRef = useRef(false);

  const startRecording = useCallback(async () => {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, sampleRate: TARGET_SAMPLE_RATE, echoCancellation: true, noiseSuppression: true },
    });
    streamRef.current = stream;

    const ctx = new AudioContext({ sampleRate: TARGET_SAMPLE_RATE });
    ctxRef.current = ctx;

    const source = ctx.createMediaStreamSource(stream);
    sourceRef.current = source;

    // ScriptProcessorNode captures raw PCM Float32 samples
    const processor = ctx.createScriptProcessor(4096, 1, 1);
    processorRef.current = processor;
    samplesRef.current = [];
    recordingRef.current = true;

    processor.onaudioprocess = (e) => {
      if (!recordingRef.current) return;
      // Copy the channel data (the buffer gets reused)
      const input = e.inputBuffer.getChannelData(0);
      samplesRef.current.push(new Float32Array(input));
    };

    source.connect(processor);
    processor.connect(ctx.destination); // required for onaudioprocess to fire

    setIsRecording(true);

    timerRef.current = setTimeout(() => {
      if (onAutoStop) onAutoStop();
    }, MAX_RECORDING_MS);
  }, [onAutoStop]);

  const stopRecording = useCallback((): Promise<Blob> => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }

    recordingRef.current = false;

    // Disconnect and close everything
    try { processorRef.current?.disconnect(); } catch {}
    try { sourceRef.current?.disconnect(); } catch {}
    streamRef.current?.getTracks().forEach(t => t.stop());
    const ctx = ctxRef.current;
    if (ctx && ctx.state !== "closed") {
      ctx.close().catch(() => {});
    }
    ctxRef.current = null;

    setIsRecording(false);

    // Merge all captured chunks into a single Float32Array
    const chunks = samplesRef.current;
    samplesRef.current = [];

    if (chunks.length === 0) {
      return Promise.resolve(new Blob());
    }

    const totalLength = chunks.reduce((acc, c) => acc + c.length, 0);
    const merged = new Float32Array(totalLength);
    let offset = 0;
    for (const chunk of chunks) {
      merged.set(chunk, offset);
      offset += chunk.length;
    }

    // The AudioContext may not honor the requested sampleRate; use actual rate
    const actualRate = ctx?.sampleRate ?? TARGET_SAMPLE_RATE;

    // Resample if needed
    let finalSamples = merged;
    if (actualRate !== TARGET_SAMPLE_RATE && actualRate > 0) {
      const ratio = actualRate / TARGET_SAMPLE_RATE;
      const newLength = Math.round(merged.length / ratio);
      finalSamples = new Float32Array(newLength);
      for (let i = 0; i < newLength; i++) {
        const srcIdx = i * ratio;
        const idx = Math.floor(srcIdx);
        const frac = srcIdx - idx;
        finalSamples[i] = idx + 1 < merged.length
          ? merged[idx]! * (1 - frac) + merged[idx + 1]! * frac
          : merged[idx] ?? 0;
      }
    }

    return Promise.resolve(encodeWav(finalSamples, TARGET_SAMPLE_RATE));
  }, []);

  return { isRecording, startRecording, stopRecording };
}
