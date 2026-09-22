{
  description = "dev flake";

  inputs = {
    nixpkgs.url = "https://channels.nixos.org/nixpkgs-unstable/nixexprs.tar.zst";
  };

  outputs = {
    self,
    nixpkgs,
  }: let
    inherit (nixpkgs) lib;

    systems = [
      "x86_64-linux"
      "aarch64-darwin"
    ];

    forAllSystems = f: lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
  in {
    devShells = forAllSystems (pkgs: {
      default = pkgs.mkShellNoCC {
        packages = with pkgs; [
          go
          uv
        ];
      };
    });
  };
}
