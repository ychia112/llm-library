import SwiftUI

struct ChatBarView: View {
    @State private var query = ""
    @State private var messages: [BarMessage] = []
    @State private var isExpanded = false
    @State private var isLoading = false
    @State private var searchPhase = ""

    var body: some View {
        VStack(spacing: 0) {
            if isExpanded {
                Divider()
                chatPanel
                    .transition(.move(edge: .bottom).combined(with: .opacity))
            }
            Divider()
            inputRow
        }
        .background(.ultraThinMaterial)
        .animation(.spring(response: 0.32, dampingFraction: 0.85), value: isExpanded)
    }

    // MARK: - Chat panel

    private var chatPanel: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 12) {
                    ForEach(messages) { msg in
                        if msg.isUser {
                            userBubble(msg)
                        } else {
                            assistantBubble(msg)
                        }
                    }

                    if isLoading {
                        searchingIndicator
                            .id("loading")
                    }
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 14)
            }
            .frame(height: 280)
            .onChange(of: messages.count) { _, _ in
                withAnimation { proxy.scrollTo(messages.last?.id, anchor: .bottom) }
            }
            .onChange(of: isLoading) { _, loading in
                if loading {
                    withAnimation { proxy.scrollTo("loading", anchor: .bottom) }
                }
            }
        }
    }

    // MARK: - User bubble

    private func userBubble(_ msg: BarMessage) -> some View {
        HStack {
            Spacer(minLength: 60)
            Text(msg.text)
                .font(.system(size: 13))
                .textSelection(.enabled)
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .background(RoundedRectangle(cornerRadius: 14).fill(Color.accentColor))
                .foregroundStyle(.white)
        }
        .id(msg.id)
    }

    // MARK: - Assistant bubble

    private func assistantBubble(_ msg: BarMessage) -> some View {
        HStack(alignment: .top) {
            VStack(alignment: .leading, spacing: 8) {

                // Hit type badge
                if let hitType = msg.hitType {
                    hitBadge(hitType)
                }

                // Referenced sessions from library
                if let refs = msg.refs, !refs.isEmpty {
                    VStack(alignment: .leading, spacing: 5) {
                        Text("FROM YOUR LIBRARY")
                            .font(.system(size: 9, weight: .bold))
                            .foregroundStyle(.tertiary)
                            .kerning(0.8)

                        ForEach(refs, id: \.id) { session in
                            HStack(spacing: 7) {
                                RoundedRectangle(cornerRadius: 1.5)
                                    .fill(Color.accentColor.opacity(0.5))
                                    .frame(width: 2.5, height: 16)
                                Text(session.title)
                                    .font(.system(size: 12))
                                    .foregroundStyle(.secondary)
                                    .lineLimit(1)
                            }
                        }
                    }
                    .padding(10)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .fill(Color.accentColor.opacity(0.06))
                            .overlay(
                                RoundedRectangle(cornerRadius: 8)
                                    .strokeBorder(Color.accentColor.opacity(0.12), lineWidth: 1)
                            )
                    )
                }

                // Answer text
                Text(msg.text)
                    .font(.system(size: 13))
                    .textSelection(.enabled)
                    .foregroundStyle(.primary)
                    .fixedSize(horizontal: false, vertical: true)
            }
            .padding(12)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(
                RoundedRectangle(cornerRadius: 14)
                    .fill(Color(nsColor: .controlBackgroundColor))
            )

            Spacer(minLength: 40)
        }
        .id(msg.id)
    }

    // MARK: - Hit type badge

    private func hitBadge(_ type: String) -> some View {
        let (label, color, icon) = hitTypeInfo(type)
        return HStack(spacing: 5) {
            Image(systemName: icon)
                .font(.system(size: 9, weight: .bold))
            Text(label)
                .font(.system(size: 10, weight: .bold))
                .kerning(0.3)
        }
        .foregroundStyle(color)
        .padding(.horizontal, 8)
        .padding(.vertical, 4)
        .background(Capsule().fill(color.opacity(0.1)))
    }

    private func hitTypeInfo(_ type: String) -> (String, Color, String) {
        switch type {
        case "hit":     return ("MATCH FOUND", .green,  "checkmark.circle.fill")
        case "partial": return ("PARTIAL MATCH", .orange, "circle.lefthalf.filled")
        default:        return ("NOT IN LIBRARY", Color.secondary, "circle.dashed")
        }
    }

    // MARK: - Searching indicator

    private var searchingIndicator: some View {
        HStack(spacing: 8) {
            ProgressView()
                .controlSize(.small)
                .tint(.secondary)
            Text(searchPhase)
                .font(.system(size: 12))
                .foregroundStyle(.secondary)
        }
        .padding(.horizontal, 4)
        .padding(.vertical, 6)
    }

    // MARK: - Input row

    private var inputRow: some View {
        HStack(spacing: 10) {
            HStack(spacing: 5) {
                Image(systemName: "sparkles")
                    .font(.system(size: 11))
                    .foregroundStyle(.tertiary)
                Text("gemma4")
                    .font(.system(size: 11, weight: .medium))
                    .foregroundStyle(.tertiary)
            }

            TextField("Ask your library…", text: $query, axis: .vertical)
                .textFieldStyle(.plain)
                .font(.system(size: 13))
                .lineLimit(1...4)
                .onSubmit { send() }

            HStack(spacing: 6) {
                if !messages.isEmpty {
                    Button {
                        withAnimation { isExpanded.toggle() }
                    } label: {
                        Image(systemName: isExpanded ? "chevron.down" : "chevron.up")
                            .font(.system(size: 11, weight: .medium))
                            .foregroundStyle(.secondary)
                    }
                    .buttonStyle(.plain)
                }

                Button { send() } label: {
                    Image(systemName: "arrow.up.circle.fill")
                        .font(.system(size: 22))
                        .foregroundStyle(
                            query.trimmingCharacters(in: .whitespaces).isEmpty || isLoading
                                ? Color.secondary.opacity(0.35)
                                : Color.accentColor
                        )
                }
                .buttonStyle(.plain)
                .disabled(query.trimmingCharacters(in: .whitespaces).isEmpty || isLoading)
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
    }

    // MARK: - Send

    private func send() {
        let text = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }
        query = ""
        isExpanded = true
        messages.append(BarMessage(text: text, isUser: true))
        isLoading = true
        searchPhase = "Searching your library…"

        Task {
            do {
                let response = try await APIClient.shared.ask(query: text, provider: "ollama")

                let refs = response.referencedSessions.isEmpty ? nil : response.referencedSessions
                messages.append(BarMessage(
                    text: response.answer,
                    isUser: false,
                    hitType: response.hitType,
                    refs: refs
                ))
            } catch {
                messages.append(BarMessage(
                    text: "Error: \(error.localizedDescription)",
                    isUser: false,
                    hitType: "miss"
                ))
            }
            isLoading = false
            searchPhase = ""
        }
    }
}

// MARK: - Local model

private struct BarMessage: Identifiable {
    let id = UUID()
    let text: String
    let isUser: Bool
    var hitType: String? = nil
    var refs: [Session]? = nil
}
