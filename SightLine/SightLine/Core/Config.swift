//
//  Config.swift
//  SightLine
//
//  Central configuration for server URLs, audio/video parameters, and defaults.
//

import Foundation

enum SightLineConfig {
    // Server URL - change for Cloud Run deployment
    static let serverBaseURL = "wss://localhost:8080"

    // WebSocket path template
    static func wsURL(userId: String, sessionId: String) -> URL {
        URL(string: "\(serverBaseURL)/ws/\(userId)/\(sessionId)")!
    }

    // Audio
    static let audioInputSampleRate: Double = 16000   // Gemini requires 16kHz
    static let audioOutputSampleRate: Double = 24000   // Gemini outputs 24kHz
    static let audioBufferSize: UInt32 = 1600          // 100ms at 16kHz

    // Video
    static let videoFrameWidth: Int = 768
    static let videoFrameHeight: Int = 768
    static let jpegQuality: CGFloat = 0.7
    static let defaultFrameInterval: TimeInterval = 1.0  // 1 FPS

    // User defaults
    static let defaultUserId = "default_user"
    static let defaultSessionId: String = UUID().uuidString
}
