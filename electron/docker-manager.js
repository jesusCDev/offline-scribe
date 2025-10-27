const { spawn, exec } = require('child_process');
const { promisify } = require('util');
const http = require('http');
const net = require('net');
const path = require('path');
const fs = require('fs');

const execAsync = promisify(exec);

// Constants
const IMAGE_NAME = 'silent-scribe:latest';
const CONTAINER_NAME = 'silent-scribe-electron';
const INTERNAL_PORT = 7860;
const DEFAULT_HOST_PORT = 7860;

/**
 * Check if Docker is installed
 * @returns {Promise<{installed: boolean, version?: string, error?: string}>}
 */
async function isDockerInstalled() {
  try {
    const { stdout } = await execAsync('docker --version');
    const version = stdout.trim();
    return { installed: true, version };
  } catch (error) {
    return { installed: false, error: error.message };
  }
}

/**
 * Check if Docker daemon is running
 * @returns {Promise<{running: boolean, info?: string, error?: string}>}
 */
async function isDockerRunning() {
  try {
    const { stdout } = await execAsync('docker info');
    return { running: true, info: stdout.trim() };
  } catch (error) {
    return { running: false, error: error.message };
  }
}

/**
 * Try to start Docker Desktop (macOS/Windows/Linux)
 * @returns {Promise<{success: boolean, message: string}>}
 */
async function tryStartDockerDesktop() {
  const platform = process.platform;
  
  if (platform === 'darwin') {
    // macOS
    try {
      await execAsync('open -a Docker');
      return { success: true, message: 'Docker Desktop launch initiated. Please wait 30-60 seconds.' };
    } catch (error) {
      return { success: false, message: 'Could not start Docker Desktop. Please open it manually from Applications.' };
    }
  } else if (platform === 'win32') {
    // Windows
    const dockerPaths = [
      'C:\\Program Files\\Docker\\Docker\\Docker Desktop.exe',
      'C:\\Program Files (x86)\\Docker\\Docker\\Docker Desktop.exe'
    ];
    
    for (const dockerPath of dockerPaths) {
      if (fs.existsSync(dockerPath)) {
        try {
          await execAsync(`start "" "${dockerPath}"`);
          return { success: true, message: 'Docker Desktop launch initiated. Please wait 30-60 seconds.' };
        } catch (error) {
          continue;
        }
      }
    }
    return { success: false, message: 'Could not find Docker Desktop. Please open it manually.' };
  } else {
    // Linux - try multiple methods
    try {
      // Method 1: Try systemctl --user (Docker Desktop for Linux)
      try {
        await execAsync('systemctl --user start docker-desktop');
        return { success: true, message: 'Docker Desktop is starting via systemctl. Please wait 30-60 seconds.' };
      } catch (userServiceError) {
        // Method 2: Try starting via desktop file
        try {
          await execAsync('gtk-launch docker-desktop 2>/dev/null || true');
          return { success: true, message: 'Docker Desktop launch initiated. Please wait 30-60 seconds.' };
        } catch (gtkError) {
          // Method 3: Try traditional docker service
          try {
            await execAsync('sudo systemctl start docker');
            return { success: true, message: 'Docker service started. Ready to use.' };
          } catch (dockerServiceError) {
            return { 
              success: false, 
              message: 'Could not auto-start Docker. Please start Docker Desktop from your app menu or run: systemctl --user start docker-desktop' 
            };
          }
        }
      }
    } catch (error) {
      return { 
        success: false, 
        message: 'Could not auto-start Docker. Please start Docker Desktop manually from your app menu.' 
      };
    }
  }
}

/**
 * Check if Docker image exists
 * @param {string} imageName - Image name (default: silent-scribe:latest)
 * @returns {Promise<{exists: boolean, error?: string}>}
 */
async function imageExists(imageName = IMAGE_NAME) {
  try {
    await execAsync(`docker image inspect ${imageName}`);
    return { exists: true };
  } catch (error) {
    return { exists: false, error: error.message };
  }
}

/**
 * Load Docker image from tar.gz bundle
 * @param {string} bundlePath - Path to the .tar.gz file
 * @param {function} progressCallback - Callback for progress updates (message: string, percent?: number)
 * @returns {Promise<{success: boolean, error?: string}>}
 */
