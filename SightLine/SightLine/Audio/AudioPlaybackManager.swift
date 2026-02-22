//
//  AudioPlaybackManager.swift
//  SightLine
//
//  Plays PCM 24kHz mono 16-bit audio received from the Gemini backend.
//  Supports immediate stop for barge-in (user interrupting the agent).
//

import AVFoundation
import Combine
import os

class AudioPlaybackManager: ObservableObject {
    @Published var isPlaying = false

    private static let logger = Logger(subsystem: "com.sightline.app", category: "AudioPlayback")

    private var audioEngine: AVAudioEngine?
    private var playerNode: AVAudioPlayerNode?
    private var playbackFormat: AVAudioFormat?
    private let schedulingQueue = DispatchQueue(
        label: "com.sightline.audio.playback.scheduling",
        qos: .userInitiated
    )
    private var pendingChunks: [Data] = []
    private var isDrainActive = false
    private var jitterKickoffWorkItem: DispatchWorkItem?

    func setup() {
        configureAudioSession()

        let engine = AVAudioEngine()
        let player = AVAudioPlayerNode()

        // Gemini outputs PCM 24kHz mono 16-bit
        guard let format = AVAudioFormat(
            commonFormat: .pcmFormatInt16,
            sampleRate: SightLineConfig.audioOutputSampleRate,
            channels: 1,
            interleaved: true
        ) else {
            Self.logger.error("Failed to create playback audio format")
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
            schedulingQueue.async { [weak self] in
                guard let self = self else { return }
                self.pendingChunks.removeAll()
                self.isDrainActive = false
                self.jitterKickoffWorkItem?.cancel()
                self.jitterKickoffWorkItem = nil
            }
            DispatchQueue.main.async { self.isPlaying = false }
            Self.logger.info("Audio playback engine started")
        } catch {
            Self.logger.error("Audio playback engine start failed: \(error)")
        }
    }

    func playAudioData(_ data: Data) {
        guard !data.isEmpty else { return }
        guard let format = playbackFormat,
              let player = playerNode else { return }

        schedulingQueue.async { [weak self] in
            guard let self = self else { return }
            guard self.playerNode === player else { return }
            self.pendingChunks.append(data)

            guard !self.isDrainActive else { return }
            if self.pendingChunks.count >= SightLineConfig.audioJitterBufferChunks {
                self.startDrain(player: player, format: format)
            } else {
                self.scheduleDrainFallback(player: player, format: format)
            }
        }
    }

    /// Stop playback immediately for barge-in support
    func stopImmediately() {
        schedulingQueue.async { [weak self] in
            guard let self = self else { return }
            self.pendingChunks.removeAll(keepingCapacity: true)
            self.isDrainActive = false
            self.jitterKickoffWorkItem?.cancel()
            self.jitterKickoffWorkItem = nil
        }
        playerNode?.stop()
        playerNode?.reset()
        playerNode?.play()  // Re-ready for next audio
        DispatchQueue.main.async { self.isPlaying = false }
    }

    func teardown() {
        schedulingQueue.async { [weak self] in
            guard let self = self else { return }
            self.pendingChunks.removeAll()
            self.isDrainActive = false
            self.jitterKickoffWorkItem?.cancel()
            self.jitterKickoffWorkItem = nil
        }
        playerNode?.stop()
        audioEngine?.stop()
        audioEngine = nil
        playerNode = nil
        playbackFormat = nil
        DispatchQueue.main.async { self.isPlaying = false }
        Self.logger.info("Audio playback engine stopped")
    }

    /// Configure the shared AVAudioSession for simultaneous recording and playback.
    /// Must be called before either AVAudioEngine starts.
    private func configureAudioSession() {
        let session = AVAudioSession.sharedInstance()
        do {
            try session.setCategory(
                .playAndRecord,
                mode: .voiceChat,
                options: [.defaultToSpeaker, .allowBluetooth, .allowBluetoothA2DP]
            )
            try session.setActive(true)
            Self.logger.info("AVAudioSession configured: playAndRecord + defaultToSpeaker")
        } catch {
            Self.logger.error("AVAudioSession configuration failed: \(error)")
        }
    }

    private func scheduleNextChunk(player: AVAudioPlayerNode, format: AVAudioFormat) {
        guard isDrainActive else { return }
        guard playerNode === player else { return }
        guard !pendingChunks.isEmpty else {
            isDrainActive = false
            DispatchQueue.main.async { self.isPlaying = false }
            return
        }

        let chunk = pendingChunks.removeFirst()
        guard let buffer = makePCMBuffer(from: chunk, format: format) else {
            scheduleNextChunk(player: player, format: format)
            return
        }

        player.scheduleBuffer(buffer) { [weak self, weak player] in
            guard let self = self else { return }
            self.schedulingQueue.async {
                guard let player = player else {
                    self.isDrainActive = false
                    DispatchQueue.main.async { self.isPlaying = false }
                    return
                }
                self.scheduleNextChunk(player: player, format: format)
            }
        }
    }

    private func startDrain(player: AVAudioPlayerNode, format: AVAudioFormat) {
        jitterKickoffWorkItem?.cancel()
        jitterKickoffWorkItem = nil
        isDrainActive = true
        DispatchQueue.main.async { self.isPlaying = true }
        if !player.isPlaying {
            player.play()
        }
        scheduleNextChunk(player: player, format: format)
    }

    private func scheduleDrainFallback(player: AVAudioPlayerNode, format: AVAudioFormat) {
        jitterKickoffWorkItem?.cancel()
        let workItem = DispatchWorkItem { [weak self, weak player] in
            guard let self = self else { return }
            guard let player = player else { return }
            guard !self.isDrainActive else { return }
            guard self.playerNode === player else { return }
            guard !self.pendingChunks.isEmpty else { return }
            self.startDrain(player: player, format: format)
        }
        jitterKickoffWorkItem = workItem
        schedulingQueue.asyncAfter(
            deadline: .now() + SightLineConfig.audioJitterMaxWait,
            execute: workItem
        )
    }

    private func makePCMBuffer(from data: Data, format: AVAudioFormat) -> AVAudioPCMBuffer? {
        let frameCount = UInt32(data.count / 2)  // 16-bit = 2 bytes per frame
        guard frameCount > 0 else { return nil }
        guard let buffer = AVAudioPCMBuffer(
            pcmFormat: format,
            frameCapacity: frameCount
        ) else { return nil }

        buffer.frameLength = frameCount
        data.withUnsafeBytes { rawBufferPointer in
            if let baseAddress = rawBufferPointer.baseAddress,
               let channelData = buffer.int16ChannelData {
                memcpy(channelData[0], baseAddress, data.count)
            }
        }
        return buffer
    }
}
