"""Compatibility and environment bootstrap helper."""

import ctypes
import os
import sys


def bootstrap_nixos_libs() -> None:
    """Preload standard C/C++ libraries on NixOS via nix-ld if needed.
    
    Prevents 'libstdc++.so.6: cannot open shared object file' when running binary
    wheels (numpy, torch) on NixOS systems.
    """
    if sys.platform != "linux":
        return

    candidate_dirs = [
        os.environ.get("NIX_LD_LIBRARY_PATH", ""),
        "/run/current-system/sw/share/nix-ld/lib",
    ]
    common_libs = [
        "libgcc_s.so.1",
        "libstdc++.so.6",
        "libz.so.1",
    ]

    for cdir in candidate_dirs:
        if cdir and os.path.isdir(cdir):
            for lib_name in common_libs:
                lib_path = os.path.join(cdir, lib_name)
                if os.path.exists(lib_path):
                    try:
                        ctypes.CDLL(lib_path, mode=ctypes.RTLD_GLOBAL)
                    except Exception:
                        pass
