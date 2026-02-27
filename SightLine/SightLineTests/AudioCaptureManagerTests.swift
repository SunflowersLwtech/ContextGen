//
//  AudioCaptureManagerTests.swift
//  SightLineTests
//
//  Smoke tests for the audio capture pipeline.
//

import Testing
import Foundation
@testable import SightLine

@Suite("Audio Capture Manager Tests")
struct AudioCaptureManagerTests {

    @Test("AudioCaptureManager initializes without error")
    func initialization() {
        let manager = AudioCaptureManager()
        // Manager should be creatable
        #expect(manager != nil)
    }

    @Test("AudioCaptureManager exposes audio callback")
    func audioCallback() {
        let manager = AudioCaptureManager()
        manager.onAudioCaptured = { data in
            // Verify callback is settable
        }
    }

    @Test("AudioCaptureManager stop without start does not crash")
    func stopWithoutStart() {
        let manager = AudioCaptureManager()
        manager.stopCapture()
        // No crash = pass
    }

    @Test("AudioPlaybackManager setup and teardown lifecycle")
    func playbackLifecycle() {
        let manager = AudioPlaybackManager()
        manager.setup()
        manager.teardown()
        // No crash = pass
    }

    @Test("SharedAudioEngine singleton exists and starts not running")
    func sharedAudioEngineInit() {
        let engine = SharedAudioEngine.shared
        // Before setup(), engine should not be running
        #expect(engine.isRunning == false)
        #expect(engine.isVoiceProcessingEnabled == false)
    }

    @Test("SharedAudioEngine teardown without setup does not crash")
    func sharedAudioEngineTeardownSafe() {
        SharedAudioEngine.shared.teardown()
        // No crash = pass
    }
}
