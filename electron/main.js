const { app, BrowserWindow, ipcMain, shell } = require('electron');
const path = require('path');
const fs = require('fs');
const dockerManager = require('./docker-manager');
const logger = require('./logger');

// Global state
let splashWindow = null;
let mainWindow = null;
let currentPort = null;
let isQuitting = false;
let settings = { offlineMode: true }; // Default to air-gapped mode

// Determine if running in development mode
const isDevelopment = process.env.NODE_ENV === 'development';

/**
 * Single instance lock - prevent multiple instances
 */
const gotTheLock = app.requestSingleInstanceLock();

if (!gotTheLock) {
  console.log('Another instance is already running. Exiting...');
  app.quit();
} else {
  app.on('second-instance', () => {
    // Someone tried to run a second instance, focus our window
    if (splashWindow) {
      if (splashWindow.isMinimized()) splashWindow.restore();
      splashWindow.focus();
    } else if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });
}

/**
 * Create the splash/loading window
 */
function createSplashWindow() {
  splashWindow = new BrowserWindow({
    width: 600,
    height: 500,
    resizable: false,
    frame: true,
    show: false,
    webPreferences: {
      contextIsolation: true,
      sandbox: true,
      nodeIntegration: false,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  splashWindow.loadFile(path.join(__dirname, 'splash.html'));

  splashWindow.once('ready-to-show', () => {
    splashWindow.show();
  });

  splashWindow.on('closed', () => {
    splashWindow = null;
  });

  // Open external links in browser
  splashWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  return splashWindow;
}

/**
 * Create the main application window
 */
function createMainWindow(port) {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    show: false,
    webPreferences: {
      contextIsolation: true,
      sandbox: true,
      nodeIntegration: false
    }
  });

  const appUrl = `http://localhost:${port}`;
  mainWindow.loadURL(appUrl);

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Open external links in browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (!url.startsWith('http://localhost')) {
      shell.openExternal(url);
      return { action: 'deny' };
    }
    return { action: 'allow' };
  });

  return mainWindow;
}

/**
 * Send status update to splash window
 */
function sendStatus(stage, message, progress = null, error = null) {
  if (splashWindow && !splashWindow.isDestroyed()) {
    splashWindow.webContents.send('status:update', {
      stage,
      message,
      progress,
      error,
      timestamp: Date.now()
    });
  }
}

/**
 * Get bundle path (dev vs packaged)
 */
function getBundlePath() {
  if (isDevelopment || !app.isPackaged) {
    // Development: look in project root
    return path.resolve(process.cwd(), 'resources', 'silent-scribe.tar.gz');
  } else {
    // Packaged: look in app resources
    return path.join(process.resourcesPath, 'resources', 'silent-scribe.tar.gz');
  }
}

/**
 * Get data directory path
 */
function getDataPath() {
  if (isDevelopment || !app.isPackaged) {
    // Development: use project data directory
    return path.resolve(process.cwd(), 'data');
  } else {
    // Packaged: use user data directory
    return path.join(app.getPath('userData'), 'data');
  }
}

/**
 * Get settings file path
 */
function getSettingsPath() {
  return path.join(app.getPath('userData'), 'settings.json');
}

/**
 * Load settings from file
 */
function loadSettings() {
  try {
    const settingsPath = getSettingsPath();
    if (fs.existsSync(settingsPath)) {
      const data = fs.readFileSync(settingsPath, 'utf8');
      settings = { ...settings, ...JSON.parse(data) };
    }
  } catch (error) {
    console.error('Failed to load settings:', error);
  }
}

/**
 * Save settings to file
 */
function saveSettings() {
  try {
    const settingsPath = getSettingsPath();
    fs.writeFileSync(settingsPath, JSON.stringify(settings, null, 2), 'utf8');
  } catch (error) {
    console.error('Failed to save settings:', error);
  }
}

// ============================================================================
// IPC Handlers
// ============================================================================

/**
 * Check Docker installation and status
 */
ipcMain.handle('docker:check', async () => {
  try {
    logger.info('Checking Docker installation');
    const installed = await dockerManager.isDockerInstalled();
    if (!installed.installed) {
      logger.warn('Docker not installed', installed);
      return { success: false, error: 'Docker is not installed', details: installed };
    }

    const running = await dockerManager.isDockerRunning();
    if (!running.running) {
      logger.warn('Docker not running', running);
      return { success: false, error: 'Docker is not running', details: running };
    }

    logger.info('Docker check successful');
    return { success: true, details: { installed, running } };
  } catch (error) {
    logger.error('Docker check failed', { error: error.message });
    return { success: false, error: error.message };
  }
});

