//
//  WebSocketManager.swift
//  SightLine
//
//  WebSocket client using Apple's Network framework (NWConnection).
//  Handles connection lifecycle, automatic reconnection with exponential backoff,
//  and network path monitoring for seamless WiFi/Cellular transitions.
//

import Network
import Foundation
import Combine
import UIKit

class WebSocketManager: ObservableObject {
    @Published var isConnected = false

    private var connection: NWConnection?
    private let queue = DispatchQueue(label: "com.sightline.websocket", qos: .userInitiated)
    private var reconnectDelay: TimeInterval = 1.0
    private let maxReconnectDelay: TimeInterval = 30.0
    private var serverURL: URL?
    private var intentionalDisconnect = false
    private var pathMonitor: NWPathMonitor?

    // Callbacks
    var onAudioReceived: ((Data) -> Void)?
    var onTextReceived: ((String) -> Void)?
    var onConnectionStateChanged: ((Bool) -> Void)?

    func connect(url: URL) {
        serverURL = url
        intentionalDisconnect = false
        reconnectDelay = 1.0
        startConnection(url: url)
        startPathMonitor()
    }

    func disconnect() {
        intentionalDisconnect = true
        pathMonitor?.cancel()
        pathMonitor = nil
        connection?.cancel()
        connection = nil
        updateConnectionState(false)
    }

    func sendText(_ text: String) {
        guard let data = text.data(using: .utf8) else { return }
        let metadata = NWProtocolWebSocket.Metadata(opcode: .text)
        let context = NWConnection.ContentContext(identifier: "textMessage",
                                                  metadata: [metadata])
        connection?.send(content: data, contentContext: context, isComplete: true,
                        completion: .contentProcessed { error in
            if let error = error {
                print("[SightLine] WebSocket send text error: \(error)")
            }
        })
    }

    func sendBinary(_ data: Data) {
        let metadata = NWProtocolWebSocket.Metadata(opcode: .binary)
        let context = NWConnection.ContentContext(identifier: "binaryMessage",
                                                  metadata: [metadata])
        connection?.send(content: data, contentContext: context, isComplete: true,
                        completion: .contentProcessed { error in
            if let error = error {
                print("[SightLine] WebSocket send binary error: \(error)")
            }
        })
    }

    // MARK: - Private

    private func startConnection(url: URL) {
        let parameters = NWParameters.tls
        let wsOptions = NWProtocolWebSocket.Options()
        wsOptions.autoReplyPing = true
        parameters.defaultProtocolStack.applicationProtocols.insert(wsOptions, at: 0)

        let connection = NWConnection(to: .url(url), using: parameters)
        self.connection = connection

        connection.stateUpdateHandler = { [weak self] state in
            guard let self = self else { return }
            switch state {
            case .ready:
                print("[SightLine] WebSocket connected")
                self.reconnectDelay = 1.0
                self.updateConnectionState(true)
                self.receiveLoop()

            case .failed(let error):
                print("[SightLine] WebSocket failed: \(error)")
                self.updateConnectionState(false)
                self.handleDisconnect()

            case .cancelled:
                print("[SightLine] WebSocket cancelled")
                self.updateConnectionState(false)

            case .waiting(let error):
                print("[SightLine] WebSocket waiting: \(error)")

            default:
                break
            }
        }

        connection.start(queue: queue)
    }

    private func receiveLoop() {
        connection?.receiveMessage { [weak self] content, context, isComplete, error in
            guard let self = self else { return }

            if let error = error {
                print("[SightLine] WebSocket receive error: \(error)")
                self.handleDisconnect()
                return
            }

            // Determine message type from WebSocket metadata
            if let metadata = context?.protocolMetadata(definition: NWProtocolWebSocket.definition)
                as? NWProtocolWebSocket.Metadata {
                switch metadata.opcode {
                case .binary:
                    if let data = content {
                        self.onAudioReceived?(data)
                    }
                case .text:
                    if let data = content, let text = String(data: data, encoding: .utf8) {
                        self.onTextReceived?(text)
                    }
                case .close:
                    self.handleDisconnect()
                    return
                default:
                    break
                }
            }

            // Continue receiving
            self.receiveLoop()
        }
    }

    private func handleDisconnect() {
        guard !intentionalDisconnect else { return }

        updateConnectionState(false)

        // Haptic feedback to alert user of disconnection
        DispatchQueue.main.async {
            let generator = UINotificationFeedbackGenerator()
            generator.notificationOccurred(.warning)
        }

        // Exponential backoff reconnection
        let delay = reconnectDelay
        reconnectDelay = min(reconnectDelay * 2, maxReconnectDelay)

        print("[SightLine] Reconnecting in \(delay)s...")
        queue.asyncAfter(deadline: .now() + delay) { [weak self] in
            guard let self = self, !self.intentionalDisconnect,
                  let url = self.serverURL else { return }
            self.connection?.cancel()
            self.startConnection(url: url)
        }
    }

    private func updateConnectionState(_ connected: Bool) {
        DispatchQueue.main.async { [weak self] in
            self?.isConnected = connected
            self?.onConnectionStateChanged?(connected)
        }
    }

    /// Monitor network path changes (WiFi <-> Cellular) for seamless transitions
    private func startPathMonitor() {
        let monitor = NWPathMonitor()
        monitor.pathUpdateHandler = { [weak self] path in
            guard let self = self, !self.intentionalDisconnect else { return }

            if path.status == .satisfied {
                // Network available - reconnect if not already connected
                if self.connection?.state != .ready, let url = self.serverURL {
                    print("[SightLine] Network path changed, reconnecting...")
                    self.reconnectDelay = 1.0
                    self.connection?.cancel()
                    self.startConnection(url: url)
                }
            } else {
                print("[SightLine] Network path unsatisfied")
                self.updateConnectionState(false)
            }
        }
        monitor.start(queue: queue)
        pathMonitor = monitor
    }
}
