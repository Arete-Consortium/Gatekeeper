/**
 * Tests for desktop app configuration
 */
const fs = require('fs');
const path = require('path');

describe('Desktop App Configuration', () => {
  describe('package.json', () => {
    let packageJson;

    beforeAll(() => {
      const packagePath = path.join(__dirname, '..', 'package.json');
      packageJson = JSON.parse(fs.readFileSync(packagePath, 'utf8'));
    });

    it('should have correct app name', () => {
      expect(packageJson.name).toBe('eve-gatekeeper-desktop');
    });

    it('should have a version', () => {
      expect(packageJson.version).toMatch(/^\d+\.\d+\.\d+$/);
    });

    it('should have main entry point', () => {
      expect(packageJson.main).toBe('src/main.js');
    });

    it('should have build configuration', () => {
      expect(packageJson.build).toBeDefined();
      expect(packageJson.build.appId).toBe('com.evegatekeeper.desktop');
      expect(packageJson.build.productName).toBe('EVE Gatekeeper');
    });

    it('should have platform build targets', () => {
      expect(packageJson.build.mac).toBeDefined();
      expect(packageJson.build.win).toBeDefined();
      expect(packageJson.build.linux).toBeDefined();
    });

    it('should have required scripts', () => {
      expect(packageJson.scripts.start).toBeDefined();
      expect(packageJson.scripts.dev).toBeDefined();
      expect(packageJson.scripts.build).toBeDefined();
      expect(packageJson.scripts.test).toBeDefined();
    });

    it('should have electron as dev dependency', () => {
      expect(packageJson.devDependencies.electron).toBeDefined();
    });
  });

  describe('main.js', () => {
    let mainJsPath;
    let mainJsContent;

    beforeAll(() => {
      mainJsPath = path.join(__dirname, '..', 'src', 'main.js');
      mainJsContent = fs.readFileSync(mainJsPath, 'utf8');
    });

    it('should exist', () => {
      expect(fs.existsSync(mainJsPath)).toBe(true);
    });

    it('should import required electron modules', () => {
      expect(mainJsContent).toContain('BrowserWindow');
      expect(mainJsContent).toContain('app');
      expect(mainJsContent).toContain('Menu');
    });

    it('should define createWindow function', () => {
      expect(mainJsContent).toContain('function createWindow()');
    });

    it('should define createMenu function', () => {
      expect(mainJsContent).toContain('function createMenu()');
    });

    it('should handle app ready event', () => {
      expect(mainJsContent).toContain('app.whenReady()');
    });

    it('should handle window-all-closed event', () => {
      expect(mainJsContent).toContain("app.on('window-all-closed'");
    });

    it('should set window dimensions', () => {
      expect(mainJsContent).toContain('width:');
      expect(mainJsContent).toContain('height:');
    });

    it('should have security settings', () => {
      expect(mainJsContent).toContain('nodeIntegration: false');
      expect(mainJsContent).toContain('contextIsolation: true');
    });

    it('should have dev mode detection', () => {
      expect(mainJsContent).toContain('isDev');
    });
  });

  describe('preload.js', () => {
    let preloadJsPath;
    let preloadJsContent;

    beforeAll(() => {
      preloadJsPath = path.join(__dirname, '..', 'src', 'preload.js');
      preloadJsContent = fs.readFileSync(preloadJsPath, 'utf8');
    });

    it('should exist', () => {
      expect(fs.existsSync(preloadJsPath)).toBe(true);
    });

    it('should import contextBridge', () => {
      expect(preloadJsContent).toContain('contextBridge');
    });

    it('should expose electronAPI to renderer', () => {
      expect(preloadJsContent).toContain('electronAPI');
      expect(preloadJsContent).toContain('exposeInMainWorld');
    });

    it('should expose platform info', () => {
      expect(preloadJsContent).toContain('platform');
      expect(preloadJsContent).toContain('isElectron');
    });

    it('should expose version info', () => {
      expect(preloadJsContent).toContain('versions');
    });

    it('should have IPC communication methods', () => {
      expect(preloadJsContent).toContain('send');
      expect(preloadJsContent).toContain('receive');
    });

    it('should validate IPC channels', () => {
      expect(preloadJsContent).toContain('validChannels');
    });
  });

  describe('assets', () => {
    it('should have icon.png', () => {
      const iconPath = path.join(__dirname, '..', 'assets', 'icon.png');
      expect(fs.existsSync(iconPath)).toBe(true);
    });
  });

  describe('Menu structure', () => {
    let mainJsContent;

    beforeAll(() => {
      const mainJsPath = path.join(__dirname, '..', 'src', 'main.js');
      mainJsContent = fs.readFileSync(mainJsPath, 'utf8');
    });

    it('should have Edit menu', () => {
      expect(mainJsContent).toContain("label: 'Edit'");
    });

    it('should have View menu', () => {
      expect(mainJsContent).toContain("label: 'View'");
    });

    it('should have Window menu', () => {
      expect(mainJsContent).toContain("label: 'Window'");
    });

    it('should have Help menu', () => {
      expect(mainJsContent).toContain("label: 'Help'");
    });

    it('should have external links in Help menu', () => {
      expect(mainJsContent).toContain('zkillboard.com');
      expect(mainJsContent).toContain('github.com/AreteDriver/EVE_Gatekeeper');
    });
  });
});
