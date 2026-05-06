import SwiftUI

@MainActor
@Observable
class SessionDetailViewModel {
    var session: SessionDetail?
    var isLoading: Bool = false
    var errorMessage: String?
    
    private let apiClient = APIClient.shared
    
    func loadSession(id: String) async {
        isLoading = true
        errorMessage = nil
        do {
            self.session = try await apiClient.fetchSession(id: id)
        } catch {
            self.errorMessage = error.localizedDescription
        }
        isLoading = false
    }
}

struct SessionDetailView: View {
    let sessionID: String?
    @State private var viewModel = SessionDetailViewModel()
    
    var body: some View {
        Group {
            if let id = sessionID {
                detailContent(id: id)
            } else {
                ContentUnavailableView("No Session Selected", systemImage: "message", description: Text("Select a session to view the conversation."))
            }
        }
        .onChange(of: sessionID) { _, newID in
            if let newID = newID {
                Task { await viewModel.loadSession(id: newID) }
            }
        }
    }
    
    @ViewBuilder
    private func detailContent(id: String) -> some View {
        if viewModel.isLoading {
            ProgressView()
        } else if let session = viewModel.session {
            VStack(spacing: 0) {
                // Header
                headerView(session: session)
                
                Divider()
                
                // Messages Timeline
                ScrollViewReader { proxy in
                    List {
                        // Summary Card
                        if let summary = session.summary {
                            summaryCard(summary: summary)
                                .listRowSeparator(.hidden)
                                .padding(.vertical, 8)
                        }
                        
                        // Messages
                        ForEach(session.messages) { message in
                            MessageBubble(message: message)
                                .listRowSeparator(.hidden)
                                .listRowInsets(EdgeInsets(top: 4, leading: 16, bottom: 4, trailing: 16))
                        }
                    }
                    .listStyle(.plain)
                }
            }
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button {
                        copyAllMessages(session: session)
                    } label: {
                        Label("Copy All", systemImage: "doc.on.doc")
                    }
                }
            }
        } else if let error = viewModel.errorMessage {
            ContentUnavailableView("Error Loading Session", systemImage: "exclamationmark.triangle", description: Text(error))
        }
    }
    
    private func headerView(session: SessionDetail) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text(session.title)
                    .font(.title)
                    .fontWeight(.bold)
                Spacer()
                platformBadge(platform: session.platform)
            }
            
            HStack {
                if let qType = session.questionType {
                    Text(qType.uppercased())
                        .font(.caption2)
                        .fontWeight(.black)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(.secondary.opacity(0.2))
                        .cornerRadius(4)
                }
                
                Text(session.updatedAt)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            
            // Tags
            FlowLayout(spacing: 6) {
                ForEach(session.tags, id: \.self) { tag in
                    Text("#\(tag)")
                        .font(.caption2)
                        .monospaced()
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(Capsule().fill(Color.accentColor.opacity(0.1)))
                        .foregroundStyle(Color.accentColor)
                }
            }
        }
        .padding()
        .background(.background)
    }
    
    private func summaryCard(summary: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("AI Summary", systemImage: "sparkles")
                .font(.caption)
                .fontWeight(.bold)
                .foregroundStyle(.secondary)
            
            Text(summary)
                .font(.body)
                .lineSpacing(4)
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(RoundedRectangle(cornerRadius: 12).fill(.quaternary.opacity(0.5)))
    }
    
    private func platformBadge(platform: String) -> some View {
        Text(platform.capitalized)
            .font(.caption2)
            .fontWeight(.bold)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(platform == "chatgpt" ? Color.green.opacity(0.2) : Color.purple.opacity(0.2))
            .foregroundStyle(platform == "chatgpt" ? .green : .purple)
            .cornerRadius(6)
    }
    
    private func copyAllMessages(session: SessionDetail) {
        let text = session.messages.map { "[\($0.role)]\n\($0.content)" }.joined(separator: "\n\n")
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(text, forType: .string)
    }
}

struct MessageBubble: View {
    let message: Message
    @State private var isExpanded: Bool = false
    
    var isUser: Bool { message.role == "user" || message.role == "human" }
    
    var body: some View {
        HStack {
            if isUser { Spacer(minLength: 50) }
            
            VStack(alignment: isUser ? .trailing : .leading, spacing: 4) {
                Text(message.role.capitalized)
                    .font(.caption2)
                    .fontWeight(.bold)
                    .foregroundStyle(.secondary)
                
                VStack(alignment: .leading) {
                    Text(message.content)
                        .font(.system(.body, design: .monospaced))
                        .textSelection(.enabled)
                        .lineLimit(isExpanded ? nil : 10)
                    
                    if message.content.count > 500 {
                        Button(isExpanded ? "Show Less" : "Show More") {
                            isExpanded.toggle()
                        }
                        .buttonStyle(.link)
                        .font(.caption)
                    }
                }
                .padding(12)
                .background(
                    RoundedRectangle(cornerRadius: 16)
                        .fill(isUser ? Color.accentColor : Color(nsColor: .secondarySystemFill))
                )
                .foregroundStyle(isUser ? .white : .primary)
            }
            
            if !isUser { Spacer(minLength: 50) }
        }
    }
}
