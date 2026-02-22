//
//  DeveloperConsoleView.swift
//  SightLine
//
//  Developer-only debug console for testing and demos.
//  Dark theme, monospace text, tab-based sections.
//  Reads state from existing managers — does NOT create duplicates.
//
//  Entry point: 4-finger tap on MainView, or gear icon in DEBUG builds.
//

import SwiftUI
import AVFoundation
import Combine
import os

private let logger = Logger(subsystem: "com.sightline.app", category: "DevConsole")

// MARK: - Developer Console Model

@MainActor
final class DeveloperConsoleModel: ObservableObject {
    struct TranscriptEntry: Identifiable {
        let id = UUID()
        let timestamp: Date
        let role: String
        let text: String
    }

    struct NetworkEvent: Identifiable {
        let id = UUID()
        let timestamp: Date
        let direction: String
        let payload: String
    }

    struct DebugBoundingBox: Identifiable {
        let id = UUID()
        let source: String
        let label: String
        let confidence: Double
        let normalizedRect: CGRect
    }

    @Published var transcripts: [TranscriptEntry] = []
    @Published var networkEvents: [NetworkEvent] = []

    // Sensor data
    @Published var motionState: String = "unknown"
    @Published var heartRate: Double?
    @Published var stepCadence: Double = 0
    @Published var noiseDb: Double = 50.0
    @Published var latitude: Double = 0
    @Published var longitude: Double = 0
    @Published var gpsAccuracy: Double = 0
    @Published var gpsSpeed: Double = 0
    @Published var heading: Double = 0
    @Published var timeContext: String = "unknown"

    // LOD
    @Published var currentLOD: Int = 2
    @Published var lodHistory: [(Date, Int, String)] = []
    @Published var triggeredRules: [String] = []

    // Connection
    @Published var isConnected: Bool = false
    @Published var isSafeMode: Bool = false

    // Sub-agent capabilities
    @Published var visionStatus: String = "ready"
    @Published var ocrStatus: String = "ready"
    @Published var faceStatus: String = "ready"

    // Memory
    @Published var memoryTop3: [String] = []
    @Published var memoryTop3Detailed: [[String: Any]] = []

    // Watch
    @Published var isWatchReachable: Bool = false
    @Published var isWatchMonitoring: Bool = false

    // Camera
    @Published var isCameraRunning: Bool = false
    @Published var visionBoxes: [DebugBoundingBox] = []
    @Published var ocrBoxes: [DebugBoundingBox] = []
    @Published var faceBoxes: [DebugBoundingBox] = []
    @Published var lastFrameAckId: Int = -1
    @Published var lastFrameQueuedAgents: [String] = []

    private var cancellables = Set<AnyCancellable>()

