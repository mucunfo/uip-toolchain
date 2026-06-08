from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_windows_installer_launcher_calls_interactive_powershell():
    launcher = ROOT / "instalar-ccs-uip.cmd"
    text = launcher.read_text(encoding="utf-8")

    assert launcher.is_file()
    assert "ExecutionPolicy Bypass" in text
    assert "tools\\install-ccs-uip.ps1" in text
    assert "pause" in text.lower()


def test_interactive_installer_is_user_level_and_no_admin():
    script = (ROOT / "tools" / "install-ccs-uip.ps1").read_text(encoding="utf-8")

    assert 'pip", "install", "--user", "-e"' in script
    assert "@uipath/cli@1" in script
    assert "install-dotnet-sdk-portable.cmd" in script
    assert "SetEnvironmentVariable(\"PATH\"" in script
    assert "-Verb RunAs" not in script
    assert "Start-Process" not in script


def test_interactive_installer_captures_native_stderr_without_powershell_redirection():
    script = (ROOT / "tools" / "install-ccs-uip.ps1").read_text(encoding="utf-8")

    assert "System.Diagnostics.ProcessStartInfo" in script
    assert "RedirectStandardOutput = $true" in script
    assert "RedirectStandardError = $true" in script
    assert "Invoke-Native" in script
    assert "2>&1" not in script


def test_readme_documents_easy_install_flow():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "Instalacao facil em computador novo" in readme
    assert "instalar-ccs-uip.cmd" in readme
    assert "ccs-uip-publish --help" in readme
