/**
 * EVE Gatekeeper Desktop
 * Preload script - bridges main and renderer processes
 */
const { contextBridge, ipcRenderer } = require('electron');

// Valid IPC channels for security
const SEND_CHANNELS = [
  'navigate',
  'settings',
  'show-notification',
  'kill-alert',
  'minimize-to-tray',
];

const RECEIVE_CHANNELS = ['fromMain', 'navigate'];

const INVOKE_CHANNELS = ['get-window-state'];

// Expose protected methods to the renderer process
contextBridge.exposeInMainWorld('electronAPI', {
  // App info
  platform: process.platform,
  isElectron: true,

  // Version info
  versions: {
    node: process.versions.node,
    chrome: process.versions.chrome,
    electron: process.versions.electron,
  },

  // IPC communication - send messages to main process
  send: (channel, data) => {
    if (SEND_CHANNELS.includes(channel)) {
      ipcRenderer.send(channel, data);
    } else {
      console.warn(`[Preload] Invalid send channel: ${channel}`);
    }
  },

  // IPC communication - receive messages from main process
  receive: (channel, func) => {
    if (RECEIVE_CHANNELS.includes(channel)) {
      const subscription = (event, ...args) => func(...args);
      ipcRenderer.on(channel, subscription);
      // Return unsubscribe function
      return () => ipcRenderer.removeListener(channel, subscription);
    }
    console.warn(`[Preload] Invalid receive channel: ${channel}`);
    return () => {};
  },

  // IPC communication - invoke and wait for response
  invoke: async (channel, ...args) => {
    if (INVOKE_CHANNELS.includes(channel)) {
      return ipcRenderer.invoke(channel, ...args);
    }
    console.warn(`[Preload] Invalid invoke channel: ${channel}`);
    return null;
  },

  // Convenience methods for common operations
  showNotification: (title, body, options = {}) => {
    ipcRenderer.send('show-notification', { title, body, options });
  },

  sendKillAlert: (alert) => {
    ipcRenderer.send('kill-alert', alert);
  },

  minimizeToTray: () => {
    ipcRenderer.send('minimize-to-tray');
  },

  getWindowState: async () => {
    return ipcRenderer.invoke('get-window-state');
  },

  // Listen for navigation events from main process (tray menu, etc.)
  onNavigate: (callback) => {
    const subscription = (event, screen) => callback(screen);
    ipcRenderer.on('navigate', subscription);
    return () => ipcRenderer.removeListener('navigate', subscription);
  },
});

// Log that we're running in Electron
console.log('[EVE Gatekeeper] Running in Electron desktop mode');