    /// Bind to existing managers via Combine. Called once from MainView.onAppear.
    /// Does NOT replace any callbacks — reads only via @Published subscriptions.
    func bind(
        sensorManager: SensorManager,
        cameraManager: CameraManager,
        debugModel: DebugOverlayModel,
        frameSelector: FrameSelector? = nil
    ) {
        // Frame rate -> DebugOverlay
        if let fs = frameSelector {
            fs.$effectiveFPS
                .receive(on: DispatchQueue.main)
                .sink { v in debugModel.frameRate = v }
                .store(in: &cancellables)
        }
        // DebugOverlayModel mirrors (already fed by MainView pipeline)
        debugModel.$currentLOD
            .receive(on: DispatchQueue.main)
            .sink { [weak self] lod in self?.currentLOD = lod }
            .store(in: &cancellables)

        debugModel.$isConnected
            .receive(on: DispatchQueue.main)
            .sink { [weak self] v in self?.isConnected = v }
            .store(in: &cancellables)

        debugModel.$isSafeMode
            .receive(on: DispatchQueue.main)
            .sink { [weak self] v in self?.isSafeMode = v }
            .store(in: &cancellables)

        debugModel.$visionStatus
            .receive(on: DispatchQueue.main)
            .sink { [weak self] v in self?.visionStatus = v }
            .store(in: &cancellables)

        debugModel.$ocrStatus
            .receive(on: DispatchQueue.main)
            .sink { [weak self] v in self?.ocrStatus = v }
            .store(in: &cancellables)

        debugModel.$faceStatus
            .receive(on: DispatchQueue.main)
            .sink { [weak self] v in self?.faceStatus = v }
            .store(in: &cancellables)

        debugModel.$memoryTop3
            .receive(on: DispatchQueue.main)
            .sink { [weak self] v in self?.memoryTop3 = v }
            .store(in: &cancellables)

        debugModel.$memoryTop3Detailed
            .receive(on: DispatchQueue.main)
            .sink { [weak self] v in self?.memoryTop3Detailed = v }
            .store(in: &cancellables)

        debugModel.$triggeredRules
            .receive(on: DispatchQueue.main)
            .sink { [weak self] v in self?.triggeredRules = v }
            .store(in: &cancellables)

        debugModel.$motionState
            .receive(on: DispatchQueue.main)
            .sink { [weak self] v in self?.motionState = v }
            .store(in: &cancellables)

        debugModel.$noiseDb
            .receive(on: DispatchQueue.main)
            .sink { [weak self] v in self?.noiseDb = v }
            .store(in: &cancellables)

        debugModel.$stepCadence
            .receive(on: DispatchQueue.main)
            .sink { [weak self] v in self?.stepCadence = v }
            .store(in: &cancellables)

        // GPS + heading from LocationManager
        sensorManager.locationManager.$latitude
            .receive(on: DispatchQueue.main)
            .sink { [weak self] v in
                self?.latitude = v
                debugModel.latitude = v
            }
            .store(in: &cancellables)

        sensorManager.locationManager.$longitude
            .receive(on: DispatchQueue.main)
            .sink { [weak self] v in
                self?.longitude = v
                debugModel.longitude = v
            }
            .store(in: &cancellables)

        sensorManager.locationManager.$accuracy
            .receive(on: DispatchQueue.main)
            .sink { [weak self] v in self?.gpsAccuracy = v }
            .store(in: &cancellables)

        sensorManager.locationManager.$speed
            .receive(on: DispatchQueue.main)
            .sink { [weak self] v in self?.gpsSpeed = v }
            .store(in: &cancellables)

        sensorManager.locationManager.$heading
            .receive(on: DispatchQueue.main)
            .sink { [weak self] v in self?.heading = v }
            .store(in: &cancellables)

        // Watch state
        sensorManager.watchReceiver.$isWatchReachable
            .receive(on: DispatchQueue.main)
            .sink { [weak self] v in self?.isWatchReachable = v }
            .store(in: &cancellables)

        sensorManager.watchReceiver.$isWatchMonitoring
            .receive(on: DispatchQueue.main)
            .sink { [weak self] v in self?.isWatchMonitoring = v }
            .store(in: &cancellables)

        // Camera running state
        cameraManager.$isRunning
            .receive(on: DispatchQueue.main)
            .sink { [weak self] v in self?.isCameraRunning = v }
            .store(in: &cancellables)

        // Time context
        sensorManager.$currentTelemetry
            .receive(on: DispatchQueue.main)
            .sink { [weak self] data in
                self?.timeContext = data.timeContext
                self?.heartRate = data.heartRate
                self?.motionState = data.motionState
                self?.stepCadence = Double(data.stepCadence)
                self?.noiseDb = data.ambientNoiseDb
            }
            .store(in: &cancellables)

        // LOD history tracking
        debugModel.$currentLOD
            .combineLatest(debugModel.$lodReason)
            .receive(on: DispatchQueue.main)
            .sink { [weak self] lod, reason in
                guard let self = self else { return }
                let last = self.lodHistory.last
                if last == nil || last?.1 != lod {
                    self.lodHistory.append((Date(), lod, reason))
                    if self.lodHistory.count > 50 {
                        self.lodHistory.removeFirst()
                    }
                }
            }
            .store(in: &cancellables)
    }

    /// Called from MainView.handleDownstreamMessage to capture transcripts
    /// without intercepting the WebSocket callback.
    func captureTranscript(text: String, role: String) {
        let entry = TranscriptEntry(timestamp: Date(), role: role, text: text)
        transcripts.append(entry)
        if transcripts.count > 200 {
            transcripts.removeFirst()
        }
    }

