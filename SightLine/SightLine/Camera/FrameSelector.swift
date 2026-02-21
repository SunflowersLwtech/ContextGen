//
//  FrameSelector.swift
//  SightLine
//
//  LOD-based frame throttling. Controls how often camera frames are sent
//  to the server based on the current Level of Detail:
//    LOD 1: 1 FPS (safety/navigation focus)
//    LOD 2: 1 FPS (balanced)
//    LOD 3: 0.5 FPS (static/low-activity scenes)
//

import Foundation
import Combine

class FrameSelector: ObservableObject {
    @Published var currentLOD: Int = 2

    private var lastFrameTime: Date = .distantPast

    var minInterval: TimeInterval {
        switch currentLOD {
        case 1: return 1.0   // 1 FPS
        case 2: return 1.0   // 1 FPS
        case 3: return 2.0   // 0.5 FPS (static scenes)
        default: return 1.0
        }
    }

    func shouldSendFrame() -> Bool {
        let now = Date()
        return now.timeIntervalSince(lastFrameTime) >= minInterval
    }

    func markFrameSent() {
        lastFrameTime = Date()
    }

    func updateLOD(_ lod: Int) {
        DispatchQueue.main.async {
            self.currentLOD = lod
        }
    }
}
