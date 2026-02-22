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
    @StateObject private var devConsoleModel = DeveloperConsoleModel()

    @State private var transcript: String = ""
    @State private var isActive = false
    @State private var currentLOD: Int = 2
    @State private var connectionStatus: String = "Connecting..."
    @State private var isSafeMode = false
    @State private var whenIdleToolQueue: [String] = []
    @State private var showDebugOverlay = false
    @State private var showDevConsole = false
    @State private var showFaceRegistration = false
    @State private var showUserProfile = false
    @State private var isMuted = false
    @State private var isEmergencyPaused = false
    @State private var lastAgentTranscript = ""
    @State private var sessionResumptionHandle = UserDefaults.standard.string(
        forKey: SightLineConfig.sessionResumptionHandleDefaultsKey
    ) ?? ""

    /// Local TTS synthesizer for disconnection alerts (no network needed).
    private let localSynthesizer = AVSpeechSynthesizer()

    var body: some View {
        ZStack {
            // Background color shifts with LOD level (0.3s smooth transition per spec)
            lodBackgroundColor
                .ignoresSafeArea()
                .animation(.easeInOut(duration: 0.3), value: currentLOD)

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

                // Direct caregiver setup actions (non-debug flow).
                HStack(spacing: 12) {
                    quickActionButton(
                        title: "Profile",
                        systemImage: "person.crop.circle",
                        accessibilityLabel: "Edit user profile"
                    ) {
                        showUserProfile = true
                    }

                    quickActionButton(
                        title: "Familiar Faces",
                        systemImage: "person.2.crop.square.stack",
                        accessibilityLabel: "Upload family and friend photos"
                    ) {
                        showFaceRegistration = true
                    }
                }
                .padding(.horizontal, 24)
                .padding(.bottom, 24)
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

            // Developer Console gear icon (DEBUG builds only)
            #if DEBUG
            VStack {
                HStack {
                    Spacer()
                    Button(action: { showDevConsole = true }) {
                        Image(systemName: "gearshape.fill")
                            .font(.system(size: 16))
                            .foregroundColor(.white.opacity(0.3))
                            .padding(10)
                    }
                    .accessibilityLabel("Developer Console")
                }
                Spacer()
            }
            .padding(.top, 50)
            #endif
        }
        // MARK: - Gesture Recognizers
        // Triple tap: repeat last agent sentence
        .onTapGesture(count: 3) {
            handleTripleTap()
        }
        // Double tap: force interrupt agent speech
        .onTapGesture(count: 2) {
            handleDoubleTap()
        }
        // Single tap: toggle mute/unmute microphone
        .onTapGesture(count: 1) {
            handleSingleTap()
        }
        // Long press (3s): emergency pause
        .simultaneousGesture(
            LongPressGesture(minimumDuration: 3.0)
                .onEnded { _ in
                    handleLongPress()
                }
        )
        // Swipe up/down: LOD upgrade/downgrade
        .simultaneousGesture(
            DragGesture(minimumDistance: 50)
                .onEnded { value in
                    handleSwipe(translation: value.translation)
                }
        )
        .onAppear {
            #if DEBUG
            showDebugOverlay = true
            #endif
            HapticManager.shared.prepare()
            setupPipeline()
            devConsoleModel.bind(
                sensorManager: sensorManager,
                cameraManager: cameraManager,
                debugModel: debugModel,
                frameSelector: frameSelector
            )
        }
        .onDisappear {
            teardownPipeline()
        }
        // Shake detection via NotificationCenter
        .onReceive(NotificationCenter.default.publisher(for: .deviceDidShake)) { _ in
            handleShake()
        }
        .onReceive(NotificationCenter.default.publisher(for: .faceLibraryChanged)) { _ in
            webSocketManager.sendText("{\"type\":\"reload_face_library\"}")
            logger.info("Face library changed notification received, sending reload request")
        }
        .sheet(isPresented: $showDevConsole) {
            DeveloperConsoleView(
                model: devConsoleModel,
                webSocketManager: webSocketManager,
                cameraManager: cameraManager,
                telemetryAggregator: telemetryAggregator,
                showFaceRegistration: $showFaceRegistration,
                showUserProfile: $showUserProfile
            )
        }
        .sheet(isPresented: $showFaceRegistration) {
            FaceRegistrationView()
        }
        .sheet(isPresented: $showUserProfile) {
            UserProfileOnboardingView()
        }
        .accessibilityLabel("SightLine is \(isActive ? "active" : "connecting")")
    }

    // MARK: - Setup Action Buttons

    private func quickActionButton(
        title: String,
        systemImage: String,
        accessibilityLabel: String,
        action: @escaping () -> Void
    ) -> some View {
        Button(action: action) {
            Label(title, systemImage: systemImage)
                .font(.subheadline.weight(.semibold))
                .frame(maxWidth: .infinity)
                .padding(.vertical, 10)
                .background(Color.white.opacity(0.14))
                .foregroundStyle(.white)
                .clipShape(RoundedRectangle(cornerRadius: 10))
        }
        .accessibilityLabel(accessibilityLabel)
    }

    // MARK: - Gesture Handlers

    private func handleSingleTap() {
        isMuted.toggle()
        HapticManager.shared.singleTap()
        if isMuted {
            audioCapture.stopCapture()
        } else if !isEmergencyPaused {
            audioCapture.startCapture()
        }
        webSocketManager.sendText("{\"type\":\"gesture\",\"gesture\":\"mute_toggle\",\"muted\":\(isMuted)}")
        UIAccessibility.post(notification: .announcement, argument: isMuted ? "Microphone muted" : "Microphone unmuted")
        logger.info("Gesture: mute_toggle (isMuted=\(isMuted))")
    }

    private func handleDoubleTap() {
        HapticManager.shared.doubleTap()
        audioPlayback.stopImmediately()
        webSocketManager.sendText(UpstreamMessage.gesture(type: "interrupt").toJSON())
        UIAccessibility.post(notification: .announcement, argument: "Speech interrupted")
        logger.info("Gesture: interrupt")
    }

    private func handleTripleTap() {
        HapticManager.shared.tripleTap()
        webSocketManager.sendText(UpstreamMessage.gesture(type: "repeat_last").toJSON())
        UIAccessibility.post(notification: .announcement, argument: "Repeating last message")
        logger.info("Gesture: repeat_last")
    }

    private func handleLongPress() {
        isEmergencyPaused.toggle()
        HapticManager.shared.longPress()
        if isEmergencyPaused {
            audioCapture.stopCapture()
            audioPlayback.stopImmediately()
        } else {
            if !isMuted {
                audioCapture.startCapture()
            }
        }
        webSocketManager.sendText("{\"type\":\"gesture\",\"gesture\":\"emergency_pause\",\"paused\":\(isEmergencyPaused)}")
        UIAccessibility.post(notification: .announcement, argument: isEmergencyPaused ? "Emergency pause activated" : "Emergency pause released")
        logger.info("Gesture: emergency_pause (paused=\(isEmergencyPaused))")
    }

    private func handleSwipe(translation: CGSize) {
        // Require primarily vertical movement
        guard abs(translation.height) > abs(translation.width) else { return }
        HapticManager.shared.swipe()
        if translation.height < 0 {
            // Swipe up -> LOD upgrade
            webSocketManager.sendText(UpstreamMessage.gesture(type: "lod_up").toJSON())
            UIAccessibility.post(notification: .announcement, argument: "Detail level increasing")
            logger.info("Gesture: lod_up")
        } else {
            // Swipe down -> LOD downgrade
            webSocketManager.sendText(UpstreamMessage.gesture(type: "lod_down").toJSON())
            UIAccessibility.post(notification: .announcement, argument: "Detail level decreasing")
            logger.info("Gesture: lod_down")
        }
    }

    private func handleShake() {
        HapticManager.shared.sos()
        webSocketManager.sendText(UpstreamMessage.gesture(type: "sos").toJSON())
        UIAccessibility.post(notification: .announcement, argument: "SOS signal sent")
        logger.info("Gesture: sos (shake)")
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
            sessionId: SightLineConfig.defaultSessionId,
            resumeHandle: sessionResumptionHandle.isEmpty ? nil : sessionResumptionHandle
        )

        webSocketManager.onTextSent = { text in
            DispatchQueue.main.async {
                devConsoleModel.captureNetworkMessage(direction: "UP", payload: text)
            }
        }

        webSocketManager.onAudioReceived = { [weak audioPlayback] data in
            audioPlayback?.playAudioData(data)
        }

        webSocketManager.onTextReceived = { text in
            DispatchQueue.main.async {
                devConsoleModel.captureNetworkMessage(direction: "DOWN", payload: text)
            }
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
        cameraManager.onCameraFailure = { reason in
            webSocketManager.sendText("{\"type\":\"camera_failure\",\"error\":\"\(reason)\",\"reason\":\"\(reason)\"}")
        }
        cameraManager.frameSelector = frameSelector
        cameraManager.onFrameCaptured = { jpegData in
            guard frameSelector.isFrameDifferent(jpegData: jpegData) else {
                frameSelector.markFrameSkipped()
                logger.debug("Frame skipped (pixel-diff below threshold)")
                return
            }
            // Phase 5: Binary frame optimization — eliminates ~33% Base64 overhead
            let msg = UpstreamMessage.image(data: jpegData, mimeType: "image/jpeg")
            if let binaryFrame = msg.toBinary() {
                webSocketManager.sendBinary(binaryFrame)
            } else {
                webSocketManager.sendText(msg.toJSON())
            }
            frameSelector.markFrameSent()
        }

        // 4. Setup audio capture -> WebSocket + NoiseMeter RMS feed
        //    Phase 5: Binary frame optimization — raw PCM without Base64 encoding
        audioCapture.onAudioCaptured = { pcmData in
            let msg = UpstreamMessage.audio(data: pcmData)
            if let binaryFrame = msg.toBinary() {
                webSocketManager.sendBinary(binaryFrame)
            } else {
                webSocketManager.sendText(msg.toJSON())
            }
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
        case .faceLibraryReloaded(let count):
            DispatchQueue.main.async {
                let message = "Face library reloaded (\(count) faces)."
                transcript = message
                devConsoleModel.captureTranscript(text: message, role: "system")
            }
            logger.info("Face library reloaded: \(count)")
        case .faceLibraryCleared(let deletedCount):
            DispatchQueue.main.async {
                let message = "Face library cleared (\(deletedCount) deleted)."
                transcript = message
                devConsoleModel.captureTranscript(text: message, role: "system")
            }
            logger.info("Face library cleared: \(deletedCount)")
        case .error(let message):
            DispatchQueue.main.async {
                connectionStatus = "Server error"
                transcript = "Server error: \(message)"
                devConsoleModel.captureTranscript(text: "Server error: \(message)", role: "system")
                audioCapture.stopCapture()
                cameraManager.stopCapture()
            }
            logger.error("Server error message: \(message, privacy: .public)")
        case .transcript(let text, let role):
            DispatchQueue.main.async {
                transcript = text
                if role == "agent" {
                    lastAgentTranscript = text
                }
                devConsoleModel.captureTranscript(text: text, role: role)
                drainWhenIdleToolQueueIfPossible()
            }
        case .lodUpdate(let lod):
            DispatchQueue.main.async {
                let lodNames = [1: "Safety", 2: "Balanced", 3: "Detailed"]
                if lod != currentLOD {
                    UIAccessibility.post(notification: .announcement, argument: "Detail level \(lod): \(lodNames[lod] ?? "")")
                }
                currentLOD = lod
                frameSelector.updateLOD(lod)
                telemetryAggregator.updateLOD(lod)
                debugModel.currentLOD = lod
            }
        case .toolEvent(let tool, let behavior, let payload):
            let status = (payload["status"] as? String)?.lowercased() ?? ""
            if !status.isEmpty {
                DispatchQueue.main.async {
                    devConsoleModel.captureTranscript(text: "Tool \(tool): \(status)", role: "system")
                }
            }
            switch status {
            case "queued", "invoked", "completed":
                // Keep these in dev console only; avoid freezing user-facing transcript on tool progress text.
                return
            case "error", "unavailable":
                handleToolMessage(text: "Tool \(tool) is unavailable.", behavior: .INTERRUPT)
            default:
                handleToolMessage(
                    text: "Tool update: \(tool)",
                    behavior: behavior
                )
            }
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
        case .visionDebug(let data):
            DispatchQueue.main.async {
                devConsoleModel.captureVisionDebug(data)
            }
        case .ocrDebug(let data):
            DispatchQueue.main.async {
                devConsoleModel.captureOCRDebug(data)
            }
        case .faceDebug(let data):
            DispatchQueue.main.async {
                devConsoleModel.captureFaceDebug(data)
            }
        case .frameAck(let frameId, let queuedAgents):
            DispatchQueue.main.async {
                devConsoleModel.captureFrameAck(frameId: frameId, queuedAgents: queuedAgents)
            }
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
            let memoryTop3 = (data["memory_top3"] as? [String]) ?? []
            DispatchQueue.main.async {
                // SL-77: explicit debugLod -> memory top3 injection for overlay gate.
                debugModel.memoryTop3 = Array(memoryTop3.prefix(3))
                debugModel.updateFromLodDebug(data)
            }
        case .debugActivity(let data):
            DispatchQueue.main.async {
                debugModel.updateFromActivityDebug(data)
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
            DispatchQueue.main.async {
                connectionStatus = "Reconnecting..."
            }
            webSocketManager.reconnect(afterMs: retryMs)
        case .sessionResumption(let handle):
            guard !handle.isEmpty else { return }
            DispatchQueue.main.async {
                sessionResumptionHandle = handle
            }
            UserDefaults.standard.set(handle, forKey: SightLineConfig.sessionResumptionHandleDefaultsKey)
            logger.info("Session resumption handle updated: \(handle.prefix(20))...")
        case .unknown(let raw):
            logger.debug("Unknown downstream message: \(String(raw.prefix(200)), privacy: .public)")
            DispatchQueue.main.async {
                devConsoleModel.captureTranscript(
                    text: "Unknown downstream: \(String(raw.prefix(160)))",
                    role: "system"
                )
            }
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
        HapticManager.shared.safeMode()

        // Local TTS alert (no network dependency)
        let utterance = AVSpeechUtterance(string: "Connection lost. Safe mode active.")
        utterance.voice = AVSpeechSynthesisVoice(language: "en-US")
        utterance.rate = AVSpeechUtteranceDefaultSpeechRate
        localSynthesizer.speak(utterance)

        UIAccessibility.post(notification: .announcement, argument: "Connection lost. Safe mode active.")
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

        UIAccessibility.post(notification: .announcement, argument: "Connection restored.")
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
        transcript = whenIdleToolQueue.last ?? transcript
        whenIdleToolQueue.removeAll()
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

// MARK: - Shake Detection

extension Notification.Name {
    static let deviceDidShake = Notification.Name("deviceDidShake")
}

extension UIWindow {
    open override func motionEnded(_ motion: UIEvent.EventSubtype, with event: UIEvent?) {
        super.motionEnded(motion, with: event)
        if motion == .motionShake {
            NotificationCenter.default.post(name: .deviceDidShake, object: nil)
        }
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
}
