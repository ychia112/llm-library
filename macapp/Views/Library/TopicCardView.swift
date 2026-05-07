import SwiftUI

func questionTypeColor(_ type: String) -> Color {
    switch type.lowercased() {
    case "debug":    return .blue
    case "research": return .green
    case "howto":    return .orange
    case "design":   return .purple
    default:         return .gray
    }
}

struct TopicCardView: View {
    let topic: TopicSummary
    @State private var isHovered = false

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            VStack(alignment: .leading, spacing: 10) {
                HStack(alignment: .firstTextBaseline) {
                    Text(topic.topic)
                        .font(.system(size: 14, weight: .semibold))
                        .lineLimit(2)
                        .foregroundStyle(.primary)

                    Spacer(minLength: 8)

                    Text("\(topic.count)")
                        .font(.system(size: 11, weight: .bold, design: .rounded))
                        .foregroundStyle(.secondary)
                        .monospacedDigit()
                        .padding(.horizontal, 7)
                        .padding(.vertical, 3)
                        .background(Capsule().fill(.secondary.opacity(0.1)))
                }

                if !topic.topTags.isEmpty {
                    HStack(spacing: 4) {
                        ForEach(topic.topTags.prefix(3), id: \.self) { tag in
                            Text(tag)
                                .font(.system(size: 10, design: .monospaced))
                                .foregroundStyle(.tertiary)
                                .padding(.horizontal, 5)
                                .padding(.vertical, 2)
                                .background(
                                    RoundedRectangle(cornerRadius: 3)
                                        .fill(.secondary.opacity(0.07))
                                )
                        }
                    }
                }
            }
            .padding(14)

            if !topic.byQuestionType.isEmpty {
                miniTypeBar
                    .padding(.horizontal, 14)
                    .padding(.bottom, 12)
            }
        }
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color(nsColor: .controlBackgroundColor))
                .shadow(
                    color: .black.opacity(isHovered ? 0.09 : 0.035),
                    radius: isHovered ? 14 : 4,
                    y: isHovered ? 4 : 1
                )
        )
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .strokeBorder(.secondary.opacity(isHovered ? 0.12 : 0.06), lineWidth: 1)
        )
        .scaleEffect(isHovered ? 1.015 : 1.0)
        .animation(.spring(response: 0.22, dampingFraction: 0.7), value: isHovered)
        .onHover { isHovered = $0 }
    }

    private var miniTypeBar: some View {
        let total = topic.byQuestionType.reduce(0) { $0 + $1.count }
        return GeometryReader { geo in
            HStack(spacing: 2) {
                ForEach(topic.byQuestionType.sorted { $0.count > $1.count }) { stat in
                    let width = geo.size.width * CGFloat(stat.count) / CGFloat(max(total, 1))
                    RoundedRectangle(cornerRadius: 2)
                        .fill(questionTypeColor(stat.questionType).opacity(0.65))
                        .frame(width: max(width, 2))
                }
            }
        }
        .frame(height: 3)
        .clipShape(RoundedRectangle(cornerRadius: 2))
    }
}
