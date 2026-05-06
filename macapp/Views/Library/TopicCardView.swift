import SwiftUI

struct TopicCardView: View {
    let topic: TopicSummary
    let isSelected: Bool
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text(topic.topic)
                    .font(.headline)
                    .lineLimit(1)
                Spacer()
                Text("\(topic.count)")
                    .font(.caption)
                    .fontWeight(.bold)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Capsule().fill(isSelected ? .white.opacity(0.3) : .secondary.opacity(0.15)))
            }
            
            HStack {
                ForEach(topic.topTags.prefix(3), id: \.self) { tag in
                    Text(tag)
                        .font(.caption2)
                        .monospaced()
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(RoundedRectangle(cornerRadius: 4).fill(isSelected ? .white.opacity(0.2) : .secondary.opacity(0.1)))
                }
            }
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(isSelected ? Color.accentColor : Color(nsColor: .controlBackgroundColor))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(isSelected ? Color.white.opacity(0.3) : Color.secondary.opacity(0.2), lineWidth: 1)
        )
        .foregroundStyle(isSelected ? .white : .primary)
    }
}
