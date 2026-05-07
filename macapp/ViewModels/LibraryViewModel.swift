import Foundation
import SwiftUI

@MainActor
@Observable
class LibraryViewModel {
    var overview: LibraryOverview?
    var topics: [TopicSummary] = []
    var isLoading: Bool = false

    var alertMessage: String?
    var showInfoAlert: Bool = false

    var ingestStatus: IngestStatus? = nil
    var isImporting: Bool = false

    var topTags: [TagStats] { overview?.topTags ?? [] }

    private let apiClient = APIClient.shared

    func loadOverview() async {
        isLoading = true
        do {
            self.overview = try await apiClient.fetchOverview()
            self.topics = try await apiClient.fetchTopics()
        } catch {
            print("Failed to load library overview: \(error)")
        }
        isLoading = false
    }

    func importFile(path: String, platform: String) async {
        isImporting = true
        defer {
            isImporting = false
            ingestStatus = nil
        }

        do {
            _ = try await apiClient.ingest(filePath: path, platform: platform)

            // Give background task a moment to start
            try? await Task.sleep(for: .milliseconds(400))

            // Poll until done (max 600 polls ≈ 8 minutes)
            for _ in 0..<600 {
                try? await Task.sleep(for: .milliseconds(900))
                guard let status = try? await apiClient.fetchIngestStatus() else { break }
                ingestStatus = status
                if !status.running { break }
            }

            await loadOverview()
        } catch {
            alertMessage = "Import failed: \(error.localizedDescription)"
            showInfoAlert = true
        }
    }
}
