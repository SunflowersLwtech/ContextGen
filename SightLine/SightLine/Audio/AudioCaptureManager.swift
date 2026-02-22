//
//  AudioCaptureManager.swift
//  SightLine
//
//  Captures microphone audio using AVAudioEngine, converts to PCM 16kHz mono 16-bit,
//  and delivers raw PCM data via callback for WebSocket transmission.
//

import AVFoundation
import Combine
import os

class AudioCaptureManager: ObservableObject {
    @Published var isCapturing = false

    private static let logger = Logger(subsystem: "com.sightline.app", category: "AudioCapture")

    private var audioEngine: AVAudioEngine?
    var onAudioCaptured: ((Data) -> Void)?
    /// RMS audio level callback for NoiseMeter (ambient noise calculation).
    var onAudioLevelUpdate: ((Float) -> Void)?

    func startCapture() {
        let engine = AVAudioEngine()
        let inputNode = engine.inputNode
        let inputFormat = inputNode.outputFormat(forBus: 0)

        // Target format: PCM 16kHz Mono 16-bit (what Gemini expects)
        guard let targetFormat = AVAudioFormat(
            commonFormat: .pcmFormatInt16,
            sampleRate: SightLineConfig.audioInputSampleRate,
            channels: 1,
            interleaved: true
        ) else {
            Self.logger.error("Failed to create target audio format")
            return
        }

        guard let converter = AVAudioConverter(from: inputFormat, to: targetFormat) else {
            Self.logger.error("Failed to create audio converter")
            return
        }

        inputNode.installTap(onBus: 0, bufferSize: SightLineConfig.audioBufferSize, format: inputFormat) {
            [weak self] buffer, _ in

            let targetFrameCount = AVAudioFrameCount(SightLineConfig.audioBufferSize)
            guard let outputBuffer = AVAudioPCMBuffer(
                pcmFormat: targetFormat,
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
                    self?.onAudioLevelUpdate?(rms)
                }
            }

            if let channelData = outputBuffer.int16ChannelData {
                let byteCount = Int(outputBuffer.frameLength) * 2  // 16-bit = 2 bytes per sample
                let data = Data(bytes: channelData[0], count: byteCount)
                self?.onAudioCaptured?(data)
            }
        }

        engine.prepare()
        do {
            try engine.start()
            audioEngine = engine
            DispatchQueue.main.async { self.isCapturing = true }
            Self.logger.info("Audio capture started")
        } catch {
            Self.logger.error("Audio engine start failed: \(error)")
        }
    }

    func stopCapture() {
        audioEngine?.inputNode.removeTap(onBus: 0)
        audioEngine?.stop()
        audioEngine = nil
        DispatchQueue.main.async { self.isCapturing = false }
        Self.logger.info("Audio capture stopped")
    }
}
