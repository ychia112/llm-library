import SwiftUI

struct ContentView: View {
    @State private var selectedSessionID: String? = nil

    private var showingDetail: Bool { selectedSessionID != nil }

    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: 0) {
                NavigationStack {
                    LibraryView(selectedSessionID: $selectedSessionID)
                }

                if showingDetail {
                    Divider()
                    SessionDetailView(sessionID: selectedSessionID)
                        .frame(width: 400)
                        .transition(.asymmetric(
                            insertion: .move(edge: .trailing).combined(with: .opacity),
                            removal: .move(edge: .trailing).combined(with: .opacity)
                        ))
                }
            }

            ChatBarView()
        }
        .frame(minWidth: showingDetail ? 1060 : 680, minHeight: 640)
        .animation(.spring(response: 0.35, dampingFraction: 0.85), value: showingDetail)
    }
}