/**
 * Try to start Docker Desktop
 */
ipcMain.handle('docker:start', async () => {
  try {
    return await dockerManager.tryStartDockerDesktop();
  } catch (error) {
    return { success: false, message: error.message };
  }
});

/**
 * Check if image exists
 */
ipcMain.handle('image:exists', async () => {
  try {
    const result = await dockerManager.imageExists();
    return result;
  } catch (error) {
    return { exists: false, error: error.message };
  }
});

/**
 * Check image version and compare with expected version
 */
ipcMain.handle('image:check-version', async () => {
  try {
    const imageCheck = await dockerManager.imageExists();
    if (!imageCheck.exists) {
      return { needsUpdate: false, reason: 'no-image', message: 'Image not found' };
    }

    // Get current image version
    const currentVersion = await dockerManager.getImageVersion();
    
    // Load expected version from manifest
    const manifestPath = path.join(__dirname, 'image-version.json');
    const manifest = JSON.parse(require('fs').readFileSync(manifestPath, 'utf8'));
    const expectedVersion = manifest.expectedVersion;

    if (!currentVersion.version) {
      // Image has no version label (old image)
      return {
        needsUpdate: true,
        reason: 'no-version-label',
        message: 'Current image does not have version metadata. Please load the new image.',
        currentVersion: 'unknown',
        expectedVersion,
        updateInstructions: manifest.updateInstructions
      };
    }

    if (currentVersion.version !== expectedVersion) {
      return {
        needsUpdate: true,
        reason: 'version-mismatch',
        message: `Image version mismatch. Current: ${currentVersion.version}, Expected: ${expectedVersion}`,
        currentVersion: currentVersion.version,
        expectedVersion,
        buildDate: currentVersion.buildDate,
        updateInstructions: manifest.updateInstructions
      };
    }

    return {
      needsUpdate: false,
      reason: 'up-to-date',
      message: 'Image is up to date',
      currentVersion: currentVersion.version,
      expectedVersion,
      buildDate: currentVersion.buildDate
    };
  } catch (error) {
    return { needsUpdate: false, reason: 'error', error: error.message };
  }
});

/**
 * Load image from bundle
 */
ipcMain.handle('image:load', async () => {
  try {
    const bundlePath = getBundlePath();
    const fs = require('fs');
    
    // Check if bundle exists
    if (!fs.existsSync(bundlePath)) {
      return {
        success: false,
        error: `Bundled image not found at: ${bundlePath}. Please use "Build from Source" option or ensure the image bundle is included.`
      };
    }
    
    sendStatus('loading-image', `Loading image from ${path.basename(bundlePath)}...`, 0);
    
    const result = await dockerManager.loadImageFromBundle(
      bundlePath,
      (message, progress) => {
        sendStatus('loading-image', message, progress);
      }
    );
    
    return result;
  } catch (error) {
    return { success: false, error: error.message };
  }
});

/**
 * Build image from source
 */
ipcMain.handle('image:build', async () => {
  try {
    const dockerfilePath = path.resolve(process.cwd(), 'docker', 'Dockerfile');
    const contextPath = process.cwd();
    
    sendStatus('building-image', 'Building Docker image from source...', 0);
    
    const result = await dockerManager.buildImageFromSource(
      dockerfilePath,
      contextPath,
      dockerManager.IMAGE_NAME,
      (message, progress) => {
        sendStatus('building-image', message, progress);
      }
    );
    
    return result;
  } catch (error) {
    return { success: false, error: error.message };
  }
});

/**
 * Start container
 */
