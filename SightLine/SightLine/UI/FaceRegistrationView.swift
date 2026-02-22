//
//  FaceRegistrationView.swift
//  SightLine
//
//  Face registration interface for sighted family members / caregivers.
//  Captures photos via the camera, collects person metadata, and sends
//  the image to the backend REST API for InsightFace embedding extraction.
//
//  Spec: Final_Specification.md §4.2
//  Backend: POST /api/face/register, GET /api/face/list/{user_id}
//

import SwiftUI
import AVFoundation
import os

private let logger = Logger(subsystem: "com.sightline.app", category: "FaceRegistration")

// MARK: - Face Registration Model

@MainActor
final class FaceRegistrationModel: ObservableObject {
    struct RegisteredFace: Identifiable {
        let id: String     // face_id
        let personName: String
        let relationship: String
        let photoIndex: Int
        let createdAt: String
    }

    @Published var personName: String = ""
    @Published var relationship: String = "friend"
    @Published var isRegistering: Bool = false
    @Published var registrationResult: String = ""
    @Published var registrationSuccess: Bool = false
    @Published var registeredFaces: [RegisteredFace] = []
    @Published var isLoadingFaces: Bool = false
    @Published var capturedImage: UIImage?
    @Published var showCamera: Bool = false
    @Published var errorMessage: String = ""

    let relationships = ["friend", "family", "spouse", "colleague", "caregiver", "other"]

    private var baseURL: String {
        // Use the same server URL as the WebSocket, but with https
        let wsURL = SightLineConfig.serverBaseURL
        return wsURL
            .replacingOccurrences(of: "wss://", with: "https://")
            .replacingOccurrences(of: "ws://", with: "http://")
    }

    // MARK: - Register Face

    func registerFace() async {
        guard let image = capturedImage else {
            errorMessage = "Please capture a photo first"
            return
        }
        guard !personName.trimmingCharacters(in: .whitespaces).isEmpty else {
            errorMessage = "Please enter the person's name"
            return
        }

        errorMessage = ""
        isRegistering = true
        registrationResult = ""

        // Compress to JPEG and encode
        guard let jpegData = image.jpegData(compressionQuality: 0.85) else {
            errorMessage = "Failed to encode image"
            isRegistering = false
            return
        }
        let base64Image = jpegData.base64EncodedString()

        let body: [String: Any] = [
            "user_id": SightLineConfig.defaultUserId,
            "person_name": personName.trimmingCharacters(in: .whitespaces),
            "relationship": relationship,
            "image_base64": base64Image,
            "photo_index": 0,
        ]

        guard let url = URL(string: "\(baseURL)/api/face/register") else {
            errorMessage = "Invalid server URL"
            isRegistering = false
            return
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = 30

        do {
            request.httpBody = try JSONSerialization.data(withJSONObject: body)
            let (data, response) = try await URLSession.shared.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse else {
                errorMessage = "Invalid server response"
                isRegistering = false
                return
            }

            let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] ?? [:]

            if httpResponse.statusCode == 201 {
                let faceId = json["face_id"] as? String ?? "unknown"
                registrationResult = "Registered \(personName) (ID: \(faceId.prefix(8))...)"
                registrationSuccess = true
                logger.info("Face registered: \(personName) -> \(faceId)")

                // Reset for next registration
                capturedImage = nil
                personName = ""

                // Refresh face list
                await loadFaces()
            } else {
                let error = json["error"] as? String ?? "Unknown error"
                errorMessage = "Registration failed: \(error)"
                registrationSuccess = false
                logger.error("Face registration failed: \(error)")
            }
        } catch {
            errorMessage = "Network error: \(error.localizedDescription)"
            registrationSuccess = false
            logger.error("Face registration network error: \(error)")
        }

        isRegistering = false
    }

    // MARK: - Load Faces

