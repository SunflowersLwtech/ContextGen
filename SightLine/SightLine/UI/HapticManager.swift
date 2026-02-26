//
//  HapticManager.swift
//  SightLine
//
//  Provides distinct haptic patterns for each gesture type.
//  Designed for visually impaired users who rely on tactile feedback
//  to confirm gesture recognition.
//

import UIKit

final class HapticManager {
    static let shared = HapticManager()

    private let lightImpact = UIImpactFeedbackGenerator(style: .light)
    private let mediumImpact = UIImpactFeedbackGenerator(style: .medium)
    private let heavyImpact = UIImpactFeedbackGenerator(style: .heavy)
    private let notification = UINotificationFeedbackGenerator()
    private let selection = UISelectionFeedbackGenerator()

    private init() {}

    /// Pre-warm all generators so first haptic fires without delay.
    func prepare() {
        lightImpact.prepare()
        mediumImpact.prepare()
        heavyImpact.prepare()
        notification.prepare()
        selection.prepare()
    }

    /// Single tap: light impact confirming mute toggle.
    func singleTap() {
        lightImpact.impactOccurred()
    }

    /// Double tap: two medium impacts confirming speech interrupt.
    func doubleTap() {
        mediumImpact.impactOccurred()
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) { [weak self] in
            self?.mediumImpact.impactOccurred()
        }
    }

    /// Triple tap: success notification confirming repeat-last request.
    func tripleTap() {
        notification.notificationOccurred(.success)
    }

    /// Long press: heavy impact confirming emergency pause.
    func longPress() {
        heavyImpact.impactOccurred()
    }

    /// Swipe: selection tick confirming LOD change.
    func swipe() {
        selection.selectionChanged()
    }

    /// SOS: three warning haptics in rapid succession.
    func sos() {
        notification.notificationOccurred(.warning)
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.15) { [weak self] in
            self?.notification.notificationOccurred(.warning)
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.30) { [weak self] in
            self?.notification.notificationOccurred(.warning)
        }
    }

    /// Safe mode: three heavy impacts signaling disconnection.
    func safeMode() {
        heavyImpact.impactOccurred()
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.12) { [weak self] in
            self?.heavyImpact.impactOccurred()
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.24) { [weak self] in
            self?.heavyImpact.impactOccurred()
        }
    }

    /// Connection restored: success notification confirming reconnection.
    func connectionRestored() {
        notification.notificationOccurred(.success)
    }

    /// Connection lost: warning notification for disconnection.
    func connectionLost() {
        notification.notificationOccurred(.warning)
    }

    /// Camera on: medium impact simulating a shutter click.
    func cameraOn() {
        mediumImpact.impactOccurred()
    }

    /// Camera off: light impact confirming deactivation.
    func cameraOff() {
        lightImpact.impactOccurred()
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.08) { [weak self] in
            self?.lightImpact.impactOccurred()
        }
    }
}
