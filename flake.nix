{
  description = "gh-agent-pr - GitHub PR merge confidence evaluator";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      supportedSystems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forEachSupportedSystem = f: nixpkgs.lib.genAttrs supportedSystems (system: f {
        inherit system;
        pkgs = import nixpkgs { inherit system; };
      });
    in
    {
      packages = forEachSupportedSystem ({ pkgs, ... }:
        let
          laya = pkgs.python3Packages.buildPythonPackage rec {
            pname = "laya";
            version = "0.3.20";
            format = "setuptools";

            src = pkgs.python3Packages.fetchPypi {
              inherit pname version;
              hash = "sha256-aS3hNGzwI5u3u8/98M+9U4wkg0+Lxh6bYPQQZGXAM8k=";
            };

            doCheck = false;

            propagatedBuildInputs = with pkgs.python3Packages; [
              torch
              transformers
              safetensors
              huggingface-hub
              numpy
            ];
          };

          gh-agent-pr = pkgs.python3Packages.buildPythonApplication {
            pname = "gh-agent-pr";
            version = "0.1.0";
            pyproject = true;

            src = pkgs.lib.cleanSourceWith {
              src = ./.;
              filter = name: type:
                let
                  base = baseNameOf name;
                in
                !(base == ".venv" || base == ".direnv" || base == ".pytest_cache" || base == ".git" || base == "result");
            };

            build-system = [
              pkgs.python3Packages.setuptools
            ];

            dependencies = [
              laya
              pkgs.python3Packages.rich
              pkgs.python3Packages.pyyaml
            ];

            makeWrapperArgs = [
              "--prefix PATH : ${pkgs.lib.makeBinPath [ pkgs.gh ]}"
            ];

            doCheck = false;
          };
        in
        {
          default = gh-agent-pr;
          inherit gh-agent-pr laya;
        }
      );

      apps = forEachSupportedSystem ({ system, ... }: {
        default = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/gh-agent-pr";
        };
        gh-agent-pr = {
          type = "app";
          program = "${self.packages.${system}.gh-agent-pr}/bin/gh-agent-pr";
        };
      });

      devShells = forEachSupportedSystem ({ system, pkgs }: {
        default = pkgs.mkShell {
          packages = [
            self.packages.${system}.default
            pkgs.python3
            pkgs.python3Packages.pip
            pkgs.python3Packages.virtualenv
            pkgs.python3Packages.pytest
            pkgs.gh
          ];

          shellHook = ''
            if [ -d .venv ]; then
              source .venv/bin/activate
            fi
          '';
        };
      });
    };
}