ipcMain.handle('container:start', async () => {
  try {
    logger.info('Starting container', { offlineMode: settings.offlineMode });
    sendStatus('starting-container', 'Starting container...', 0);
    
    const dataPath = getDataPath();
    const result = await dockerManager.startContainer({
      hostPort: dockerManager.DEFAULT_HOST_PORT,
      dataPath,
      offlineMode: settings.offlineMode
    });
    logger.docker('start container', result, { port: result.port });
    
    if (!result.success) {
      return result;
    }
    
    currentPort = result.port;
    
    // Wait for HTTP to be ready
    sendStatus('waiting-ready', `Waiting for service on port ${currentPort}...`, 50);
    
    const appUrl = `http://localhost:${currentPort}`;
    const ready = await dockerManager.waitForHttpReady(appUrl, 120000, 1000);
    
    if (!ready.ready) {
      return { success: false, error: 'Service did not become ready in time' };
    }
    
    sendStatus('ready', `Service ready on port ${currentPort}`, 100);
    
    return { success: true, port: currentPort, url: appUrl };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

/**
 * Stop container
 */
ipcMain.handle('container:stop', async () => {
  try {
    return await dockerManager.stopContainer();
  } catch (error) {
    return { success: false, error: error.message };
  }
});

/**
 * Get container state
 */
ipcMain.handle('container:state', async () => {
  try {
    return await dockerManager.getContainerState();
  } catch (error) {
    return { state: 'unknown', error: error.message };
  }
});

/**
 * Open main window
 */
ipcMain.handle('window:open-main', async () => {
  try {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.focus();
      return { success: true };
    }
    
    if (!currentPort) {
      return { success: false, error: 'No port available' };
    }
    
    createMainWindow(currentPort);
    return { success: true };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

/**
 * Get system info
 */
ipcMain.handle('system:info', async () => {
  return {
    platform: process.platform,
    arch: process.arch,
    isDevelopment,
    bundlePath: getBundlePath(),
    dataPath: getDataPath()
  };
});

/**
 * Get offline mode setting
 */
ipcMain.handle('settings:getOfflineMode', async () => {
  return { offlineMode: settings.offlineMode };
});

/**
 * Get log file path
 */
ipcMain.handle('logs:getPath', async () => {
  return {
    logFile: logger.getLogPath(),
    logDir: logger.getLogDir()
  };
});

/**
 * Get recent logs
 */
ipcMain.handle('logs:getRecent', async (event, lines = 100) => {
  return logger.readRecentLogs(lines);
});

/**
 * Set offline mode setting and restart container
 */
ipcMain.handle('settings:setOfflineMode', async (event, offlineMode) => {
  try {
    logger.info('Offline mode changed', { from: settings.offlineMode, to: offlineMode });
    settings.offlineMode = offlineMode;
    saveSettings();
    
    // Check if container is running
    const state = await dockerManager.getContainerState();
    
    if (state.state === 'running') {
      // Stop current container
      sendStatus('restarting', 'Restarting container with new settings...', 0);
      await dockerManager.stopContainer();
      
      // Start with new settings
      const dataPath = getDataPath();
      const result = await dockerManager.startContainer({
        hostPort: dockerManager.DEFAULT_HOST_PORT,
        dataPath,
        offlineMode: settings.offlineMode
      });
      
      if (!result.success) {
        return { success: false, error: result.error };
      }
      
      currentPort = result.port;
      
      // Wait for HTTP to be ready
      const appUrl = `http://localhost:${currentPort}`;
      const ready = await dockerManager.waitForHttpReady(appUrl, 120000, 1000);
      
      if (!ready.ready) {
        return { success: false, error: 'Service did not become ready after restart' };
      }
      
      sendStatus('ready', 'Container restarted successfully', 100);
    }
    
    return { success: true, offlineMode: settings.offlineMode };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

// ============================================================================
// App Lifecycle
// ============================================================================

/**
 * App ready - create splash window
 */
app.whenReady().then(() => {
  logger.init();
  logger.info('Silent Scribe starting', {
    version: app.getVersion(),
    platform: process.platform,
    arch: process.arch,
    isPackaged: app.isPackaged
  });
  
  loadSettings();
  logger.info('Settings loaded', settings);
  
  createSplashWindow();
});

/**
 * All windows closed
 */
app.on('window-all-closed', () => {
  // On macOS, keep app running until user explicitly quits
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

/**
 * App activated (macOS)
 */
app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createSplashWindow();
  }
});

/**
 * Before quit - cleanup
 */
app.on('before-quit', () => {
  isQuitting = true;
  logger.info('Application quitting');
});

/**
 * Handle uncaught exceptions
 */
process.on('uncaughtException', (error) => {
  console.error('Uncaught exception:', error);
  sendStatus('error', `Unexpected error: ${error.message}`, null, error.message);
});

/**
 * Handle unhandled promise rejections
 */
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled rejection at:', promise, 'reason:', reason);
});

console.log(`
=============================================
Silent Scribe Electron App
=============================================
Platform: ${process.platform}
Architecture: ${process.arch}
Development: ${isDevelopment}
App Path: ${app.getAppPath()}
User Data: ${app.getPath('userData')}
Bundle Path: ${getBundlePath()}
Data Path: ${getDataPath()}
=============================================
`);