async function loadImageFromBundle(bundlePath, progressCallback = () => {}) {
  return new Promise((resolve) => {
    if (!fs.existsSync(bundlePath)) {
      resolve({ success: false, error: `Bundle not found at: ${bundlePath}` });
      return;
    }

    progressCallback('Extracting and loading Docker image (this may take 10-20 minutes)...', 0);

    const dockerLoad = spawn('docker', ['load', '-i', bundlePath]);
    let output = '';
    let lastPercent = 0;

    dockerLoad.stdout.on('data', (data) => {
      const text = data.toString();
      output += text;
      
      // Parse progress from docker load output
      // Example: "Loading layer [==============>] 100 MB/500 MB"
      const match = text.match(/(\d+)%/);
      if (match) {
        const percent = parseInt(match[1], 10);
        if (percent > lastPercent) {
          lastPercent = percent;
          progressCallback(`Loading image: ${percent}%`, percent);
        }
      } else {
        progressCallback(text.trim());
      }
    });

    dockerLoad.stderr.on('data', (data) => {
      progressCallback(data.toString().trim());
    });

    dockerLoad.on('close', (code) => {
      if (code === 0) {
        progressCallback('Image loaded successfully!', 100);
        resolve({ success: true });
      } else {
        resolve({ success: false, error: `docker load failed with code ${code}: ${output}` });
      }
    });

    dockerLoad.on('error', (error) => {
      resolve({ success: false, error: error.message });
    });
  });
}

/**
 * Build Docker image from source
 * @param {string} dockerfilePath - Path to Dockerfile
 * @param {string} contextPath - Build context path
 * @param {string} tag - Image tag
 * @param {function} progressCallback - Progress callback
 * @returns {Promise<{success: boolean, error?: string}>}
 */
async function buildImageFromSource(dockerfilePath, contextPath, tag = IMAGE_NAME, progressCallback = () => {}) {
  return new Promise((resolve) => {
    progressCallback('Building Docker image from source (this may take 30-60 minutes)...', 0);

    const dockerBuild = spawn('docker', [
      'build',
      '-t', tag,
      '-f', dockerfilePath,
      contextPath
    ]);

    let output = '';
    let stepCount = 0;
    let totalSteps = 0;

    dockerBuild.stdout.on('data', (data) => {
      const text = data.toString();
      output += text;
      
      // Parse Dockerfile steps
      const stepMatch = text.match(/Step (\d+)\/(\d+)/);
      if (stepMatch) {
        stepCount = parseInt(stepMatch[1], 10);
        totalSteps = parseInt(stepMatch[2], 10);
        const percent = Math.floor((stepCount / totalSteps) * 100);
        progressCallback(`Build step ${stepCount}/${totalSteps}`, percent);
      } else {
        progressCallback(text.trim());
      }
    });

    dockerBuild.stderr.on('data', (data) => {
      progressCallback(data.toString().trim());
    });

    dockerBuild.on('close', (code) => {
      if (code === 0) {
        progressCallback('Build completed successfully!', 100);
        resolve({ success: true });
      } else {
        resolve({ success: false, error: `docker build failed with code ${code}` });
      }
    });

    dockerBuild.on('error', (error) => {
      resolve({ success: false, error: error.message });
    });
  });
}

/**
 * Get container state
 * @returns {Promise<{state: 'running'|'exited'|'missing', details?: string}>}
 */
async function getContainerState() {
  try {
    const { stdout } = await execAsync(`docker ps -a --filter "name=^/${CONTAINER_NAME}$" --format "{{.Status}}"`);
    const status = stdout.trim();
    
    if (!status) {
      return { state: 'missing' };
    } else if (status.startsWith('Up')) {
      return { state: 'running', details: status };
    } else {
      return { state: 'exited', details: status };
    }
  } catch (error) {
    return { state: 'missing', details: error.message };
  }
}

/**
 * Remove container (force)
 * @returns {Promise<{success: boolean, error?: string}>}
 */
async function removeContainer() {
  try {
    await execAsync(`docker rm -f ${CONTAINER_NAME}`);
    return { success: true };
  } catch (error) {
    // Container might not exist, that's okay
    return { success: true };
  }
}

/**
 * Find an available port starting from preferred port
 * @param {number} preferredPort - Preferred port number
 * @returns {Promise<number>} - Available port
 */
async function resolvePort(preferredPort = DEFAULT_HOST_PORT) {
  return new Promise((resolve) => {
    const testPort = (port) => {
      const server = net.createServer();
      
      server.once('error', (err) => {
        if (err.code === 'EADDRINUSE') {
          // Port is in use, try next one
          testPort(port + 1);
        } else {
          resolve(port);
        }
      });
      
      server.once('listening', () => {
        server.close(() => {
          resolve(port);
        });
      });
      
      server.listen(port);
    };
    
    testPort(preferredPort);
  });
}

/**
 * Start container
 * @param {object} options - Container options
 * @param {number} options.hostPort - Host port to bind
 * @param {string} options.dataPath - Path to data directory
 * @param {boolean} options.offlineMode - Enable air-gapped mode (default: true)
 * @returns {Promise<{success: boolean, port?: number, error?: string}>}
 */
