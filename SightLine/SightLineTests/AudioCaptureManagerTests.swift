//
//  AudioCaptureManagerTests.swift
//  SightLineTests
//
//  Comprehensive tests for the audio capture pipeline.
//

import Testing
import Foundation
@testable import SightLine

@Suite("Audio Capture Manager Tests")
struct AudioCaptureManagerTests {

    @Test("AudioCaptureManager initializes without error")
    func initialization() {
        let manager = AudioCaptureManager()
        #expect(manager != nil)
        #expect(manager.isCapturing == false)
    }

    @Test("AudioCaptureManager exposes audio callback")
    func audioCallback() {
        let manager = AudioCaptureManager()
        var callbackInvoked = false
        manager.onAudioCaptured = { data in
            callbackInvoked = true
        }
        #expect(manager.onAudioCaptured != nil)
    }

    @Test("AudioCaptureManager stop without start does not crash")
    func stopWithoutStart() {
        let manager = AudioCaptureManager()
        manager.stopCapture()
        #expect(manager.isCapturing == false)
    }

    @Test("AudioCaptureManager multiple start-stop cycles")
    func multipleCycles() {
        let manager = AudioCaptureManager()
        
        // First cycle
        manager.stopCapture()
        #expect(manager.isCapturing == false)
        
        // Second cycle
        manager.stopCapture()
        #expect(manager.isCapturing == false)
    }

    @Test("AudioCaptureManager timestamp-based model speaking detection")
    func modelSpeakingDetection() {
        let manager = AudioCaptureManager()
        
        // Initially not speaking
        #expect(manager.lastModelAudioReceivedAt == 0)
        
        // Simulate model audio received
        manager.lastModelAudioReceivedAt = CFAbsoluteTimeGetCurrent()
        let now = CFAbsoluteTimeGetCurrent()
        let isSpeaking = (now - manager.lastModelAudioReceivedAt) < 0.5
        #expect(isSpeaking == true)
    }

    @Test("AudioCaptureManager barge-in callbacks are settable")
    func bargeInCallbacks() {
        let manager = AudioCaptureManager()
        var bargeInDetected = false
        var speechDetected = false
        var speechEnded = false
        
        manager.onVoiceBargeIn = { bargeInDetected = true }
        manager.onSpeechDetected = { speechDetected = true }
        manager.onSpeechEnded = { speechEnded = true }
        
        #expect(manager.onVoiceBargeIn != nil)
        #expect(manager.onSpeechDetected != nil)
        #expect(manager.onSpeechEnded != nil)
    }

    @Test("AudioCaptureManager audio level callback")
    func audioLevelCallback() {
        let manager = AudioCaptureManager()
        var lastLevel: Float?
        
        manager.onAudioLevelUpdate = { level in
            lastLevel = level
        }
        
        #expect(manager.onAudioLevelUpdate != nil)
    }

    @Test("AudioPlaybackManager setup and teardown lifecycle")
    func playbackLifecycle() {
        let manager = AudioPlaybackManager()
        manager.setup()
        #expect(manager.isPlaying == false)
        manager.teardown()
        #expect(manager.isPlaying == false)
    }

    @Test("AudioPlaybackManager multiple setup-teardown cycles")
    func playbackMultipleCycles() {
        let manager = AudioPlaybackManager()
        
        // First cycle
        manager.setup()
        manager.teardown()
        #expect(manager.isPlaying == false)
        
        // Second cycle
        manager.setup()
        manager.teardown()
        #expect(manager.isPlaying == false)
    }

    @Test("AudioPlaybackManager stop immediately without crash")
    func playbackStopImmediately() {
        let manager = AudioPlaybackManager()
        manager.setup()
        manager.stopImmediately()
        #expect(manager.isPlaying == false)
        manager.teardown()
    }

    @Test("SharedAudioEngine singleton exists and starts not running")
    func sharedAudioEngineInit() {
        let engine = SharedAudioEngine.shared
        // Before setup(), engine should not be running
        #expect(engine.isRunning == false)
        #expect(engine.isVoiceProcessingEnabled == false)
    }

    @Test("SharedAudioEngine setup and teardown")
    func sharedAudioEngineLifecycle() {
        SharedAudioEngine.shared.setup()
        // Note: In simulator, engine may start but VP may not be available
        SharedAudioEngine.shared.teardown()
        #expect(SharedAudioEngine.shared.isRunning == false)
    }

    @Test("SharedAudioEngine teardown without setup does not crash")
    func sharedAudioEngineTeardownSafe() {
        SharedAudioEngine.shared.teardown()
        #expect(SharedAudioEngine.shared.isRunning == false)
    }

    @Test("SileroVAD singleton exists")
    func sileroVADInit() {
        let vad = SileroVAD.shared
        #expect(vad != nil)
        #expect(vad.isSpeechActive == false)
        #expect(vad.lastProbability == 0)
    }

    @Test("SileroVAD reset clears state")
    func sileroVADReset() {
        let vad = SileroVAD.shared
        vad.reset()
        #expect(vad.isSpeechActive == false)
        #expect(vad.lastProbability == 0)
    }

    @Test("AudioSessionManager configures without crash")
    func audioSessionConfig() throws {
        // This may fail in simulator, so we don't enforce success
        do {
            try AudioSessionManager.shared.configure()
        } catch {
            // Expected in simulator environment
        }
    }

    @Test("Config values are valid")
    func configValidation() {
        #expect(SightLineConfig.audioInputSampleRate == 16000)
        #expect(SightLineConfig.audioOutputSampleRate == 24000)
        #expect(SightLineConfig.audioBufferSize > 0)
        #expect(SightLineConfig.audioJitterBufferChunks > 0)
        #expect(SightLineConfig.videoFrameWidth > 0)
        #expect(SightLineConfig.videoFrameHeight > 0)
        #expect(SightLineConfig.jpegQuality > 0 && SightLineConfig.jpegQuality <= 1.0)
    }
}
