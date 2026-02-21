//
//  CameraManager.swift
//  SightLine
//
//  Captures frames from the back camera, resizes to 768x768,
//  encodes as JPEG, and delivers via callback for WebSocket transmission.
//  Frame rate is controlled by FrameSelector (LOD-based throttling).
//

import AVFoundation
import Combine
import UIKit
import CoreImage

class CameraManager: NSObject, ObservableObject {
    @Published var isRunning = false

    private var captureSession: AVCaptureSession?
    private let sessionQueue = DispatchQueue(label: "com.sightline.camera")
    private let context = CIContext()

    var onFrameCaptured: ((Data) -> Void)?  // JPEG data callback
    var frameSelector: FrameSelector?

    func startCapture() {
        sessionQueue.async { [weak self] in
            self?.setupCaptureSession()
        }
    }

    private func setupCaptureSession() {
        let session = AVCaptureSession()
        session.sessionPreset = .medium

        guard let camera = AVCaptureDevice.default(
            .builtInWideAngleCamera,
            for: .video,
            position: .back
        ) else {
            print("[SightLine] Back camera not available")
            return
        }

        guard let input = try? AVCaptureDeviceInput(device: camera) else {
            print("[SightLine] Failed to create camera input")
            return
        }

        if session.canAddInput(input) {
            session.addInput(input)
        }

        let output = AVCaptureVideoDataOutput()
        output.videoSettings = [
            kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA
        ]
        output.setSampleBufferDelegate(self, queue: sessionQueue)
        output.alwaysDiscardsLateVideoFrames = true

        if session.canAddOutput(output) {
            session.addOutput(output)
        }

        session.startRunning()
        captureSession = session

        DispatchQueue.main.async { self.isRunning = true }
        print("[SightLine] Camera capture started")
    }

    func stopCapture() {
        sessionQueue.async { [weak self] in
            self?.captureSession?.stopRunning()
            self?.captureSession = nil
            DispatchQueue.main.async { self?.isRunning = false }
            print("[SightLine] Camera capture stopped")
        }
    }
}

// MARK: - AVCaptureVideoDataOutputSampleBufferDelegate

extension CameraManager: AVCaptureVideoDataOutputSampleBufferDelegate {
    func captureOutput(
        _ output: AVCaptureOutput,
        didOutput sampleBuffer: CMSampleBuffer,
        from connection: AVCaptureConnection
    ) {
        guard let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }

        // Check with frame selector for LOD-based throttling
        if let selector = frameSelector, !selector.shouldSendFrame() {
            return
        }

        let ciImage = CIImage(cvPixelBuffer: pixelBuffer)

        // Resize to 768x768 maintaining aspect ratio
        let targetSize = CGSize(
            width: SightLineConfig.videoFrameWidth,
            height: SightLineConfig.videoFrameHeight
        )
        let scaleX = targetSize.width / ciImage.extent.width
        let scaleY = targetSize.height / ciImage.extent.height
        let scale = min(scaleX, scaleY)
        let scaledImage = ciImage.transformed(by: CGAffineTransform(scaleX: scale, y: scale))

        guard let cgImage = context.createCGImage(scaledImage, from: scaledImage.extent) else {
            return
        }

        let uiImage = UIImage(cgImage: cgImage)
        guard let jpegData = uiImage.jpegData(compressionQuality: SightLineConfig.jpegQuality) else {
            return
        }

        frameSelector?.markFrameSent()
        onFrameCaptured?(jpegData)
    }
}
