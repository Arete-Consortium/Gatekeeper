# EVE Gatekeeper Desktop

Electron desktop application for EVE Gatekeeper.

## Overview

This desktop app wraps the React Native web build, providing a native desktop experience on Windows, macOS, and Linux.

## Development

```bash
# Install dependencies
npm install

# Start in development mode (requires mobile app dev server)
cd ../mobile && npm start  # In one terminal
npm run dev                 # In another terminal
```

## Building

```bash
# Build for current platform
npm run build

# Build for specific platforms
npm run build:win    # Windows (NSIS installer)
npm run build:mac    # macOS (DMG)
npm run build:linux  # Linux (AppImage)
```

## Architecture

- **main.js** - Electron main process, window management, native menus
- **preload.js** - Context bridge for secure IPC between main and renderer
- **web-build/** - Production web build from mobile app (created during build)

## Features

- Native window with custom menu
- External link handling (opens in default browser)
- Keyboard shortcuts (Cmd/Ctrl+, for Settings)
- Development mode with DevTools
- Cross-platform builds

## Requirements

- Node.js 18+
- npm 9+
- For building: platform-specific tools (see electron-builder docs)
