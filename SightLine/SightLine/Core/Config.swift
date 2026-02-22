//
//  Config.swift
//  SightLine
//
//  Central configuration for server URLs, audio/video parameters, and defaults.
//

import Foundation

enum SightLineConfig {
    // Server URL - change for Cloud Run deployment
    static let serverBaseURL = "wss://sightline-backend-kp47ssyf4q-uc.a.run.app"
    static let sessionResumptionHandleDefaultsKey = "sightline.session_resumption_handle"

    // WebSocket path template
    static func wsURL(userId: String, sessionId: String, resumeHandle: String? = nil) -> URL {
        var components = URLComponents(string: "\(serverBaseURL)/ws/\(userId)/\(sessionId)")!
        if let resumeHandle, !resumeHandle.isEmpty {
            components.queryItems = [URLQueryItem(name: "resume_handle", value: resumeHandle)]
        }
        return components.url!
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
    static let defaultSessionId: String = UUID().uuidString.lowercased()
}
