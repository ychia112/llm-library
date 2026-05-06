import Foundation
import SwiftUI
import Combine

@MainActor
@Observable
class LibraryViewModel {
    // Overview Data
    var overview: LibraryOverview?
    var topics: [TopicSummary] = []
    
    // UI State
    var alertMessage: String?
    var showInfoAlert: Bool = false
    
    // Filter State
    var selectedPlatform: String = "All"
    var selectedQuestionType: String = "All"
    var selectedTopic: String?
    var selectedTags: Set<String> = []
    
    // Filtered Results
    var sessions: [Session] = []
    var isLoading: Bool = false
    
    private let apiClient = APIClient.shared
    
    func loadOverview() async {
        do {
            let overview = try await apiClient.fetchOverview()
            self.overview = overview
            self.topics = try await apiClient.fetchTopics()
        } catch {
            print("Failed to load library overview: \(error)")
        }
    }
    
    func loadSessions() async {
        isLoading = true
        do {
            let platform = selectedPlatform == "All" ? nil : selectedPlatform.lowercased()
            let qType = selectedQuestionType == "All" ? nil : selectedQuestionType.lowercased()
            let tag = selectedTags.first
            
            self.sessions = try await apiClient.fetchSessions(
                tag: tag,
                platform: platform,
                questionType: qType,
                topic: selectedTopic
            )
        } catch {
            print("Failed to load sessions: \(error)")
            self.sessions = []
        }
        isLoading = false
    }
    
    var topTags: [TagStats] {
        overview?.topTags ?? []
    }
    
    func toggleTag(_ tag: String) {
        if selectedTags.contains(tag) {
            selectedTags.remove(tag)
        } else {
            selectedTags.insert(tag)
        }
    }
    
    func importFile(path: String, platform: String) async {
        isLoading = true
        do {
            let response = try await apiClient.ingest(filePath: path, platform: platform)
            self.alertMessage = "Import task submitted successfully to backend."
            self.showInfoAlert = true
            
            // Wait a bit for some processing to happen
            try? await Task.sleep(for: .seconds(3))
            await loadOverview()
        } catch {
            self.alertMessage = "API Error: \(error.localizedDescription)"
            self.showInfoAlert = true
        }
        isLoading = false
    }
}