async function startContainer(options = {}) {
  const { hostPort = DEFAULT_HOST_PORT, dataPath = null, offlineMode = true } = options;
  
  try {
    // Check current state
    const state = await getContainerState();
    
    if (state.state === 'running') {
      return { success: true, port: hostPort, message: 'Container already running' };
    }
    
    if (state.state === 'exited') {
      // Remove old container
      await removeContainer();
    }
    
    // Resolve available port
    const availablePort = await resolvePort(hostPort);
    
    // Prepare docker run command
    const args = [
      'run',
      '-d',  // Detached mode
      '--name', CONTAINER_NAME,
      '-p', `${availablePort}:${INTERNAL_PORT}`,
    ];
    
    // Add data volume if provided
    if (dataPath && fs.existsSync(dataPath)) {
      // Add :z for SELinux (Fedora/RHEL)
      const platform = process.platform;
      const volumeFlag = platform === 'linux' ? `${dataPath}:/data:z` : `${dataPath}:/data`;
      args.push('-v', volumeFlag);
    }
    
    // Add environment variables for offline/online mode
    if (offlineMode) {
      args.push('-e', 'HF_HUB_OFFLINE=1');
      args.push('-e', 'TRANSFORMERS_OFFLINE=1');
    } else {
      args.push('-e', 'HF_HUB_OFFLINE=0');
      args.push('-e', 'TRANSFORMERS_OFFLINE=0');
    }
    
    // Add image name
    args.push(IMAGE_NAME);
    
    // Start container
    const { stdout } = await execAsync(`docker ${args.join(' ')}`);
    
    return { success: true, port: availablePort, containerId: stdout.trim() };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * Stop container
 * @param {number} timeout - Timeout in seconds
 * @returns {Promise<{success: boolean, error?: string}>}
 */
async function stopContainer(timeout = 10) {
  try {
    await execAsync(`docker stop -t ${timeout} ${CONTAINER_NAME}`);
    await removeContainer();
    return { success: true };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

/**
 * Wait for HTTP endpoint to be ready
 * @param {string} url - URL to poll
 * @param {number} timeoutMs - Timeout in milliseconds
 * @param {number} intervalMs - Polling interval in milliseconds
 * @returns {Promise<{ready: boolean, error?: string}>}
 */
async function waitForHttpReady(url, timeoutMs = 120000, intervalMs = 1000) {
  const startTime = Date.now();
  
  return new Promise((resolve) => {
    const check = () => {
      // Parse URL
      const urlObj = new URL(url);
      const options = {
        hostname: urlObj.hostname,
        port: urlObj.port || 80,
        path: urlObj.pathname,
        method: 'GET',
        timeout: 5000
      };
      
      const req = http.request(options, (res) => {
        if (res.statusCode === 200 || res.statusCode === 302) {
          resolve({ ready: true });
        } else {
          retryOrTimeout();
        }
      });
      
      req.on('error', () => {
        retryOrTimeout();
      });
      
      req.on('timeout', () => {
        req.destroy();
        retryOrTimeout();
      });
      
      req.end();
    };
    
    const retryOrTimeout = () => {
      if (Date.now() - startTime > timeoutMs) {
        resolve({ ready: false, error: 'Timeout waiting for service to become ready' });
      } else {
        setTimeout(check, intervalMs);
      }
    };
    
    check();
  });
}

/**
 * Get container logs
 * @param {number} tail - Number of lines to tail
 * @returns {Promise<{logs: string, error?: string}>}
 */
async function getContainerLogs(tail = 100) {
  try {
    const { stdout } = await execAsync(`docker logs --tail ${tail} ${CONTAINER_NAME}`);
    return { logs: stdout };
  } catch (error) {
    return { logs: '', error: error.message };
  }
}

/**
 * Get Docker image version from labels
 * @param {string} imageName - Image name (default: silent-scribe:latest)
 * @returns {Promise<{version: string|null, buildDate: string|null, error?: string}>}
 */
async function getImageVersion(imageName = IMAGE_NAME) {
  try {
    const { stdout } = await execAsync(`docker image inspect ${imageName} --format '{{index .Config.Labels "org.opencontainers.image.version"}} {{index .Config.Labels "org.opencontainers.image.created"}}'`);
    const parts = stdout.trim().split(' ');
    return {
      version: parts[0] || null,
      buildDate: parts[1] || null
    };
  } catch (error) {
    return { version: null, buildDate: null, error: error.message };
  }
}

module.exports = {
  isDockerInstalled,
  isDockerRunning,
  tryStartDockerDesktop,
  imageExists,
  loadImageFromBundle,
  buildImageFromSource,
  getContainerState,
  startContainer,
  stopContainer,
  removeContainer,
  resolvePort,
  waitForHttpReady,
  getContainerLogs,
  getImageVersion,
  // Constants
  IMAGE_NAME,
  CONTAINER_NAME,
  INTERNAL_PORT,
  DEFAULT_HOST_PORT
};
