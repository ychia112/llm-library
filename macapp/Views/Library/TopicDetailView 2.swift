import SwiftUI

@MainActor
@Observable
class TopicDetailViewModel {
    var sessions: [Session] = []
    var isLoading: Bool = false
    var errorMessage: String?

    private let apiClient = APIClient.shared

    func load(topic: String) async {
        isLoading = true
        errorMessage = nil
        do {
            let fetched = try await apiClient.fetchSessions(topic: topic)
            self.sessions = fetched
        } catch {
            self.errorMessage = error.localizedDescription
            self.sessions = []
        }
        isLoading = false
    }
}

struct TopicDetailView: View {
    let topic: TopicSummary
    @Binding var selectedSessionID: String?
    @State private var viewModel = TopicDetailViewModel()

    var body: some View {
        VStack(spacing: 0) {
            header
                .padding()
                .background(.thinMaterial)

            content
        }
        .navigationTitle(topic.topic)
        .task {
            await viewModel.load(topic: topic.topic)
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(topic.topic)
                    .font(.title2)
                    .fontWeight(.bold)
                Spacer()
                Text("\(topic.count) sessions")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            // Top tags
            if !topic.topTags.isEmpty {
                FlowLayout(spacing: 6) {
                    ForEach(topic.topTags.prefix(10), id: \.self) { tag in
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

            // Mini distribution bar by question type
            if !topic.byQuestionType.isEmpty {
                questionTypeMiniBar
                    .frame(height: 6)
                    .clipShape(RoundedRectangle(cornerRadius: 3))
            }
        }
    }

    private var content: some View {
        Group {
            if viewModel.isLoading {
                ProgressView("Loading sessions…")
                    .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .center)
            } else if let error = viewModel.errorMessage {
                ContentUnavailableView("Failed to Load", systemImage: "exclamationmark.triangle", description: Text(error))
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if viewModel.sessions.isEmpty {
                ContentUnavailableView("No Sessions", systemImage: "text.bubble", description: Text("No sessions found for this topic."))
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                List(viewModel.sessions, selection: $selectedSessionID) { session in
                    sessionRow(session)
                        .tag(session.id)
                        .padding(.vertical, 4)
                }
                .listStyle(.inset)
            }
        }
    }

    private func sessionRow(_ session: Session) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(session.title)
                    .font(.headline)
                    .lineLimit(1)
                Spacer()
                Text(session.platform.uppercased())
                    .font(.caption2)
                    .fontWeight(.bold)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(Capsule().fill(.secondary.opacity(0.15)))
            }
            if let summary = session.summary {
                Text(summary)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
            }
            // tags
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 6) {
                    ForEach(session.tags.prefix(6), id: \.self) { tag in
                        Text(tag)
                            .font(.caption2)
                            .monospaced()
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background(Capsule().stroke(.secondary.opacity(0.5), lineWidth: 1))
                    }
                }
            }
        }
    }

    private var questionTypeMiniBar: some View {
        let total = topic.byQuestionType.reduce(0) { $0 + $1.count }
        return GeometryReader { geo in
            HStack(spacing: 1) {
                ForEach(topic.byQuestionType.sorted { $0.count > $1.count }) { stat in
                    let width = geo.size.width * CGFloat(stat.count) / CGFloat(max(total, 1))
                    RoundedRectangle(cornerRadius: 2)
                        .fill(questionTypeColor(stat.questionType))
                        .frame(width: max(width, 0))
                }
            }
        }
    }

    private func questionTypeColor(_ type: String) -> Color {
        switch type.lowercased() {
        case "debug": return .red
        case "howto", "how_to", "how-to": return .blue
        case "design": return .purple
        case "research": return .green
        default: return .orange
        }
    }
}
