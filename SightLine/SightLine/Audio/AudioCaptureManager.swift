//
//  AudioCaptureManager.swift
//  SightLine
//
//  Captures microphone audio using the shared AVAudioEngine, converts to
//  PCM 16kHz mono 16-bit, and delivers raw PCM data via callback for
//  WebSocket transmission.
//
//  Uses SharedAudioEngine.shared.engine.inputNode so that capture and
//  playback share a single audio graph, enabling hardware AEC.
//

import AVFoundation
import Combine
import os

class AudioCaptureManager: ObservableObject {
    @Published var isCapturing = false

    private static let logger = Logger(subsystem: "com.sightline.app", category: "AudioCapture")

    var onAudioCaptured: ((Data) -> Void)?
    /// RMS audio level callback for NoiseMeter (ambient noise calculation).
    var onAudioLevelUpdate: ((Float) -> Void)?

    /// Timestamp of the last model audio chunk received via WebSocket.
    /// Used with `modelSpeakingTimeout` to determine if the model is currently speaking.
    /// Timestamp-based approach is more robust than a boolean flag because it handles
    /// playback buffer starvation (network jitter) gracefully — no false toggles.
    var lastModelAudioReceivedAt: CFAbsoluteTime = 0

    /// How long after the last audio chunk we still consider the model "speaking".
    /// Covers: network jitter between chunks (~100ms) + AEC tail (~150ms) + margin.
    private let modelSpeakingTimeout: Double = 0.5

    /// RMS threshold for voice barge-in during model playback.
    /// Post-AEC residual echo is typically < 0.02 RMS; human speech at arm's length > 0.08.
    private let bargeInRMSThreshold: Float = 0.05

    /// Called when client-side VAD detects speech onset — sends activity_start.
    var onSpeechDetected: (() -> Void)?
    /// Called when client-side VAD detects speech offset — sends activity_end.
    var onSpeechEnded: (() -> Void)?

    /// Called when voice barge-in detected (RMS above threshold during model speech).
    var onVoiceBargeIn: (() -> Void)?

    /// Last computed RMS value, reused by echo gating logic.
    private var lastRMS: Float = 0

    private var converter: AVAudioConverter?
    private var targetFormat: AVAudioFormat?
    private var restartObserver: NSObjectProtocol?
    private var pauseObserver: NSObjectProtocol?

