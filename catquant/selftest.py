"""CatQuant environment self-test.

Usage:
    python -m catquant.selftest
    from catquant.selftest import check; print(check())
"""

import json
import os
import sys

__all__ = ["check"]


def _check(name: str, fn, required: bool = True):
    """Run a single check. Returns (pass: bool, message: str)."""
    try:
        msg = fn()
        print(f"[PASS] {name} {msg}")
        return True, msg
    except Exception as e:
        tag = "FAIL" if required else "SKIP"
        print(f"[{tag}] {name} ({e})")
        return False, str(e)


def check() -> dict:
    """Run all environment checks. Returns structured result dict."""

    result = {
        "status": "ready",
        "python": False,
        "numpy": False,
        "pandas": False,
        "matplotlib": False,
        "dotenv": False,
        "env_file": False,
        "facecat_url": False,
        "facecat_api": False,
        "cache_writable": False,
        "tdx": False,
    }

    # Python version
    ok, _ = _check("python", lambda: f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    if sys.version_info < (3, 9):
        result["status"] = "error"
        print("  Python >= 3.9 required")
    result["python"] = ok and sys.version_info >= (3, 9)

    # numpy
    def _numpy():
        import numpy
        return numpy.__version__
    ok, _ = _check("numpy", _numpy)
    result["numpy"] = ok

    # pandas
    def _pandas():
        import pandas
        return pandas.__version__
    ok, _ = _check("pandas", _pandas)
    result["pandas"] = ok

    # matplotlib
    def _matplotlib():
        import matplotlib
        return matplotlib.__version__
    ok, _ = _check("matplotlib", _matplotlib)
    result["matplotlib"] = ok

    # python-dotenv
    def _dotenv():
        import dotenv
        return getattr(dotenv, "__version__", "installed")
    ok, _ = _check("python-dotenv", _dotenv)
    result["dotenv"] = ok

    # .env file
    def _env_file():
        from dotenv import find_dotenv, load_dotenv
        path = find_dotenv(usecwd=True)
        if not path:
            raise FileNotFoundError("no .env found")
        load_dotenv(path)
        return path
    ok, _ = _check(".env", _env_file)
    result["env_file"] = ok

    # FaceCat_URL
    def _facecat_url():
        url = os.environ.get("FaceCat_URL", "")
        if not url:
            raise ValueError("not set")
        return url
    ok, _ = _check("facecat_url", _facecat_url)
    result["facecat_url"] = ok

    # FaceCat API connectivity
    def _facecat_api():
        from catquant.facecat import fetch_kline
        bars = fetch_kline("600000.SH", count=5, verify_ssl=False)
        if not bars:
            raise ConnectionError("0 bars returned")
        return f"({len(bars)} bars)"
    ok, _ = _check("facecat_api", _facecat_api)
    result["facecat_api"] = ok

    # Cache directory writable
    def _cache_dir():
        cache_dir = os.environ.get("CACHE_DIR", "./cache")
        os.makedirs(cache_dir, exist_ok=True)
        if not os.access(cache_dir, os.W_OK):
            raise PermissionError(f"{cache_dir} not writable")
        return cache_dir
    ok, _ = _check("cache_dir", _cache_dir)
    result["cache_writable"] = ok

    # TDX (optional)
    def _tdx():
        tdx_dir = os.environ.get("TDX_DIR", "")
        if not tdx_dir:
            raise ValueError("not set, optional")
        import glob
        day_files = glob.glob(os.path.join(tdx_dir, "vipdoc", "**", "*.day"), recursive=True)
        return f"{len(day_files)} .day files"
    ok, _ = _check("tdx_dir", _tdx, required=False)
    result["tdx"] = ok

    # Chart capability (matplotlib + Agg backend)
    result["chart"] = result["matplotlib"]

    # Overall status
    required_keys = ["python", "numpy", "pandas", "matplotlib", "dotenv", "facecat_api"]
    if not all(result[k] for k in required_keys):
        result["status"] = "error"

    print("---")
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    check()