    func loadFaces() async {
        isLoadingFaces = true
        let userId = SightLineConfig.defaultUserId

        guard let url = URL(string: "\(baseURL)/api/face/list/\(userId)") else {
            isLoadingFaces = false
            return
        }

        do {
            let (data, response) = try await URLSession.shared.data(from: url)
            guard let httpResponse = response as? HTTPURLResponse,
                  httpResponse.statusCode == 200 else {
                isLoadingFaces = false
                return
            }

            let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] ?? [:]
            let faces = json["faces"] as? [[String: Any]] ?? []

            registeredFaces = faces.map { face in
                RegisteredFace(
                    id: face["face_id"] as? String ?? UUID().uuidString,
                    personName: face["person_name"] as? String ?? "Unknown",
                    relationship: face["relationship"] as? String ?? "",
                    photoIndex: face["photo_index"] as? Int ?? 0,
                    createdAt: face["created_at"] as? String ?? ""
                )
            }
            logger.info("Loaded \(registeredFaces.count) registered face(s)")
        } catch {
            logger.error("Load faces failed: \(error)")
        }

        isLoadingFaces = false
    }

    // MARK: - Delete Face

    func deleteFace(_ face: RegisteredFace) async {
        let userId = SightLineConfig.defaultUserId
        guard let url = URL(string: "\(baseURL)/api/face/\(userId)/\(face.id)") else { return }

        var request = URLRequest(url: url)
        request.httpMethod = "DELETE"

        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            if let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 {
                logger.info("Deleted face: \(face.personName) (\(face.id))")
                await loadFaces()
            }
        } catch {
            logger.error("Delete face failed: \(error)")
        }
    }
}

// MARK: - Camera Capture View (UIImagePickerController wrapper)

struct CameraCaptureView: UIViewControllerRepresentable {
    @Binding var image: UIImage?
    @Environment(\.dismiss) private var dismiss

    func makeUIViewController(context: Context) -> UIImagePickerController {
        let picker = UIImagePickerController()
        picker.sourceType = .camera
        picker.cameraDevice = .front
        picker.allowsEditing = false
        picker.delegate = context.coordinator
        return picker
    }

    func updateUIViewController(_ uiViewController: UIImagePickerController, context: Context) {}

    func makeCoordinator() -> Coordinator { Coordinator(self) }

    final class Coordinator: NSObject, UIImagePickerControllerDelegate, UINavigationControllerDelegate {
        let parent: CameraCaptureView

        init(_ parent: CameraCaptureView) {
            self.parent = parent
        }

        func imagePickerController(
            _ picker: UIImagePickerController,
            didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey: Any]
        ) {
            if let image = info[.originalImage] as? UIImage {
                parent.image = image
            }
            parent.dismiss()
        }

        func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
            parent.dismiss()
        }
    }
}

// MARK: - Face Registration View

