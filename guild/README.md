# Willow Desktop Pet (`v0.2.0`)

**Willow** is a local Linux desktop companion (`KDE/X11`) featuring seamless 8-second transparent WebM video loops, a modular animation manifest (`assets/animations.json`), an interactive **Google Flow Dress-Up & Wardrobe Studio** (24+ items across 4 themes and 6 anatomical slots), and a Three.js 3D mode.

**Launch:** double-click [Start Lumen.desktop](Start%20Lumen.desktop) (or run `npm start`, or `npm run wardrobe` to open the Wardrobe Studio directly). The self-contained packaged app is in `dist/Lumen-linux-x64`; its runtime is included. Normal use requires no code, terminal, account, or installation step.

Click Willow to interact. Drag her to move. Hover for controls (`✦` opens the Dress-Up Wardrobe Studio), or right-click for **Playback Speed & 8s Cycle** (`50%`–`125%` + automatic 8-second cycle pacing), **Animations** (trigger any clip on demand or edit `animations.json`), video/3D mode, size, sleep, artwork folders, and Quit. The tray icon provides another route to the menu. Nothing starts automatically at login.

## Artwork, 8-Second Seamless Loops & Modular Wardrobe

Willow's master still is in `assets/source_art/character.png` (`720×1280` `9:16` on `#FFFFFF`) and her primary idle animation is in `assets/raw_videos/idle.mp4` $\rightarrow$ `assets/processed_webm/idle.webm`.

1. **Seamless Loop Polisher (`pipeline/ingest.cjs` v8)**: Automatically trims stationary ease-in/ease-out frames at the ends of Veo clips and applies a 14-frame circular cosine premultiplied-alpha cross-dissolve across the loop wrap so `idle.webm` loops with zero pause or hitch.
2. **8-Second Default Cycle & Speed Control**: Shorter 4-second Veo clips are automatically paced to a calm **8-second cycle** (`0.5x`) by default, and can be adjusted live from the right-click menu.
3. **Modular Animation Manifest (`assets/animations.json`)**: Drop `click.mp4`, `wave.mp4`, `random1.mp4`, `hover.mp4`, `drag.mp4`, `sleep.mp4`, or any custom clip mapped in `assets/animations.json` into `assets/raw_videos/` and click **Reload artwork**.
4. **Dress-Up Wardrobe Studio (`✦`)**: Mix and match 24+ items across 4 fashion themes, copy tailored Google Flow prompts, and 1-click export `720×1280` `#FFFFFF` Start/End frames (`assets/wardrobe/flow_exports/`).

See the [full artwork & Google Flow guide](docs/ARTWORK-GUIDE.md) for copy/paste 8-second continuous-motion prompts and the Google Flow `Save frame` mid-motion anchor workflow.

## What is verified

60+ automated unit/integration tests and 26 native X11 checks pass on this Linux/KDE/X11 workstation, including the packaged launcher, clear-space click-through, immediate pointer entry/exit, dragging, still preview, transparent WebM with circular cosine loop polishing, modular animation mapping, 8-second cycle auto-pacing, the 6-slot Wardrobe Studio, and a skinned two-clip GLB.

These are bounded local results with synthetic media. Your artwork, long-duration behavior, other GPUs/compositors, and broader monitor/scaling combinations remain unqualified. White-background removal is approximate; true-alpha media avoids its white-edge ambiguity. Native input regions use a finite grid and may clip soft edges. See the [acceptance record](docs/ACCEPTANCE.md) for evidence and retained failures.

## Project documents

- [Critical audit](docs/BLUEPRINT-AUDIT.md)
- [Reconciled implementation specification](docs/IMPLEMENTATION-SPEC.md)
- [Independent code review](docs/CODE-REVIEW.md)
- [Acceptance and recovery record](docs/ACCEPTANCE.md)
- [Pipeline contract and limits](pipeline/README.md)

## Developer reproduction

The application is already built. For a new development checkout, use Node 22.12 or newer, `npm ci`, then `node node_modules/electron/install.js` to provision the pinned development runtime. Run `npm test`; `npm run smoke` opens bounded native test windows and temporarily moves/restores the pointer. `npm run package` creates a new Linux x64 folder and refuses to overwrite an existing package. No command here changes global settings or publishes a release.

Runtime: Electron 45.0.0, Three.js 0.186.1, FFmpeg-static 5.3.0 providing FFmpeg 7.0.2. The native codec version needs a separate update/security review before external distribution; npm audit does not cover its binary internals. FFmpeg's included license and build information are retained with the package.

## Recovery

Quit from the pet or tray menu. Keep the entire folder, especially `assets`, if restoring or moving the app. Settings and logs for this workstation's launcher live in `.runtime`. The independent portable package uses its user-data artwork folder, shown by **Open New Artwork folder**; it does not automatically read this source directory. No artwork is removed during a rebuild or failed conversion.

## LFS Suite `v1.1.0` Capsule Alignment (`3-lfs-aegis-linux/capsules/willow-desktop-pet`, `PA-14`)

This standalone repository serves as the upstream source for the **Willow Desktop Pet `v0.2.0` (`PA-14`)** capsule integrated into `3-lfs-aegis-linux/capsules/willow-desktop-pet` under the [LFS Ecosystem Plug-In & Synergy Standard](../../governance/LFS-ECOSYSTEM-PLUGIN-STANDARD.md).
