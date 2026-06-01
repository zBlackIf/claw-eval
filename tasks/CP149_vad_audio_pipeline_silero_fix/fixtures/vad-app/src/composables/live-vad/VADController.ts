/**
 * VADController - Manages microphone capture, audio processing, and VAD inference.
 *
 * Audio pipeline:
 *   Microphone → MediaStreamSource → AnalyserNode → getFloatTimeDomainData
 *   → resample 48kHz→16kHz → SileroVADService.process() → probability → trigger logic
 */
import { SileroVADService, SileroVADResult } from './SileroVADService';
import {
  VADConfig,
  VADState,
  VADCallbacks,
  VADControllerOptions,
  VADRealtimeStatus,
  VADError,
  VADErrorType,
  DEFAULT_VAD_CONFIG,
} from './types';

const READ_INTERVAL_MS = 100; // How often we read audio data from AnalyserNode

export class VADController {
  private config: VADConfig;
  private callbacks: VADCallbacks;
  private state: VADState = VADState.IDLE;
  private previousState: VADState = VADState.IDLE;

  private audioContext: AudioContext | null = null;
  private mediaStream: MediaStream | null = null;
  private sourceNode: MediaStreamAudioSourceNode | null = null;
  private analyser: AnalyserNode | null = null;

  private vadService: SileroVADService;
  private animFrameId: number | null = null;
  private lastReadTime = 0;

  private currentProbability = 0;
  private currentVolume = 0;
  private continuousVoiceFrames = 0;
  private silenceStartTime = 0;

  constructor(options: VADControllerOptions = {}) {
    this.config = { ...DEFAULT_VAD_CONFIG, ...options.config };
    this.callbacks = options.callbacks ?? {};
    this.vadService = new SileroVADService({
      enableLog: this.config.enableLog,
    });
  }

  getRealtimeStatus(): VADRealtimeStatus {
    return {
      state: this.state,
      currentProbability: this.currentProbability,
      currentVolume: this.currentVolume,
      isVoiceDetected: this.state === VADState.VOICE_DETECTED,
      continuousVoiceFrames: this.continuousVoiceFrames,
    };
  }

  async start(deviceId?: string): Promise<boolean> {
    try {
      await this.vadService.initialize();
      await this.startMicrophone(deviceId);
      this.startVADLoop();
      this.setState(VADState.LISTENING);
      return true;
    } catch (err) {
      this.handleError(this.parseError(err));
      return false;
    }
  }

