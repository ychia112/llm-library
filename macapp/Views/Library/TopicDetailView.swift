import SwiftUI

struct TopicDetailView: View {
    let topic: TopicSummary
    @Binding var selectedSessionID: String?
    @State private var viewModel = TopicDetailViewModel()

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                heroSection

                if !topic.byQuestionType.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        sectionLabel("Question Types")
                        questionTypeBar
                        questionTypeLegend
                    }
                }

                if !topic.topEntities.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        sectionLabel("Key Entities")
                        FlowLayout(spacing: 6) {
                            ForEach(topic.topEntities, id: \.self) { entity in
                                Text(entity)
                                    .font(.caption)
                                    .padding(.horizontal, 8)
                                    .padding(.vertical, 4)
                                    .background(RoundedRectangle(cornerRadius: 6).fill(.secondary.opacity(0.12)))
                            }
                        }
                    }
                }

                if !allTags.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        sectionLabel("Filter by Tag")
                        FlowLayout(spacing: 6) {
                            ForEach(allTags, id: \.self) { tag in
                                Toggle(tag, isOn: Binding(
                                    get: { viewModel.selectedTags.contains(tag) },
                                    set: { _ in viewModel.toggleTag(tag) }
                                ))
                                .toggleStyle(.button)
                                .controlSize(.small)
                                .buttonStyle(.bordered)
                            }
                        }
                    }
                }

                VStack(alignment: .leading, spacing: 8) {
                    sectionLabel("Sessions (\(viewModel.filteredSessions.count))")
                    if viewModel.isLoading {
                        ProgressView().frame(maxWidth: .infinity, alignment: .center).padding()
                    } else {
                        ForEach(viewModel.filteredSessions) { session in
                            sessionCard(session)
                        }
                    }
                }
            }
            .padding()
        }
        .navigationTitle(topic.topic)
        .task { await viewModel.load(topic: topic.topic) }
    }

    // MARK: - Hero

    private var heroSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .firstTextBaseline, spacing: 12) {
                Text(topic.topic)
                    .font(.largeTitle)
                    .fontWeight(.bold)
                Spacer()
                HStack(spacing: 4) {
                    Text("\(topic.count)").fontWeight(.bold)
                    Text("sessions").foregroundStyle(.secondary)
                }
                .font(.subheadline)
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
                .background(Capsule().fill(.secondary.opacity(0.12)))
            }

            platformChips
        }
    }

    @ViewBuilder
    private var platformChips: some View {
        let platforms: [(name: String, count: Int)] = Dictionary(grouping: viewModel.allSessions, by: \.platform)
            .map { (name: $0.key, count: $0.value.count) }
            .sorted { $0.count > $1.count }
        if !platforms.isEmpty {
            HStack(spacing: 8) {
                ForEach(platforms, id: \.name) { item in
                    Text("\(item.name.capitalized) · \(item.count)")
                        .font(.caption)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 4)
                        .background(Capsule().fill(.secondary.opacity(0.12)))
                }
            }
        }
    }

    // MARK: - Question type bar

    private var questionTypeBar: some View {
        let total = topic.byQuestionType.reduce(0) { $0 + $1.count }
        let sorted = topic.byQuestionType.sorted { $0.count > $1.count }
        return GeometryReader { geo in
            HStack(spacing: 2) {
                ForEach(sorted) { stat in
                    let width = geo.size.width * CGFloat(stat.count) / CGFloat(max(total, 1))
                    RoundedRectangle(cornerRadius: 3)
                        .fill(questionTypeColor(stat.questionType))
                        .frame(width: max(width, 0))
                }
            }
        }
        .frame(height: 12)
        .clipShape(RoundedRectangle(cornerRadius: 3))
    }

    private var questionTypeLegend: some View {
        HStack(spacing: 12) {
            ForEach(topic.byQuestionType.sorted { $0.count > $1.count }) { stat in
                HStack(spacing: 4) {
                    Circle()
                        .fill(questionTypeColor(stat.questionType))
                        .frame(width: 8, height: 8)
                    Text("\(stat.questionType) (\(stat.count))")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            }
        }
    }

    // MARK: - Tags

    private var allTags: [String] {
        var counts: [String: Int] = [:]
        for session in viewModel.allSessions {
            for tag in session.tags { counts[tag, default: 0] += 1 }
        }
        return counts.sorted { $0.value > $1.value }.map(\.key)
    }

    // MARK: - Session cards

    private func sessionCard(_ session: Session) -> some View {
        Button {
            selectedSessionID = session.id
        } label: {
            HStack(alignment: .top, spacing: 12) {
                VStack(alignment: .leading, spacing: 6) {
                    Text(session.title)
                        .font(.headline)
                        .multilineTextAlignment(.leading)
                    if let summary = session.summary {
                        Text(summary)
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                            .lineLimit(2)
                            .multilineTextAlignment(.leading)
                    }
                    if !session.tags.isEmpty {
                        FlowLayout(spacing: 4) {
                            ForEach(session.tags.prefix(5), id: \.self) { tag in
                                Text(tag)
                                    .font(.caption2)
                                    .padding(.horizontal, 6)
                                    .padding(.vertical, 2)
                                    .background(RoundedRectangle(cornerRadius: 4).fill(.secondary.opacity(0.1)))
                            }
                        }
                    }
                }
                Spacer(minLength: 8)
                if let qType = session.questionType {
                    Text(qType)
                        .font(.caption2)
                        .fontWeight(.semibold)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(Capsule().fill(questionTypeColor(qType).opacity(0.15)))
                        .foregroundStyle(questionTypeColor(qType))
                }
            }
            .padding()
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(
                RoundedRectangle(cornerRadius: 10)
                    .fill(selectedSessionID == session.id
                          ? Color.accentColor.opacity(0.08)
                          : Color(nsColor: .controlBackgroundColor))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 10)
                    .stroke(selectedSessionID == session.id
                            ? Color.accentColor.opacity(0.3)
                            : Color.secondary.opacity(0.15),
                            lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
    }

    // MARK: - Helpers

    private func sectionLabel(_ text: String) -> some View {
        Text(text)
            .font(.caption)
            .fontWeight(.bold)
            .foregroundStyle(.secondary)
            .textCase(.uppercase)
    }
}