    func startCapture() {
        guard let engine = SharedAudioEngine.shared.engine, engine.isRunning else {
            Self.logger.error("SharedAudioEngine not running; cannot start capture")
            return
        }

        let inputNode = engine.inputNode
        let inputFormat = inputNode.outputFormat(forBus: 0)

        // Target format: PCM 16kHz Mono 16-bit (what Gemini expects)
        guard let fmt = AVAudioFormat(
            commonFormat: .pcmFormatInt16,
            sampleRate: SightLineConfig.audioInputSampleRate,
            channels: 1,
            interleaved: true
        ) else {
            Self.logger.error("Failed to create target audio format")
            return
        }
        targetFormat = fmt

        guard let conv = AVAudioConverter(from: inputFormat, to: fmt) else {
            Self.logger.error("Failed to create audio converter (input: \(inputFormat))")
            return
        }
        converter = conv

        inputNode.installTap(onBus: 0, bufferSize: SightLineConfig.audioBufferSize, format: inputFormat) {
            [weak self] buffer, _ in
            guard let self = self, let fmt = self.targetFormat, let converter = self.converter else { return }

            let targetFrameCount = AVAudioFrameCount(SightLineConfig.audioBufferSize)
            guard let outputBuffer = AVAudioPCMBuffer(
                pcmFormat: fmt,
                frameCapacity: targetFrameCount
            ) else { return }

            var error: NSError?
            converter.convert(to: outputBuffer, error: &error) { _, outStatus in
                outStatus.pointee = .haveData
                return buffer
            }

            if let error = error {
                Self.logger.error("Audio conversion error: \(error)")
                return
            }

            // Calculate RMS for NoiseMeter (from input buffer, not converted output)
            if let floatData = buffer.floatChannelData {
                let frameLength = Int(buffer.frameLength)
                if frameLength > 0 {
                    var sumSquares: Float = 0
                    let samples = floatData[0]
                    for i in 0..<frameLength {
                        sumSquares += samples[i] * samples[i]
                    }
                    let rms = sqrtf(sumSquares / Float(frameLength))
                    self.lastRMS = rms
                    self.onAudioLevelUpdate?(rms)
                }
            }

            // Feed converted 16kHz Int16 samples to client-side VAD
            if let int16Data = outputBuffer.int16ChannelData {
                SileroVAD.shared.processAudioFrame(int16Data[0], count: Int(outputBuffer.frameLength))
            }

            if let channelData = outputBuffer.int16ChannelData {
                let byteCount = Int(outputBuffer.frameLength) * 2  // 16-bit = 2 bytes per sample

                // Timestamp-based model speaking detection: immune to drain starvation toggles
                let now = CFAbsoluteTimeGetCurrent()
                let isModelCurrentlySpeaking =
                    (now - self.lastModelAudioReceivedAt) < self.modelSpeakingTimeout

                if isModelCurrentlySpeaking {
                    // During model speech: energy-gated — only pass genuine human voice
                    let rms = self.lastRMS
                    if rms > self.bargeInRMSThreshold && SileroVAD.shared.isSpeechActive {
                        // Genuine barge-in: RMS + VAD confirms human speech, not ambient noise
                        let data = Data(bytes: channelData[0], count: byteCount)
                        self.onAudioCaptured?(data)
                        self.lastModelAudioReceivedAt = 0  // Expire immediately
                        self.onVoiceBargeIn?()
                    } else {
                        // Echo residual: send silence to maintain stream continuity
                        let silence = Data(count: byteCount)
                        self.onAudioCaptured?(silence)
                    }
                } else {
                    let data = Data(bytes: channelData[0], count: byteCount)
                    self.onAudioCaptured?(data)
                }
            }
        }

        // Remove tap cleanly when engine pauses (phone call / Siri interruption).
        // isCapturing stays true so the didRestart observer re-installs the tap.
        pauseObserver = NotificationCenter.default.addObserver(
            forName: .sharedAudioEngineDidPause,
            object: nil,
            queue: .main
        ) { [weak self] _ in
            guard let self = self, self.isCapturing else { return }
            Self.logger.info("SharedAudioEngine paused — removing capture tap")
            self.removeTap()
        }

        // Re-install tap if the shared engine restarts (route change, interruption)
        restartObserver = NotificationCenter.default.addObserver(
            forName: .sharedAudioEngineDidRestart,
            object: nil,
            queue: .main
        ) { [weak self] _ in
            guard let self = self, self.isCapturing else { return }
            Self.logger.info("SharedAudioEngine restarted — re-installing capture tap")
            self.removeTap()
            self.startCapture()
        }

        // Initialize client-side VAD for speech detection
        SileroVAD.shared.loadModel()
        SileroVAD.shared.reset()
        SileroVAD.shared.onSpeechStart = { [weak self] in self?.onSpeechDetected?() }
        SileroVAD.shared.onSpeechEnd = { [weak self] in self?.onSpeechEnded?() }

        DispatchQueue.main.async { self.isCapturing = true }
        Self.logger.info("Audio capture started (shared engine, VP=\(SharedAudioEngine.shared.isVoiceProcessingEnabled))")
    }

    func stopCapture() {
        removeTap()
        converter = nil
        targetFormat = nil

        if let obs = pauseObserver {
            NotificationCenter.default.removeObserver(obs)
            pauseObserver = nil
        }
        if let obs = restartObserver {
            NotificationCenter.default.removeObserver(obs)
            restartObserver = nil
        }

        DispatchQueue.main.async { self.isCapturing = false }
        Self.logger.info("Audio capture stopped")
    }

    private func removeTap() {
        // Only remove tap — do NOT stop the shared engine (playback may still be active)
        SharedAudioEngine.shared.engine?.inputNode.removeTap(onBus: 0)
    }
}
