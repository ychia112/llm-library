import SwiftUI

struct PlaceholderSearchView: View {
    @Binding var selectedSessionID: String?
    
    var body: some View {
        ContentUnavailableView("Search Results", systemImage: "magnifyingglass", description: Text("Enter a query to search your library."))
            .navigationTitle("Search")
    }
}

struct PlaceholderLibraryView: View {
    @Binding var selectedSessionID: String?
    
    var body: some View {
        ContentUnavailableView("Library", systemImage: "books.vertical", description: Text("Browse sessions by topic or tag."))
            .navigationTitle("Library")
    }
}

struct PlaceholderSessionDetailView: View {
    let sessionID: String?
    
    var body: some View {
        Group {
            if let id = sessionID {
                Text("Session Details for \(id)")
            } else {
                ContentUnavailableView("No Session Selected", systemImage: "message", description: Text("Select a session to view the conversation."))
            }
        }
    }
}
