import Foundation

enum Config {
    #if DEBUG
        static let url: URL = {
            let port =
                Bundle.main.object(forInfoDictionaryKey: "PORT") as? String
                ?? "8080"
            return URL(string: "http://localhost:\(port)")!
        }()
    #endif
}
