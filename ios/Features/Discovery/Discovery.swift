import OpenAPIURLSession
import SwiftUI

extension Components.Schemas.Restaurant: Identifiable {}
extension Components.Schemas.ErrorResponse.CodePayload: Error {}
extension String: Error {}

typealias Restaurant = Components.Schemas.Restaurant
typealias ErrorCode = Components.Schemas.ErrorResponse.CodePayload

struct Discovery: View {

    @State private var restaurants: [Restaurant] = []

    var body: some View {
        List(restaurants) { r in
            VStack(alignment: .leading) {
                Text(r.name)
                    .font(.headline)
                Text(r.kind)
            }
        }.task {
            do {
                restaurants = try await DiscoveryClient.shared.restaurants()
            } catch let code as ErrorCode {
                switch code {
                case .invalidCursor, .invalidLimit:
                    break
                case .internalError:
                    break
                }
            } catch {
                print(error)
            }
        }
    }
}

struct DiscoveryClient {

    static let shared = DiscoveryClient()
    private let client: Client

    private init() {
        client = Client(
            serverURL: Config.url,
            transport: URLSessionTransport()
        )
    }

    func restaurants(cursor: UUID? = nil, limit: Int? = nil) async throws
        -> [Restaurant]
    {
        let resp = try await client.listRestaurants(
            query: .init(after: cursor?.uuidString, limit: limit)
        )

        switch resp {
        case .ok(let ok):
            let payload = try ok.body.json
            return payload.data

        case .badRequest(let err):
            let payload = try err.body.json
            print("client error: \(payload.message)")
            throw payload.code

        case .internalServerError(let err):
            let payload = try err.body.json
            print("server error: \(payload.message)")
            throw payload.code

        case .undocumented(let statusCode, _):
            print(statusCode)
            throw "unexpected status: \(statusCode)"
        }
    }
}
