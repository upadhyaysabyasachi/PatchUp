"use client";

// Reuse a single AudioContext to avoid exhausting the browser limit (~6 concurrent)
let _sharedCtx: AudioContext | null = null;

function getAudioContext(): AudioContext {
  if (!_sharedCtx || _sharedCtx.state === "closed") {
    _sharedCtx = new AudioContext();
  }
  return _sharedCtx;
}

/**
 * Convert WebM/Opus recording blob to WAV so Sarvam STT accepts it.
 * Uses Web Audio API to decode then writes a simple WAV header + PCM.
 */
export async function webmToWav(blob: Blob): Promise<Blob> {
  const arrayBuffer = await blob.arrayBuffer();
  const ctx = getAudioContext();

  // decodeAudioData detaches the buffer, so we must pass a copy
  const copy = arrayBuffer.slice(0);
  const audioBuffer = await ctx.decodeAudioData(copy);

  // Sarvam works best with 16kHz; resample if we have a higher rate
  const targetSampleRate = 16000;
  const sourceRate = audioBuffer.sampleRate;
  const numChannels = 1;
  const channelData = audioBuffer.getChannelData(0);
  let samples: Float32Array;
  if (sourceRate !== targetSampleRate && sourceRate > 0) {
    const ratio = sourceRate / targetSampleRate;
    const newLength = Math.round(channelData.length / ratio);
    samples = new Float32Array(newLength);
    for (let i = 0; i < newLength; i++) {
      const srcIndex = i * ratio;
      const idx = Math.floor(srcIndex);
      const frac = srcIndex - idx;
      samples[i] = idx + 1 < channelData.length
        ? channelData[idx]! * (1 - frac) + channelData[idx + 1]! * frac
        : channelData[idx] ?? 0;
    }
  } else {
    samples = channelData;
  }

  const sampleRate = sourceRate !== targetSampleRate ? targetSampleRate : sourceRate;
  const numSamples = samples.length;
  const bytesPerSample = 2;
  const dataLength = numSamples * numChannels * bytesPerSample;
  const buffer = new ArrayBuffer(44 + dataLength);
  const view = new DataView(buffer);

  const writeStr = (offset: number, str: string) => {
    for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
  };

  writeStr(0, "RIFF");
  view.setUint32(4, 36 + dataLength, true);
  writeStr(8, "WAVE");
  writeStr(12, "fmt ");
  view.setUint32(16, 16, true); // fmt chunk size
  view.setUint16(20, 1, true);   // PCM
  view.setUint16(22, numChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * numChannels * bytesPerSample, true);
  view.setUint16(32, numChannels * bytesPerSample, true);
  view.setUint16(34, 16, true);  // bits per sample
  writeStr(36, "data");
  view.setUint32(40, dataLength, true);

  for (let i = 0; i < numSamples; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]!));
    const v = s < 0 ? s * 0x8000 : s * 0x7fff;
    view.setInt16(44 + i * 2, v, true);
  }

  return new Blob([buffer], { type: "audio/wav" });
}
