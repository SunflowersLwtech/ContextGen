//
//  ConfigTests.swift
//  SightLineTests
//
//  Tests for SightLineConfig constants and URL generation.
//

import Testing
import Foundation
@testable import SightLine

@Suite("SightLineConfig")
struct ConfigTests {

    @Test("wsURL generates correct WebSocket URL")
    func wsUrlGeneration() {
        let url = SightLineConfig.wsURL(userId: "user123", sessionId: "sess456")
        #expect(url.absoluteString.contains("/ws/user123/sess456"))
        #expect(url.scheme == "wss")
    }

    @Test("server base URL uses wss scheme")
    func serverBaseUrlScheme() {
        #expect(SightLineConfig.serverBaseURL.hasPrefix("wss://"))
    }

    @Test("audio input sample rate is 16kHz for Gemini")
    func audioInputSampleRate() {
        #expect(SightLineConfig.audioInputSampleRate == 16000)
    }

    @Test("audio output sample rate is 24kHz from Gemini")
    func audioOutputSampleRate() {
        #expect(SightLineConfig.audioOutputSampleRate == 24000)
    }

    @Test("audio buffer size gives 100ms at 16kHz")
    func audioBufferSize() {
        // 16000 samples/sec * 0.1 sec = 1600 samples
        #expect(SightLineConfig.audioBufferSize == 1600)
    }

    @Test("video frame dimensions are 768x768")
    func videoFrameDimensions() {
        #expect(SightLineConfig.videoFrameWidth == 768)
        #expect(SightLineConfig.videoFrameHeight == 768)
    }

    @Test("JPEG quality is 0.7")
    func jpegQuality() {
        #expect(SightLineConfig.jpegQuality == 0.7)
    }

    @Test("default frame interval is 1.0s")
    func defaultFrameInterval() {
        #expect(SightLineConfig.defaultFrameInterval == 1.0)
    }

    @Test("default user ID is set")
    func defaultUserId() {
        #expect(!SightLineConfig.defaultUserId.isEmpty)
    }

    @Test("default session ID is a UUID")
    func defaultSessionId() {
        #expect(!SightLineConfig.defaultSessionId.isEmpty)
        // UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        #expect(SightLineConfig.defaultSessionId.count == 36)
    }
}
