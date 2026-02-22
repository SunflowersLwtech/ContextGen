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
import Combine
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
    @StateObject private var mediaPermissionGate = MediaPermissionGate()
    @StateObject private var debugModel = DebugOverlayModel()

    @State private var transcript: String = ""
    @State private var isActive = false
    @State private var currentLOD: Int = 2
    @State private var connectionStatus: String = "Connecting..."
    @State private var isSafeMode = false
    @State private var whenIdleToolQueue: [String] = []
    @State private var showDebugOverlay = false

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

            // Debug overlay (SL-77) - top-aligned
            if showDebugOverlay {
                VStack {
                    DebugOverlay(model: debugModel)
                    Spacer()
                }
                .padding(.top, 60)
                .transition(.opacity)
            }
        }
        .onTapGesture(count: 3) {
            withAnimation(.easeInOut(duration: 0.2)) {
                showDebugOverlay.toggle()
            }
        }
        .onAppear {
            #if DEBUG
            showDebugOverlay = true
            #endif
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
        // Prompt camera/mic early so the app does not look "stuck" before session_ready.
        Task {
            let granted = await mediaPermissionGate.preflightMediaPermissions()
            if !granted {
                await MainActor.run {
                    connectionStatus = "Camera/Microphone permission required"
                }
                logger.error("Media permissions missing at startup")
            }
        }

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
                debugModel.isConnected = connected
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

        // 3. Setup camera with LOD-based frame selector + pixel-diff dedup (SL-75)
        cameraManager.frameSelector = frameSelector
        cameraManager.onFrameCaptured = { jpegData in
            guard frameSelector.isFrameDifferent(jpegData: jpegData) else {
                logger.debug("Frame skipped (pixel-diff below threshold)")
                return
            }
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
        Task {
            let granted = await mediaPermissionGate.preflightMediaPermissions()
            guard granted else {
                await MainActor.run {
                    connectionStatus = "Enable camera and microphone in Settings"
                    transcript = "Please enable camera and microphone permissions."
                }
                logger.error("Media capture blocked: camera/microphone permission denied")
                return
            }

            await MainActor.run {
                audioCapture.startCapture()
                cameraManager.startCapture()
            }
        }
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
                drainWhenIdleToolQueueIfPossible()
            }
        case .lodUpdate(let lod):
            DispatchQueue.main.async {
                currentLOD = lod
                frameSelector.updateLOD(lod)
                telemetryAggregator.updateLOD(lod)
                debugModel.currentLOD = lod
            }
        case .toolEvent(let tool, let behavior, _):
            handleToolMessage(
                text: "Tool update: \(tool)",
                behavior: behavior
            )
        case .visionResult(let summary, let behavior):
            DispatchQueue.main.async { debugModel.markCapabilityReady("vision") }
            handleToolMessage(
                text: summary.isEmpty ? "Vision analysis updated." : summary,
                behavior: behavior
            )
        case .ocrResult(let summary, let behavior):
            DispatchQueue.main.async { debugModel.markCapabilityReady("ocr") }
            handleToolMessage(
                text: summary.isEmpty ? "OCR result received." : summary,
                behavior: behavior
            )
        case .navigationResult(let summary, let behavior):
            handleToolMessage(
                text: summary.isEmpty ? "Navigation result received." : summary,
                behavior: behavior
            )
        case .searchResult(let summary, let behavior):
            handleToolMessage(
                text: summary.isEmpty ? "Search result received." : summary,
                behavior: behavior
            )
        case .personIdentified(let name, let behavior):
            DispatchQueue.main.async { debugModel.markCapabilityReady("face") }
            handleIdentityMessage(name: name, matched: true, behavior: behavior)
        case .identityUpdate(let name, let matched, let behavior):
            DispatchQueue.main.async { debugModel.markCapabilityReady("face") }
            handleIdentityMessage(name: name, matched: matched, behavior: behavior)
        case .capabilityDegraded(let capability, let reason, _):
            DispatchQueue.main.async {
                debugModel.markCapabilityDegraded(capability)
            }
            logger.warning("Capability degraded: \(capability, privacy: .public) - \(reason, privacy: .public)")
        case .debugLod(let data):
            DispatchQueue.main.async {
                debugModel.updateFromLodDebug(data)
            }
        case .panic(let message):
            DispatchQueue.main.async {
                currentLOD = 1
                debugModel.currentLOD = 1
                transcript = message
            }
            logger.warning("PANIC: \(message, privacy: .public)")
        case .interrupted:
            logger.info("Model output interrupted")
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
        debugModel.isSafeMode = true
        debugModel.currentLOD = 1
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
        debugModel.isSafeMode = false
        telemetryAggregator.resume()

        // Local TTS confirmation
        let utterance = AVSpeechUtterance(string: "Connection restored.")
        utterance.voice = AVSpeechSynthesisVoice(language: "en-US")
        utterance.rate = AVSpeechUtteranceDefaultSpeechRate
        localSynthesizer.speak(utterance)

        logger.info("Exited safe mode")
    }

    // MARK: - Tool Behavior Routing (SL-55)

    private func handleToolMessage(text: String, behavior: ToolBehaviorMode) {
        DispatchQueue.main.async {
            switch behavior {
            case .INTERRUPT:
                // INTERRUPT must stop ongoing playback immediately.
                audioPlayback.stopImmediately()
                transcript = text
            case .WHEN_IDLE:
                // WHEN_IDLE respects current playback state and queues updates.
                if audioPlayback.isPlaying {
                    whenIdleToolQueue.append(text)
                } else {
                    transcript = text
                }
            case .SILENT:
                logger.debug("SILENT tool update received")
            }
            drainWhenIdleToolQueueIfPossible()
        }
    }

    private func handleIdentityMessage(name: String, matched: Bool, behavior: ToolBehaviorMode) {
        let personText = matched ? "Person identified: \(name)" : "Identity update available."
        if behavior == .SILENT {
            // identify_person must support SILENT path and avoid hard interruption.
            logger.debug("identity SILENT update for \(name, privacy: .public)")
            return
        }
        handleToolMessage(text: personText, behavior: behavior)
    }

    private func drainWhenIdleToolQueueIfPossible() {
        guard !audioPlayback.isPlaying else { return }
        guard !whenIdleToolQueue.isEmpty else { return }
        transcript = whenIdleToolQueue.removeFirst()
    }

    // MARK: - Face Privacy Action (SL-59)

    private func clearFaceLibrary() {
        webSocketManager.sendText("{\"type\":\"clear_face_library\"}")
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

@MainActor
private final class MediaPermissionGate: ObservableObject {
    @Published private(set) var hasMediaPermissions = false

    func preflightMediaPermissions() async -> Bool {
        let cameraGranted = await ensureCameraPermission()
        let microphoneGranted = await ensureMicrophonePermission()
        hasMediaPermissions = cameraGranted && microphoneGranted
        return hasMediaPermissions
    }

    private func ensureCameraPermission() async -> Bool {
        switch AVCaptureDevice.authorizationStatus(for: .video) {
        case .authorized:
            return true
        case .notDetermined:
            return await withCheckedContinuation { continuation in
                AVCaptureDevice.requestAccess(for: .video) { granted in
                    continuation.resume(returning: granted)
                }
            }
        case .denied, .restricted:
            return false
        @unknown default:
            return false
        }
    }

    private func ensureMicrophonePermission() async -> Bool {
        if #available(iOS 17.0, *) {
            switch AVAudioApplication.shared.recordPermission {
            case .granted:
                return true
            case .undetermined:
                return await withCheckedContinuation { continuation in
                    AVAudioApplication.requestRecordPermission { granted in
                        continuation.resume(returning: granted)
                    }
                }
            case .denied:
                return false
            @unknown default:
                return false
            }
        }

        let session = AVAudioSession.sharedInstance()
        switch session.recordPermission {
        case .granted:
            return true
        case .undetermined:
            return await withCheckedContinuation { continuation in
                session.requestRecordPermission { granted in
                    continuation.resume(returning: granted)
                }
            }
        case .denied:
            return false
        @unknown default:
            return false
        }
    }
}
