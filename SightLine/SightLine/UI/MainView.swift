//
//  MainView.swift
//  SightLine
//
//  Full-screen dark UI with minimal visual elements.
//  Background color shifts with LOD level. A breathing circle indicates active state.
//  Designed for accessibility - all elements have VoiceOver labels.
//
//  Phase 2: Integrated SensorManager, TelemetryAggregator, and disconnection degradation.
//

import SwiftUI
import AVFoundation
import os

private let logger = Logger(subsystem: "com.sightline.app", category: "MainView")

struct MainView: View {
    @StateObject private var webSocketManager = WebSocketManager()
    @StateObject private var audioCapture = AudioCaptureManager()
    @StateObject private var audioPlayback = AudioPlaybackManager()
    @StateObject private var cameraManager = CameraManager()
    @StateObject private var frameSelector = FrameSelector()
    @StateObject private var sensorManager = SensorManager()
    @StateObject private var telemetryAggregator = TelemetryAggregator()

    @State private var transcript: String = ""
    @State private var isActive = false
    @State private var currentLOD: Int = 2
    @State private var connectionStatus: String = "Connecting..."
    @State private var isSafeMode = false

    /// Local TTS synthesizer for disconnection alerts (no network needed).
    private let localSynthesizer = AVSpeechSynthesizer()

    var body: some View {
        ZStack {
            // Background color shifts with LOD level
            lodBackgroundColor
                .ignoresSafeArea()

            VStack {
                Spacer()

                // Breathing indicator - pulses when active
                Circle()
                    .fill(isActive ? Color.green.opacity(0.6) : Color.gray.opacity(0.3))
                    .frame(width: 80, height: 80)
                    .scaleEffect(isActive ? 1.1 : 0.9)
                    .animation(
                        .easeInOut(duration: 2).repeatForever(autoreverses: true),
                        value: isActive
                    )
                    .accessibilityHidden(true)

                Spacer()

                // Connection status
                Text(connectionStatus)
                    .font(.caption)
                    .foregroundColor(isSafeMode ? .red.opacity(0.7) : .white.opacity(0.5))
                    .padding(.bottom, 8)
                    .accessibilityLabel(connectionStatus)

                // Latest transcript from agent or user
                if !transcript.isEmpty {
                    Text(transcript)
                        .font(.body)
                        .foregroundColor(.white.opacity(0.8))
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 24)
                        .padding(.bottom, 32)
                        .lineLimit(3)
                        .accessibilityLabel("Last message: \(transcript)")
                }
            }
        }
        .onAppear {
            setupPipeline()
        }
        .onDisappear {
            teardownPipeline()
        }
        .accessibilityLabel("SightLine is \(isActive ? "active" : "connecting")")
    }

    // MARK: - LOD Background Colors

    private var lodBackgroundColor: Color {
        switch currentLOD {
        case 1: return Color(red: 0.05, green: 0.05, blue: 0.15)  // Deep blue - silent
        case 2: return Color(red: 0.15, green: 0.10, blue: 0.05)  // Warm orange tint
        case 3: return Color(red: 0.10, green: 0.10, blue: 0.10)  // Soft grey
        default: return .black
        }
    }

    // MARK: - Pipeline Setup

    private func setupPipeline() {
        // 1. Setup audio playback engine
        audioPlayback.setup()

        // 2. Build WebSocket URL and wire callbacks
        let url = SightLineConfig.wsURL(
            userId: SightLineConfig.defaultUserId,
            sessionId: SightLineConfig.defaultSessionId
        )

        webSocketManager.onAudioReceived = { [weak audioPlayback] data in
            audioPlayback?.playAudioData(data)
        }

        webSocketManager.onTextReceived = { text in
            if let msg = DownstreamMessage.parse(text: text) {
                handleDownstreamMessage(msg)
            }
        }

        webSocketManager.onConnectionStateChanged = { connected in
            DispatchQueue.main.async {
                isActive = connected
                if connected {
                    connectionStatus = "Connected"
                } else {
                    audioCapture.stopCapture()
                    cameraManager.stopCapture()
                }
            }
        }

        // SL-38: Disconnection degradation callbacks
        webSocketManager.onDisconnectionDegraded = {
            DispatchQueue.main.async {
                enterSafeMode()
            }
        }

        webSocketManager.onConnectionRestored = {
            DispatchQueue.main.async {
                exitSafeMode()
            }
        }

        webSocketManager.connect(url: url)

        // 3. Setup camera with LOD-based frame selector
        cameraManager.frameSelector = frameSelector
        cameraManager.onFrameCaptured = { jpegData in
            let msg = UpstreamMessage.image(data: jpegData, mimeType: "image/jpeg")
            webSocketManager.sendText(msg.toJSON())
        }

        // 4. Setup audio capture -> WebSocket + NoiseMeter RMS feed
        audioCapture.onAudioCaptured = { pcmData in
            let msg = UpstreamMessage.audio(data: pcmData)
            webSocketManager.sendText(msg.toJSON())
        }
        audioCapture.onAudioLevelUpdate = { rms in
            sensorManager.processAudioRMS(rms)
        }

        // 5. Start sensor collection
        sensorManager.startAll()

        // 6. Start telemetry aggregator
        telemetryAggregator.start(sensorManager: sensorManager, webSocket: webSocketManager)
    }

    private func startMediaCapture() {
        audioCapture.startCapture()
        cameraManager.startCapture()
    }

    private func handleDownstreamMessage(_ msg: DownstreamMessage) {
        switch msg {
        case .sessionReady:
            logger.info("Session ready, starting media capture")
            DispatchQueue.main.async {
                startMediaCapture()
            }
        case .transcript(let text, _):
            DispatchQueue.main.async {
                transcript = text
            }
        case .lodUpdate(let lod):
            DispatchQueue.main.async {
                currentLOD = lod
                frameSelector.updateLOD(lod)
                telemetryAggregator.updateLOD(lod)
            }
        case .goAway(let retryMs):
            logger.info("GoAway received, reconnecting in \(retryMs)ms")
        case .sessionResumption(let handle):
            logger.info("Session resumption handle: \(handle.prefix(20))...")
        default:
            break
        }
    }

    // MARK: - Safe Mode (SL-38)

    private func enterSafeMode() {
        isSafeMode = true
        currentLOD = 1
        connectionStatus = "Safe Mode - Reconnecting..."
        telemetryAggregator.pause()

        // Local TTS alert (no network dependency)
        let utterance = AVSpeechUtterance(string: "Connection lost. Safe mode active.")
        utterance.voice = AVSpeechSynthesisVoice(language: "en-US")
        utterance.rate = AVSpeechUtteranceDefaultSpeechRate
        localSynthesizer.speak(utterance)

        logger.warning("Entered safe mode (LOD 1)")
    }

    private func exitSafeMode() {
        isSafeMode = false
        connectionStatus = "Connected"
        telemetryAggregator.resume()

        // Local TTS confirmation
        let utterance = AVSpeechUtterance(string: "Connection restored.")
        utterance.voice = AVSpeechSynthesisVoice(language: "en-US")
        utterance.rate = AVSpeechUtteranceDefaultSpeechRate
        localSynthesizer.speak(utterance)

        logger.info("Exited safe mode")
    }

    // MARK: - Teardown

    private func teardownPipeline() {
        telemetryAggregator.stop()
        sensorManager.stopAll()
        audioCapture.stopCapture()
        cameraManager.stopCapture()
        audioPlayback.teardown()
        webSocketManager.disconnect()
    }
}