    func captureNetworkMessage(direction: String, payload: String) {
        let entry = NetworkEvent(timestamp: Date(), direction: direction, payload: payload)
        networkEvents.append(entry)
        if networkEvents.count > 400 {
            networkEvents.removeFirst()
        }
    }

    func captureVisionDebug(_ data: [String: Any]) {
        visionBoxes = extractBoxes(
            from: data,
            candidateKeys: ["bounding_boxes", "boxes", "objects"],
            source: "vision",
            defaultLabel: "object"
        )
    }

    func captureOCRDebug(_ data: [String: Any]) {
        ocrBoxes = extractBoxes(
            from: data,
            candidateKeys: ["text_regions", "regions", "boxes"],
            source: "ocr",
            defaultLabel: "text"
        )
    }

    func captureFaceDebug(_ data: [String: Any]) {
        faceBoxes = extractBoxes(
            from: data,
            candidateKeys: ["face_boxes", "faces", "detections"],
            source: "face",
            defaultLabel: "face"
        )
    }

    func captureFrameAck(frameId: Int, queuedAgents: [String]) {
        lastFrameAckId = frameId
        lastFrameQueuedAgents = queuedAgents
    }

    func clearNetworkEvents() {
        networkEvents.removeAll()
    }

    private func extractBoxes(
        from data: [String: Any],
        candidateKeys: [String],
        source: String,
        defaultLabel: String
    ) -> [DebugBoundingBox] {
        let candidates = candidatePayloadArray(from: data, keys: candidateKeys)
        return candidates.compactMap { item in
            guard let rect = parseNormalizedRect(from: item) else { return nil }
            let label = (item["label"] as? String)
                ?? (item["name"] as? String)
                ?? (item["person_name"] as? String)
                ?? defaultLabel
            let confidence = (item["confidence"] as? Double)
                ?? (item["score"] as? Double)
                ?? (item["similarity"] as? Double)
                ?? 0.0
            return DebugBoundingBox(
                source: source,
                label: label,
                confidence: confidence,
                normalizedRect: rect
            )
        }
    }

    private func candidatePayloadArray(from data: [String: Any], keys: [String]) -> [[String: Any]] {
        for key in keys {
            if let items = data[key] as? [[String: Any]] {
                return items
            }
        }
        if let nested = data["data"] as? [String: Any] {
            for key in keys {
                if let items = nested[key] as? [[String: Any]] {
                    return items
                }
            }
        }
        return []
    }

    private func parseNormalizedRect(from item: [String: Any]) -> CGRect? {
        if let box2D = item["box_2d"] as? [Double], box2D.count == 4 {
            let scale = (box2D.max() ?? 1.0) > 1.0 ? 1000.0 : 1.0
            return normalizedRect(
                xmin: box2D[1] / scale,
                ymin: box2D[0] / scale,
                xmax: box2D[3] / scale,
                ymax: box2D[2] / scale
            )
        }

        if let bbox = item["bbox"] as? [Double], bbox.count == 4 {
            let maxVal = bbox.max() ?? 1.0
            let scale = maxVal > 1.0 ? 768.0 : 1.0
            return normalizedRect(
                xmin: bbox[0] / scale,
                ymin: bbox[1] / scale,
                xmax: bbox[2] / scale,
                ymax: bbox[3] / scale
            )
        }

        return nil
    }

    private func normalizedRect(xmin: Double, ymin: Double, xmax: Double, ymax: Double) -> CGRect? {
        let clampedMinX = min(max(xmin, 0), 1)
        let clampedMinY = min(max(ymin, 0), 1)
        let clampedMaxX = min(max(xmax, 0), 1)
        let clampedMaxY = min(max(ymax, 0), 1)
        let width = clampedMaxX - clampedMinX
        let height = clampedMaxY - clampedMinY
        guard width > 0, height > 0 else { return nil }
        return CGRect(x: clampedMinX, y: clampedMinY, width: width, height: height)
    }
}

// MARK: - Camera Preview (UIViewRepresentable)

struct CameraPreviewView: UIViewRepresentable {
    let session: AVCaptureSession

    final class PreviewContainerView: UIView {
        override class var layerClass: AnyClass { AVCaptureVideoPreviewLayer.self }

