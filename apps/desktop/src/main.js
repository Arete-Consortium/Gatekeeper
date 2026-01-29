/**
 * EVE Gatekeeper Desktop
 * Electron main process
 */
const {
  app,
  BrowserWindow,
  Menu,
  shell,
  Tray,
  nativeImage,
  Notification,
  ipcMain,
} = require('electron');
const path = require('path');

// Check if running in development mode
const isDev = process.argv.includes('--dev') || !app.isPackaged;

let mainWindow;
let tray = null;
let isQuitting = false;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    title: 'EVE Gatekeeper',
    backgroundColor: '#000000',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
    icon: path.join(__dirname, '../assets/icon.png'),
  });

  // Load the app
  if (isDev) {
    // Development: load from Expo dev server
    mainWindow.loadURL('http://localhost:8081');
    mainWindow.webContents.openDevTools();
  } else {
    // Production: load from built web files
    mainWindow.loadFile(path.join(__dirname, '../web-build/index.html'));
  }

  // Handle external links
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  // Minimize to tray instead of closing
  mainWindow.on('close', (event) => {
    if (!isQuitting) {
      event.preventDefault();
      mainWindow.hide();
      return false;
    }
    return true;
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// Create system tray
function createTray() {
  // Create tray icon (use a smaller icon for tray)
  const iconPath = path.join(__dirname, '../assets/icon.png');
  let trayIcon = nativeImage.createFromPath(iconPath);

  // Resize for tray (16x16 on most platforms, 22x22 on some Linux)
  trayIcon = trayIcon.resize({ width: 16, height: 16 });

  tray = new Tray(trayIcon);
  tray.setToolTip('EVE Gatekeeper');

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Show Window',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
        }
      },
    },
    {
      label: 'Plan Route',
      accelerator: 'CmdOrCtrl+R',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.webContents.send('navigate', 'Route');
        }
      },
    },
    {
      label: 'Fitting Analyzer',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.webContents.send('navigate', 'Fitting');
        }
      },
    },
    {
      label: 'Kill Alerts',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.webContents.send('navigate', 'Alerts');
        }
      },
    },
    { type: 'separator' },
    {
      label: 'Settings',
      accelerator: 'CmdOrCtrl+,',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.webContents.send('navigate', 'Settings');
        }
      },
    },
    { type: 'separator' },
    {
      label: 'Quit',
      accelerator: 'CmdOrCtrl+Q',
      click: () => {
        isQuitting = true;
        app.quit();
      },
    },
  ]);

  tray.setContextMenu(contextMenu);

  // Double-click to show window
  tray.on('double-click', () => {
    if (mainWindow) {
      mainWindow.show();
      mainWindow.focus();
    }
  });
}

// Show native notification
function showNotification(title, body, options = {}) {
  if (Notification.isSupported()) {
    const notification = new Notification({
      title,
      body,
      icon: path.join(__dirname, '../assets/icon.png'),
      silent: options.silent || false,
      urgency: options.urgency || 'normal',
    });

    notification.on('click', () => {
      if (mainWindow) {
        mainWindow.show();
        mainWindow.focus();
      }
      if (options.onClick) {
        options.onClick();
      }
    });

    notification.show();
    return notification;
  }
  return null;
}

// Register IPC handlers
function registerIpcHandlers() {
  // Handle notification requests from renderer
  ipcMain.on('show-notification', (event, { title, body, options }) => {
    showNotification(title, body, options);
  });

  // Handle navigation requests
  ipcMain.on('navigate', (event, screen) => {
    if (mainWindow) {
      mainWindow.webContents.executeJavaScript(`
        window.history.pushState({}, '', '/${screen}');
        window.dispatchEvent(new PopStateEvent('popstate'));
      `);
    }
  });

  // Handle settings updates
  ipcMain.on('settings', (event, settings) => {
    // Store settings or handle as needed
    console.log('Settings updated:', settings);
  });

  // Handle kill alerts from renderer (for background notifications)
  ipcMain.on('kill-alert', (event, alert) => {
    const valueStr = alert.value
      ? ` - ${(alert.value / 1000000).toFixed(0)}M ISK`
      : '';
    showNotification(
      `Kill Alert: ${alert.system}`,
      `${alert.shipType || 'Ship'} destroyed${valueStr}`,
      {
        urgency: 'critical',
        onClick: () => {
          if (alert.zkillUrl) {
            shell.openExternal(alert.zkillUrl);
          }
        },
      }
    );
  });

  // Handle window state requests
  ipcMain.handle('get-window-state', () => {
    if (mainWindow) {
      return {
        isMaximized: mainWindow.isMaximized(),
        isMinimized: mainWindow.isMinimized(),
        isVisible: mainWindow.isVisible(),
        isFocused: mainWindow.isFocused(),
      };
    }
    return null;
  });

  // Handle minimize to tray
  ipcMain.on('minimize-to-tray', () => {
    if (mainWindow) {
      mainWindow.hide();
    }
  });
}

