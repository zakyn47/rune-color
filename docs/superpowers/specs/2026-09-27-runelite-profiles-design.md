# Per-script RuneLite profiles (design)

Date: 2026-09-27. Status: awaiting review.

## Goal

Each bot script ships with the RuneLite profile it was built and tested against.
When the user selects a script in the RuneColor UI, the running RuneLite client
switches to that profile, with no restart or relogin. A UI checkbox lets the user
opt out and keep their own profile.

## Decisions

- The switch happens live, inside the client, through the RuneColor Bridge
  plug-in.
- The bridge starts when the UI starts, not when a script starts.
- Profiles are captured by the developer and committed with the script. There is
  no capture UI.
- The opt-out checkbox is remembered between launches.
- `src/rscolorprofile.properties` stays as a generic starting point. Script
  profiles live beside it in `src/profiles/`.

## Profiles in the repo

- One file per script: `src/profiles/<script>.properties`. The first is
  `src/profiles/power_chopper.properties`, taken from the client's current
  profile ("Imported Profile").
- Window-geometry keys are stripped when a profile is captured
  (`runelite.clientBounds`, `runelite.clientMaximized`). Stripping alone is not
  enough: RuneLite re-applies the bounds of the profile it switches to, and without
  any it falls back to `runelite.gameSize`, shrinking the window (seen live: 1750x1073
  became 1074x585). The plug-in therefore imports a temporary copy of the file that
  carries the client's current `runelite.clientBounds`, so the window stays as it is.
- Every script profile must enable the bridge (`runelite.runecolorbridgeplugin=true`).
  Switching profiles also switches which plug-ins are enabled, so a profile
  without it would turn off the bridge that asked for the switch. A unit test
  checks every file in `src/profiles/` for this key and for the stripped keys.
- A script names its profile with a class attribute on `Bot`:
  `runelite_profile: Optional[str] = None`. `OSRSPowerChopper` sets
  `"power_chopper"`.
- In RuneLite the profile is called `RuneColor - <bot_title>`, e.g.
  "RuneColor - Power Chopper & Firemaking".

## Python to plug-in

The plug-in already POSTs a snapshot every tick. The reply to that POST becomes
JSON that states the wanted profile:

```json
{"profile": {"name": "RuneColor - Power Chopper & Firemaking",
             "path": "C:\\Users\\...\\src\\profiles\\power_chopper.properties"}}
```

or `{"profile": null}` when no profile is wanted. It is a declared state, not a
command, so a lost reply is corrected by the next one.

The snapshot gains an optional field `profile`: the name of the client's active
profile. Python uses it to confirm the switch. The schema stays at 1 because the
field is optional, as for `fire` and `idle` before it. An older plug-in ignores
the reply body and sends no `profile` field.

`BridgeAPI` gains `request_profile(name, path)`, `clear_profile()` and an
`active_profile` property.

## Plug-in

A new class, `ProfileSwitcher`, owns the switch. `SnapshotPublisher` hands it
each reply body. When the wanted profile's name differs from the active one,
`ProfileSwitcher` runs this on its own single-thread executor, never on the
client thread:

1. `profileManager.lock()`, then find the profile by name, or create it.
2. `configManager.importAndMigrate(lock, file, profile)`, the same import that
   RuneLite's Profiles panel uses. The repo file is the source of truth, so a
   change made in the client to a RuneColor profile is overwritten on the next
   switch.
3. `configManager.switchProfile(profile)`.

While a switch is in progress, further requests for the same name are ignored.
A failed switch is logged once and retried only when the wanted profile changes,
so a broken file can't cause a switch loop. A null profile never touches the
client, and there is no switch back.

`ProfileManager` and `ConfigManager` are injected. Both are public in RuneLite
1.12.38, which the plug-in builds against.

## UI

- The bridge is attached when the app starts (`BridgeAPI.shared(port=8099)`), so
  the profile reply works before a script runs. On script select, the controller
  calls `attach_bridge()` on a `RuneLiteBot`, which picks up the same shared
  instance. Scripts started from the UI then use the plug-in's data, as the live
  tests already do. Until now they read the screen only.
- The script info panel gets a checkbox, "Use my own RuneLite profile",
  unchecked by default. Its value is stored with `utilities.settings` under
  `use_own_runelite_profile`.
- On script select, if the box is unchecked and the script has a profile, the
  controller calls `request_profile`. Otherwise it calls `clear_profile`.
- Ticking the box calls `clear_profile`. Unticking it requests the selected
  script's profile again.
- The log says "Switched RuneLite to profile X" once `active_profile` matches.
  If it doesn't match within 10 s, the log warns that the bridge plug-in isn't
  answering.

## Testing

- Python unit tests: the reply payload for requested and cleared profiles,
  `active_profile` parsing, the controller's select and checkbox logic (with a
  fake bridge), and the profile-file checks above.
- Java unit tests: `ProfileSwitcher` switches when the names differ, not when they
  match, ignores null, and doesn't retry a failed file until the request changes.
  The managers are mocked.
- Live check: select the Power Chopper with the client on another profile. The
  active profile becomes "RuneColor - Power Chopper & Firemaking", the window
  size stays the same, and the bridge keeps pushing snapshots after the switch.

## Out of scope

- A capture UI or capture tool.
- Switching back to the user's profile when a script is deselected.
- Profiles for scripts other than the Power Chopper. They are added as those
  scripts are built.
