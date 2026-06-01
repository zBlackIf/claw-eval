/**
 * VAD Configuration types
 */
export interface VADConfig {
  /** Probability threshold (0-100) to trigger voice detection */
  probabilityThreshold: number;
  /** Number of continuous frames above threshold to confirm voice */
  continuousFrames: number;
  /** Silence duration (ms) before switching back to silence state */
  silenceDuration: number;
  /** Audio read interval in milliseconds */
  readIntervalMs: number;
  /** Enable debug logging */
  enableLog: boolean;
}

export const DEFAULT_VAD_CONFIG: VADConfig = {
  probabilityThreshold: 50,
  continuousFrames: 3,
  silenceDuration: 1500,
  readIntervalMs: 100,
  enableLog: false,
};

export enum VADState {
  IDLE = 'idle',
  LISTENING = 'listening',
  VOICE_DETECTED = 'voice_detected',
  SILENCE = 'silence',
  ERROR = 'error',
}

export enum VADErrorType {
  MODEL_LOAD_FAILED = 'model_load_failed',
  MICROPHONE_ACCESS_DENIED = 'microphone_access_denied',
  AUDIO_CONTEXT_FAILED = 'audio_context_failed',
  INFERENCE_FAILED = 'inference_failed',
}

export interface VADError {
  type: VADErrorType;
  message: string;
  originalError?: Error;
}

export interface VADRealtimeStatus {
  state: VADState;
  currentProbability: number;
  currentVolume: number;
  isVoiceDetected: boolean;
  continuousVoiceFrames: number;
}

export interface VADCallbacks {
  onVoiceDetected?: (event: { probability: number; timestamp: number }) => void;
  onSilenceDetected?: (event: { duration: number; timestamp: number }) => void;
  onStateChange?: (newState: VADState, previousState: VADState) => void;
  onError?: (error: VADError) => void;
  onVolumeUpdate?: (volume: number) => void;
  onProbabilityUpdate?: (probability: number) => void;
}

export interface VADControllerOptions {
  config?: Partial<VADConfig>;
  callbacks?: VADCallbacks;
}