  stop(): void {
    this.stopMicrophone();
    if (this.animFrameId !== null) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }
    this.setState(VADState.IDLE);
  }

  updateConfig(newConfig: Partial<VADConfig>): void {
    this.config = { ...this.config, ...newConfig };
  }

  dispose(): void {
    this.stop();
    this.vadService.dispose();
  }

  /**
   * Set up microphone audio capture.
   */
  private async startMicrophone(deviceId?: string): Promise<void> {
    const constraints: MediaStreamConstraints = {
      audio: {
        deviceId: deviceId ? { exact: deviceId } : undefined,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
        sampleRate: 48000,
      },
    };

    this.mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
    this.audioContext = new AudioContext({ sampleRate: 48000 });
    this.sourceNode = this.audioContext.createMediaStreamSource(this.mediaStream);

    this.analyser = this.audioContext.createAnalyser();
    this.analyser.fftSize = 2048;
    this.analyser.smoothingTimeConstant = 0;

    // Connect source to analyser for reading audio data
    this.sourceNode.connect(this.analyser);
  }

  private stopMicrophone(): void {
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((t) => t.stop());
      this.mediaStream = null;
    }
    if (this.sourceNode) {
      this.sourceNode.disconnect();
      this.sourceNode = null;
    }
    if (this.analyser) {
      this.analyser.disconnect();
      this.analyser = null;
    }
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
  }

  /**
   * Main VAD analysis loop using requestAnimationFrame.
   * Reads audio data at READ_INTERVAL_MS intervals, resamples to 16kHz,
   * and feeds to Silero VAD for inference.
   */
  private startVADLoop(): void {
    const bufferLength = this.analyser!.fftSize;
    const timeData = new Float32Array(bufferLength);

    const readLoop = (timestamp: number) => {
      this.animFrameId = requestAnimationFrame(readLoop);

      // Throttle reads to READ_INTERVAL_MS
      if (timestamp - this.lastReadTime < READ_INTERVAL_MS) {
        return;
      }
      this.lastReadTime = timestamp;

      if (!this.analyser) return;

      // Read time-domain audio data
      this.analyser.getFloatTimeDomainData(timeData);

      // Calculate volume (RMS)
      let sum = 0;
      for (let i = 0; i < bufferLength; i++) {
        sum += timeData[i] * timeData[i];
      }
      const rms = Math.sqrt(sum / bufferLength);
      this.currentVolume = rms;
      this.callbacks.onVolumeUpdate?.(rms);

      // Resample from 48kHz to 16kHz and run VAD inference
      const resampled = this.resample(timeData, 48000, 16000);
      this.processAudioFrame(resampled);
    };

    this.animFrameId = requestAnimationFrame(readLoop);
  }

  /**
   * Resample audio data from source rate to target rate.
   * Simple linear interpolation resampler.
   */
  private resample(
    data: Float32Array,
    fromRate: number,
    toRate: number
  ): Float32Array {
    if (fromRate === toRate) return data;
    const ratio = fromRate / toRate;
    const outputLength = Math.round(data.length / ratio);
    const output = new Float32Array(outputLength);
    for (let i = 0; i < outputLength; i++) {
      const srcIdx = i * ratio;
      const idx = Math.floor(srcIdx);
      const frac = srcIdx - idx;
      output[i] =
        idx + 1 < data.length
          ? data[idx] * (1 - frac) + data[idx + 1] * frac
          : data[idx] ?? 0;
    }
    return output;
  }

  /**
   * Process a resampled audio frame through Silero VAD.
   * Slices the resampled buffer into frame-sized chunks for inference.
   */
  private async processAudioFrame(audioData: Float32Array): Promise<void> {
    const frameSize = 480;
    if (audioData.length < frameSize) return;

    const frame = audioData.slice(0, frameSize);
    const result: SileroVADResult = await this.vadService.process(frame);

    this.currentProbability = result.probability;
    this.callbacks.onProbabilityUpdate?.(result.probability);

    const threshold = this.config.probabilityThreshold / 100;

    if (result.probability >= threshold) {
      this.continuousVoiceFrames++;
      if (this.continuousVoiceFrames >= this.config.continuousFrames) {
        this.triggerVoice(result.probability);
      }
    } else {
      if (this.state === VADState.VOICE_DETECTED) {
        if (this.silenceStartTime === 0) {
          this.silenceStartTime = Date.now();
        }
        if (Date.now() - this.silenceStartTime >= this.config.silenceDuration) {
          this.triggerSilence();
        }
      }
      this.continuousVoiceFrames = 0;
    }
  }

  private triggerVoice(probability: number): void {
    if (this.state !== VADState.VOICE_DETECTED) {
      this.setState(VADState.VOICE_DETECTED);
      this.callbacks.onVoiceDetected?.({
        probability,
        timestamp: Date.now(),
      });
    }
    this.silenceStartTime = 0;
  }

  private triggerSilence(): void {
    const duration = Date.now() - this.silenceStartTime;
    this.setState(VADState.LISTENING);
    this.callbacks.onSilenceDetected?.({
      duration,
      timestamp: Date.now(),
    });
    this.silenceStartTime = 0;
    this.continuousVoiceFrames = 0;
  }

  private setState(newState: VADState): void {
    this.previousState = this.state;
    this.state = newState;
    this.callbacks.onStateChange?.(newState, this.previousState);
  }

  private handleError(error: VADError): void {
    this.setState(VADState.ERROR);
    this.callbacks.onError?.(error);
  }

  private parseError(err: unknown): VADError {
    if (err instanceof DOMException && err.name === 'NotAllowedError') {
      return {
        type: VADErrorType.MICROPHONE_ACCESS_DENIED,
        message: 'Microphone access denied',
      };
    }
    return {
      type: VADErrorType.AUDIO_CONTEXT_FAILED,
      message: err instanceof Error ? err.message : String(err),
      originalError: err instanceof Error ? err : undefined,
    };
  }
}
