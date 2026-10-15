{
  description = "Lucism Monitor TUI";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs =
    { self, nixpkgs }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
      ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
    in {
      packages = forAllSystems ( system:
        let
          pkgs = import nixpkgs { inherit system; };

          app = pkgs.python3Packages.buildPythonApplication {
            pname = "lucism_monitor_tui";
            version = "0.1.0";
            pyproject = true;
            src = ./.;

            build-system = with pkgs.python3Packages; [
              setuptools
            ];

            dependencies = with pkgs.python3Packages; [
              aiohttp
              certifi
              pydantic
              python-dotenv
              textual
            ];
          };
        in
        {
          default = app;
          # app.${system}.default = {
          #   type = "app";
          #   program = "${app}/bin/lucism_monitor_tui";
          # };
        }
      );
    };
}