        var previewLayer: AVCaptureVideoPreviewLayer {
            // Safe by construction: layerClass is AVCaptureVideoPreviewLayer.
            layer as! AVCaptureVideoPreviewLayer
        }

        override func layoutSubviews() {
            super.layoutSubviews()
            previewLayer.frame = bounds
        }
    }

    func makeUIView(context: Context) -> UIView {
        let view = PreviewContainerView(frame: .zero)
        view.backgroundColor = .black
        view.previewLayer.videoGravity = .resizeAspectFill
        view.previewLayer.session = session
        return view
    }

    func updateUIView(_ uiView: UIView, context: Context) {
        guard let previewView = uiView as? PreviewContainerView else { return }
        if previewView.previewLayer.session !== session {
            previewView.previewLayer.session = session
        }
        previewView.previewLayer.frame = previewView.bounds
    }
}

// MARK: - Developer Console View

struct DeveloperConsoleView: View {
    @ObservedObject var model: DeveloperConsoleModel
    @ObservedObject var webSocketManager: WebSocketManager
    @ObservedObject var cameraManager: CameraManager
    @ObservedObject var telemetryAggregator: TelemetryAggregator
    @Binding var showFaceRegistration: Bool
    @Binding var showUserProfile: Bool

    @State private var selectedTab = 0
    @Environment(\.dismiss) private var dismiss

    private let tabs = ["Log", "Context", "Status", "Controls", "Video", "Network"]

    var body: some View {
        VStack(spacing: 0) {
            header
            tabBar

            TabView(selection: $selectedTab) {
                conversationLogTab.tag(0)
                contextTab.tag(1)
                systemStatusTab.tag(2)
                controlsTab.tag(3)
                videoDebugTab.tag(4)
                networkTab.tag(5)
            }
            .tabViewStyle(.page(indexDisplayMode: .never))
        }
        .background(Color.black)
        .preferredColorScheme(.dark)
    }

    // MARK: - Header

