# Starts RuneLite directly in developer mode so the side-loaded bridge plugin loads.
# See README.md for why the official launcher cannot do this, and for how a Jagex
# account logs in here via ~/.runelite/credentials.properties.

$java = Join-Path $env:LOCALAPPDATA 'RuneLite\jre\bin\java.exe'
$repo = Join-Path $env:USERPROFILE '.runelite\repository2'

# After a client update the launcher leaves the old jars next to the new ones, and a
# wildcard classpath would load both. Keep only the newest version of each artifact.
# Anything after the version (-runtime, -natives-windows, -jre) is part of the artifact
# name. Names that do not fit name-version.jar at all are kept as they are.
$jars = Get-ChildItem $repo -Filter *.jar | ForEach-Object {
    $jar = [pscustomobject]@{ Key = $_.Name; Version = [version]'0.0'; Path = $_.FullName }
    if ($_.Name -match '^(?<name>.+?)-(?<ver>\d+(\.\d+){1,3})(?<suffix>-[a-z][\w-]*)?\.jar$') {
        $jar.Key = $Matches.name + $Matches.suffix
        $jar.Version = [version]$Matches.ver
    }
    $jar
} | Group-Object Key | ForEach-Object {
    ($_.Group | Sort-Object Version -Descending | Select-Object -First 1).Path
}

& $java `
    -ea `
    --add-opens=java.base/java.net=ALL-UNNAMED `
    --add-opens=java.base/java.io=ALL-UNNAMED `
    -Xmx768m -Xss2m '-Dsun.java2d.d3d=true' '-Dsun.java2d.opengl=false' `
    -cp ($jars -join ';') `
    net.runelite.client.RuneLite --developer-mode
