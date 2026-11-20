param(
    [string]$ProcessName = 'Orveta',
    [Parameter(Mandatory = $true)][string]$OutputPath
)

# Capture an already running window. No application is launched by this script.
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class OrvetaWindowCapture {
    [StructLayout(LayoutKind.Sequential)] public struct Rect { public int Left, Top, Right, Bottom; }
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out Rect r);
    [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr dc, uint flags);
}
'@
$window = Get-Process -Name $ProcessName -ErrorAction Stop | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
if (-not $window) { throw "No visible window was found for process $ProcessName." }
$rect = New-Object OrvetaWindowCapture+Rect
if (-not [OrvetaWindowCapture]::GetWindowRect($window.MainWindowHandle, [ref]$rect)) { throw 'Could not read window bounds.' }
$width = $rect.Right - $rect.Left
$height = $rect.Bottom - $rect.Top
if ($width -le 0 -or $height -le 0) { throw 'Window has invalid dimensions.' }
$bitmap = New-Object System.Drawing.Bitmap($width, $height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$dc = $graphics.GetHdc()
try {
    if (-not [OrvetaWindowCapture]::PrintWindow($window.MainWindowHandle, $dc, 2)) { throw 'Windows could not capture the window.' }
} finally {
    $graphics.ReleaseHdc($dc)
    $graphics.Dispose()
}
try { $bitmap.Save($OutputPath, [System.Drawing.Imaging.ImageFormat]::Png) } finally { $bitmap.Dispose() }
