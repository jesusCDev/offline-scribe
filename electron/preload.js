const { contextBridge, ipcRenderer, shell } = require('electron');

/**
 * Expose safe API to renderer process via contextBridge
 * This ensures the renderer has no direct access to Node.js APIs
 */
contextBridge.exposeInMainWorld('electronAPI', {
  /**
   * Check Docker installation and status
   * @returns {Promise<{success: boolean, error?: string, details?: object}>}
   */
  checkDocker: () => ipcRenderer.invoke('docker:check'),

  /**
   * Try to start Docker Desktop
   * @returns {Promise<{success: boolean, message: string}>}
   */
  startDocker: () => ipcRenderer.invoke('docker:start'),

  /**
   * Check if Docker image exists
   * @returns {Promise<{exists: boolean, error?: string}>}
   */
  imageExists: () => ipcRenderer.invoke('image:exists'),

  /**
   * Check if image version matches expected version
   * @returns {Promise<{needsUpdate: boolean, reason: string, message: string, currentVersion?: string, expectedVersion?: string}>}
   */
  checkImageVersion: () => ipcRenderer.invoke('image:check-version'),

  /**
   * Load Docker image from bundled tar.gz
   * @returns {Promise<{success: boolean, error?: string}>}
   */
  loadImage: () => ipcRenderer.invoke('image:load'),

  /**
   * Build Docker image from source
   * @returns {Promise<{success: boolean, error?: string}>}
   */
  buildImage: () => ipcRenderer.invoke('image:build'),

  /**
   * Start the Docker container
   * @returns {Promise<{success: boolean, port?: number, url?: string, error?: string}>}
   */
  startContainer: () => ipcRenderer.invoke('container:start'),

  /**
   * Stop the Docker container
   * @returns {Promise<{success: boolean, error?: string}>}
   */
  stopContainer: () => ipcRenderer.invoke('container:stop'),

  /**
   * Get container state
   * @returns {Promise<{state: string, details?: string, error?: string}>}
   */
  getContainerState: () => ipcRenderer.invoke('container:state'),

  /**
   * Open the main application window
   * @returns {Promise<{success: boolean, error?: string}>}
   */
  openMainWindow: () => ipcRenderer.invoke('window:open-main'),

  /**
   * Get system information
   * @returns {Promise<{platform: string, arch: string, isDevelopment: boolean, bundlePath: string, dataPath: string}>}
   */
  getSystemInfo: () => ipcRenderer.invoke('system:info'),

  /**
   * Get offline mode setting
   * @returns {Promise<{offlineMode: boolean}>}
   */
  getOfflineMode: () => ipcRenderer.invoke('settings:getOfflineMode'),

  /**
   * Set offline mode setting (will restart container if running)
   * @param {boolean} offlineMode - Enable/disable offline mode
   * @returns {Promise<{success: boolean, offlineMode?: boolean, error?: string}>}
   */
  setOfflineMode: (offlineMode) => ipcRenderer.invoke('settings:setOfflineMode', offlineMode),

  /**
   * Get log file path and directory
   * @returns {Promise<{logFile: string, logDir: string}>}
   */
  getLogPath: () => ipcRenderer.invoke('logs:getPath'),

  /**
   * Get recent log entries
   * @param {number} lines - Number of recent lines to retrieve (default: 100)
   * @returns {Promise<Array<object>>}
   */
  getRecentLogs: (lines) => ipcRenderer.invoke('logs:getRecent', lines),

  /**
   * Open a path in the system file explorer
   * @param {string} path - Path to open
   * @returns {Promise<string>} - Error string if failed
   */
  openPath: (path) => shell.openPath(path),

  /**
   * Subscribe to status updates from main process
   * @param {function} callback - Callback function to receive status updates
   * @returns {function} - Unsubscribe function
   */
  onStatus: (callback) => {
    const subscription = (event, payload) => callback(payload);
    ipcRenderer.on('status:update', subscription);
    
    // Return unsubscribe function
    return () => {
      ipcRenderer.removeListener('status:update', subscription);
    };
  }
});

// Log preload script loaded
console.log('Preload script loaded successfully');
