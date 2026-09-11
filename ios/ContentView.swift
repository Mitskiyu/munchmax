import Foundation
import SwiftUI

enum Config {
    #if DEBUG
        static let port = Bundle.main.object(forInfoDictionaryKey: "PORT") as? String ?? "8080"
        static let baseURL = URL(string: "http://localhost:\(port)")!
    #endif
}

struct Response: Codable {
    var data: [Restaurant]
}

struct Restaurant: Codable, Identifiable {
    let id: UUID
    let name: String
    let kind: String
    let cuisines: [String]
    let street: String
    let housenumber: String
    let postcode: String
    let city: String
    let website: String
    let phone: String
    let openingHours: String
}

struct ContentView: View {
    func loadData() async {
        let url = URL(string: "\(Config.baseURL)/restaurants?limit=100")!

        do {
            let (data, _) = try await URLSession.shared.data(from: url)

            let decoder = JSONDecoder()
            decoder.keyDecodingStrategy = .convertFromSnakeCase
            restaurants = try decoder.decode(Response.self, from: data).data
        } catch {
            print("\(error)")
        }
    }

    @State private var restaurants = [Restaurant]()

    var body: some View {
        List(restaurants) { r in
            VStack(alignment: .leading) {
                Text(r.name)
                    .font(.headline)
                Text(r.kind)
            }
        }.task {
            await loadData()
        }
    }
}

#Preview {
    ContentView()
}