// Helper to navigate to a screen
function navigateToScreen(screen) {
  if (mainWindow) {
    mainWindow.show();
    mainWindow.webContents.send('navigate', screen);
    mainWindow.webContents.executeJavaScript(`
      window.history.pushState({}, '', '/${screen}');
      window.dispatchEvent(new PopStateEvent('popstate'));
    `);
  }
}

// Create application menu
function createMenu() {
  const template = [
    {
      label: 'EVE Gatekeeper',
      submenu: [
        { role: 'about' },
        { type: 'separator' },
        {
          label: 'Settings',
          accelerator: 'CmdOrCtrl+,',
          click: () => navigateToScreen('Settings'),
        },
        { type: 'separator' },
        {
          label: 'Minimize to Tray',
          accelerator: 'CmdOrCtrl+M',
          click: () => {
            if (mainWindow) {
              mainWindow.hide();
            }
          },
        },
        { type: 'separator' },
        { role: 'hide' },
        { role: 'hideOthers' },
        { role: 'unhide' },
        { type: 'separator' },
        {
          label: 'Quit',
          accelerator: 'CmdOrCtrl+Q',
          click: () => {
            isQuitting = true;
            app.quit();
          },
        },
      ],
    },
    {
      label: 'Navigate',
      submenu: [
        {
          label: 'Home',
          accelerator: 'CmdOrCtrl+1',
          click: () => navigateToScreen('Home'),
        },
        {
          label: 'Route Planner',
          accelerator: 'CmdOrCtrl+2',
          click: () => navigateToScreen('Route'),
        },
        {
          label: 'Fitting Analyzer',
          accelerator: 'CmdOrCtrl+3',
          click: () => navigateToScreen('Fitting'),
        },
        {
          label: 'Kill Alerts',
          accelerator: 'CmdOrCtrl+4',
          click: () => navigateToScreen('Alerts'),
        },
        {
          label: 'Settings',
          accelerator: 'CmdOrCtrl+5',
          click: () => navigateToScreen('Settings'),
        },
      ],
    },
    {
      label: 'Edit',
      submenu: [
        { role: 'undo' },
        { role: 'redo' },
        { type: 'separator' },
        { role: 'cut' },
        { role: 'copy' },
        { role: 'paste' },
        { role: 'selectAll' },
      ],
    },
    {
      label: 'View',
      submenu: [
        { role: 'reload' },
        { role: 'forceReload' },
        { role: 'toggleDevTools' },
        { type: 'separator' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
        { type: 'separator' },
        { role: 'togglefullscreen' },
      ],
    },
    {
      label: 'Window',
      submenu: [
        { role: 'minimize' },
        { role: 'zoom' },
        {
          label: 'Minimize to Tray',
          click: () => {
            if (mainWindow) {
              mainWindow.hide();
            }
          },
        },
        { type: 'separator' },
        { role: 'close' },
      ],
    },
    {
      label: 'Help',
      submenu: [
        {
          label: 'Keyboard Shortcuts',
          accelerator: 'CmdOrCtrl+/',
          click: () => {
            const shortcuts = `
Keyboard Shortcuts:

Navigation:
  Cmd/Ctrl+1  Home
  Cmd/Ctrl+2  Route Planner
  Cmd/Ctrl+3  Fitting Analyzer
  Cmd/Ctrl+4  Kill Alerts
  Cmd/Ctrl+5  Settings
  Cmd/Ctrl+,  Settings

Window:
  Cmd/Ctrl+M  Minimize to Tray
  Cmd/Ctrl+Q  Quit

View:
  Cmd/Ctrl+R  Reload
  Cmd/Ctrl++  Zoom In
  Cmd/Ctrl+-  Zoom Out
  Cmd/Ctrl+0  Reset Zoom
            `.trim();

            const { dialog } = require('electron');
            dialog.showMessageBox(mainWindow, {
              type: 'info',
              title: 'Keyboard Shortcuts',
              message: shortcuts,
              buttons: ['OK'],
            });
          },
        },
        { type: 'separator' },
        {
          label: 'EVE Online ESI Docs',
          click: () => {
            shell.openExternal('https://esi.evetech.net/ui/');
          },
        },
        {
          label: 'zKillboard',
          click: () => {
            shell.openExternal('https://zkillboard.com/');
          },
        },
        { type: 'separator' },
        {
          label: 'GitHub Repository',
          click: () => {
            shell.openExternal('https://github.com/AreteDriver/EVE_Gatekeeper');
          },
        },
      ],
    },
  ];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}

// App lifecycle
app.whenReady().then(() => {
  createWindow();
  createMenu();
  createTray();
  registerIpcHandlers();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    } else if (mainWindow) {
      mainWindow.show();
    }
  });
});

// Set isQuitting flag before quitting
app.on('before-quit', () => {
  isQuitting = true;
});

app.on('window-all-closed', () => {
  // On macOS, keep app running in background (tray)
  // On other platforms, quit only if user explicitly quits
  if (process.platform !== 'darwin' && isQuitting) {
    app.quit();
  }
});

// Security: prevent new window creation
app.on('web-contents-created', (event, contents) => {
  contents.on('new-window', (event, navigationUrl) => {
    event.preventDefault();
    shell.openExternal(navigationUrl);
  });
});