    private var header: some View {
        HStack {
            Text("DEV CONSOLE")
                .font(.system(size: 14, weight: .bold, design: .monospaced))
                .foregroundColor(.green)

            Spacer()

            connectionBadge

            Spacer()

            Button(action: { dismiss() }) {
                Text("CLOSE")
                    .font(.system(size: 12, weight: .medium, design: .monospaced))
                    .foregroundColor(.red)
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(Color.black)
    }

    private var connectionBadge: some View {
        HStack(spacing: 4) {
            Circle()
                .fill(model.isSafeMode ? .red : (model.isConnected ? .green : .yellow))
                .frame(width: 6, height: 6)
            Text(model.isSafeMode ? "SAFE" : (model.isConnected ? "CONN" : "DISC"))
                .font(.system(size: 10, design: .monospaced))
                .foregroundColor(.white.opacity(0.7))
            Text("LOD \(model.currentLOD)")
                .font(.system(size: 10, weight: .bold, design: .monospaced))
                .foregroundColor(lodColor)
        }
    }

    // MARK: - Tab Bar

    private var tabBar: some View {
        HStack(spacing: 0) {
            ForEach(Array(tabs.enumerated()), id: \.offset) { index, title in
                Button(action: { withAnimation(.easeInOut(duration: 0.15)) { selectedTab = index } }) {
                    Text(title)
                        .font(.system(size: 11, weight: selectedTab == index ? .bold : .regular, design: .monospaced))
                        .foregroundColor(selectedTab == index ? .green : .white.opacity(0.5))
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 8)
                        .background(selectedTab == index ? Color.white.opacity(0.08) : Color.clear)
                }
            }
        }
        .background(Color.white.opacity(0.04))
    }

    // MARK: - Tab 0: Conversation Log

    private var conversationLogTab: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 4) {
                    ForEach(model.transcripts) { entry in
                        HStack(alignment: .top, spacing: 6) {
                            Text(formatTime(entry.timestamp))
                                .font(.system(size: 9, design: .monospaced))
                                .foregroundColor(.white.opacity(0.3))

                            Text(entry.role.uppercased())
                                .font(.system(size: 9, weight: .bold, design: .monospaced))
                                .foregroundColor(entry.role == "user" ? .cyan : .green)
                                .frame(width: 40, alignment: .leading)

                            Text(entry.text)
                                .font(.system(size: 11, design: .monospaced))
                                .foregroundColor(.white.opacity(0.85))
                                .fixedSize(horizontal: false, vertical: true)
                        }
                        .id(entry.id)
                    }
                }
                .padding(8)
            }
            .onChange(of: model.transcripts.count) { _, _ in
                if let last = model.transcripts.last {
                    withAnimation(.easeOut(duration: 0.2)) {
                        proxy.scrollTo(last.id, anchor: .bottom)
                    }
                }
            }
        }
    }

    // MARK: - Tab 1: Context Panel

    private var contextTab: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                sectionHeader("WATCH DATA")
                dataRow("Heart Rate", value: model.heartRate.map { String(format: "%.0f BPM", $0) } ?? "--")
                dataRow("Watch Reachable", value: model.isWatchReachable ? "YES" : "NO",
                         color: model.isWatchReachable ? .green : .red)
                dataRow("Watch Monitoring", value: model.isWatchMonitoring ? "ACTIVE" : "OFF",
                         color: model.isWatchMonitoring ? .green : .yellow)
                dataRow("Motion State", value: model.motionState)
                dataRow("Step Cadence", value: String(format: "%.0f", model.stepCadence))

                Divider().background(Color.white.opacity(0.1))

                sectionHeader("GPS")
                dataRow("Lat", value: String(format: "%.6f", model.latitude))
                dataRow("Lng", value: String(format: "%.6f", model.longitude))
                dataRow("Accuracy", value: String(format: "%.1f m", model.gpsAccuracy))
                dataRow("Speed", value: String(format: "%.1f m/s", model.gpsSpeed))

                Divider().background(Color.white.opacity(0.1))

                sectionHeader("ENVIRONMENT")
                dataRow("Noise", value: String(format: "%.0f dB", model.noiseDb))
                dataRow("Heading", value: String(format: "%.0f\u{00B0}", model.heading))
                dataRow("LOD", value: "\(model.currentLOD)", color: lodColor)
                dataRow("Time Context", value: model.timeContext)
            }
            .padding(8)
        }
    }

    // MARK: - Tab 2: System Status

    private var systemStatusTab: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                sectionHeader("CONNECTION")
                dataRow("WebSocket", value: model.isConnected ? "Connected" : "Disconnected",
                         color: model.isConnected ? .green : .red)
                dataRow("Safe Mode", value: model.isSafeMode ? "ACTIVE" : "OFF",
                         color: model.isSafeMode ? .red : .green)

                Divider().background(Color.white.opacity(0.1))

                sectionHeader("SUB-AGENTS")
                capabilityRow("Vision", status: model.visionStatus)
                capabilityRow("OCR", status: model.ocrStatus)
                capabilityRow("Face", status: model.faceStatus)

                Divider().background(Color.white.opacity(0.1))

                sectionHeader("MEMORY TOP 3")
                if model.memoryTop3Detailed.isEmpty && model.memoryTop3.isEmpty {
                    Text("No memories loaded")
                        .font(.system(size: 10, design: .monospaced))
                        .foregroundColor(.white.opacity(0.3))
                } else if !model.memoryTop3Detailed.isEmpty {
                    ForEach(Array(model.memoryTop3Detailed.prefix(3).enumerated()), id: \.offset) { idx, memory in
                        VStack(alignment: .leading, spacing: 2) {
                            HStack(spacing: 4) {
                                Text("\(idx + 1).")
                                    .font(.system(size: 10, weight: .bold, design: .monospaced))
                                    .foregroundColor(.green)
                                Text(memory["category"] as? String ?? "general")
                                    .font(.system(size: 8, weight: .bold, design: .monospaced))
                                    .foregroundColor(.cyan)
                                    .padding(.horizontal, 4)
                                    .background(Color.cyan.opacity(0.15))
                                    .cornerRadius(3)
                                Text(String(format: "imp=%.2f", memory["importance"] as? Double ?? 0.5))
                                    .font(.system(size: 8, design: .monospaced))
                                    .foregroundColor(.yellow)
                                Text(String(format: "score=%.3f", memory["score"] as? Double ?? 0))
                                    .font(.system(size: 8, design: .monospaced))
                                    .foregroundColor(.orange)
                            }
                            Text(memory["content"] as? String ?? "")
                                .font(.system(size: 10, design: .monospaced))
                                .foregroundColor(.white.opacity(0.7))
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                } else {
                    ForEach(Array(model.memoryTop3.enumerated()), id: \.offset) { idx, memory in
                        HStack(alignment: .top, spacing: 4) {
                            Text("\(idx + 1).")
                                .font(.system(size: 10, weight: .bold, design: .monospaced))
                                .foregroundColor(.green)
                            Text(memory)
                                .font(.system(size: 10, design: .monospaced))
                                .foregroundColor(.white.opacity(0.7))
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                }

                Divider().background(Color.white.opacity(0.1))

                sectionHeader("LOD HISTORY")
                ForEach(Array(model.lodHistory.suffix(10).reversed().enumerated()), id: \.offset) { _, entry in
                    HStack(spacing: 6) {
                        Text(formatTime(entry.0))
                            .font(.system(size: 9, design: .monospaced))
                            .foregroundColor(.white.opacity(0.3))
                        Text("LOD \(entry.1)")
                            .font(.system(size: 10, weight: .bold, design: .monospaced))
                            .foregroundColor(lodColorFor(entry.1))
                        Text(entry.2)
                            .font(.system(size: 9, design: .monospaced))
                            .foregroundColor(.white.opacity(0.5))
                            .lineLimit(1)
                    }
                }

                if !model.triggeredRules.isEmpty {
                    Divider().background(Color.white.opacity(0.1))
                    sectionHeader("TRIGGERED RULES")
                    ForEach(model.triggeredRules, id: \.self) { rule in
                        Text("- \(rule)")
                            .font(.system(size: 10, design: .monospaced))
                            .foregroundColor(.yellow)
                    }
                }
            }
            .padding(8)
        }
    }

    // MARK: - Tab 3: Debug Controls

    private var controlsTab: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                sectionHeader("FORCE LOD")
                HStack(spacing: 8) {
                    lodButton(1)
                    lodButton(2)
                    lodButton(3)
                }

                Divider().background(Color.white.opacity(0.1))

                sectionHeader("CAMERA")
                controlButton(
                    model.isCameraRunning ? "Stop Camera" : "Start Camera",
                    color: model.isCameraRunning ? .red : .green
                ) {
                    if model.isCameraRunning {
                        cameraManager.stopCapture()
                    } else {
                        cameraManager.startCapture()
                    }
                }

                Divider().background(Color.white.opacity(0.1))

                sectionHeader("TELEMETRY")
                controlButton("Send Connectivity Telemetry", color: .blue) {
                    telemetryAggregator.sendGesture("dev_console_test")
                }

                Divider().background(Color.white.opacity(0.1))

                sectionHeader("FACE LIBRARY")
                controlButton("Register Face", color: .blue) {
                    dismiss()
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
                        showFaceRegistration = true
                    }
                }
                controlButton("Clear Face Library", color: .red) {
                    webSocketManager.sendText("{\"type\":\"clear_face_library\"}")
                }

                Divider().background(Color.white.opacity(0.1))

                sectionHeader("USER PROFILE")
                controlButton("Edit User Profile", color: .blue) {
                    dismiss()
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
                        showUserProfile = true
                    }
                }

                Divider().background(Color.white.opacity(0.1))

                sectionHeader("WEBSOCKET")
                controlButton("Reconnect", color: .orange) {
                    let resumeHandle = UserDefaults.standard.string(
                        forKey: SightLineConfig.sessionResumptionHandleDefaultsKey
                    )
                    let url = SightLineConfig.wsURL(
                        userId: SightLineConfig.defaultUserId,
                        sessionId: SightLineConfig.defaultSessionId,
                        resumeHandle: resumeHandle
                    )
                    webSocketManager.disconnect()
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                        webSocketManager.connect(url: url)
                    }
                }

                Divider().background(Color.white.opacity(0.1))

                sectionHeader("SESSION")
                controlButton("Copy Session Info", color: .cyan) {
                    let info = """
                    Session: \(SightLineConfig.defaultSessionId)
                    User: \(SightLineConfig.defaultUserId)
                    Server: \(SightLineConfig.serverBaseURL)
                    LOD: \(model.currentLOD)
                    Connected: \(model.isConnected)
                    Safe Mode: \(model.isSafeMode)
                    """
                    UIPasteboard.general.string = info
                }

                controlButton("Clear Transcript Log", color: .yellow) {
                    model.transcripts.removeAll()
                }
            }
            .padding(8)
        }
    }

    // MARK: - Tab 4: Video Debug

    private var videoDebugTab: some View {
        VStack(alignment: .leading, spacing: 10) {
            sectionHeader("LIVE PREVIEW + OVERLAYS")

            if let session = cameraManager.previewSession {
                ZStack(alignment: .topLeading) {
                    CameraPreviewView(session: session)
                        .clipShape(.rect(cornerRadius: 10))
                        .overlay(
                            RoundedRectangle(cornerRadius: 10)
                                .stroke(Color.white.opacity(0.2), lineWidth: 1)
                        )

                    geometryOverlay(boxes: model.visionBoxes, color: .green)
                    geometryOverlay(boxes: model.ocrBoxes, color: .yellow)
                    geometryOverlay(boxes: model.faceBoxes, color: .cyan)
                }
                .frame(maxWidth: .infinity, maxHeight: 420)
            } else {
                VStack(spacing: 12) {
                    Text("Camera preview unavailable")
                        .font(.system(size: 12, design: .monospaced))
                        .foregroundColor(.white.opacity(0.7))
                    controlButton("Start Camera", color: .green) {
                        cameraManager.startCapture()
                    }
                }
                .frame(maxWidth: .infinity, minHeight: 220)
                .background(Color.white.opacity(0.04))
                .clipShape(.rect(cornerRadius: 10))
            }

            Divider().background(Color.white.opacity(0.1))

            dataRow("Vision Boxes", value: "\(model.visionBoxes.count)", color: .green)
            dataRow("OCR Boxes", value: "\(model.ocrBoxes.count)", color: .yellow)
            dataRow("Face Boxes", value: "\(model.faceBoxes.count)", color: .cyan)
            dataRow(
                "Camera Running",
                value: model.isCameraRunning ? "YES" : "NO",
                color: model.isCameraRunning ? .green : .red
            )
            dataRow(
                "Preview Session",
                value: previewSessionStatus,
                color: previewSessionColor
            )
            dataRow("Last Frame Ack", value: model.lastFrameAckId >= 0 ? "#\(model.lastFrameAckId)" : "--")
            dataRow(
                "Queued Agents",
                value: model.lastFrameQueuedAgents.isEmpty ? "--" : model.lastFrameQueuedAgents.joined(separator: ", ")
            )
        }
        .padding(8)
    }

    // MARK: - Tab 5: Network Debug

    private var networkTab: some View {
        VStack(spacing: 8) {
            HStack {
                sectionHeader("WEBSOCKET JSON FLOW")
                Spacer()
                controlButton("Clear", color: .yellow) {
                    model.clearNetworkEvents()
                }
                .frame(width: 96)
            }

            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 6) {
                        ForEach(model.networkEvents) { event in
                            VStack(alignment: .leading, spacing: 2) {
                                HStack(spacing: 6) {
                                    Text(formatTime(event.timestamp))
                                        .font(.system(size: 9, design: .monospaced))
                                        .foregroundColor(.white.opacity(0.35))
                                    Text(event.direction)
                                        .font(.system(size: 9, weight: .bold, design: .monospaced))
                                        .foregroundColor(event.direction == "UP" ? .cyan : .green)
                                }
                                Text(event.payload)
                                    .font(.system(size: 10, design: .monospaced))
                                    .foregroundColor(.white.opacity(0.78))
                                    .textSelection(.enabled)
                            }
                            .id(event.id)
                            .padding(.vertical, 4)
                            .padding(.horizontal, 6)
                            .background(Color.white.opacity(0.04))
                            .clipShape(.rect(cornerRadius: 6))
                        }
                    }
                    .padding(.horizontal, 2)
                    .padding(.bottom, 8)
                }
                .onChange(of: model.networkEvents.count) { _, _ in
                    if let last = model.networkEvents.last {
                        withAnimation(.easeOut(duration: 0.15)) {
                            proxy.scrollTo(last.id, anchor: .bottom)
                        }
                    }
                }
            }
        }
        .padding(8)
    }

    // MARK: - Subviews

    private func sectionHeader(_ title: String) -> some View {
        Text(title)
            .font(.system(size: 10, weight: .bold, design: .monospaced))
            .foregroundColor(.white.opacity(0.4))
            .tracking(1)
    }

    private func dataRow(_ label: String, value: String, color: Color = .green) -> some View {
        HStack {
            Text(label)
                .font(.system(size: 11, design: .monospaced))
                .foregroundColor(.white.opacity(0.6))
            Spacer()
            Text(value)
                .font(.system(size: 11, weight: .medium, design: .monospaced))
                .foregroundColor(color)
        }
    }

    private func capabilityRow(_ name: String, status: String) -> some View {
        HStack(spacing: 6) {
            Circle()
                .fill(status == "ready" ? Color.green : Color.red)
                .frame(width: 8, height: 8)
            Text(name)
                .font(.system(size: 11, design: .monospaced))
                .foregroundColor(.white.opacity(0.7))
            Spacer()
            Text(status.uppercased())
                .font(.system(size: 10, weight: .bold, design: .monospaced))
                .foregroundColor(status == "ready" ? .green : .red)
        }
    }

    private func geometryOverlay(boxes: [DeveloperConsoleModel.DebugBoundingBox], color: Color) -> some View {
        GeometryReader { geometry in
            ForEach(Array(boxes.enumerated()), id: \.element.id) { _, box in
                let rect = box.normalizedRect
                let x = rect.minX * geometry.size.width
                let y = rect.minY * geometry.size.height
                let width = rect.width * geometry.size.width
                let height = rect.height * geometry.size.height
                let labelText = box.confidence > 0
                    ? "\(box.label) \(String(format: "%.2f", box.confidence))"
                    : box.label

                ZStack(alignment: .topLeading) {
                    RoundedRectangle(cornerRadius: 4)
                        .stroke(color, lineWidth: 2)
                        .frame(width: max(width, 2), height: max(height, 2))

                    Text(labelText)
                        .font(.system(size: 9, weight: .bold, design: .monospaced))
                        .foregroundStyle(.black)
                        .padding(.horizontal, 4)
                        .padding(.vertical, 2)
                        .background(color.opacity(0.9))
                        .clipShape(.rect(cornerRadius: 3))
                        .offset(x: 0, y: -14)
                }
                .position(x: x + (width / 2), y: y + (height / 2))
            }
        }
        .allowsHitTesting(false)
    }

    private func lodButton(_ lod: Int) -> some View {
        Button(action: {
            webSocketManager.sendText(UpstreamMessage.gesture(type: "force_lod_\(lod)").toJSON())
        }) {
            Text("LOD \(lod)")
                .font(.system(size: 12, weight: .bold, design: .monospaced))
                .foregroundColor(.white)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 10)
                .background(lodColorFor(lod).opacity(model.currentLOD == lod ? 1.0 : 0.4))
                .cornerRadius(6)
        }
    }

    private func controlButton(_ title: String, color: Color, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(title)
                .font(.system(size: 12, weight: .medium, design: .monospaced))
                .foregroundColor(.white)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 10)
                .background(color.opacity(0.3))
                .overlay(
                    RoundedRectangle(cornerRadius: 6)
                        .stroke(color.opacity(0.6), lineWidth: 1)
                )
                .cornerRadius(6)
        }
    }

    // MARK: - Helpers

    private var lodColor: Color { lodColorFor(model.currentLOD) }

    private var previewSessionStatus: String {
        guard let session = cameraManager.previewSession else { return "nil" }
        return session.isRunning ? "running" : "stopped"
    }

    private var previewSessionColor: Color {
        switch previewSessionStatus {
        case "running":
            return .green
        case "stopped":
            return .yellow
        default:
            return .red
        }
    }

    private func lodColorFor(_ lod: Int) -> Color {
        switch lod {
        case 1: return .red
        case 2: return .orange
        case 3: return .green
        default: return .gray
        }
    }

    private func formatTime(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "HH:mm:ss"
        return formatter.string(from: date)
    }
}
