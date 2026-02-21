//
//  AudioPlaybackManager.swift
//  SightLine
//
//  Plays PCM 24kHz mono 16-bit audio received from the Gemini backend.
//  Supports immediate stop for barge-in (user interrupting the agent).
//

import AVFoundation
import Combine

class AudioPlaybackManager: ObservableObject {
    @Published var isPlaying = false

    private var audioEngine: AVAudioEngine?
    private var playerNode: AVAudioPlayerNode?
    private var playbackFormat: AVAudioFormat?

    func setup() {
        let engine = AVAudioEngine()
        let player = AVAudioPlayerNode()

        // Gemini outputs PCM 24kHz mono 16-bit
        guard let format = AVAudioFormat(
            commonFormat: .pcmFormatInt16,
            sampleRate: SightLineConfig.audioOutputSampleRate,
            channels: 1,
            interleaved: true
        ) else {
            print("[SightLine] Failed to create playback audio format")
            return
        }

        engine.attach(player)
        engine.connect(player, to: engine.mainMixerNode, format: format)

        engine.prepare()
        do {
            try engine.start()
            player.play()

            audioEngine = engine
            playerNode = player
            playbackFormat = format
            DispatchQueue.main.async { self.isPlaying = true }
            print("[SightLine] Audio playback engine started")
        } catch {
            print("[SightLine] Audio playback engine start failed: \(error)")
        }
    }

    func playAudioData(_ data: Data) {
        guard let format = playbackFormat,
              let player = playerNode else { return }

        let frameCount = UInt32(data.count / 2)  // 16-bit = 2 bytes per frame
        guard let buffer = AVAudioPCMBuffer(
            pcmFormat: format,
            frameCapacity: frameCount
        ) else { return }

        buffer.frameLength = frameCount
        data.withUnsafeBytes { rawBufferPointer in
            if let baseAddress = rawBufferPointer.baseAddress,
               let channelData = buffer.int16ChannelData {
                memcpy(channelData[0], baseAddress, data.count)
            }
        }

        player.scheduleBuffer(buffer, completionHandler: nil)
    }

    /// Stop playback immediately for barge-in support
    func stopImmediately() {
        playerNode?.stop()
        playerNode?.play()  // Re-ready for next audio
    }

    func teardown() {
        playerNode?.stop()
        audioEngine?.stop()
        audioEngine = nil
        playerNode = nil
        playbackFormat = nil
        DispatchQueue.main.async { self.isPlaying = false }
        print("[SightLine] Audio playback engine stopped")
    }
}
