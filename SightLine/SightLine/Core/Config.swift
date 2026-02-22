//
//  Config.swift
//  SightLine
//
//  Central configuration for server URLs, audio/video parameters, and defaults.
//

import Foundation

enum SightLineConfig {
    // Server URL - change for Cloud Run deployment
    static let serverBaseURL = "wss://sightline-backend-200455604992.us-central1.run.app"

    // WebSocket path template
    static func wsURL(userId: String, sessionId: String) -> URL {
        URL(string: "\(serverBaseURL)/ws/\(userId)/\(sessionId)")!
    }

    // Audio
    static let audioInputSampleRate: Double = 16000   // Gemini requires 16kHz
    static let audioOutputSampleRate: Double = 24000   // Gemini outputs 24kHz
    static let audioBufferSize: UInt32 = 1600          // 100ms at 16kHz
    static let audioJitterBufferChunks: Int = 2        // ~60-90ms depending server chunk size
    static let audioJitterMaxWait: TimeInterval = 0.09 // 90ms fallback for short utterances

    // Video
    static let videoFrameWidth: Int = 768
    static let videoFrameHeight: Int = 768
    static let jpegQuality: CGFloat = 0.7
    static let defaultFrameInterval: TimeInterval = 1.0  // 1 FPS

    // User defaults
    static let defaultUserId = "default_user"
    static let defaultSessionId: String = UUID().uuidString
}
