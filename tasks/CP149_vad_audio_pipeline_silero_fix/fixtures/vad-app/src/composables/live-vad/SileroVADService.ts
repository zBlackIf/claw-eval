/**
 * Silero VAD Service - ONNX Runtime Web inference wrapper.
 *
 * Loads the Silero VAD model and runs frame-level inference to produce
 * voice activity probability (0.0 - 1.0).
 */
import * as ort from 'onnxruntime-web';

export interface SileroVADOptions {
  modelPath?: string;
  enableLog?: boolean;
}

export interface SileroVADResult {
  probability: number;
  isVoice: boolean;
  inferenceTimeMs: number;
}

export enum SileroVADState {
  UNINITIALIZED = 'uninitialized',
  LOADING = 'loading',
  READY = 'ready',
  ERROR = 'error',
  DISPOSED = 'disposed',
}

const REQUIRED_SAMPLES = 480;
const SAMPLE_RATE = 16000;

export class SileroVADService {
  private session: ort.InferenceSession | null = null;
  private state: SileroVADState = SileroVADState.UNINITIALIZED;
  private enableLog: boolean;
  private modelPath: string;

  // v4 LSTM state: shape [2, 1, 128]
  private hState: ort.Tensor | null = null;
  private cState: ort.Tensor | null = null;
  private srTensor: ort.Tensor | null = null;

  private inferenceCount = 0;
  private totalInferenceTime = 0;

  constructor(options: SileroVADOptions = {}) {
    this.enableLog = options.enableLog ?? false;
    this.modelPath = options.modelPath ?? '/models/silero_vad_v4.onnx';
  }

  get isReady(): boolean {
    return this.state === SileroVADState.READY;
  }

  get avgInferenceTime(): number {
    return this.inferenceCount > 0
      ? this.totalInferenceTime / this.inferenceCount
      : 0;
  }

  async initialize(): Promise<void> {
    if (this.state === SileroVADState.READY) return;
    this.state = SileroVADState.LOADING;

    try {
      this.session = await ort.InferenceSession.create(this.modelPath, {
        executionProviders: ['wasm'],
      });

      // Initialize LSTM states - v4 uses shape [2, 1, 128]
      const stateSize = 128;
      this.hState = new ort.Tensor(
        'float32',
        new Float32Array(2 * 1 * stateSize),
        [2, 1, stateSize]
      );
      this.cState = new ort.Tensor(
        'float32',
        new Float32Array(2 * 1 * stateSize),
        [2, 1, stateSize]
      );
      this.srTensor = new ort.Tensor(
        'int64',
        BigInt64Array.from([BigInt(SAMPLE_RATE)]),
        []
      );

      this.state = SileroVADState.READY;
      this.log('Silero VAD v4 model loaded successfully');
    } catch (err) {
      this.state = SileroVADState.ERROR;
      throw err;
    }
  }

  /**
   * Process a single audio frame and return voice probability.
   *
   * @param audioChunk - Float32Array of PCM samples at 16kHz.
   *   Must be REQUIRED_SAMPLES in length.
   */
  async process(audioChunk: Float32Array): Promise<SileroVADResult> {
    if (!this.session || this.state !== SileroVADState.READY) {
      return { probability: 0, isVoice: false, inferenceTimeMs: 0 };
    }

    // Ensure correct frame size
    if (audioChunk.length !== REQUIRED_SAMPLES) {
      this.log(`Frame size mismatch: got ${audioChunk.length}, need ${REQUIRED_SAMPLES}`);
      return { probability: 0, isVoice: false, inferenceTimeMs: 0 };
    }

    const startTime = performance.now();

    const inputTensor = new ort.Tensor(
      'float32',
      audioChunk,
      [1, REQUIRED_SAMPLES]
    );

    const feeds: Record<string, ort.Tensor> = {
      input: inputTensor,
      h: this.hState!,
      c: this.cState!,
      sr: this.srTensor!,
    };

    const results = await this.session.run(feeds);

    // Update LSTM states for next frame
    this.hState = results.hn as ort.Tensor;
    this.cState = results.cn as ort.Tensor;

    const probability = (results.output as ort.Tensor).data[0] as number;
    const inferenceTimeMs = performance.now() - startTime;

    this.inferenceCount++;
    this.totalInferenceTime += inferenceTimeMs;

    this.log(`VAD inference: prob=${probability.toFixed(4)}, time=${inferenceTimeMs.toFixed(1)}ms`);

    return {
      probability,
      isVoice: probability >= 0.5,
      inferenceTimeMs,
    };
  }

  reset(): void {
    if (this.hState) {
      const size = (this.hState.data as Float32Array).length;
      this.hState = new ort.Tensor('float32', new Float32Array(size), this.hState.dims);
    }
    if (this.cState) {
      const size = (this.cState.data as Float32Array).length;
      this.cState = new ort.Tensor('float32', new Float32Array(size), this.cState.dims);
    }
  }

  dispose(): void {
    this.session?.release();
    this.session = null;
    this.hState = null;
    this.cState = null;
    this.srTensor = null;
    this.state = SileroVADState.DISPOSED;
  }

  private log(...args: any[]): void {
    if (this.enableLog) {
      console.log('[SileroVAD]', ...args);
    }
  }
}
