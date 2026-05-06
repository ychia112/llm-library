import SwiftUI

struct ChatView: View {
    @State private var query: String = ""
    @State private var selectedSource: String = "ChatGPT"
    @State private var chatHistory: [ChatMessage] = []
    @State private var isLoading: Bool = false
    @Binding var selectedSessionID: String?
    
    let sources = ["ChatGPT", "Claude", "All"]
    
    var body: some View {
        VStack(spacing: 0) {
            if chatHistory.isEmpty {
                welcomeView
            } else {
                chatTimeline
            }
            inputArea
        }
        .navigationTitle("AI Knowledge Chat")
    }
    
    private var welcomeView: some View {
        VStack(spacing: 20) {
            Spacer()
            Image(systemName: "sparkles")
                .font(.system(size: 60))
                .foregroundColor(.accentColor)
            Text("How can I help you today?")
                .font(.largeTitle)
                .fontWeight(.bold)
            Text("Search your history or ask a new question.")
                .foregroundStyle(.secondary)
            Spacer()
        }
    }
    
    private var chatTimeline: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(spacing: 20) {
                    ForEach(chatHistory) { message in
                        ChatBubble(message: message, onSessionClick: { id in
                            selectedSessionID = id
                        })
                    }
                    if isLoading {
                        HStack {
                            ProgressView().controlSize(.small)
                            Text("AI is thinking...").font(.caption).foregroundStyle(.secondary)
                            Spacer()
                        }.padding(.horizontal).id("loading")
                    }
                }
                .padding()
            }
            .onChange(of: chatHistory.count) { _, _ in
                withAnimation { proxy.scrollTo(chatHistory.last?.id, anchor: .bottom) }
            }
        }
    }
    
    private var inputArea: some View {
        VStack(spacing: 0) {
            Divider()
            HStack(alignment: .bottom, spacing: 12) {
                Menu {
                    ForEach(sources, id: \.self) { source in
                        Button(source) { selectedSource = source }
                    }
                } label: {
                    HStack {
                        Image(systemName: selectedSource == "ChatGPT" ? "quote.bubble" : "moon.stars")
                        Text(selectedSource)
                    }
                    .font(.caption).fontWeight(.bold)
                    .padding(.horizontal, 8).padding(.vertical, 6)
                    .background(RoundedRectangle(cornerRadius: 8).fill(.quaternary))
                }
                // Use a supported MenuStyle on macOS
                .menuStyle(.borderlessButton)
                .frame(width: 100)
                
                TextField("Ask anything...", text: $query, axis: .vertical)
                    .textFieldStyle(.plain)
                    .padding(8)
                    .background(RoundedRectangle(cornerRadius: 8).fill(.tertiary.opacity(0.5)))
                    .lineLimit(1...5)
                    .onSubmit { performAsk() }
                
                Button { performAsk() } label: {
                    Image(systemName: "arrow.up.circle.fill")
                        .font(.system(size: 30))
                        .foregroundColor(query.isEmpty ? .secondary : .accentColor)
                }
                .buttonStyle(.plain)
                .disabled(query.isEmpty || isLoading)
            }
            .padding()
            .background(.background)
        }
    }
    
    private func performAsk() {
        let userMsg = ChatMessage(role: "user", content: query)
        chatHistory.append(userMsg)
        let currentQuery = query
        let currentPlatform = selectedSource.lowercased()
        query = ""
        isLoading = true
        
        Task {
            do {
                let response = try await APIClient.shared.ask(query: currentQuery, platform: currentPlatform)
                let aiMsg = ChatMessage(
                    role: "assistant",
                    content: response.answer,
                    hitType: response.hitType,
                    referencedSessions: response.referencedSessions
                )
                chatHistory.append(aiMsg)
            } catch {
                chatHistory.append(ChatMessage(role: "assistant", content: "Error: \(error.localizedDescription)"))
            }
            isLoading = false
        }
    }
}

struct ChatMessage: Identifiable {
    let id = UUID()
    let role: String
    let content: String
    var hitType: String? = nil
    var referencedSessions: [Session]? = []
}

struct ChatBubble: View {
    let message: ChatMessage
    let onSessionClick: (String) -> Void
    var isUser: Bool { message.role == "user" }
    
    var body: some View {
        HStack {
            if isUser { Spacer(minLength: 100) }
            VStack(alignment: .leading, spacing: 8) {
                if let hitType = message.hitType {
                    HStack(spacing: 4) {
                        Image(systemName: hitType == "hit" ? "checkmark.circle.fill" : "bolt.fill")
                        Text(hitType.uppercased())
                    }
                    .font(.system(size: 9, weight: .bold))
                    .padding(.horizontal, 6).padding(.vertical, 2)
                    .background(hitType == "hit" ? Color.green : Color.orange)
                    .foregroundStyle(.white).cornerRadius(4)
                }
                Text(message.content).textSelection(.enabled)
                if let refs = message.referencedSessions, !refs.isEmpty {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("References:").font(.caption2).fontWeight(.bold).foregroundStyle(.secondary)
                        ForEach(refs) { session in
                            Button { onSessionClick(session.id) } label: {
                                HStack { Image(systemName: "link"); Text(session.title).lineLimit(1) }
                                .font(.caption)
                                .foregroundColor(.accentColor)
                            }.buttonStyle(.link)
                        }
                    }.padding(.top, 4)
                }
            }
            .padding(12)
            .background(RoundedRectangle(cornerRadius: 16).fill(isUser ? Color.accentColor : Color(nsColor: .secondarySystemFill)))
            .foregroundStyle(isUser ? .white : .primary)
            if !isUser { Spacer(minLength: 100) }
        }
    }
}