struct FaceRegistrationView: View {
    @StateObject private var model = FaceRegistrationModel()
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 20) {
                    instructionHeader

                    photoSection

                    formSection

                    registerButton

                    if !model.errorMessage.isEmpty {
                        errorBanner
                    }

                    if model.registrationSuccess {
                        successBanner
                    }

                    registeredFacesSection
                }
                .padding()
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("Register Face")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Close") { dismiss() }
                }
            }
            .sheet(isPresented: $model.showCamera) {
                CameraCaptureView(image: $model.capturedImage)
            }
            .task {
                await model.loadFaces()
            }
        }
    }

    // MARK: - Subviews

    private var instructionHeader: some View {
        VStack(spacing: 8) {
            Image(systemName: "person.crop.circle.badge.plus")
                .font(.system(size: 48))
                .foregroundStyle(.blue)

            Text("Register a Face")
                .font(.title2.bold())

            Text("Take a clear photo of the person's face. This helps SightLine recognize them and announce their presence.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal)
        }
        .padding(.top, 8)
    }

    private var photoSection: some View {
        VStack(spacing: 12) {
            if let image = model.capturedImage {
                Image(uiImage: image)
                    .resizable()
                    .scaledToFill()
                    .frame(width: 200, height: 200)
                    .clipShape(Circle())
                    .overlay(Circle().stroke(.blue, lineWidth: 3))
                    .shadow(radius: 4)

                Button("Retake Photo") {
                    model.showCamera = true
                }
                .font(.subheadline)
            } else {
                Button(action: { model.showCamera = true }) {
                    VStack(spacing: 12) {
                        Image(systemName: "camera.fill")
                            .font(.system(size: 36))
                        Text("Tap to Take Photo")
                            .font(.headline)
                    }
                    .foregroundStyle(.blue)
                    .frame(width: 200, height: 200)
                    .background(Color(.systemGray6))
                    .clipShape(Circle())
                    .overlay(Circle().stroke(.blue.opacity(0.3), lineWidth: 2))
                }
            }
        }
    }

    private var formSection: some View {
        VStack(spacing: 16) {
            VStack(alignment: .leading, spacing: 6) {
                Text("Person's Name")
                    .font(.subheadline.bold())
                    .foregroundStyle(.secondary)

                TextField("e.g. Mom, David Chen", text: $model.personName)
                    .textFieldStyle(.roundedBorder)
                    .textContentType(.name)
                    .autocorrectionDisabled()
                    .accessibilityLabel("Person's name")
            }

            VStack(alignment: .leading, spacing: 6) {
                Text("Relationship")
                    .font(.subheadline.bold())
                    .foregroundStyle(.secondary)

                Picker("Relationship", selection: $model.relationship) {
                    ForEach(model.relationships, id: \.self) { r in
                        Text(r.capitalized).tag(r)
                    }
                }
                .pickerStyle(.segmented)
                .accessibilityLabel("Relationship to user")
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private var registerButton: some View {
        Button(action: {
            Task { await model.registerFace() }
        }) {
            HStack(spacing: 8) {
                if model.isRegistering {
                    ProgressView()
                        .progressViewStyle(CircularProgressViewStyle(tint: .white))
                } else {
                    Image(systemName: "person.crop.circle.badge.checkmark")
                }
                Text(model.isRegistering ? "Registering..." : "Register Face")
                    .fontWeight(.semibold)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 14)
            .background(
                (model.capturedImage != nil && !model.personName.isEmpty && !model.isRegistering)
                    ? Color.blue : Color.gray
            )
            .foregroundStyle(.white)
            .clipShape(RoundedRectangle(cornerRadius: 12))
        }
        .disabled(model.capturedImage == nil || model.personName.isEmpty || model.isRegistering)
        .accessibilityLabel("Register this person's face")
    }

    private var errorBanner: some View {
        HStack {
            Image(systemName: "exclamationmark.triangle.fill")
                .foregroundStyle(.yellow)
            Text(model.errorMessage)
                .font(.subheadline)
                .foregroundStyle(.red)
        }
        .padding()
        .frame(maxWidth: .infinity)
        .background(Color.red.opacity(0.1))
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }

    private var successBanner: some View {
        HStack {
            Image(systemName: "checkmark.circle.fill")
                .foregroundStyle(.green)
            Text(model.registrationResult)
                .font(.subheadline)
                .foregroundStyle(.green)
        }
        .padding()
        .frame(maxWidth: .infinity)
        .background(Color.green.opacity(0.1))
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }

    private var registeredFacesSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Registered Faces")
                    .font(.headline)

                Spacer()

                if model.isLoadingFaces {
                    ProgressView()
                }

                Button(action: {
                    Task { await model.loadFaces() }
                }) {
                    Image(systemName: "arrow.clockwise")
                        .font(.subheadline)
                }
                .accessibilityLabel("Refresh face list")
            }

            if model.registeredFaces.isEmpty && !model.isLoadingFaces {
                Text("No faces registered yet")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, alignment: .center)
                    .padding(.vertical, 20)
            } else {
                ForEach(model.registeredFaces) { face in
                    HStack(spacing: 12) {
                        Image(systemName: "person.circle.fill")
                            .font(.title2)
                            .foregroundStyle(.blue)

                        VStack(alignment: .leading, spacing: 2) {
                            Text(face.personName)
                                .font(.body.bold())
                            Text(face.relationship.capitalized)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }

                        Spacer()

                        Button(role: .destructive) {
                            Task { await model.deleteFace(face) }
                        } label: {
                            Image(systemName: "trash")
                                .font(.subheadline)
                        }
                        .accessibilityLabel("Delete \(face.personName)")
                    }
                    .padding(.vertical, 8)
                    .padding(.horizontal, 12)
                    .background(Color(.systemBackground))
                    .clipShape(RoundedRectangle(cornerRadius: 8))
                }
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }
}
