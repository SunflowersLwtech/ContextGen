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

    @Published var transcripts: [TranscriptEntry] = []

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

    // Watch
    @Published var isWatchReachable: Bool = false
    @Published var isWatchMonitoring: Bool = false

    // Camera
    @Published var isCameraRunning: Bool = false

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

        debugModel.$triggeredRules
            .receive(on: DispatchQueue.main)
            .sink { [weak self] v in self?.triggeredRules = v }
            .store(in: &cancellables)

        debugModel.$motionState
            .receive(on: DispatchQueue.main)
            .sink { [weak self] v in self?.motionState = v }
            .store(in: &cancellables)

        debugModel.$heartRate
            .receive(on: DispatchQueue.main)
            .sink { [weak self] v in self?.heartRate = v }
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
            .sink { [weak self] data in self?.timeContext = data.timeContext }
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
}

// MARK: - Camera Preview (UIViewRepresentable)

struct CameraPreviewView: UIViewRepresentable {
    let session: AVCaptureSession

    func makeUIView(context: Context) -> UIView {
        let view = UIView(frame: .zero)
        let previewLayer = AVCaptureVideoPreviewLayer(session: session)
        previewLayer.videoGravity = .resizeAspectFill
        view.layer.addSublayer(previewLayer)
        return view
    }

    func updateUIView(_ uiView: UIView, context: Context) {
        if let previewLayer = uiView.layer.sublayers?.first as? AVCaptureVideoPreviewLayer {
            previewLayer.frame = uiView.bounds
        }
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

    private let tabs = ["Log", "Context", "Status", "Controls"]

    var body: some View {
        VStack(spacing: 0) {
            header
            tabBar

            TabView(selection: $selectedTab) {
                conversationLogTab.tag(0)
                contextTab.tag(1)
                systemStatusTab.tag(2)
                controlsTab.tag(3)
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
                if model.memoryTop3.isEmpty {
                    Text("No memories loaded")
                        .font(.system(size: 10, design: .monospaced))
                        .foregroundColor(.white.opacity(0.3))
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
                controlButton("Send Test Telemetry", color: .blue) {
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
                    let url = SightLineConfig.wsURL(
                        userId: SightLineConfig.defaultUserId,
                        sessionId: SightLineConfig.defaultSessionId
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

    private func lodButton(_ lod: Int) -> some View {
        Button(action: {
            telemetryAggregator.sendGesture("force_lod_\(lod)")
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
