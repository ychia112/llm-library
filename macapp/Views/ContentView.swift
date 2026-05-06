import SwiftUI

struct ContentView: View {
    @State private var viewModel = AppViewModel()
    @State private var apiClient = APIClient.shared
    
    var body: some View {
        NavigationSplitView {
            // 左側窄欄：導航入口
            List(selection: $viewModel.selection) {
                NavigationLink(value: NavigationItem.search) {
                    Label("Chat", systemImage: "message")
                }
                NavigationLink(value: NavigationItem.library) {
                    Label("Library", systemImage: "books.vertical")
                }
            }
            .listStyle(.sidebar)
            .navigationSplitViewColumnWidth(min: 150, ideal: 180, max: 200)
            
            // 底部顯示連線狀態
            .safeAreaInset(edge: .bottom) {
                HStack {
                    Circle()
                        .fill(apiClient.isConnected ? .green : .red)
                        .frame(width: 8, height: 8)
                    Text(apiClient.isConnected ? "Online" : "Offline")
                        .font(.caption2)
                        .help(apiClient.isConnected ? "Connected to 127.0.0.1:8765" : "Connection failed. Hover for info.")
                    Spacer()
                }
                .padding()
                .onTapGesture {
                    // 點擊可以嘗試重新整理
                    Task { await viewModel.loadRecent() }
                }
            }
        } content: {
            // 中間主要區域
            Group {
                switch viewModel.selection {
                case .search:
                    ChatView(selectedSessionID: $viewModel.selectedSessionID)
                case .library:
                    LibraryView(selectedSessionID: $viewModel.selectedSessionID)
                case .none:
                    Text("Select a tool")
                }
            }
        } detail: {
            // 右側詳細區域
            SessionDetailView(sessionID: viewModel.selectedSessionID)
        }
        .frame(minWidth: 1000, minHeight: 650)
    }
}
